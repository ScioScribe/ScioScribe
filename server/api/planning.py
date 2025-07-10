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
    
    pending_approval = state.get('pending_approval', {})
    return bool(pending_approval and pending_approval.get('status') == 'waiting')


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
        
        # Run the graph until it hits an interrupt (approval node)
        current_state = initial_state
        async for event in graph.astream(initial_state, config, stream_mode="values"):
            # Only process non-None events
            if event is not None:
                current_state = event
                # Check if we've hit an approval node (interrupt)
                if _is_waiting_for_approval(current_state):
                    break
        
        # Ensure current_state is not None
        if current_state is None:
            logger.warning("current_state is None, using initial_state as fallback")
            current_state = initial_state
        
        # Check if we're interrupted before an approval node
        if not _is_waiting_for_approval(current_state):
            try:
                state_snapshot = await graph.aget_state(config)
                if state_snapshot and state_snapshot.next and any("approval" in str(node) for node in state_snapshot.next):
                    # We're interrupted before an approval node, but check if it's already approved
                    next_node = str(state_snapshot.next[0]) if state_snapshot.next else ""
                    stage_name = next_node.replace("_approval", "") if "_approval" in next_node else "unknown"
                    
                    # Only set pending_approval if the stage hasn't been approved yet
                    approvals = current_state.get('approvals', {})
                    if not approvals.get(stage_name, False):
                        current_state["pending_approval"] = {
                            "stage": stage_name,
                            "timestamp": datetime.utcnow().isoformat(),
                            "status": "waiting"
                        }
                        
                        # Update the state in the checkpoint
                        await graph.aupdate_state(config, current_state)
                        
                        logger.info(f"Set pending_approval for stage: {stage_name}")
                    else:
                        logger.info(f"Stage {stage_name} already approved, not setting pending_approval")
            except Exception as e:
                logger.warning(f"Failed to check/set pending_approval: {e}")
        
        logger.info(f"Started HITL planning session {session_id}, waiting for approval: {_is_waiting_for_approval(current_state)}")
        
        return HITLSessionResponse(
            session_id=session_id,
            experiment_id=current_state["experiment_id"],
            current_stage=current_state["current_stage"],
            is_waiting_for_approval=_is_waiting_for_approval(current_state),
            pending_approval=current_state.get("pending_approval"),
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
            
            # If waiting for approval, send approval request
            if _is_waiting_for_approval(current_state):
                await _send_approval_request(websocket, session_id, current_state.get("pending_approval", {}))
        
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
                await _send_error_message(websocket, session_id, f"Error processing message: {str(e)}")
                
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
    """Send a message via WebSocket."""
    try:
        await websocket.send_text(json.dumps(message))
    except Exception as e:
        logger.error(f"Failed to send WebSocket message: {e}")


async def _send_session_status(websocket: WebSocket, session_id: str):
    """Send session status to frontend."""
    try:
        current_state = await _get_current_state(session_id)
        status_data = {
            "session_id": session_id,
            "is_active": current_state is not None,
            "current_stage": current_state.get("current_stage") if current_state else None,
            "is_waiting_for_approval": _is_waiting_for_approval(current_state) if current_state else False
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

        # Add user message to state
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

        # Handle approval
        if _is_waiting_for_approval(current_state):
            # Clear pending approval and mark stage as approved/rejected
            pending_approval = current_state.get("pending_approval", {})
            stage = pending_approval.get("stage")
            
            updated_state = current_state.copy()
            updated_state["pending_approval"] = None
            
            if stage:
                approvals = updated_state.get("approvals", {})
                approvals[stage] = approved
                updated_state["approvals"] = approvals
                logger.info(f"Marked stage {stage} as {'approved' if approved else 'rejected'}")
            
            # Add approval response to chat history
            approval_message = f"{'Approved' if approved else 'Rejected'}"
            if feedback:
                approval_message += f": {feedback}"
            updated_state = add_chat_message(updated_state, "user", approval_message)
            
            await graph.aupdate_state(config, updated_state)
            
            # Continue processing if approved
            if approved:
                await _process_planning_execution(websocket, session_id, updated_state, graph, config, resume_from_approval=True)
            else:
                # Send rejection confirmation
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
            # Resume from approval node
            logger.info("Resuming planning execution from approval node")
            async for event in graph.astream(None, config, stream_mode="values"):
                if event is not None:
                    final_state = event
                    await _send_planning_update(websocket, session_id, final_state)
                    
                    # Check if we've reached another approval point
                    if _is_waiting_for_approval(final_state):
                        await _send_approval_request(websocket, session_id, final_state.get("pending_approval", {}))
                        break
        else:
            # Continue with normal processing
            logger.info("Starting new planning execution")
            async for event in graph.astream(state, config, stream_mode="values"):
                if event is not None:
                    final_state = event
                    await _send_planning_update(websocket, session_id, final_state)
                    
                    if _is_waiting_for_approval(final_state):
                        await _send_approval_request(websocket, session_id, final_state.get("pending_approval", {}))
                        break

        # Check if we need to set pending approval for the next stage
        if not _is_waiting_for_approval(final_state):
            try:
                state_snapshot = await graph.aget_state(config)
                if state_snapshot and state_snapshot.next and any("approval" in str(node) for node in state_snapshot.next):
                    next_node = str(state_snapshot.next[0]) if state_snapshot.next else ""
                    stage_name = next_node.replace("_approval", "") if "_approval" in next_node else "unknown"
                    
                    # Only set pending_approval if the stage hasn't been approved yet
                    approvals = final_state.get('approvals', {})
                    if not approvals.get(stage_name, False):
                        final_state["pending_approval"] = {
                            "stage": stage_name,
                            "timestamp": datetime.utcnow().isoformat(),
                            "status": "waiting"
                        }
                        await graph.aupdate_state(config, final_state)
                        await _send_approval_request(websocket, session_id, final_state["pending_approval"])
                        logger.info(f"Set pending approval for stage: {stage_name}")
            except Exception as e:
                logger.warning(f"Failed to check/set pending approval: {e}")
                
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
        
        return HITLSessionResponse(
            session_id=session_id,
            experiment_id=current_state["experiment_id"],
            current_stage=current_state["current_stage"],
            is_waiting_for_approval=_is_waiting_for_approval(current_state),
            pending_approval=current_state.get("pending_approval"),
            streaming_enabled=True,
            checkpoint_available=session_id in _active_graphs
        )
        
    except Exception as e:
        logger.error(f"Failed to get session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_hitl_session(session_id: str):
    """
    Delete a HITL planning session and clean up resources.
    """
    try:
        # Remove from active graphs
        if session_id in _active_graphs:
            del _active_graphs[session_id]
        
        logger.info(f"Deleted HITL planning session {session_id}")
        
        return {
            "session_id": session_id,
            "status": "deleted",
            "message": "HITL planning session deleted successfully"
        }
        
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