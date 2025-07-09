"""
FastAPI endpoints for experiment planning with human-in-the-loop support.

This module provides REST API endpoints with streaming responses, user approval
mechanisms, and state management for proper frontend integration.
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse
from langgraph.checkpoint.memory import MemorySaver

from agents.planning.graph.graph_builder import (
    create_planning_graph,
)
from agents.planning.state import ExperimentPlanState, PLANNING_STAGES
from agents.planning.debug import StateDebugger, get_global_debugger
from agents.planning.validation import StateValidationError
from agents.planning.serialization import (
    serialize_state_to_dict,
    deserialize_dict_to_state,
    SerializationError
)
from agents.planning.factory import create_new_experiment_state, add_chat_message
from config import validate_openai_config

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/planning", tags=["planning-hitl"])

# Global instances
_global_debugger = get_global_debugger()
_active_graphs: Dict[str, Dict[str, Any]] = {}


# Request/Response Models
class StartHITLPlanningRequest(BaseModel):
    """Request model for starting a new HITL planning session."""
    research_query: str = Field(..., description="Initial research query or idea")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID")
    user_id: Optional[str] = Field("demo-user", description="User ID for session tracking")


class StreamChatRequest(BaseModel):
    """Request model for sending input to the streaming chat endpoint."""
    user_input: str = Field(..., description="User's input, which could be a response, an approval, or a command.")


class HITLSessionResponse(BaseModel):
    """Response model for HITL session info."""
    session_id: str = Field(..., description="Session identifier")
    experiment_id: str = Field(..., description="Experiment identifier")
    current_stage: str = Field(..., description="Current planning stage")
    is_waiting_for_approval: bool = Field(..., description="Whether waiting for user approval")
    pending_approval: Optional[Dict[str, Any]] = Field(None, description="Pending approval details")
    streaming_enabled: bool = Field(..., description="Whether streaming is enabled")
    checkpoint_available: bool = Field(..., description="Whether checkpoint is available")


class StreamEvent(BaseModel):
    """Model for streaming events."""
    event_type: str = Field(..., description="Type of event (update, approval_request, error)")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


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
            "created_at": datetime.utcnow(),
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
            current_state = event
            # Check if we've hit an approval node (interrupt)
            if _is_waiting_for_approval(current_state):
                break
        
        # Check if we're interrupted before an approval node
        if not _is_waiting_for_approval(current_state):
            try:
                state_snapshot = await graph.aget_state(config)
                if state_snapshot.next and any("approval" in str(node) for node in state_snapshot.next):
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


@router.post("/stream/chat/{session_id}")
async def stream_chat(session_id: str, request: StreamChatRequest):
    """
    Handles all user interactions for a session, streaming back the agent's response.
    This single endpoint replaces /process, /approve, and GET /stream.
    """
    async def event_generator():
        try:
            graph_components = _get_or_create_graph_components(session_id)
            graph = graph_components["graph"]
            config = graph_components["config"]

            # Get the state before this interaction
            current_state = await _get_current_state(session_id)
            if not current_state:
                error_event = StreamEvent(
                    event_type="error",
                    data={"error": f"Session {session_id} not found or no state available."}
                )
                yield f"data: {error_event.json()}\n\n"
                return

            was_waiting_for_approval = _is_waiting_for_approval(current_state)

            # Add user message to state and clear pending approval flag
            updated_state = add_chat_message(current_state, "user", request.user_input)
            if "pending_approval" in updated_state and updated_state["pending_approval"]:
                updated_state["pending_approval"] = None

            # Update the state in the checkpoint
            await graph.aupdate_state(config, updated_state)

            # If we were waiting for approval, resume from the approval node
            # Otherwise, continue with the updated state
            if was_waiting_for_approval:
                # Resume from approval node - don't re-inject state
                graph_input = None
                logger.info(f"Resuming from approval node for session {session_id}")
            else:
                # Continue with updated state
                graph_input = updated_state
                logger.info(f"Continuing with updated state for session {session_id}")

            # Resume execution and stream updates until next approval or completion
            async for event in graph.astream(graph_input, config, stream_mode="values"):
                # The event is the state after each node execution
                current_state = event
                
                # Serialize and send the state update
                try:
                    serialized_output = serialize_state_to_dict(current_state)
                except (SerializationError, TypeError) as e:
                    logger.warning(f"Could not serialize state update: {e}")
                    serialized_output = {"error": "Serialization failed", "details": str(e)}

                stream_event = StreamEvent(
                    event_type="update",
                    data={"state": serialized_output}
                )
                yield f"data: {stream_event.json()}\n\n"
                
                # Check if we've reached another approval node
                if _is_waiting_for_approval(current_state):
                    logger.info(f"Reached approval node for session {session_id}")
                    break

            # After the stream is done, check if we are waiting for another approval
            final_state = await _get_current_state(session_id)
            
            # Check if we're interrupted before an approval node
            if not _is_waiting_for_approval(final_state):
                try:
                    state_snapshot = await graph.aget_state(config)
                    if state_snapshot.next and any("approval" in str(node) for node in state_snapshot.next):
                        # We're interrupted before an approval node, but check if it's already approved
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
                            
                            # Update the state in the checkpoint
                            await graph.aupdate_state(config, final_state)
                            
                            logger.info(f"Set pending_approval for stage: {stage_name}")
                        else:
                            logger.info(f"Stage {stage_name} already approved, not setting pending_approval")
                except Exception as e:
                    logger.warning(f"Failed to check/set pending_approval: {e}")
            
            # Send approval request if we're waiting for approval
            if _is_waiting_for_approval(final_state):
                approval_event = StreamEvent(
                    event_type="approval_request",
                    data=final_state.get("pending_approval", {})
                )
                yield f"data: {approval_event.json()}\n\n"

        except Exception as e:
            logger.error(f"Streaming chat error for session {session_id}: {e}", exc_info=True)
            error_event = StreamEvent(
                event_type="error",
                data={"error": f"An unexpected error occurred: {str(e)}"}
            )
            yield f"data: {error_event.json()}\n\n"

    return EventSourceResponse(event_generator())


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
async def hitl_health_check():
    """
    Health check endpoint for the HITL planning system.
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
            "features": [
                "Human-in-the-loop approval",
                "Real-time streaming via single endpoint",
                "State checkpointing",
                "Session persistence"
            ]
        }
        
    except Exception as e:
        logger.error(f"HITL health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 