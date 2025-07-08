"""
FastAPI endpoints for data cleaning and ingestion.

This module provides REST API endpoints for uploading files, managing data artifacts,
and applying AI-generated suggestions for data cleaning.
"""

import os
import uuid
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
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
from agents.dataclean.image_processor import ImageProcessingAgent
from agents.dataclean.file_processor import FileProcessingAgent
from agents.dataclean.quality_agent import DataQualityAgent
from agents.dataclean.transformation_engine import TransformationEngine
from agents.dataclean.firebase_store import get_data_store
from config import get_openai_client, validate_openai_config

router = APIRouter(prefix="/api/dataclean", tags=["data-cleaning"])

# Initialize the file processing agent
file_processor = FileProcessingAgent()

# Initialize the AI-powered data quality agent
openai_client = get_openai_client()
quality_agent = DataQualityAgent(openai_client) if openai_client else None

# Initialize the transformation engine for Phase 2.5
transformation_engine = TransformationEngine()

# Initialize the EasyOCR processor for better OCR accuracy
from agents.dataclean.easyocr_processor import EasyOCRProcessor
easyocr_processor = EasyOCRProcessor(languages=['en'], gpu=False)  # CPU mode for compatibility

# Keep old image processor as fallback
image_processor = ImageProcessingAgent()

# Initialize Firebase data store (with fallback to in-memory)
data_store = get_data_store()


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
        
        # Store in Firebase (with fallback to in-memory)
        await data_store.save_data_artifact(artifact)
        
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
    artifact = await data_store.get_data_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
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
    artifact = await data_store.get_data_artifact(request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
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
    
    # Update timestamp and save
    artifact.updated_at = datetime.now()
    await data_store.update_data_artifact(artifact)
    
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
    artifact = await data_store.get_data_artifact(request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    artifact.notes = request.notes
    artifact.updated_at = datetime.now()
    await data_store.update_data_artifact(artifact)
    
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
    artifact = await data_store.get_data_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    artifact.status = ProcessingStatus.READY_FOR_ANALYSIS
    artifact.updated_at = datetime.now()
    await data_store.update_data_artifact(artifact)
    
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
    artifact = await data_store.get_data_artifact(request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
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
    await data_store.update_data_artifact(artifact)
    
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
    artifact = await data_store.get_data_artifact(request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    # Get current DataFrame
    df = await data_store.get_dataframe(request.artifact_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Data not available for preview")
    
    # Find the transformation
    transformation = None
    for t in artifact.custom_transformations:
        if t.transformation_id == request.transformation_id:
            transformation = t
            break
    
    if not transformation:
        raise HTTPException(status_code=404, detail="Transformation not found")
    
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
    artifact = await data_store.get_data_artifact(request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    # Get current DataFrame
    df = await data_store.get_dataframe(request.artifact_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Data not available for transformation")
    
    # Find the transformation
    transformation = None
    for t in artifact.custom_transformations:
        if t.transformation_id == request.transformation_id:
            transformation = t
            break
    
    if not transformation:
        raise HTTPException(status_code=404, detail="Transformation not found")
    
    try:
        # Apply transformation
        transformed_df, data_version = await transformation_engine.apply_transformation(
            df, transformation, request.artifact_id, artifact.owner_id
        )
        
        # Update stored DataFrame
        await data_store.save_dataframe(request.artifact_id, transformed_df)
        
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
        await data_store.update_data_artifact(artifact)
        
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
    artifact = await data_store.get_data_artifact(request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
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
        await data_store.save_dataframe(request.artifact_id, reverted_df)
        
        # Update transformation history
        artifact.transformation_history.versions.append(data_version)
        artifact.transformation_history.current_version = data_version.version_number
        artifact.transformation_history.can_undo = len(artifact.transformation_history.versions) > 1
        artifact.transformation_history.can_redo = True
        
        artifact.updated_at = datetime.now()
        await data_store.update_data_artifact(artifact)
        
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


# === Phase 3: OCR Processing Endpoints ===

@router.post("/test-ocr")
async def test_ocr_direct(
    file: UploadFile = File(...),
    processor: str = "easyocr"
):
    """
    Test OCR processing directly without creating data artifacts.
    
    This endpoint is for testing OCR functionality and comparing different
    OCR processors. It processes the image immediately and returns results.
    
    Args:
        file: The uploaded image file
        processor: OCR processor to use ("easyocr", "simple", or "legacy")
        languages: List of language codes for EasyOCR (default: ["en"])
        
    Returns:
        OCR results including extracted data, confidence, and processing notes
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_extension = Path(file.filename).suffix.lower()
        supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif', '.webp']
        
        if file_extension not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format: {file_extension}. Supported: {', '.join(supported_formats)}"
            )
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"test_ocr_{uuid.uuid4()}_{file.filename}")
        
        # Save uploaded file
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Initialize OCR processor based on selection
        if processor == "easyocr":
            ocr_proc = EasyOCRProcessor(languages=['en'], gpu=False)
        elif processor == "simple":
            from agents.dataclean.simple_ocr_processor import SimpleOCRProcessor
            ocr_proc = SimpleOCRProcessor()
        elif processor == "legacy":
            from agents.dataclean.image_processor import ImageProcessingAgent
            ocr_proc = ImageProcessingAgent()
        else:
            raise HTTPException(status_code=400, detail="Invalid processor. Use 'easyocr', 'simple', or 'legacy'")
        
        # Process the image
        start_time = datetime.now()
        ocr_result = await ocr_proc.process_image(temp_file_path)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Clean up temporary file
        os.remove(temp_file_path)
        
        # Format response
        response = {
            "success": True,
            "processor_used": processor,
            "processing_time_seconds": processing_time,
            "file_info": {
                "filename": file.filename,
                "size_bytes": len(content),
                "format": file_extension
            },
            "ocr_results": {
                "confidence": ocr_result.confidence,
                "quality": ocr_result.quality.value if hasattr(ocr_result, 'quality') else "unknown",
                "processing_notes": ocr_result.processing_notes,
                "raw_text": ocr_result.raw_text,
                "extracted_data": {
                    "shape": ocr_result.extracted_data.shape,
                    "columns": list(ocr_result.extracted_data.columns),
                    "sample_data": ocr_result.extracted_data.head(5).to_dict('records') if not ocr_result.extracted_data.empty else [],
                    "empty": ocr_result.extracted_data.empty
                }
            }
        }
        
        # Add processor-specific details
        if processor == "easyocr":
            try:
                if hasattr(ocr_result, 'detected_text_boxes') and ocr_result.detected_text_boxes:
                    response["ocr_results"]["detected_text_boxes"] = len(ocr_result.detected_text_boxes)
                    response["ocr_results"]["text_regions"] = [
                        {
                            "text": box["text"],
                            "confidence": box["confidence"],
                            "bbox": box["bbox"]
                        } for box in ocr_result.detected_text_boxes[:5]  # Show first 5 boxes
                    ]
            except AttributeError:
                pass  # detected_text_boxes not available for this result type
        
        return response
        
    except Exception as e:
        # Clean up temporary file on error
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        raise HTTPException(status_code=500, detail=f"OCR testing failed: {str(e)}")


@router.get("/ocr-processors")
async def get_ocr_processors():
    """
    Get information about available OCR processors.
    
    Returns:
        List of available OCR processors and their capabilities
    """
    try:
        processors = []
        
        # EasyOCR info
        try:
            easyocr_proc = EasyOCRProcessor(languages=['en'], gpu=False)
            processors.append({
                "name": "easyocr",
                "description": "Deep learning-based OCR with high accuracy",
                "supported_languages": await easyocr_proc.get_supported_languages(),
                "supported_formats": await easyocr_proc.get_supported_formats(),
                "features": [
                    "80+ language support",
                    "GPU acceleration",
                    "Text positioning",
                    "Confidence scoring",
                    "Table detection"
                ],
                "status": "available"
            })
        except Exception as e:
            processors.append({
                "name": "easyocr",
                "status": "unavailable",
                "error": str(e)
            })
        
        # Simple OCR info
        try:
            from agents.dataclean.simple_ocr_processor import SimpleOCRProcessor
            simple_proc = SimpleOCRProcessor()
            processors.append({
                "name": "simple",
                "description": "Tesseract-based OCR with image preprocessing",
                "supported_formats": await simple_proc.get_supported_formats(),
                "features": [
                    "Image enhancement",
                    "Tesseract OCR",
                    "Text parsing",
                    "Confidence scoring"
                ],
                "status": "available"
            })
        except Exception as e:
            processors.append({
                "name": "simple",
                "status": "unavailable",
                "error": str(e)
            })
        
        # Legacy image processor info
        try:
            from agents.dataclean.image_processor import ImageProcessingAgent
            processors.append({
                "name": "legacy",
                "description": "OpenCV-based table detection with Tesseract OCR",
                "features": [
                    "Table structure detection",
                    "OpenCV preprocessing",
                    "Tesseract OCR",
                    "Cell positioning"
                ],
                "status": "available"
            })
        except Exception as e:
            processors.append({
                "name": "legacy",
                "status": "unavailable",
                "error": str(e)
            })
        
        return {
            "available_processors": processors,
            "recommended": "easyocr",
            "total_count": len([p for p in processors if p.get("status") == "available"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get processor info: {str(e)}")


@router.post("/upload-image")
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    experiment_id: str = "demo-experiment"
):
    """
    Upload an image file for OCR processing and data extraction.
    
    Args:
        file: The uploaded image file
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
        supported_formats = await easyocr_processor.get_supported_formats()
        
        if file_extension not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image format: {file_extension}. Supported formats: {', '.join(supported_formats)}"
            )
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"{artifact_id}_{file.filename}")
        
        # Save uploaded file
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Validate image file
        if not await easyocr_processor.validate_image_file(temp_file_path):
            os.remove(temp_file_path)
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")
        
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
        
        # Store in Firebase (with fallback to in-memory)
        await data_store.save_data_artifact(artifact)
        
        # Queue background OCR processing
        background_tasks.add_task(process_image_background, artifact_id, temp_file_path)
        
        return {
            "artifact_id": artifact_id,
            "status": "processing",
            "message": "Image uploaded successfully, OCR processing in background"
        }
        
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")


@router.get("/ocr-result/{artifact_id}")
async def get_ocr_result(artifact_id: str):
    """
    Get the OCR processing result for an image.
    
    Args:
        artifact_id: ID of the data artifact
        
    Returns:
        OCR result including extracted data and confidence scores
    """
    artifact = await data_store.get_data_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    # Get extracted DataFrame
    df = await data_store.get_dataframe(artifact_id)
    
    return {
        "artifact_id": artifact_id,
        "status": artifact.status,
        "extracted_data": df.to_dict(orient="records") if df is not None and not df.empty else [],
        "data_shape": [df.shape[0], df.shape[1]] if df is not None else [0, 0],
        "quality_score": artifact.quality_score,
        "suggestions": artifact.suggestions,
        "processing_notes": getattr(artifact, 'processing_notes', []),
        "ocr_confidence": getattr(artifact, 'ocr_confidence', 0.0),
        "created_at": artifact.created_at,
        "updated_at": artifact.updated_at
    }


@router.post("/reprocess-image")
async def reprocess_image(
    background_tasks: BackgroundTasks,
    artifact_id: str,
    tesseract_config: Optional[str] = None
):
    """
    Reprocess an image with different OCR settings.
    
    Args:
        artifact_id: ID of the data artifact
        tesseract_config: Optional custom Tesseract configuration
        
    Returns:
        Success message
    """
    artifact = await data_store.get_data_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    # Check if original file still exists
    if not os.path.exists(artifact.original_file.path):
        raise HTTPException(status_code=404, detail="Original image file not found")
    
    # Update status to processing
    artifact.status = ProcessingStatus.PROCESSING
    artifact.updated_at = datetime.now()
    await data_store.update_data_artifact(artifact)
    
    # Queue reprocessing
    background_tasks.add_task(
        process_image_background,
        artifact_id,
        artifact.original_file.path,
        tesseract_config
    )
    
    return {
        "status": "success",
        "message": "Image reprocessing started"
    }


@router.get("/storage-stats")
async def get_storage_stats():
    """
    Get storage statistics for monitoring.
    
    Returns:
        Storage statistics including counts and storage type
    """
    try:
        stats = await data_store.get_storage_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get storage stats: {str(e)}")


async def process_file_background(artifact_id: str, file_path: str):
    """
    Background task for processing uploaded files with AI analysis.
    
    Args:
        artifact_id: ID of the data artifact
        file_path: Path to the uploaded file
    """
    try:
        # Get the artifact
        artifact = await data_store.get_data_artifact(artifact_id)
        if not artifact:
            print(f"Artifact {artifact_id} not found for background processing")
            return
        
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
                            
                            # Save DataFrame to Firebase
                            await data_store.save_dataframe(artifact_id, full_df)
                            print(f"Stored full DataFrame for transformations: {full_df.shape}")
                        except Exception as df_error:
                            print(f"Could not store full DataFrame: {str(df_error)}")
                            # Fall back to sample data
                            await data_store.save_dataframe(artifact_id, df_sample)
                        
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
            await data_store.update_data_artifact(artifact)
            
            print(f"Processing completed for artifact {artifact_id}")
            
        else:
            # Handle processing error
            artifact.status = ProcessingStatus.ERROR
            artifact.error_message = result.error_message or "File processing failed"
            artifact.updated_at = datetime.now()
            await data_store.update_data_artifact(artifact)
            print(f"File processing failed for artifact {artifact_id}: {artifact.error_message}")
            
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error processing artifact {artifact_id}: {str(e)}")
        artifact = await data_store.get_data_artifact(artifact_id)
        if artifact:
            artifact.status = ProcessingStatus.ERROR
            artifact.error_message = f"Processing failed: {str(e)}"
            artifact.updated_at = datetime.now()
            await data_store.update_data_artifact(artifact)
    
    finally:
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up temporary file: {file_path}")


async def process_image_background(artifact_id: str, image_path: str, tesseract_config: Optional[str] = None):
    """
    Background task for processing uploaded images with OCR.
    
    Args:
        artifact_id: ID of the data artifact
        image_path: Path to the uploaded image file
        tesseract_config: Optional custom Tesseract configuration
    """
    try:
        # Get the artifact
        artifact = await data_store.get_data_artifact(artifact_id)
        if not artifact:
            print(f"Artifact {artifact_id} not found for background processing")
            return
        
        print(f"Starting EasyOCR processing for artifact {artifact_id}")
        
        # Process the image with EasyOCR (better accuracy than pytesseract)
        ocr_result = await easyocr_processor.process_image(image_path)
        
        if ocr_result and not ocr_result.extracted_data.empty:
            print(f"OCR processing completed for artifact {artifact_id}")
            print(f"Extracted data shape: {ocr_result.extracted_data.shape}")
            print(f"OCR confidence: {ocr_result.confidence}")
            
            # Store the extracted DataFrame
            await data_store.save_dataframe(artifact_id, ocr_result.extracted_data)
            
            # Update artifact with OCR results
            artifact.quality_score = ocr_result.confidence
            artifact.ocr_confidence = ocr_result.confidence
            artifact.processing_notes = ocr_result.processing_notes
            
            # AI-powered data quality analysis (if available)
            if quality_agent and openai_client:
                try:
                    print(f"Starting AI quality analysis for OCR data")
                    
                    # Analyze data quality issues
                    quality_issues = await quality_agent.analyze_data(ocr_result.extracted_data)
                    print(f"Found {len(quality_issues)} quality issues")
                    
                    # Generate AI suggestions
                    suggestions = await quality_agent.generate_suggestions(quality_issues, ocr_result.extracted_data)
                    print(f"Generated {len(suggestions)} AI suggestions")
                    
                    # Update artifact with AI-generated suggestions
                    artifact.suggestions = suggestions
                    
                    # Update quality score considering both OCR confidence and AI analysis
                    total_rows = ocr_result.extracted_data.shape[0]
                    total_issues = sum(issue.affected_rows for issue in quality_issues)
                    ai_quality_score = max(0.0, 1.0 - (total_issues / max(total_rows, 1)))
                    
                    # Combine OCR confidence and AI quality score
                    combined_score = (ocr_result.confidence * 0.6) + (ai_quality_score * 0.4)
                    artifact.quality_score = round(combined_score, 2)
                    
                    print(f"Combined quality score: {artifact.quality_score}")
                    
                except Exception as ai_error:
                    print(f"AI analysis failed for OCR data {artifact_id}: {str(ai_error)}")
                    # Continue without AI suggestions
                    
            else:
                print("OpenAI not configured - skipping AI analysis for OCR data")
            
            # Update artifact status
            artifact.status = ProcessingStatus.PENDING_REVIEW
            artifact.updated_at = datetime.now()
            await data_store.update_data_artifact(artifact)
            
            print(f"OCR processing completed for artifact {artifact_id}")
            
        else:
            # Handle OCR processing failure
            artifact.status = ProcessingStatus.ERROR
            artifact.error_message = "OCR processing failed - no data extracted"
            artifact.quality_score = 0.0
            artifact.processing_notes = ocr_result.processing_notes if ocr_result else ["OCR processing failed"]
            artifact.updated_at = datetime.now()
            await data_store.update_data_artifact(artifact)
            print(f"OCR processing failed for artifact {artifact_id}")
            
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error processing OCR artifact {artifact_id}: {str(e)}")
        artifact = await data_store.get_data_artifact(artifact_id)
        if artifact:
            artifact.status = ProcessingStatus.ERROR
            artifact.error_message = f"OCR processing failed: {str(e)}"
            artifact.quality_score = 0.0
            artifact.updated_at = datetime.now()
            await data_store.update_data_artifact(artifact)
    
    finally:
        # Clean up temporary file
        if os.path.exists(image_path):
            os.remove(image_path)
            print(f"Cleaned up temporary image file: {image_path}") 