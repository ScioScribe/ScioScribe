"""
FastAPI endpoints for data cleaning and ingestion.

This module provides REST API endpoints for uploading files, managing data artifacts,
and applying AI-generated suggestions for data cleaning.
"""

import os
import uuid
import tempfile
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import aiofiles

from agents.dataclean.models import (
    DataArtifact,
    ProcessingStatus,
    ApplySuggestionRequest,
    UpdateNotesRequest,
    FileMetadata
)
from agents.dataclean.file_processor import FileProcessingAgent

router = APIRouter(prefix="/api/dataclean", tags=["data-cleaning"])

# Initialize the file processing agent
file_processor = FileProcessingAgent()

# In-memory storage for demo purposes (replace with Firestore later)
data_artifacts: Dict[str, DataArtifact] = {}


@router.post("/upload-file")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    experiment_id: str = "demo-experiment"
):
    """
    Upload a file for data cleaning and processing.
    
    Args:
        file: The uploaded file
        experiment_id: ID of the experiment this data belongs to
        
    Returns:
        Dict containing the artifact_id and processing status
    """
    try:
        # Generate unique artifact ID
        artifact_id = str(uuid.uuid4())
        
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ['.csv', '.xlsx', '.xls']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_extension}"
            )
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"{artifact_id}_{file.filename}")
        
        # Save uploaded file
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create file metadata
        file_metadata = FileMetadata(
            name=file.filename,
            path=temp_file_path,
            size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            uploaded_at=datetime.now()
        )
        
        # Create data artifact
        artifact = DataArtifact(
            artifact_id=artifact_id,
            experiment_id=experiment_id,
            owner_id="demo-user",  # Replace with actual user ID
            status=ProcessingStatus.PROCESSING,
            original_file=file_metadata,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store in memory (replace with Firestore later)
        data_artifacts[artifact_id] = artifact
        
        # Queue background processing
        background_tasks.add_task(process_file_background, artifact_id, temp_file_path)
        
        return {
            "artifact_id": artifact_id,
            "status": "processing",
            "message": "File uploaded successfully, processing in background"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/data-artifact/{artifact_id}")
async def get_data_artifact(artifact_id: str):
    """
    Retrieve the current state of a data artifact.
    
    Args:
        artifact_id: ID of the data artifact
        
    Returns:
        DataArtifact object with current status and suggestions
    """
    if artifact_id not in data_artifacts:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    artifact = data_artifacts[artifact_id]
    return artifact


@router.post("/apply-suggestion")
async def apply_suggestion(request: ApplySuggestionRequest):
    """
    Apply or reject a data quality suggestion.
    
    Args:
        request: Contains artifact_id, suggestion_id, and action
        
    Returns:
        Success message
    """
    if request.artifact_id not in data_artifacts:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    artifact = data_artifacts[request.artifact_id]
    
    # Find the suggestion
    suggestion = None
    for s in artifact.suggestions:
        if s.suggestion_id == request.suggestion_id:
            suggestion = s
            break
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    # For now, just log the action (implement actual data transformation later)
    action_msg = f"Suggestion {request.suggestion_id} was {request.action}ed"
    
    # Update timestamp
    artifact.updated_at = datetime.now()
    
    return {
        "status": "success",
        "message": action_msg
    }


@router.post("/update-notes")
async def update_notes(request: UpdateNotesRequest):
    """
    Update the notes for a data artifact.
    
    Args:
        request: Contains artifact_id and notes
        
    Returns:
        Success message
    """
    if request.artifact_id not in data_artifacts:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    artifact = data_artifacts[request.artifact_id]
    artifact.notes = request.notes
    artifact.updated_at = datetime.now()
    
    return {
        "status": "success",
        "message": "Notes updated successfully"
    }


@router.post("/finalize-data/{artifact_id}")
async def finalize_data(artifact_id: str):
    """
    Finalize the data artifact and mark it ready for analysis.
    
    Args:
        artifact_id: ID of the data artifact
        
    Returns:
        Success message
    """
    if artifact_id not in data_artifacts:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    artifact = data_artifacts[artifact_id]
    artifact.status = ProcessingStatus.READY_FOR_ANALYSIS
    artifact.updated_at = datetime.now()
    
    return {
        "status": "success",
        "message": "Data artifact finalized and ready for analysis"
    }


async def process_file_background(artifact_id: str, file_path: str):
    """
    Background task for processing uploaded files.
    
    Args:
        artifact_id: ID of the data artifact
        file_path: Path to the uploaded file
    """
    try:
        # Get the artifact
        artifact = data_artifacts[artifact_id]
        
        # Process the file
        result = await file_processor.process_file(file_path, artifact.original_file.mime_type)
        
        if result.success:
            # Update artifact with processing results
            artifact.status = ProcessingStatus.PENDING_REVIEW
            artifact.updated_at = datetime.now()
            
            # For now, add a simple mock suggestion
            # (Replace with actual AI analysis later)
            mock_suggestion = {
                "suggestion_id": str(uuid.uuid4()),
                "type": "convert_datatype",
                "column": "example_column",
                "description": "Convert text column to numeric",
                "confidence": 0.85,
                "risk_level": "low",
                "transformation": {"action": "convert", "target_type": "float"},
                "explanation": "This column appears to contain numeric values stored as text"
            }
            
            # Note: This is a simplified mock - actual suggestions would come from AI analysis
            print(f"Processing completed for artifact {artifact_id}")
            print(f"Data preview: {result.data_preview}")
            
        else:
            # Handle processing error
            artifact.status = ProcessingStatus.ERROR
            artifact.error_message = result.error_message
            artifact.updated_at = datetime.now()
            
    except Exception as e:
        # Handle unexpected errors
        artifact = data_artifacts[artifact_id]
        artifact.status = ProcessingStatus.ERROR
        artifact.error_message = f"Processing failed: {str(e)}"
        artifact.updated_at = datetime.now()
    
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path) 