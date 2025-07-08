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
from fastapi.responses import JSONResponse, FileResponse
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
    user_prompt: str = Field(..., description="Natural language analytical question or visualization request")
    experiment_plan_path: str = Field(..., description="Path to experiment plan file")
    csv_file_path: str = Field(..., description="Path to dataset CSV file")
    memory: Optional[Dict[str, Any]] = Field(None, description="Optional memory for iterative refinement")
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")


class GenerateVisualizationResponse(BaseModel):
    """Response model for visualization generation."""
    session_id: str = Field(..., description="Session identifier")
    explanation: str = Field(..., description="Clear explanation of the visualization and findings")
    image_path: str = Field(..., description="Primary path to interactive HTML visualization")
    html_path: str = Field(..., description="Interactive Plotly HTML for exploration")
    png_path: str = Field(..., description="Static PNG image for reports")
    memory: Dict[str, Any] = Field(..., description="Updated memory for context retention")
    llm_code_used: str = Field(..., description="Generated code for transparency")
    warnings: List[str] = Field(..., description="Important caveats or limitations")
    generated_at: datetime = Field(..., description="Generation timestamp")


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
        if not os.path.exists(request.experiment_plan_path):
            raise HTTPException(
                status_code=400,
                detail=f"Experiment plan file not found: {request.experiment_plan_path}"
            )
        
        if not os.path.exists(request.csv_file_path):
            raise HTTPException(
                status_code=400,
                detail=f"CSV file not found: {request.csv_file_path}"
            )
        
        # Get session data for memory
        session_data = _analysis_sessions.get(session_id, {"memory": {}})
        memory = request.memory or session_data.get("memory", {})
        
        logger.info(f"🎯 Generating visualization for session {session_id}")
        logger.info(f"📝 User prompt: {request.user_prompt}")
        logger.info(f"📊 Experiment plan: {request.experiment_plan_path}")
        logger.info(f"📈 Dataset: {request.csv_file_path}")
        
        # Generate visualization using the specialized agent system
        result = agent.generate_visualization(
            user_prompt=request.user_prompt,
            experiment_plan_path=request.experiment_plan_path,
            csv_file_path=request.csv_file_path,
            memory=memory
        )
        
        # Update session data
        if session_id in _analysis_sessions:
            session_data = _analysis_sessions[session_id]
            session_data["visualizations_generated"] += 1
            session_data["updated_at"] = datetime.now()
            session_data["memory"] = result["memory"]
            session_data["generated_visualizations"].append({
                "prompt": request.user_prompt,
                "generated_at": datetime.now(),
                "image_path": result["image_path"],
                "html_path": result["html_path"],
                "png_path": result["png_path"]
            })
            _save_session(session_id, session_data)
        
        logger.info(f"✅ Visualization generated successfully for session {session_id}")
        
        return GenerateVisualizationResponse(
            session_id=session_id,
            explanation=result["explanation"],
            image_path=result["image_path"],
            html_path=result["html_path"],
            png_path=result["png_path"],
            memory=result["memory"],
            llm_code_used=result["llm_code_used"],
            warnings=result["warnings"],
            generated_at=datetime.now()
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
        
        # Save uploaded files
        plan_path = os.path.join(temp_dir, experiment_plan.filename)
        csv_path = os.path.join(temp_dir, dataset.filename)
        
        async with aiofiles.open(plan_path, 'wb') as f:
            content = await experiment_plan.read()
            await f.write(content)
        
        async with aiofiles.open(csv_path, 'wb') as f:
            content = await dataset.read()
            await f.write(content)
        
        # Generate visualization
        request = GenerateVisualizationRequest(
            user_prompt=user_prompt,
            experiment_plan_path=plan_path,
            csv_file_path=csv_path,
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


@router.get("/download/{session_id}/{file_type}")
async def download_visualization(session_id: str, file_type: str):
    """
    Download generated visualization files.
    
    Supports downloading HTML (interactive) and PNG (static) versions
    of generated visualizations.
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
        
        if file_type == "html":
            file_path = latest_viz["html_path"]
            media_type = "text/html"
        elif file_type == "png":
            file_path = latest_viz["png_path"]
            media_type = "image/png"
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Supported types: html, png"
            )
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Visualization file not found: {file_path}"
            )
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=f"visualization_{session_id}.{file_type}"
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
    
    Removes session data and cleans up generated files.
    """
    try:
        session_data = _get_session(session_id)
        
        # Clean up generated files
        for viz in session_data.get("generated_visualizations", []):
            for path_key in ["image_path", "html_path", "png_path"]:
                file_path = viz.get(path_key)
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"⚠️ Could not remove file {file_path}: {e}")
        
        # Remove session
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