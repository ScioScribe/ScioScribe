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
    FileMetadata,
    CreateCustomTransformationRequest,
    PreviewTransformationRequest,
    ApplyTransformationRequest,
    SaveTransformationRuleRequest,
    UndoTransformationRequest,
    RedoTransformationRequest,
    SearchRulesRequest,
    CustomTransformation,
    TransformationAction,
    ValueMapping
)
from agents.dataclean.file_processor import FileProcessingAgent
from agents.dataclean.quality_agent import DataQualityAgent
from agents.dataclean.transformation_engine import TransformationEngine
from config import get_openai_client, validate_openai_config

router = APIRouter(prefix="/api/dataclean", tags=["data-cleaning"])

# Initialize the file processing agent
file_processor = FileProcessingAgent()

# Initialize the AI-powered data quality agent
openai_client = get_openai_client()
quality_agent = DataQualityAgent(openai_client) if openai_client else None

# Initialize the transformation engine for Phase 2.5
transformation_engine = TransformationEngine()

# In-memory storage for demo purposes (replace with Firestore later)
data_artifacts: Dict[str, DataArtifact] = {}

# In-memory storage for current DataFrames (replace with persistent storage later)
current_dataframes: Dict[str, Any] = {}


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


# === Phase 2.5: Interactive Transformation Endpoints ===

@router.post("/create-custom-transformation")
async def create_custom_transformation(request: CreateCustomTransformationRequest):
    """
    Create a custom transformation based on user input.
    
    Args:
        request: Custom transformation specification
        
    Returns:
        Created transformation details
    """
    if request.artifact_id not in data_artifacts:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    artifact = data_artifacts[request.artifact_id]
    
    # Create transformation
    transformation = CustomTransformation(
        transformation_id=str(uuid.uuid4()),
        column=request.column,
        action=request.action,
        value_mappings=request.value_mappings,
        parameters=request.parameters,
        description=request.description,
        created_by=artifact.owner_id,
        created_at=datetime.now()
    )
    
    # Add to artifact
    artifact.custom_transformations.append(transformation)
    artifact.updated_at = datetime.now()
    
    return {
        "status": "success",
        "transformation_id": transformation.transformation_id,
        "message": "Custom transformation created successfully"
    }


@router.post("/preview-transformation")
async def preview_transformation(request: PreviewTransformationRequest):
    """
    Preview the effects of a transformation without applying it.
    
    Args:
        request: Preview request with transformation details
        
    Returns:
        Transformation preview with before/after samples
    """
    if request.artifact_id not in data_artifacts:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    if request.artifact_id not in current_dataframes:
        raise HTTPException(status_code=404, detail="Data not available for preview")
    
    artifact = data_artifacts[request.artifact_id]
    
    # Find the transformation
    transformation = None
    for t in artifact.custom_transformations:
        if t.transformation_id == request.transformation_id:
            transformation = t
            break
    
    if not transformation:
        raise HTTPException(status_code=404, detail="Transformation not found")
    
    # Get current DataFrame
    df = current_dataframes[request.artifact_id]
    
    try:
        # Generate preview
        preview = await transformation_engine.create_transformation_preview(df, transformation)
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@router.post("/apply-transformation")
async def apply_transformation(request: ApplyTransformationRequest):
    """
    Apply a custom transformation to the data.
    
    Args:
        request: Transformation application request
        
    Returns:
        Success message and updated artifact info
    """
    if request.artifact_id not in data_artifacts:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    if request.artifact_id not in current_dataframes:
        raise HTTPException(status_code=404, detail="Data not available for transformation")
    
    artifact = data_artifacts[request.artifact_id]
    
    # Find the transformation
    transformation = None
    for t in artifact.custom_transformations:
        if t.transformation_id == request.transformation_id:
            transformation = t
            break
    
    if not transformation:
        raise HTTPException(status_code=404, detail="Transformation not found")
    
    # Get current DataFrame
    df = current_dataframes[request.artifact_id]
    
    try:
        # Apply transformation
        transformed_df, data_version = await transformation_engine.apply_transformation(
            df, transformation, request.artifact_id, artifact.owner_id
        )
        
        # Update stored DataFrame
        current_dataframes[request.artifact_id] = transformed_df
        
        # Update artifact with version history
        if not artifact.transformation_history:
            from agents.dataclean.models import TransformationHistory
            artifact.transformation_history = TransformationHistory(
                artifact_id=request.artifact_id,
                current_version=data_version.version_number,
                versions=[data_version],
                can_undo=True,
                can_redo=False
            )
        else:
            artifact.transformation_history.versions.append(data_version)
            artifact.transformation_history.current_version = data_version.version_number
            artifact.transformation_history.can_undo = True
            artifact.transformation_history.can_redo = False
        
        # Save as rule if requested
        if request.save_as_rule and request.rule_name:
            rule = await transformation_engine.save_transformation_rule(
                transformation,
                request.rule_name,
                request.rule_description or transformation.description,
                transformation.column,  # Use column name as pattern
                artifact.owner_id
            )
            artifact.saved_rules.append(rule.rule_id)
        
        artifact.updated_at = datetime.now()
        
        return {
            "status": "success",
            "version": data_version.version_number,
            "message": "Transformation applied successfully",
            "can_undo": True,
            "can_redo": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transformation failed: {str(e)}")


@router.post("/undo-transformation")
async def undo_transformation(request: UndoTransformationRequest):
    """
    Undo the last transformation.
    
    Args:
        request: Undo request
        
    Returns:
        Success message and updated state
    """
    if request.artifact_id not in data_artifacts:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    artifact = data_artifacts[request.artifact_id]
    
    if not artifact.transformation_history:
        raise HTTPException(status_code=400, detail="No transformation history available")
    
    if not artifact.transformation_history.can_undo:
        raise HTTPException(status_code=400, detail="Cannot undo: already at first version")
    
    try:
        # Undo transformation
        reverted_df, data_version = await transformation_engine.undo_transformation(
            request.artifact_id,
            artifact.transformation_history.current_version,
            artifact.owner_id
        )
        
        # Update stored DataFrame
        current_dataframes[request.artifact_id] = reverted_df
        
        # Update transformation history
        artifact.transformation_history.versions.append(data_version)
        artifact.transformation_history.current_version = data_version.version_number
        artifact.transformation_history.can_undo = len(artifact.transformation_history.versions) > 1
        artifact.transformation_history.can_redo = True
        
        artifact.updated_at = datetime.now()
        
        return {
            "status": "success",
            "version": data_version.version_number,
            "message": "Transformation undone successfully",
            "can_undo": artifact.transformation_history.can_undo,
            "can_redo": artifact.transformation_history.can_redo
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Undo failed: {str(e)}")


@router.post("/search-transformation-rules")
async def search_transformation_rules(request: SearchRulesRequest):
    """
    Search for saved transformation rules.
    
    Args:
        request: Search criteria
        
    Returns:
        List of matching transformation rules
    """
    try:
        rules = await transformation_engine.search_transformation_rules(
            column_name=request.column_name,
            action=request.action,
            search_term=request.search_term,
            user_id=request.owner_id
        )
        
        return {
            "status": "success",
            "rules": rules,
            "count": len(rules)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule search failed: {str(e)}")


@router.post("/save-transformation-rule")
async def save_transformation_rule(request: SaveTransformationRuleRequest):
    """
    Save a transformation as a reusable rule.
    
    Args:
        request: Rule saving request
        
    Returns:
        Success message and rule details
    """
    # This endpoint is called when saving a rule manually
    # (The apply_transformation endpoint can also save rules automatically)
    
    # Find the transformation (this would typically be from a temporary store)
    # For now, we'll return a placeholder implementation
    
    return {
        "status": "success",
        "message": "Rule saving functionality will be implemented in the frontend workflow"
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
                        
                        # Store full DataFrame for Phase 2.5 transformations
                        # Read the full file again for transformations
                        try:
                            if file_path.endswith('.csv'):
                                full_df = pd.read_csv(file_path)
                            elif file_path.endswith(('.xlsx', '.xls')):
                                full_df = pd.read_excel(file_path)
                            else:
                                full_df = df_sample
                            
                            current_dataframes[artifact_id] = full_df
                            print(f"Stored full DataFrame for transformations: {full_df.shape}")
                        except Exception as df_error:
                            print(f"Could not store full DataFrame: {str(df_error)}")
                            # Fall back to sample data
                            current_dataframes[artifact_id] = df_sample
                        
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