"""
FastAPI endpoints for experiment planning agent interactions.

This module provides REST API endpoints for managing experiment planning sessions,
processing user input through the LangGraph planning agents, and managing conversation state.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agents.planning.graph import (
    PlanningGraphExecutor,
    start_new_experiment_planning,
    execute_planning_conversation
)
from agents.planning.state import ExperimentPlanState, PLANNING_STAGES
from agents.planning.debug import StateDebugger, get_global_debugger
from agents.planning.validation import StateValidationError
from agents.planning.transitions import TransitionError, get_stage_progress
from agents.planning.serialization import (
    serialize_state_to_dict,
    deserialize_dict_to_state,
    SerializationError
)
from config import validate_openai_config

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/planning", tags=["experiment-planning"])

# In-memory storage for planning sessions (replace with database in production)
_planning_sessions: Dict[str, Dict[str, Any]] = {}

# Global debugger instance
_global_debugger = get_global_debugger()


# Request/Response Models
class StartPlanningRequest(BaseModel):
    """Request model for starting a new planning session."""
    research_query: str = Field(..., description="Initial research query or idea")
    experiment_id: Optional[str] = Field(None, description="Optional experiment ID")
    user_id: Optional[str] = Field("demo-user", description="User ID for session tracking")


class StartPlanningResponse(BaseModel):
    """Response model for starting a new planning session."""
    session_id: str = Field(..., description="Unique session identifier")
    experiment_id: str = Field(..., description="Experiment identifier")
    status: str = Field(..., description="Session status")
    current_stage: str = Field(..., description="Current planning stage")
    message: str = Field(..., description="Welcome message or initial agent response")


class ProcessInputRequest(BaseModel):
    """Request model for processing user input."""
    session_id: str = Field(..., description="Session identifier")
    user_input: str = Field(..., description="User's input or response")
    force_transition: bool = Field(False, description="Force stage transition if needed")


class ProcessInputResponse(BaseModel):
    """Response model for processing user input."""
    session_id: str = Field(..., description="Session identifier")
    agent_response: str = Field(..., description="Agent's response to user input")
    current_stage: str = Field(..., description="Current planning stage")
    progress: Dict[str, Any] = Field(..., description="Progress information")
    is_complete: bool = Field(..., description="Whether planning is complete")
    next_steps: List[str] = Field(..., description="Suggested next steps")


class SessionStatusResponse(BaseModel):
    """Response model for session status."""
    session_id: str = Field(..., description="Session identifier")
    experiment_id: str = Field(..., description="Experiment identifier")
    current_stage: str = Field(..., description="Current planning stage")
    completed_stages: List[str] = Field(..., description="Completed planning stages")
    progress: Dict[str, Any] = Field(..., description="Progress information")
    chat_history: List[Dict[str, Any]] = Field(..., description="Chat conversation history")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ExportPlanResponse(BaseModel):
    """Response model for exporting experiment plan."""
    session_id: str = Field(..., description="Session identifier")
    experiment_plan: Dict[str, Any] = Field(..., description="Complete experiment plan")
    export_format: str = Field(..., description="Export format (json)")
    exported_at: datetime = Field(..., description="Export timestamp")


# Utility Functions
def _get_session(session_id: str) -> Dict[str, Any]:
    """Get planning session by ID."""
    if session_id not in _planning_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Planning session {session_id} not found"
        )
    return _planning_sessions[session_id]


def _save_session(session_id: str, session_data: Dict[str, Any]) -> None:
    """Save planning session data."""
    _planning_sessions[session_id] = session_data


def _get_latest_agent_response(state: ExperimentPlanState) -> str:
    """Extract the latest agent response from chat history."""
    chat_history = state.get("chat_history", [])
    
    # Find the most recent assistant message
    for message in reversed(chat_history):
        if message.get("role") == "assistant":
            return message.get("content", "")
    
    return "I'm ready to help you plan your experiment. Please tell me about your research idea."


def _get_next_steps(state: ExperimentPlanState) -> List[str]:
    """Generate next steps based on current stage."""
    current_stage = state.get("current_stage", "")
    
    next_steps_map = {
        "objective_setting": [
            "Clearly define your research objective",
            "State your hypothesis if you have one",
            "Describe the problem you're trying to solve"
        ],
        "variable_identification": [
            "Identify your independent variables",
            "Define your dependent variables",
            "Consider what needs to be controlled"
        ],
        "experimental_design": [
            "Design your experimental groups",
            "Plan your control groups",
            "Determine appropriate sample sizes"
        ],
        "methodology_protocol": [
            "Outline step-by-step procedures",
            "List required materials and equipment",
            "Define specific parameters and conditions"
        ],
        "data_planning": [
            "Plan your data collection methods",
            "Choose appropriate statistical analyses",
            "Consider potential challenges and solutions"
        ],
        "final_review": [
            "Review your complete experiment plan",
            "Make any necessary adjustments",
            "Export your final plan"
        ]
    }
    
    return next_steps_map.get(current_stage, ["Continue with the planning process"])


# API Endpoints
@router.post("/start", response_model=StartPlanningResponse)
async def start_planning_session(request: StartPlanningRequest):
    """
    Start a new experiment planning session.
    
    Creates a new planning session with the LangGraph executor and initializes
    the conversation with the objective setting agent.
    """
    try:
        # Validate OpenAI configuration
        if not validate_openai_config():
            raise HTTPException(
                status_code=500,
                detail="OpenAI configuration is invalid. Please check your API key."
            )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Start planning session
        executor, initial_state = start_new_experiment_planning(
            research_query=request.research_query,
            experiment_id=request.experiment_id,
            debugger=_global_debugger,
            log_level="INFO"
        )
        
        # Execute first step to get initial agent response
        updated_state = executor.execute_step(initial_state)
        
        # Get agent response
        agent_response = _get_latest_agent_response(updated_state)
        
        # Save session
        session_data = {
            "executor": executor,
            "state": updated_state,
            "user_id": request.user_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        _save_session(session_id, session_data)
        
        logger.info(f"Started new planning session {session_id} for experiment {updated_state['experiment_id']}")
        
        return StartPlanningResponse(
            session_id=session_id,
            experiment_id=updated_state["experiment_id"],
            status="active",
            current_stage=updated_state["current_stage"],
            message=agent_response
        )
        
    except StateValidationError as e:
        logger.error(f"State validation error: {e}")
        raise HTTPException(status_code=400, detail=f"State validation failed: {e.message}")
    
    except Exception as e:
        logger.error(f"Failed to start planning session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start planning session: {str(e)}")


@router.post("/process", response_model=ProcessInputResponse)
async def process_user_input(request: ProcessInputRequest):
    """
    Process user input through the planning graph.
    
    Takes user input, processes it through the appropriate agent,
    and returns the agent's response along with updated session state.
    """
    try:
        # Get session
        session_data = _get_session(request.session_id)
        executor = session_data["executor"]
        current_state = session_data["state"]
        
        # Add user input to chat history
        from agents.planning.factory import add_chat_message
        current_state = add_chat_message(current_state, "user", request.user_input)
        
        # Process input through the graph
        updated_state = executor.execute_step(current_state, request.user_input)
        
        # Get agent response
        agent_response = _get_latest_agent_response(updated_state)
        
        # Get progress information
        progress = get_stage_progress(updated_state)
        
        # Get next steps
        next_steps = _get_next_steps(updated_state)
        
        # Check if planning is complete
        is_complete = updated_state.get("current_stage") == "final_review" and progress.get("is_final_stage", False)
        
        # Update session
        session_data["state"] = updated_state
        session_data["updated_at"] = datetime.now()
        _save_session(request.session_id, session_data)
        
        logger.info(f"Processed input for session {request.session_id}, stage: {updated_state['current_stage']}")
        
        return ProcessInputResponse(
            session_id=request.session_id,
            agent_response=agent_response,
            current_stage=updated_state["current_stage"],
            progress=progress,
            is_complete=is_complete,
            next_steps=next_steps
        )
        
    except TransitionError as e:
        logger.error(f"Transition error: {e}")
        raise HTTPException(status_code=400, detail=f"Stage transition failed: {str(e)}")
    
    except StateValidationError as e:
        logger.error(f"State validation error: {e}")
        raise HTTPException(status_code=400, detail=f"State validation failed: {e.message}")
    
    except Exception as e:
        logger.error(f"Failed to process input: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process input: {str(e)}")


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Get the current status of a planning session.
    
    Returns the complete session state including progress, chat history,
    and current stage information.
    """
    try:
        # Get session
        session_data = _get_session(session_id)
        state = session_data["state"]
        
        # Get progress information
        progress = get_stage_progress(state)
        
        return SessionStatusResponse(
            session_id=session_id,
            experiment_id=state["experiment_id"],
            current_stage=state["current_stage"],
            completed_stages=state.get("completed_stages", []),
            progress=progress,
            chat_history=state.get("chat_history", []),
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")


@router.get("/export/{session_id}", response_model=ExportPlanResponse)
async def export_experiment_plan(session_id: str):
    """
    Export the complete experiment plan from a planning session.
    
    Returns the finalized experiment plan in JSON format, suitable for
    use by other modules or external systems.
    """
    try:
        # Get session
        session_data = _get_session(session_id)
        state = session_data["state"]
        
        # Serialize state for export
        experiment_plan = serialize_state_to_dict(state)
        
        logger.info(f"Exported experiment plan for session {session_id}")
        
        return ExportPlanResponse(
            session_id=session_id,
            experiment_plan=experiment_plan,
            export_format="json",
            exported_at=datetime.now()
        )
        
    except SerializationError as e:
        logger.error(f"Serialization error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serialize experiment plan: {e.message}")
    
    except Exception as e:
        logger.error(f"Failed to export experiment plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export experiment plan: {str(e)}")


@router.post("/navigate/{session_id}")
async def navigate_to_stage(session_id: str, target_stage: str, force: bool = False):
    """
    Navigate to a specific planning stage.
    
    Allows users to jump back to previous stages for editing or
    move forward if prerequisites are met.
    """
    try:
        # Validate target stage
        if target_stage not in PLANNING_STAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage: {target_stage}. Valid stages: {', '.join(PLANNING_STAGES)}"
            )
        
        # Get session
        session_data = _get_session(session_id)
        executor = session_data["executor"]
        current_state = session_data["state"]
        
        # Add navigation message to chat history
        from agents.planning.factory import add_chat_message
        current_state = add_chat_message(
            current_state,
            "system",
            f"Navigating to {target_stage.replace('_', ' ')} stage..."
        )
        
        # Use the transition system to navigate
        from agents.planning.transitions import transition_to_stage
        updated_state = transition_to_stage(current_state, target_stage, force=force)
        
        # Execute step to get agent response for the new stage
        updated_state = executor.execute_step(updated_state)
        
        # Get agent response
        agent_response = _get_latest_agent_response(updated_state)
        
        # Update session
        session_data["state"] = updated_state
        session_data["updated_at"] = datetime.now()
        _save_session(session_id, session_data)
        
        logger.info(f"Navigated session {session_id} to stage {target_stage}")
        
        return {
            "session_id": session_id,
            "status": "success",
            "current_stage": target_stage,
            "message": agent_response
        }
        
    except TransitionError as e:
        logger.error(f"Navigation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Navigation failed: {str(e)}")
    
    except Exception as e:
        logger.error(f"Failed to navigate to stage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to navigate to stage: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a planning session and clean up resources.
    
    Removes the session from memory and performs any necessary cleanup.
    """
    try:
        # Check if session exists
        if session_id not in _planning_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Clean up session
        del _planning_sessions[session_id]
        
        logger.info(f"Deleted planning session {session_id}")
        
        return {
            "session_id": session_id,
            "status": "deleted",
            "message": "Planning session deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.get("/sessions")
async def list_sessions():
    """
    List all active planning sessions.
    
    Returns a summary of all active planning sessions for monitoring and debugging.
    """
    try:
        sessions = []
        for session_id, session_data in _planning_sessions.items():
            state = session_data["state"]
            sessions.append({
                "session_id": session_id,
                "experiment_id": state["experiment_id"],
                "current_stage": state["current_stage"],
                "created_at": session_data["created_at"],
                "updated_at": session_data["updated_at"]
            })
        
        return {
            "sessions": sessions,
            "total_count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/stages")
async def get_planning_stages():
    """
    Get information about all planning stages.
    
    Returns the complete list of planning stages with descriptions.
    """
    stage_descriptions = {
        "objective_setting": "Define research objectives and hypothesis",
        "variable_identification": "Identify independent, dependent, and control variables",
        "experimental_design": "Design experimental groups and sample sizes",
        "methodology_protocol": "Create step-by-step procedures and materials list",
        "data_planning": "Plan data collection and analysis methods",
        "final_review": "Review and finalize the complete experiment plan"
    }
    
    stages = [
        {
            "stage": stage,
            "description": stage_descriptions.get(stage, ""),
            "index": i
        }
        for i, stage in enumerate(PLANNING_STAGES)
    ]
    
    return {
        "stages": stages,
        "total_stages": len(PLANNING_STAGES)
    }


@router.get("/health")
async def planning_health_check():
    """
    Health check endpoint for the planning system.
    
    Verifies that all required components are properly configured.
    """
    try:
        # Check OpenAI configuration
        openai_status = "configured" if validate_openai_config() else "not_configured"
        
        # Check debugger
        debugger_status = "available" if _global_debugger else "not_available"
        
        return {
            "status": "healthy",
            "openai_status": openai_status,
            "debugger_status": debugger_status,
            "active_sessions": len(_planning_sessions),
            "supported_stages": len(PLANNING_STAGES)
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 