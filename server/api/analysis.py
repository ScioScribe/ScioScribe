"""
FastAPI endpoints for analysis agent interactions.

This module provides REST API endpoints for generating visualizations from experiment plans
and datasets using the specialized LangGraph-based analysis agent system.
"""

import logging
import uuid
import tempfile
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel, Field
import aiofiles

from agents.analysis.agent import AnalysisAgent, create_analysis_agent
from config import validate_openai_config

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Global analysis agent instance
_analysis_agent: Optional[AnalysisAgent] = None

# In-memory storage for analysis sessions (replace with database in production)
_analysis_sessions: Dict[str, Dict[str, Any]] = {}

# Request/Response Models
class GenerateVisualizationRequest(BaseModel):
    """Request model for generating visualizations."""
    prompt: str = Field(..., description="Natural language analytical question or visualization request")
    plan: str = Field(..., description="Experiment plan content as text")
    csv: str = Field(..., description="CSV data content as text")
    memory: Optional[Dict[str, Any]] = Field(None, description="Optional memory for iterative refinement")
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")


class GenerateVisualizationResponse(BaseModel):
    """Response model for visualization generation."""
    html: str = Field(..., description="Interactive Plotly HTML visualization")
    message: str = Field(..., description="Explanatory message about the visualization")


class AnalysisSessionResponse(BaseModel):
    """Response model for analysis session status."""
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Session status")
    visualizations_generated: int = Field(..., description="Number of visualizations generated")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    memory: Dict[str, Any] = Field(..., description="Session memory and context")


# Utility Functions
def _get_analysis_agent() -> AnalysisAgent:
    """Get or create the global analysis agent instance."""
    global _analysis_agent
    
    if _analysis_agent is None:
        try:
            _analysis_agent = create_analysis_agent(
                model_provider="openai",
                model_name="gpt-4"
            )
            logger.info("✅ Analysis agent initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize analysis agent: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize analysis agent: {str(e)}"
            )
    
    return _analysis_agent


def _get_session(session_id: str) -> Dict[str, Any]:
    """Get analysis session by ID."""
    if session_id not in _analysis_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis session {session_id} not found"
        )
    return _analysis_sessions[session_id]


def _save_session(session_id: str, session_data: Dict[str, Any]) -> None:
    """Save analysis session data."""
    _analysis_sessions[session_id] = session_data


def _create_session(session_id: Optional[str] = None) -> str:
    """Create a new analysis session."""
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    session_data = {
        "session_id": session_id,
        "status": "active",
        "visualizations_generated": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "memory": {},
        "generated_visualizations": []
    }
    
    _save_session(session_id, session_data)
    logger.info(f"📊 Created new analysis session: {session_id}")
    return session_id


# API Endpoints
@router.post("/generate-visualization", response_model=GenerateVisualizationResponse)
async def generate_visualization(request: GenerateVisualizationRequest):
    """
    Generate visualization from experiment plan and dataset.
    
    Orchestrates the specialized analysis agent system to create publication-quality
    visualizations with clear explanations and insights.
    """
    try:
        # Validate OpenAI configuration
        if not validate_openai_config():
            raise HTTPException(
                status_code=500,
                detail="OpenAI configuration is invalid. Please check your API key."
            )
        
        # Get or create session
        session_id = request.session_id or _create_session()
        
        # Get analysis agent
        agent = _get_analysis_agent()
        
        # Validate file paths
        if not request.plan:
            raise HTTPException(
                status_code=400,
                detail="Experiment plan content is required"
            )
        
        if not request.csv:
            raise HTTPException(
                status_code=400,
                detail="CSV data content is required"
            )
        
        # Get session data for memory
        session_data = _analysis_sessions.get(session_id, {"memory": {}})
        memory = request.memory or session_data.get("memory", {})
        
        logger.info(f"🎯 Generating visualization for session {session_id}")
        logger.info(f"📝 User prompt: {request.prompt}")
        logger.info(f"📊 Experiment plan: (content)")
        logger.info(f"📈 Dataset: (content)")
        
        # Generate visualization using the specialized agent system
        result = agent.generate_visualization(
            user_prompt=request.prompt,
            experiment_plan_content=request.plan,
            csv_data_content=request.csv,
            memory=memory
        )
        
        # Update session data
        if session_id in _analysis_sessions:
            session_data = _analysis_sessions[session_id]
            session_data["visualizations_generated"] += 1
            session_data["updated_at"] = datetime.now()
            session_data["memory"] = result.get("memory", {})
            session_data["generated_visualizations"].append({
                "prompt": request.prompt,
                "generated_at": datetime.now(),
                "html_content": result.get("html_content", "")
            })
            _save_session(session_id, session_data)
        
        logger.info(f"✅ Visualization generated successfully for session {session_id}")
        
        # Generate a user-friendly message
        explanation = result.get("explanation", "")
        if not explanation:
            explanation = f"Successfully generated visualization for: {request.prompt}"
        
        return GenerateVisualizationResponse(
            html=result.get("html_content", ""),
            message=explanation
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to generate visualization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate visualization: {str(e)}"
        )


@router.post("/upload-and-analyze")
async def upload_and_analyze(
    user_prompt: str = Form(...),
    experiment_plan: UploadFile = File(...),
    dataset: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    Upload files and generate visualization in one step.
    
    Convenient endpoint that handles file uploads and immediately generates
    visualizations using the analysis agent system.
    """
    try:
        # Validate OpenAI configuration
        if not validate_openai_config():
            raise HTTPException(
                status_code=500,
                detail="OpenAI configuration is invalid. Please check your API key."
            )
        
        # Validate file types
        if not experiment_plan.filename or not experiment_plan.filename.endswith(('.json', '.txt', '.md')):
            raise HTTPException(
                status_code=400,
                detail="Experiment plan must be a JSON, TXT, or MD file"
            )
        
        if not dataset.filename or not dataset.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Dataset must be a CSV file"
            )
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded files and read their content
        plan_path = os.path.join(temp_dir, experiment_plan.filename)
        csv_path = os.path.join(temp_dir, dataset.filename)
        
        async with aiofiles.open(plan_path, 'wb') as f:
            content = await experiment_plan.read()
            await f.write(content)
        
        async with aiofiles.open(csv_path, 'wb') as f:
            content = await dataset.read()
            await f.write(content)
        
        # Read the content as text
        async with aiofiles.open(plan_path, 'r', encoding='utf-8') as f:
            plan_content = await f.read()
            
        async with aiofiles.open(csv_path, 'r', encoding='utf-8') as f:
            csv_content = await f.read()
        
        # Generate visualization
        request = GenerateVisualizationRequest(
            prompt=user_prompt,
            plan=plan_content,
            csv=csv_content,
            session_id=session_id
        )
        
        result = await generate_visualization(request)
        
        # Note: Temporary files will be cleaned up when the temp directory is removed
        # In production, you might want to implement proper cleanup
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to upload and analyze: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload and analyze: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=AnalysisSessionResponse)
async def get_session_status(session_id: str):
    """
    Get the current status of an analysis session.
    
    Returns session information including memory, generated visualizations,
    and session statistics.
    """
    try:
        session_data = _get_session(session_id)
        
        return AnalysisSessionResponse(
            session_id=session_id,
            status=session_data["status"],
            visualizations_generated=session_data["visualizations_generated"],
            created_at=session_data["created_at"],
            updated_at=session_data["updated_at"],
            memory=session_data["memory"]
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get session status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session status: {str(e)}"
        )


@router.get("/download/{session_id}")
async def download_visualization(session_id: str):
    """
    Download generated visualization HTML content.
    
    Returns the HTML content of the most recent visualization for the session.
    """
    try:
        session_data = _get_session(session_id)
        
        if not session_data["generated_visualizations"]:
            raise HTTPException(
                status_code=404,
                detail="No visualizations found for this session"
            )
        
        # Get the most recent visualization
        latest_viz = session_data["generated_visualizations"][-1]
        html_content = latest_viz.get("html_content", "")
        
        if not html_content:
            raise HTTPException(
                status_code=404,
                detail="HTML content not found for this visualization"
            )
        
        # Return HTML content as a file response
        return Response(
            content=html_content,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=visualization_{session_id}.html"}
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to download visualization: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download visualization: {str(e)}"
        )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete an analysis session and clean up resources.
    
    Removes session data from memory storage.
    """
    try:
        session_data = _get_session(session_id)
        
        # Remove session from memory
        del _analysis_sessions[session_id]
        
        logger.info(f"🗑️ Deleted analysis session {session_id}")
        
        return {
            "session_id": session_id,
            "status": "deleted",
            "message": "Analysis session deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to delete session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/sessions")
async def list_sessions():
    """
    List all active analysis sessions.
    
    Returns a summary of all active sessions for monitoring and debugging.
    """
    try:
        sessions = []
        for session_id, session_data in _analysis_sessions.items():
            sessions.append({
                "session_id": session_id,
                "status": session_data["status"],
                "visualizations_generated": session_data["visualizations_generated"],
                "created_at": session_data["created_at"],
                "updated_at": session_data["updated_at"]
            })
        
        return {
            "sessions": sessions,
            "total_count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list sessions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/agent-info")
async def get_agent_info():
    """
    Get information about the analysis agent system.
    
    Returns details about the specialized agent team and capabilities.
    """
    return {
        "agent_system": "LangGraph-based Specialized Visualization Agent System",
        "agent_team": [
            {
                "name": "Input Validation Specialist",
                "role": "Data integrity and quality control",
                "expertise": ["Data quality assessment", "File format validation", "Error detection"]
            },
            {
                "name": "Research Methodology Analyst", 
                "role": "Experimental context extraction",
                "expertise": ["Experimental design analysis", "Research methodology", "Variable identification"]
            },
            {
                "name": "Statistical Data Profiling Expert",
                "role": "Data characterization and analysis",
                "expertise": ["Statistical analysis", "Data type detection", "Distribution analysis"]
            },
            {
                "name": "Visualization Design Strategist",
                "role": "Chart selection and design optimization",
                "expertise": ["Chart type selection", "Visual design principles", "Interactive design"]
            },
            {
                "name": "Plotly Code Generation Expert",
                "role": "Interactive visualization development",
                "expertise": ["Plotly proficiency", "Code optimization", "Visual styling"]
            },
            {
                "name": "Scientific Communication Expert",
                "role": "Insight communication and explanation",
                "expertise": ["Scientific writing", "Data interpretation", "User guidance"]
            }
        ],
        "capabilities": [
            "Publication-ready interactive visualizations",
            "Scientifically accurate chart selection",
            "Context-aware design decisions",
            "Clean, maintainable code generation",
            "Clear, insightful explanations",
            "Iterative refinement support"
        ],
        "supported_formats": {
            "input": ["JSON experiment plans", "CSV datasets"],
            "output": ["Interactive HTML", "Static PNG", "Generated code"]
        }
    }


@router.get("/health")
async def analysis_health_check():
    """
    Health check endpoint for the analysis system.
    
    Verifies that all required components are properly configured.
    """
    try:
        # Check OpenAI configuration
        openai_status = "configured" if validate_openai_config() else "not_configured"
        
        # Try to get agent (this will test initialization)
        try:
            agent = _get_analysis_agent()
            agent_status = "initialized"
        except Exception as e:
            agent_status = f"failed: {str(e)}"
        
        # Check plots directory
        plots_dir = Path(__file__).parent.parent / "agents" / "analysis" / "plots"
        plots_dir_status = "exists" if plots_dir.exists() else "missing"
        
        return {
            "status": "healthy" if openai_status == "configured" and "failed" not in agent_status else "unhealthy",
            "openai_status": openai_status,
            "agent_status": agent_status,
            "plots_directory": plots_dir_status,
            "active_sessions": len(_analysis_sessions),
            "specialized_agents": 6
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 