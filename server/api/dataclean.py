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
from agents.dataclean.quality_agent import DataQualityAgent
from config import get_openai_client, validate_openai_config

router = APIRouter(prefix="/api/dataclean", tags=["data-cleaning"])

# Initialize the file processing agent
file_processor = FileProcessingAgent()

# Initialize the AI-powered data quality agent
openai_client = get_openai_client()
quality_agent = DataQualityAgent(openai_client) if openai_client else None

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
    Background task for processing uploaded files with AI analysis.
    
    Args:
        artifact_id: ID of the data artifact
        file_path: Path to the uploaded file
    """
    try:
        # Get the artifact
        artifact = data_artifacts[artifact_id]
        
        # Step 1: Process the file
        result = await file_processor.process_file(file_path, artifact.original_file.mime_type)
        
        if result.success and result.data_preview:
            print(f"File processing completed for artifact {artifact_id}")
            
            # Step 2: AI-powered data quality analysis (if available)
            if quality_agent and openai_client:
                try:
                    # Convert data preview back to DataFrame for AI analysis
                    sample_data = result.data_preview['sample_rows']
                    if sample_data:
                        # Create a small DataFrame from sample data for analysis
                        import pandas as pd
                        df_sample = pd.DataFrame(sample_data)
                        
                        print(f"Starting AI quality analysis for artifact {artifact_id}")
                        
                        # Analyze data quality issues
                        quality_issues = await quality_agent.analyze_data(df_sample)
                        print(f"Found {len(quality_issues)} quality issues")
                        
                        # Generate AI suggestions
                        suggestions = await quality_agent.generate_suggestions(quality_issues, df_sample)
                        print(f"Generated {len(suggestions)} AI suggestions")
                        
                        # Update artifact with AI-generated suggestions
                        artifact.suggestions = suggestions
                        
                        # Calculate quality score based on issues found
                        total_rows = df_sample.shape[0]
                        total_issues = sum(issue.affected_rows for issue in quality_issues)
                        quality_score = max(0.0, 1.0 - (total_issues / max(total_rows, 1)))
                        artifact.quality_score = round(quality_score, 2)
                        
                        print(f"Quality score: {artifact.quality_score}")
                        
                except Exception as ai_error:
                    print(f"AI analysis failed for artifact {artifact_id}: {str(ai_error)}")
                    # Continue without AI suggestions - still mark as pending review
                    
            else:
                print("OpenAI not configured - skipping AI analysis")
                
            # Update artifact status
            artifact.status = ProcessingStatus.PENDING_REVIEW
            artifact.updated_at = datetime.now()
            
            print(f"Processing completed for artifact {artifact_id}")
            
        else:
            # Handle processing error
            artifact.status = ProcessingStatus.ERROR
            artifact.error_message = result.error_message or "File processing failed"
            artifact.updated_at = datetime.now()
            print(f"File processing failed for artifact {artifact_id}: {artifact.error_message}")
            
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error processing artifact {artifact_id}: {str(e)}")
        artifact = data_artifacts[artifact_id]
        artifact.status = ProcessingStatus.ERROR
        artifact.error_message = f"Processing failed: {str(e)}"
        artifact.updated_at = datetime.now()
    
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up temporary file: {file_path}") 