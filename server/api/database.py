"""
FastAPI endpoints for database operations.

This module provides REST API endpoints for managing experiments in the database,
including creating, updating, and retrieving experiment records.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import Experiment, get_db, init_db, check_db_connection

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/database", tags=["database"])

# Request/Response Models
class CreateExperimentRequest(BaseModel):
    """Request model for creating a new experiment."""
    title: Optional[str] = Field(None, description="Optional title for the experiment")
    description: Optional[str] = Field(None, description="Optional description for the experiment")
    experimental_plan: Optional[str] = Field(None, description="Experimental plan text content")
    visualization_html: Optional[str] = Field(None, description="HTML visualization content")
    csv_data: Optional[str] = Field(None, description="CSV data content")


class UpdatePlanRequest(BaseModel):
    """Request model for updating experiment plan."""
    experimental_plan: str = Field(..., description="Updated experimental plan text content")


class UpdateHtmlRequest(BaseModel):
    """Request model for updating experiment HTML visualization."""
    visualization_html: str = Field(..., description="Updated HTML visualization content")


class UpdateCsvRequest(BaseModel):
    """Request model for updating experiment CSV data."""
    csv_data: str = Field(..., description="Updated CSV data content")
    is_agent_update: bool = Field(False, description="Whether this update is from an AI agent")
    expected_version: Optional[int] = Field(None, description="Expected CSV version for optimistic locking")


class UpdateTitleRequest(BaseModel):
    """Request model for updating experiment title."""
    title: str = Field(..., description="Updated experiment title")


class AcceptRejectChangesRequest(BaseModel):
    """Request model for accepting or rejecting CSV changes."""
    action: str = Field(..., description="Action to perform: 'accept' or 'reject'", pattern="^(accept|reject)$")


class ExperimentResponse(BaseModel):
    """Response model for experiment data."""
    id: str = Field(..., description="Unique experiment identifier")
    title: Optional[str] = Field(None, description="Experiment title")
    description: Optional[str] = Field(None, description="Experiment description")
    experimental_plan: Optional[str] = Field(None, description="Experimental plan text")
    visualization_html: Optional[str] = Field(None, description="HTML visualization content")
    csv_data: Optional[str] = Field(None, description="CSV data content")
    previous_csv: Optional[str] = Field(None, description="Previous CSV data before agent modifications")
    csv_version: int = Field(0, description="CSV version number for optimistic locking")
    agent_modified_at: Optional[datetime] = Field(None, description="Timestamp of last agent modification")
    modification_source: str = Field("user", description="Source of last modification (user/agent)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ExperimentListResponse(BaseModel):
    """Response model for listing experiments."""
    experiments: List[ExperimentResponse] = Field(..., description="List of experiments")
    total_count: int = Field(..., description="Total number of experiments")


class DatabaseStatsResponse(BaseModel):
    """Response model for database statistics."""
    total_experiments: int = Field(..., description="Total number of experiments")
    connection_status: str = Field(..., description="Database connection status")
    database_initialized: bool = Field(..., description="Whether database tables exist")


# Utility Functions
def _experiment_to_response(experiment: Experiment) -> ExperimentResponse:
    """Convert Experiment model to response model."""
    return ExperimentResponse(
        id=experiment.id,
        title=experiment.title,
        description=experiment.description,
        experimental_plan=experiment.experimental_plan,
        visualization_html=experiment.visualization_html,
        csv_data=experiment.csv_data,
        previous_csv=experiment.previous_csv,
        csv_version=experiment.csv_version,
        agent_modified_at=experiment.agent_modified_at,
        modification_source=experiment.modification_source,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at
    )


# API Endpoints
@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    request: CreateExperimentRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new experiment record.
    
    Creates a new experiment with the provided data. All fields are optional
    and can be updated later using the update endpoints.
    """
    try:
        # Create new experiment
        experiment = Experiment(
            title=request.title,
            description=request.description,
            experimental_plan=request.experimental_plan,
            visualization_html=request.visualization_html,
            csv_data=request.csv_data
        )
        
        # Save to database
        db.add(experiment)
        db.commit()
        db.refresh(experiment)
        
        logger.info(f"Created new experiment: {experiment.id}")
        
        return _experiment_to_response(experiment)
        
    except SQLAlchemyError as e:
        logger.error(f"Database error creating experiment: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating experiment: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create experiment: {str(e)}"
        )


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific experiment by ID.
    
    Retrieves the complete experiment record including all text fields.
    """
    try:
        # Query experiment by ID
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment with ID {experiment_id} not found"
            )
        
        logger.info(f"Retrieved experiment: {experiment_id}")
        
        return _experiment_to_response(experiment)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving experiment {experiment_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving experiment {experiment_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve experiment: {str(e)}"
        )


@router.put("/experiments/{experiment_id}/plan", response_model=ExperimentResponse)
async def update_experiment_plan(
    experiment_id: str,
    request: UpdatePlanRequest,
    db: Session = Depends(get_db)
):
    """
    Update the experimental plan text for a specific experiment.
    
    Updates only the experimental_plan field, leaving other fields unchanged.
    """
    try:
        # Query experiment by ID
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment with ID {experiment_id} not found"
            )
        
        # Update the plan
        experiment.experimental_plan = request.experimental_plan
        experiment.updated_at = datetime.now()
        
        # Save changes
        db.commit()
        db.refresh(experiment)
        
        logger.info(f"Updated plan for experiment: {experiment_id}")
        
        return _experiment_to_response(experiment)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating plan for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating plan for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update experiment plan: {str(e)}"
        )


@router.put("/experiments/{experiment_id}/html", response_model=ExperimentResponse)
async def update_experiment_html(
    experiment_id: str,
    request: UpdateHtmlRequest,
    db: Session = Depends(get_db)
):
    """
    Update the HTML visualization for a specific experiment.
    
    Updates only the visualization_html field, leaving other fields unchanged.
    """
    try:
        # Query experiment by ID
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment with ID {experiment_id} not found"
            )
        
        # Update the HTML
        experiment.visualization_html = request.visualization_html
        experiment.updated_at = datetime.now()
        
        # Save changes
        db.commit()
        db.refresh(experiment)
        
        logger.info(f"Updated HTML for experiment: {experiment_id}")
        
        return _experiment_to_response(experiment)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating HTML for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating HTML for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update experiment HTML: {str(e)}"
        )


@router.put("/experiments/{experiment_id}/csv", response_model=ExperimentResponse)
async def update_experiment_csv(
    experiment_id: str,
    request: UpdateCsvRequest,
    db: Session = Depends(get_db)
):
    """
    Update the CSV data for a specific experiment with version control.
    
    Supports optimistic locking and tracks agent vs user modifications.
    """
    try:
        # Query experiment by ID with row-level lock
        experiment = db.query(Experiment).filter(
            Experiment.id == experiment_id
        ).with_for_update().first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment with ID {experiment_id} not found"
            )
        
        # Version check for optimistic locking
        if request.expected_version is not None and request.expected_version != experiment.csv_version:
            raise HTTPException(
                status_code=409,
                detail=f"Version conflict: expected {request.expected_version}, current {experiment.csv_version}"
            )
        
        # Backup current state for agent updates
        if request.is_agent_update:
            experiment.previous_csv = experiment.csv_data
            experiment.agent_modified_at = datetime.now()
            experiment.modification_source = 'agent'
        else:
            experiment.modification_source = 'user'
        
        # Update the CSV data
        experiment.csv_data = request.csv_data
        experiment.csv_version += 1
        experiment.updated_at = datetime.now()
        
        # Save changes
        db.commit()
        db.refresh(experiment)
        
        logger.info(f"Updated CSV data for experiment: {experiment_id} (version: {experiment.csv_version}, source: {experiment.modification_source})")
        
        return _experiment_to_response(experiment)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating CSV for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating CSV for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update experiment CSV: {str(e)}"
        )


@router.get("/experiments/{experiment_id}/diff")
async def get_experiment_diff(
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """
    Get CSV differences between current and previous versions.
    
    Returns diff information for experiments modified by agents.
    """
    try:
        # Query experiment by ID
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment with ID {experiment_id} not found"
            )
        
        # Check if there's a previous version to compare
        if not experiment.previous_csv:
            return {
                "experiment_id": experiment_id,
                "has_diff": False,
                "message": "No previous version available for comparison"
            }
        
        return {
            "experiment_id": experiment_id,
            "has_diff": True,
            "current_csv": experiment.csv_data,
            "previous_csv": experiment.previous_csv,
            "csv_version": experiment.csv_version,
            "agent_modified_at": experiment.agent_modified_at,
            "modification_source": experiment.modification_source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting diff for experiment {experiment_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get experiment diff: {str(e)}"
        )


@router.post("/experiments/{experiment_id}/csv/accept-reject", response_model=ExperimentResponse)
async def accept_reject_csv_changes(
    experiment_id: str,
    request: AcceptRejectChangesRequest,
    db: Session = Depends(get_db)
):
    """
    Accept or reject CSV changes made by an AI agent.
    
    Accept: Keeps the current CSV and clears the previous version.
    Reject: Restores the previous CSV and discards agent changes.
    """
    try:
        # Query experiment by ID with row-level lock
        experiment = db.query(Experiment).filter(
            Experiment.id == experiment_id
        ).with_for_update().first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment with ID {experiment_id} not found"
            )
        
        # Check if there are changes to accept/reject
        if not experiment.previous_csv:
            raise HTTPException(
                status_code=400,
                detail="No pending changes to accept or reject"
            )
        
        if request.action == "accept":
            # Accept changes: clear previous version
            experiment.previous_csv = None
            experiment.modification_source = 'user'
            logger.info(f"Accepted CSV changes for experiment: {experiment_id}")
        else:  # reject
            # Reject changes: restore previous version
            experiment.csv_data = experiment.previous_csv
            experiment.previous_csv = None
            experiment.modification_source = 'user'
            experiment.csv_version += 1
            logger.info(f"Rejected CSV changes for experiment: {experiment_id}")
        
        experiment.updated_at = datetime.now()
        
        # Save changes
        db.commit()
        db.refresh(experiment)
        
        return _experiment_to_response(experiment)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error processing accept/reject for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing accept/reject for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process accept/reject: {str(e)}"
        )


@router.put("/experiments/{experiment_id}/title", response_model=ExperimentResponse)
async def update_experiment_title(
    experiment_id: str,
    request: UpdateTitleRequest,
    db: Session = Depends(get_db)
):
    """
    Update the title for a specific experiment.
    
    Updates only the title field, leaving other fields unchanged.
    """
    try:
        # Query experiment by ID
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment with ID {experiment_id} not found"
            )
        
        # Update the title
        experiment.title = request.title
        experiment.updated_at = datetime.now()
        
        # Save changes
        db.commit()
        db.refresh(experiment)
        
        logger.info(f"Updated title for experiment: {experiment_id}")
        
        return _experiment_to_response(experiment)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating title for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating title for experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update experiment title: {str(e)}"
        )


@router.get("/experiments", response_model=ExperimentListResponse)
async def list_experiments(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all experiments with pagination.
    
    Returns a paginated list of all experiments in the database.
    """
    try:
        # Query experiments with pagination
        experiments = db.query(Experiment).offset(offset).limit(limit).all()
        
        # Get total count
        total_count = db.query(Experiment).count()
        
        # Convert to response models
        experiment_responses = [_experiment_to_response(exp) for exp in experiments]
        
        logger.info(f"Retrieved {len(experiments)} experiments (total: {total_count})")
        
        return ExperimentListResponse(
            experiments=experiment_responses,
            total_count=total_count
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error listing experiments: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing experiments: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list experiments: {str(e)}"
        )


@router.delete("/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a specific experiment by ID.
    
    Permanently removes the experiment from the database.
    """
    try:
        # Query experiment by ID
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail=f"Experiment with ID {experiment_id} not found"
            )
        
        # Delete the experiment
        db.delete(experiment)
        db.commit()
        
        logger.info(f"Deleted experiment: {experiment_id}")
        
        return {
            "experiment_id": experiment_id,
            "status": "deleted",
            "message": "Experiment deleted successfully"
        }
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting experiment {experiment_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete experiment: {str(e)}"
        )


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats(db: Session = Depends(get_db)):
    """
    Get database statistics and health information.
    
    Returns information about the database state and connection health.
    """
    try:
        # Get total experiment count
        total_experiments = db.query(Experiment).count()
        
        # Check connection health
        connection_status = "healthy" if check_db_connection() else "unhealthy"
        
        return DatabaseStatsResponse(
            total_experiments=total_experiments,
            connection_status=connection_status,
            database_initialized=True
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database stats: {str(e)}"
        )


@router.post("/init")
async def initialize_database():
    """
    Initialize the database tables.
    
    Creates the database tables if they don't exist. Safe to call multiple times.
    """
    try:
        init_db()
        
        logger.info("Database initialized successfully")
        
        return {
            "status": "success",
            "message": "Database initialized successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize database: {str(e)}"
        )


@router.get("/health")
async def database_health_check():
    """
    Health check endpoint for the database system.
    
    Verifies database connection and returns system status.
    """
    try:
        # Check database connection
        connection_healthy = check_db_connection()
        
        # Get basic stats if connection is healthy
        if connection_healthy:
            # Use a simple query to test functionality
            with next(get_db()) as db:
                total_experiments = db.query(Experiment).count()
        else:
            total_experiments = 0
        
        return {
            "status": "healthy" if connection_healthy else "unhealthy",
            "database_connection": "connected" if connection_healthy else "disconnected",
            "total_experiments": total_experiments,
            "database_type": "sqlite",
            "tables_initialized": connection_healthy
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_connection": "error"
        } 