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
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    SqliteSaver = None
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

# Create checkpointer directory
CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)


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
        # Create checkpointer for this session
        if SqliteSaver is not None:
            try:
                checkpoint_path = CHECKPOINT_DIR / f"{session_id}.db"
                checkpointer = SqliteSaver.from_conn_string(str(checkpoint_path))
                logger.info(f"Using SqliteSaver for session {session_id}")
            except Exception as e:
                logger.warning(f"SqliteSaver failed for session {session_id}, using MemorySaver: {e}")
                checkpointer = MemorySaver()
        else:
            logger.info(f"SqliteSaver not available, using MemorySaver for session {session_id}")
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
    Start a new HITL planning session and runs the first step.
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
        
        # Use astream to run the graph just for the first step
        async for event in graph.astream(initial_state, config, stream_mode="values"):
            # The first event will be the output of the entry point
            current_state = event
            break  # We only want the first state
        
        logger.info(f"Started HITL planning session {session_id}")
        
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
                updated_state["pending_approval"] = {}

            # Update the state in the checkpoint, making it ready for resume
            await graph.aupdate_state(config, updated_state)

            # If we were waiting for approval, the user's input was the approval itself,
            # so we don't need to pass it to the graph again.
            graph_input = None if was_waiting_for_approval else updated_state

            # Resume execution and stream updates
            async for event in graph.astream(graph_input, config):
                for node_name, output in event.items():
                    if node_name == "__interrupt__":
                        continue  # Skip the interrupt signal

                    # The output can be complex, serialize it safely
                    try:
                        serialized_output = serialize_state_to_dict(output)
                    except (SerializationError, TypeError) as e:
                        logger.warning(f"Could not serialize output from node {node_name}: {e}")
                        serialized_output = {"error": "Serialization failed", "details": str(e)}

                    stream_event = StreamEvent(
                        event_type="update",
                        data={"node": node_name, "output": serialized_output}
                    )
                    yield f"data: {stream_event.json()}\n\n"

            # After the stream is done, check if we are waiting for another approval
            final_state = await _get_current_state(session_id)
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
        
        # Clean up checkpoint file
        checkpoint_path = CHECKPOINT_DIR / f"{session_id}.db"
        if checkpoint_path.exists():
            checkpoint_path.unlink()
        
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
        
        # Check checkpoint directory
        checkpoint_status = "available" if CHECKPOINT_DIR.exists() else "not_available"
        
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