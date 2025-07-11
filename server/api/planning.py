"""
FastAPI endpoints for experiment planning with human-in-the-loop support.

This module provides WebSocket-based bidirectional communication for real-time
planning sessions with user approval mechanisms and state management.
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import MemorySaver
from starlette.websockets import WebSocketState

from agents.planning.graph.graph_builder import (
    create_planning_graph,
)
from agents.planning.state import ExperimentPlanState, PLANNING_STAGES
from agents.planning.debug import StateDebugger, get_global_debugger
from agents.planning.validation import StateValidationError
from agents.planning.serialization import (
    serialize_state_to_dict,
    deserialize_dict_to_state
)
from agents.planning.factory import create_new_experiment_state, add_chat_message
from config import validate_openai_config
from agents.planning.graph.helpers import extract_user_intent, determine_section_to_edit
from agents.planning.transitions import transition_to_stage

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/planning", tags=["planning-websocket"])

# Global instances
_global_debugger = get_global_debugger()
_active_graphs: Dict[str, Dict[str, Any]] = {}
_active_connections: Dict[str, WebSocket] = {}


# WebSocket Message Models
class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: str = Field(..., description="Session identifier")


class UserMessage(BaseModel):
    """User message from frontend."""
    type: str = Field(default="user_message")
    data: Dict[str, str] = Field(..., description="Contains 'content' field")
    session_id: str


class PlanningUpdate(BaseModel):
    """Planning progress update to frontend."""
    type: str = Field(default="planning_update")
    data: Dict[str, Any] = Field(..., description="Planning state data")
    session_id: str


class ApprovalRequest(BaseModel):
    """Approval request to frontend."""
    type: str = Field(default="approval_request")
    data: Dict[str, Any] = Field(..., description="Approval details")
    session_id: str


class ApprovalResponse(BaseModel):
    """Approval response from frontend."""
    type: str = Field(default="approval_response")
    data: Dict[str, Any] = Field(..., description="Contains 'approved' and optional 'feedback'")
    session_id: str


class ErrorMessage(BaseModel):
    """Error message to frontend."""
    type: str = Field(default="error")
    data: Dict[str, str] = Field(..., description="Contains 'message' field")
    session_id: str


class SessionStatusMessage(BaseModel):
    """Session status message."""
    type: str = Field(default="session_status")
    data: Dict[str, Any] = Field(..., description="Session status data")
    session_id: str


class SessionCompleteMessage(BaseModel):
    """Session completion message."""
    type: str = Field(default="session_complete")
    data: Dict[str, Any] = Field(..., description="Completion details and summary")
    session_id: str


# Request/Response Models (keeping existing ones for non-WebSocket endpoints)
class StartHITLPlanningRequest(BaseModel):
    """Request model for starting a new HITL planning session."""
    research_query: str = Field(..., description="Initial research query or idea")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID")
    user_id: Optional[str] = Field("demo-user", description="User ID for session tracking")


class HITLSessionResponse(BaseModel):
    """Response model for HITL session info."""
    session_id: str = Field(..., description="Session identifier")
    experiment_id: str = Field(..., description="Experiment identifier")
    current_stage: str = Field(..., description="Current planning stage")
    is_waiting_for_approval: bool = Field(..., description="Whether waiting for user approval")
    pending_approval: Optional[Dict[str, Any]] = Field(None, description="Pending approval details")
    streaming_enabled: bool = Field(..., description="Whether streaming is enabled")
    checkpoint_available: bool = Field(..., description="Whether checkpoint is available")


# Utility Functions
def _get_or_create_graph_components(session_id: str) -> Dict[str, Any]:
    """Get or create graph components for a session."""
    if session_id not in _active_graphs:
        # Use an in-memory checkpointer for each session
        logger.info(f"Using MemorySaver for session {session_id}")
        checkpointer = MemorySaver()
        
        # Create graph
        graph = create_planning_graph(
            debugger=_global_debugger,
            checkpointer=checkpointer
        )
        
        _active_graphs[session_id] = {
            "graph": graph,
            "checkpointer": checkpointer,
            "config": {"configurable": {"thread_id": session_id}}
        }
    
    return _active_graphs[session_id]


async def _get_current_state(session_id: str) -> Optional[ExperimentPlanState]:
    """Get current state for a session asynchronously."""
    graph_components = _get_or_create_graph_components(session_id)
    graph = graph_components["graph"]
    config = graph_components["config"]
    
    try:
        state_snapshot = await graph.aget_state(config)
        return state_snapshot.values if state_snapshot else None
    except Exception as e:
        logger.error(f"Failed to get state for session {session_id}: {e}")
        return None


def _is_waiting_for_approval(state: Optional[ExperimentPlanState]) -> bool:
    """Check if the session is waiting for user approval."""
    if not state:
        return False
    
    # With the new system, we don't use pending_approval in state
    # Instead, we check if the graph is interrupted before an agent node
    # This will be handled by checking the graph state snapshot
    return False


async def _is_graph_interrupted(session_id: str) -> bool:
    """Check if the graph is currently interrupted (waiting for user input)."""
    try:
        graph_components = _get_or_create_graph_components(session_id)
        graph = graph_components["graph"]
        config = graph_components["config"]
        
        state_snapshot = await graph.aget_state(config)
        
        # Check if we're interrupted before any agent node
        if state_snapshot and state_snapshot.next:
            next_nodes = [str(node) for node in state_snapshot.next]
            # These are the nodes we interrupt before
            interrupt_nodes = ["variable_agent", "design_agent", "methodology_agent", "data_agent", "review_agent"]
            return any(node in interrupt_nodes for node in next_nodes)
        
        return False
    except Exception as e:
        logger.error(f"Failed to check graph interrupt status: {e}")
        return False


async def _get_current_stage_from_graph(session_id: str) -> Optional[str]:
    """Get the current stage from the graph state."""
    try:
        graph_components = _get_or_create_graph_components(session_id)
        graph = graph_components["graph"]
        config = graph_components["config"]
        
        state_snapshot = await graph.aget_state(config)
        
        if state_snapshot and state_snapshot.next:
            next_nodes = [str(node) for node in state_snapshot.next]
            # Map agent nodes to stage names
            node_to_stage = {
                "objective_agent": "objective_setting",
                "variable_agent": "variable_identification",
                "design_agent": "experimental_design",
                "methodology_agent": "methodology_protocol",
                "data_agent": "data_planning",
                "review_agent": "final_review"
            }
            
            for node in next_nodes:
                if node in node_to_stage:
                    return node_to_stage[node]
        
        return None
    except Exception as e:
        logger.error(f"Failed to get current stage from graph: {e}")
        return None


async def _is_graph_complete(session_id: str) -> bool:
    """Check if the graph has reached completion (END state)."""
    try:
        graph_components = _get_or_create_graph_components(session_id)
        graph = graph_components["graph"]
        config = graph_components["config"]
        
        state_snapshot = await graph.aget_state(config)
        
        # Import the helper function
        from agents.planning.graph.helpers import is_graph_complete
        
        return is_graph_complete(state_snapshot)
        
    except Exception as e:
        logger.error(f"Failed to check graph completion status: {e}")
        return False


async def _send_completion_message(websocket: WebSocket, session_id: str, final_state: ExperimentPlanState):
    """Send completion message and close the session gracefully."""
    try:
        # Create a comprehensive completion message
        completion_data = {
            "session_id": session_id,
            "experiment_id": final_state.get("experiment_id"),
            "status": "completed",
            "message": "🎉 Experiment planning completed successfully! Your comprehensive plan is ready.",
            "summary": {
                "stages_completed": len(PLANNING_STAGES),
                "total_messages": len(final_state.get("chat_history", [])),
                "experiment_objective": final_state.get("experiment_objective"),
                "completion_time": datetime.utcnow().isoformat()
            }
        }
        
        await _send_websocket_message(websocket, {
            "type": "session_complete",
            "data": completion_data,
            "session_id": session_id
        })
        
        # Send final state update
        await _send_planning_update(websocket, session_id, final_state)
        
        logger.info(f"✅ Session {session_id} completed successfully")
        
        # Clean up session resources after a brief delay
        import asyncio
        await asyncio.sleep(1)  # Give frontend time to process the completion message
        
        # Remove from active graphs and connections
        if session_id in _active_graphs:
            del _active_graphs[session_id]
        if session_id in _active_connections:
            del _active_connections[session_id]
            
        # Close the WebSocket connection gracefully
        await websocket.close(code=1000, reason="Session completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to send completion message: {e}")


# API Endpoints
@router.post("/start", response_model=HITLSessionResponse)
async def start_hitl_planning_session(request: StartHITLPlanningRequest):
    """
    Start a new HITL planning session and runs until the first approval interrupt.
    """
    try:
        if not validate_openai_config():
            raise HTTPException(
                status_code=500,
                detail="OpenAI configuration is invalid. Please check your API key."
            )
        
        session_id = str(uuid.uuid4())
        
        graph_components = _get_or_create_graph_components(session_id)
        graph = graph_components["graph"]
        config = graph_components["config"]
        
        initial_state = create_new_experiment_state(
            research_query=request.research_query,
            experiment_id=request.experiment_id
        )
        
        # Run the graph until it hits an interrupt (before an agent node)
        current_state = initial_state
        async for event in graph.astream(initial_state, config, stream_mode="values"):
            # Only process non-None events
            if event is not None:
                current_state = event
        
        # Ensure current_state is not None
        if current_state is None:
            logger.warning("current_state is None, using initial_state as fallback")
            current_state = initial_state
        
        # Check if we're interrupted before an agent node
        is_interrupted = await _is_graph_interrupted(session_id)
        current_stage = await _get_current_stage_from_graph(session_id)
        
        logger.info(f"Started HITL planning session {session_id}, interrupted: {is_interrupted}, stage: {current_stage}")
        
        return HITLSessionResponse(
            session_id=session_id,
            experiment_id=current_state["experiment_id"],
            current_stage=current_stage or current_state.get("current_stage", "objective_setting"),
            is_waiting_for_approval=is_interrupted,
            pending_approval={"stage": current_stage, "status": "waiting"} if is_interrupted else None,
            streaming_enabled=True,
            checkpoint_available=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start HITL planning session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start planning session: {str(e)}")


# WebSocket endpoint for bidirectional communication
@router.websocket("/ws/{session_id}")
async def websocket_planning_session(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time bidirectional planning communication.
    Handles user messages, planning updates, and approval workflows.
    """
    await websocket.accept()
    _active_connections[session_id] = websocket
    
    logger.info(f"WebSocket connection established for session {session_id}")
    
    try:
        # Send initial session status
        await _send_session_status(websocket, session_id)
        
        # Send initial state if session exists
        current_state = await _get_current_state(session_id)
        if current_state:
            await _send_planning_update(websocket, session_id, current_state)
            
            # Check if session is already complete
            is_complete = await _is_graph_complete(session_id)
            if is_complete:
                logger.info(f"Session {session_id} is already complete")
                await _send_completion_message(websocket, session_id, current_state)
                return
            
            # If graph is interrupted, send approval request
            is_interrupted = await _is_graph_interrupted(session_id)
            if is_interrupted:
                current_stage = await _get_current_stage_from_graph(session_id)
                await _send_approval_request(websocket, session_id, {"stage": current_stage, "status": "waiting"})
        
        # Listen for messages from frontend
        while True:
            try:
                # Receive message from frontend
                message_data = await websocket.receive_text()
                message = json.loads(message_data)
                
                logger.info(f"Received WebSocket message: {message}")
                
                # Route message based on type
                if message.get("type") == "user_message":
                    await _handle_user_message(websocket, session_id, message)
                elif message.get("type") == "approval_response":
                    await _handle_approval_response(websocket, session_id, message)
                elif message.get("type") == "ping":
                    await _send_websocket_message(websocket, {
                        "type": "pong",
                        "data": {"timestamp": datetime.utcnow().isoformat()},
                        "session_id": session_id
                    })
                elif message.get("type") == "close_session":
                    # Handle explicit session closure request from frontend
                    logger.info(f"Received close_session request for {session_id}")
                    await _send_websocket_message(websocket, {
                        "type": "session_closed",
                        "data": {"message": "Session closed by user request"},
                        "session_id": session_id
                    })
                    break
                else:
                    logger.warning(f"Unknown message type: {message.get('type')}")
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                await _send_error_message(websocket, session_id, "Invalid JSON format")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")

                # If the connection has already been closed on either side
                # we should exit the loop and clean-up instead of logging
                # the same error repeatedly.
                if (
                    websocket.application_state != WebSocketState.CONNECTED
                    or websocket.client_state != WebSocketState.CONNECTED
                ):
                    logger.info(
                        "WebSocket no longer connected; ending session loop to avoid log spam."
                    )
                    break

                # Attempt to relay the error to the client (will be silently
                # skipped if the socket is indeed closed).
                await _send_error_message(
                    websocket, session_id, f"Error processing message: {str(e)}"
                )
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        # Clean up connection
        if session_id in _active_connections:
            del _active_connections[session_id]
        logger.info(f"Cleaned up WebSocket connection for session {session_id}")


# WebSocket helper functions
async def _send_websocket_message(websocket: WebSocket, message: Dict[str, Any]):
    """Safely send a message via WebSocket.

    This helper now checks the application/client connection state before
    attempting to send.  If the socket is already closed (for instance, when
    the user refreshes the page or the session ends) we silently skip the
    send to avoid noisy runtime errors like:

        RuntimeError: WebSocket is not connected. Need to call "accept" first.

    or

        RuntimeError: Cannot call "send" once a close message has been sent.

    Any failure to send is therefore downgraded to a warning so the planning
    graph can continue/terminate gracefully without spamming the logs.
    """

    try:
        # Only attempt to send if the socket is still connected on both sides.
        if (
            websocket.application_state == WebSocketState.CONNECTED
            and websocket.client_state == WebSocketState.CONNECTED
        ):
            await websocket.send_text(json.dumps(message))
        else:
            # Socket has already been closed – skip sending to prevent errors.
            logger.debug("WebSocket not connected, skipping send.")
    except RuntimeError as exc:
        # Typical Starlette error once a close frame has been sent.
        logger.warning(f"WebSocket send failed – connection already closed: {exc}")
    except Exception as exc:
        logger.error(f"Failed to send WebSocket message: {exc}")


async def _send_session_status(websocket: WebSocket, session_id: str):
    """Send session status to frontend."""
    try:
        current_state = await _get_current_state(session_id)
        is_interrupted = await _is_graph_interrupted(session_id) if current_state else False
        current_stage = await _get_current_stage_from_graph(session_id) if current_state else None
        
        status_data = {
            "session_id": session_id,
            "is_active": current_state is not None,
            "current_stage": current_stage or (current_state.get("current_stage") if current_state else None),
            "is_waiting_for_approval": is_interrupted
        }
        
        await _send_websocket_message(websocket, {
            "type": "session_status",
            "data": status_data,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Failed to send session status: {e}")


async def _send_planning_update(websocket: WebSocket, session_id: str, state: ExperimentPlanState):
    """Send planning state update to frontend."""
    try:
        serialized_state = serialize_state_to_dict(state)
        await _send_websocket_message(websocket, {
            "type": "planning_update",
            "data": {"state": serialized_state},
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Failed to send planning update: {e}")


async def _send_approval_request(websocket: WebSocket, session_id: str, approval_data: Dict[str, Any]):
    """Send approval request to frontend."""
    try:
        await _send_websocket_message(websocket, {
            "type": "approval_request",
            "data": approval_data,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Failed to send approval request: {e}")


async def _send_error_message(websocket: WebSocket, session_id: str, error_message: str):
    """Send error message to frontend."""
    try:
        await _send_websocket_message(websocket, {
            "type": "error",
            "data": {"message": error_message},
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


async def _handle_user_message(websocket: WebSocket, session_id: str, message: Dict[str, Any]):
    """Handle user message from frontend."""
    try:
        user_input = message.get("data", {}).get("content", "")
        if not user_input:
            await _send_error_message(websocket, session_id, "Empty user message")
            return
            
        logger.info(f"Processing user message for session {session_id}: {user_input}")
        
        graph_components = _get_or_create_graph_components(session_id)
        graph = graph_components["graph"]
        config = graph_components["config"]

        # Get current state
        current_state = await _get_current_state(session_id)
        if not current_state:
            await _send_error_message(websocket, session_id, "Session not found")
            return

        # ------------------------------------------------------------
        # NEW: Handle messages received while graph is interrupted
        # ------------------------------------------------------------

        is_interrupted = await _is_graph_interrupted(session_id)

        if is_interrupted:
            # Decide whether this looks like approval or an edit request
            intent = extract_user_intent(user_input)

            if intent == "approval":
                # Re-route as an approval_response = True so normal flow continues
                await _handle_approval_response(
                    websocket,
                    session_id,
                    {
                        "type": "approval_response",
                        "data": {"approved": True, "feedback": ""},
                        "session_id": session_id,
                    },
                )
                return  # handled

            elif intent == "edit":
                # IMPROVED: Process edit request directly with user's actual input
                target_section = determine_section_to_edit(user_input, current_state)
                
                # STORE CURRENT STAGE FOR RETURN NAVIGATION
                original_stage = await _get_current_stage_from_graph(session_id)
                if not original_stage:
                    original_stage = current_state.get("current_stage", "objective_setting")
                
                logger.info(f"[EDIT] User at {original_stage}, routing edit to {target_section}")
                
                # Transition to target section
                routed_state = transition_to_stage(current_state.copy(), target_section, force=True)
                
                # STORE THE RETURN STAGE IN STATE
                routed_state["return_to_stage"] = original_stage
                
                # Add the user's actual edit request to chat history (not a generic message)
                routed_state = add_chat_message(routed_state, "user", user_input)
                
                # Add system message explaining the transition
                routed_state = add_chat_message(
                    routed_state,
                    "system",
                    f"Processing your edit request for the {target_section.replace('_', ' ')} section. "
                    f"After this edit, we'll return to the {original_stage.replace('_', ' ')} stage."
                )

                await graph.aupdate_state(config, routed_state)

                # Process the edit request immediately with the user's input
                await _process_planning_execution(
                    websocket, session_id, routed_state, graph, config
                )
                return  # exit original handler
            
            else:
                # Intent is unclear - ask for clarification
                await _send_websocket_message(websocket, {
                    "type": "planning_update",
                    "data": {
                        "state": serialize_state_to_dict(current_state),
                        "clarification_needed": True
                    },
                    "session_id": session_id
                })
                
                clarification_message = add_chat_message(
                    current_state,
                    "assistant",
                    "I'm not sure if you'd like to approve this section or make changes. "
                    "Please either say 'approve' to continue, or clearly specify what you'd like to modify."
                )
                
                await graph.aupdate_state(config, clarification_message)
                await _send_planning_update(websocket, session_id, clarification_message)
                return

        # ------------------------------------------------------------
        # Normal (non-interrupted) flow
        # ------------------------------------------------------------

        updated_state = add_chat_message(current_state, "user", user_input)
        await graph.aupdate_state(config, updated_state)

        # Process the message and stream updates
        await _process_planning_execution(websocket, session_id, updated_state, graph, config)
        
    except Exception as e:
        logger.error(f"Error handling user message: {e}")
        await _send_error_message(websocket, session_id, f"Error processing message: {str(e)}")


async def _handle_approval_response(websocket: WebSocket, session_id: str, message: Dict[str, Any]):
    """Handle approval response from frontend."""
    try:
        approval_data = message.get("data", {})
        approved = approval_data.get("approved", False)
        feedback = approval_data.get("feedback", "")
        
        logger.info(f"Processing approval response for session {session_id}: approved={approved}")
        
        graph_components = _get_or_create_graph_components(session_id)
        graph = graph_components["graph"]
        config = graph_components["config"]

        # Get current state
        current_state = await _get_current_state(session_id)
        if not current_state:
            await _send_error_message(websocket, session_id, "Session not found")
            return

        # Check if graph is interrupted (waiting for approval)
        is_interrupted = await _is_graph_interrupted(session_id)
        if is_interrupted:
            # Add approval response to chat history
            approval_message = f"{'Approved' if approved else 'Rejected'}"
            if feedback:
                approval_message += f": {feedback}"
            updated_state = add_chat_message(current_state, "user", approval_message)
            
            await graph.aupdate_state(config, updated_state)
            
            # Continue processing if approved, otherwise stay interrupted
            if approved:
                await _process_planning_execution(websocket, session_id, updated_state, graph, config, resume_from_approval=True)
            else:
                # Send rejection confirmation - user can provide feedback to retry
                await _send_planning_update(websocket, session_id, updated_state)
        else:
            await _send_error_message(websocket, session_id, "No pending approval to respond to")
            
    except Exception as e:
        logger.error(f"Error handling approval response: {e}")
        await _send_error_message(websocket, session_id, f"Error processing approval: {str(e)}")


async def _process_planning_execution(websocket: WebSocket, session_id: str, state: ExperimentPlanState, 
                                    graph, config, resume_from_approval: bool = False):
    """Execute planning graph and stream updates via WebSocket."""
    try:
        final_state = state
        
        # Execute graph and stream updates
        if resume_from_approval:
            # Resume from interrupt
            logger.info("Resuming planning execution from interrupt")
            async for event in graph.astream(None, config, stream_mode="values"):
                if event is not None:
                    final_state = event
                    await _send_planning_update(websocket, session_id, final_state)
        else:
            # Continue with normal processing
            logger.info("Starting new planning execution")
            async for event in graph.astream(state, config, stream_mode="values"):
                if event is not None:
                    final_state = event
                    await _send_planning_update(websocket, session_id, final_state)

        # Check if graph has completed (reached END state)
        is_complete = await _is_graph_complete(session_id)
        if is_complete:
            logger.info(f"🎯 Graph completed for session {session_id}")
            await _send_completion_message(websocket, session_id, final_state)
            return  # Exit the function as session is complete

        # Check if we're now interrupted at the next stage
        is_interrupted = await _is_graph_interrupted(session_id)
        if is_interrupted:
            current_stage = await _get_current_stage_from_graph(session_id)
            await _send_approval_request(websocket, session_id, {"stage": current_stage, "status": "waiting"})
            logger.info(f"Interrupted at stage: {current_stage}")
                
    except Exception as e:
        logger.error(f"Error in planning execution: {e}")
        await _send_error_message(websocket, session_id, f"Planning execution error: {str(e)}")


@router.get("/session/{session_id}", response_model=HITLSessionResponse)
async def get_hitl_session_status(session_id: str):
    """
    Get the current status of a HITL planning session.
    """
    try:
        current_state = await _get_current_state(session_id)
        if not current_state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        is_interrupted = await _is_graph_interrupted(session_id)
        current_stage = await _get_current_stage_from_graph(session_id)
        
        return HITLSessionResponse(
            session_id=session_id,
            experiment_id=current_state["experiment_id"],
            current_stage=current_stage or current_state.get("current_stage", "objective_setting"),
            is_waiting_for_approval=is_interrupted,
            pending_approval={"stage": current_stage, "status": "waiting"} if is_interrupted else None,
            streaming_enabled=True,
            checkpoint_available=session_id in _active_graphs
        )
        
    except Exception as e:
        logger.error(f"Failed to get session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")


@router.post("/session/{session_id}/close")
async def close_planning_session(session_id: str):
    """
    Explicitly close a planning session and clean up all resources.
    """
    try:
        # Check if session exists
        if session_id not in _active_graphs:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get final state before cleanup
        current_state = await _get_current_state(session_id)
        
        # Close WebSocket connection if active
        if session_id in _active_connections:
            websocket = _active_connections[session_id]
            try:
                await websocket.close(code=1000, reason="Session closed by request")
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        # Clean up resources
        if session_id in _active_graphs:
            del _active_graphs[session_id]
        if session_id in _active_connections:
            del _active_connections[session_id]
        
        logger.info(f"Manually closed planning session {session_id}")
        
        return {
            "session_id": session_id,
            "status": "closed",
            "message": "Planning session closed successfully",
            "experiment_id": current_state.get("experiment_id") if current_state else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to close session: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_hitl_session(session_id: str):
    """
    Delete a HITL planning session and clean up resources.
    """
    try:
        # Use the close session logic for consistency
        return await close_planning_session(session_id)
        
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/health")
async def websocket_health_check():
    """
    Health check endpoint for the WebSocket planning system.
    """
    try:
        # Check OpenAI configuration
        openai_status = "configured" if validate_openai_config() else "not_configured"
        
        # Checkpoint status is now memory-based
        checkpoint_status = "memory_based"
        
        return {
            "status": "healthy",
            "openai_status": openai_status,
            "checkpoint_status": checkpoint_status,
            "active_sessions": len(_active_graphs),
            "active_connections": len(_active_connections),
            "features": [
                "Human-in-the-loop approval",
                "Real-time bidirectional WebSocket communication",
                "State checkpointing",
                "Session persistence",
                "Streaming planning updates",
                "Interactive approval workflows"
            ]
        }
        
    except Exception as e:
        logger.error(f"WebSocket health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 