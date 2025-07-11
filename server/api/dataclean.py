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
    ValueMapping,
    ProcessFileCompleteRequest,
    ProcessFileCompleteResponse,
    # CSV models (Task 1.1)
    CSVMessageRequest,
    CSVProcessingResponse,
    CSVTransformationRequest,
    CSVConversationState,
    CSVAnalysisResult,
    # Header generation models
    GenerateHeadersRequest,
    GenerateHeadersResponse
)
from agents.dataclean.file_processor import FileProcessingAgent
from agents.dataclean.quality_agent import DataQualityAgent
from agents.dataclean.transformation_engine import TransformationEngine
from agents.dataclean.suggestion_converter import SuggestionConverter
from agents.dataclean.complete_processor import CompleteFileProcessor
from agents.dataclean.memory_store import get_data_store
from config import get_openai_client, validate_openai_config

import logging
import json
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from datetime import datetime
from starlette.websockets import WebSocketState

# Set up module logger
logger = logging.getLogger(__name__)

# Active WebSocket connections for conversation sessions
_active_ws_connections: Dict[str, WebSocket] = {}

# Router initialization (moved up to support WebSocket decorators)
router = APIRouter(prefix="/api/dataclean", tags=["data-cleaning"])

# === WebSocket Message Models ===
class WebSocketMessage(BaseModel):
    """Generic WebSocket message structure."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message payload")
    session_id: str = Field(..., description="Conversation session identifier")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class UserMessage(BaseModel):
    """User message sent from the frontend."""
    type: str = Field(default="user_message")
    data: Dict[str, str] = Field(..., description="Must contain 'content'")
    session_id: str


class ConversationUpdate(BaseModel):
    """Assistant response back to the frontend."""
    type: str = Field(default="conversation_update")
    data: Dict[str, Any] = Field(..., description="Updated conversation state/response")
    session_id: str


class ApprovalRequest(BaseModel):
    """Request the user's confirmation for an operation."""
    type: str = Field(default="approval_request")
    data: Dict[str, Any] = Field(..., description="Approval details")
    session_id: str


class ApprovalResponse(BaseModel):
    """User's approval/confirmation response."""
    type: str = Field(default="approval_response")
    data: Dict[str, Any] = Field(..., description="Contains 'approved' and optional 'feedback'")
    session_id: str


class ErrorMessage(BaseModel):
    """Error message pushed to the frontend."""
    type: str = Field(default="error")
    data: Dict[str, str] = Field(..., description="Contains 'message'")
    session_id: str


class SessionStatusMessage(BaseModel):
    """Session status / heartbeat message."""
    type: str = Field(default="session_status")
    data: Dict[str, Any] = Field(..., description="Session status payload")
    session_id: str


# === HTTP Conversation Message Models ===
class ConversationMessageRequest(BaseModel):
    """Schema for POST /conversation/message request body."""
    user_message: str = Field(..., description="User's natural language prompt")
    session_id: str = Field(..., description="Conversation session identifier")
    user_id: Optional[str] = Field("demo-user", description="User identifier")
    artifact_id: Optional[str] = Field(None, description="Optional data artifact ID to link")

class ConversationMessageResponseModel(BaseModel):
    """Canonical shape of conversation response sent back to the frontend."""
    success: bool
    session_id: str
    response: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    suggestions_provided: Optional[bool] = None
    conversation_active: bool
    processing_result: Optional[Dict[str, Any]] = None


# === Helper functions for WebSocket communication ===
async def _send_ws_message(websocket: WebSocket, payload: Dict[str, Any]):
    """Safely serialize and send a payload via WebSocket, skipping if closed."""
    try:
        if (
            websocket.application_state == WebSocketState.CONNECTED
            and websocket.client_state == WebSocketState.CONNECTED
        ):
            await websocket.send_text(json.dumps(payload))
        else:
            logger.debug("WebSocket not connected; skipping send of %s", payload.get("type"))
    except RuntimeError as exc:
        logger.warning("WebSocket send after close: %s", exc)
    except Exception as exc:
        logger.error(f"Failed to send WebSocket message: {exc}")


async def _send_session_status(websocket: WebSocket, session_id: str):
    """Send session status information to the frontend."""
    try:
        summary = await conversation_graph.get_session_summary(session_id)
        await _send_ws_message(websocket, {
            "type": "session_status",
            "data": summary or {"session_id": session_id, "status": "not_found"},
            "session_id": session_id
        })
    except Exception as exc:
        logger.error(f"Failed to send session status: {exc}")


async def _send_conversation_update(websocket: WebSocket, session_id: str, response: Dict[str, Any]):
    """Send the assistant's response back to the client."""
    try:
        await _send_ws_message(websocket, {
            "type": "conversation_update",
            "data": response,
            "session_id": session_id
        })
    except Exception as exc:
        logger.error(f"Failed to send conversation update: {exc}")


async def _send_error_message(websocket: WebSocket, session_id: str, error_msg: str):
    """Utility to push an error message to the client."""
    await _send_ws_message(websocket, {
        "type": "error",
        "data": {"message": error_msg},
        "session_id": session_id
    })


# === Internal handlers ===
async def _handle_user_message(websocket: WebSocket, session_id: str, payload: Dict[str, Any]):
    """Process a user message coming from the frontend."""
    try:
        user_input: str = payload.get("data", {}).get("content", "").strip()
        user_id: str = payload.get("data", {}).get("user_id", "demo-user")
        if not user_input:
            await _send_error_message(websocket, session_id, "Empty user message")
            return

        # Ensure session exists (create if missing)
        try:
            summary = await conversation_graph.get_session_summary(session_id)
            if not summary or summary.get("status") == "error":
                # Create a new session with the provided session_id for continuity
                await conversation_graph.start_conversation(user_id=user_id, session_id=session_id)
        except Exception:
            await conversation_graph.start_conversation(user_id=user_id, session_id=session_id)

        # Process the message through the conversation graph
        result = await conversation_graph.process_message(
            user_message=user_input,
            session_id=session_id,
            user_id=user_id
        )

        await _send_conversation_update(websocket, session_id, result)

        # Send an updated session status after processing
        await _send_session_status(websocket, session_id)

    except Exception as exc:
        logger.error(f"Error handling user message: {exc}")
        await _send_error_message(websocket, session_id, f"Error processing message: {str(exc)}")


async def _handle_approval_response(websocket: WebSocket, session_id: str, payload: Dict[str, Any]):
    """Handle an approval/confirmation response from the user."""
    try:
        approved = bool(payload.get("data", {}).get("approved", False))
        user_id = payload.get("data", {}).get("user_id", "demo-user")

        result = await conversation_graph.handle_confirmation(
            session_id=session_id,
            user_id=user_id,
            confirmed=approved
        )
        await _send_conversation_update(websocket, session_id, result)

    except Exception as exc:
        logger.error(f"Error handling approval response: {exc}")
        await _send_error_message(websocket, session_id, f"Error processing approval: {str(exc)}")


# === WebSocket Endpoint ===
@router.websocket("/conversation/ws/{session_id}")
async def websocket_conversation_session(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint enabling real-time, bidirectional conversation for the
    data-cleaning assistant. Mirrors the behaviour of the planning WebSocket
    implementation to keep the frontend contract consistent.
    """
    await websocket.accept()
    _active_ws_connections[session_id] = websocket
    logger.info(f"WebSocket connection established for data-cleaning session {session_id}")

    # Immediately push session status so the client knows what's happening
    await _send_session_status(websocket, session_id)

    try:
        while True:
            try:
                raw_message = await websocket.receive_text()
                payload = json.loads(raw_message)
                message_type = payload.get("type")

                if message_type == "user_message":
                    await _handle_user_message(websocket, session_id, payload)
                elif message_type == "approval_response":
                    await _handle_approval_response(websocket, session_id, payload)
                elif message_type == "ping":
                    await _send_ws_message(websocket, {
                        "type": "pong",
                        "data": {"timestamp": datetime.utcnow().isoformat()},
                        "session_id": session_id
                    })
                else:
                    logger.warning(f"Unknown WebSocket message type received: {message_type}")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except json.JSONDecodeError as exc:
                await _send_error_message(websocket, session_id, "Invalid JSON format")
                logger.error(f"JSON decode error: {exc}")
            except Exception as exc:
                logger.error(f"Unhandled WebSocket error: {exc}")
                if (
                    websocket.application_state != WebSocketState.CONNECTED
                    or websocket.client_state != WebSocketState.CONNECTED
                ):
                    logger.info("WebSocket closed; ending dataclean loop for session %s", session_id)
                    break

                await _send_error_message(websocket, session_id, f"Server error: {str(exc)}")
    finally:
        # Clean up stored connection
        _active_ws_connections.pop(session_id, None)
        logger.info(f"Cleaned up WebSocket resources for session {session_id}")


# === NEW CSV WEBSOCKET ENDPOINT (Task 2.1) ===

# Active CSV WebSocket connections
_active_csv_ws_connections: Dict[str, WebSocket] = {}


@router.websocket("/csv-conversation/ws/{session_id}")
async def websocket_csv_conversation(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for CSV-based conversation data cleaning.
    
    This endpoint handles direct CSV string processing without artifacts,
    enabling streamlined conversation-based data cleaning.
    """
    await websocket.accept()
    _active_csv_ws_connections[session_id] = websocket
    logger.info(f"CSV WebSocket connection established for session {session_id}")
    
    try:
        while True:
            try:
                raw_message = await websocket.receive_text()
                payload = json.loads(raw_message)
                message_type = payload.get("type")
                
                if message_type == "csv_message":
                    await _handle_csv_message(websocket, session_id, payload)
                elif message_type == "csv_approval":
                    await _handle_csv_approval(websocket, session_id, payload)
                elif message_type == "ping":
                    await _send_ws_message(websocket, {
                        "type": "pong",
                        "data": {"timestamp": datetime.utcnow().isoformat()},
                        "session_id": session_id
                    })
                else:
                    logger.warning(f"Unknown CSV WebSocket message type: {message_type}")
                    
            except WebSocketDisconnect:
                logger.info(f"CSV WebSocket disconnected for session {session_id}")
                break
            except json.JSONDecodeError as exc:
                await _send_error_message(websocket, session_id, "Invalid JSON format")
                logger.error(f"JSON decode error: {exc}")
            except Exception as exc:
                logger.error(f"Unhandled CSV WebSocket error: {exc}")
                if (
                    websocket.application_state != WebSocketState.CONNECTED
                    or websocket.client_state != WebSocketState.CONNECTED
                ):
                    logger.info("WebSocket closed; ending CSV loop for session %s", session_id)
                    break

                await _send_error_message(websocket, session_id, f"Server error: {str(exc)}")
                
    finally:
        # Clean up stored connection
        _active_csv_ws_connections.pop(session_id, None)
        logger.info(f"Cleaned up CSV WebSocket resources for session {session_id}")


async def _handle_csv_message(websocket: WebSocket, session_id: str, payload: Dict[str, Any]):
    """Handle CSV message from the frontend."""
    try:
        data = payload.get("data", {})
        
        # Create CSV message request
        request = CSVMessageRequest(
            csv_data=data.get("csv_data", ""),
            user_message=data.get("user_message", ""),
            session_id=session_id,
            user_id=data.get("user_id", "demo-user")
        )
        
        # Process through CSV conversation graph
        response = await csv_conversation_graph.process_csv_conversation(request)
        
        # Send response back to client
        response_message = {
            "type": "csv_response",
            "data": response.dict(),
            "session_id": session_id
        }
        
        logger.info(f"📤 Sending CSV WebSocket response for session {session_id}: {response.success}")
        await _send_ws_message(websocket, response_message)
        logger.info(f"✅ CSV WebSocket response sent successfully for session {session_id}")
        
    except Exception as exc:
        logger.error(f"Error handling CSV message: {exc}")
        await _send_error_message(websocket, session_id, f"Error processing CSV message: {str(exc)}")


async def _handle_csv_approval(websocket: WebSocket, session_id: str, payload: Dict[str, Any]):
    """Handle CSV transformation approval from the frontend."""
    try:
        data = payload.get("data", {})
        
        # Create approval request
        request = CSVTransformationRequest(
            session_id=session_id,
            transformation_id=data.get("transformation_id", ""),
            approved=data.get("approved", False),
            user_feedback=data.get("user_feedback")
        )
        
        # Process approval through CSV conversation graph
        response = await csv_conversation_graph.handle_approval(request)
        
        # Send response back to client
        await _send_ws_message(websocket, {
            "type": "csv_approval_response",
            "data": response.dict(),
            "session_id": session_id
        })
        
    except Exception as exc:
        logger.error(f"Error handling CSV approval: {exc}")
        await _send_error_message(websocket, session_id, f"Error processing CSV approval: {str(exc)}")


# === HTTP FALLBACK ENDPOINT (Task 2.3) ===

@router.post("/csv-conversation/process", response_model=CSVProcessingResponse)
async def process_csv_http(request: CSVMessageRequest) -> CSVProcessingResponse:
    """
    HTTP fallback endpoint for CSV processing.
    
    This endpoint provides the same functionality as the WebSocket endpoint
    but through HTTP requests for clients that don't support WebSockets.
    """
    try:
        response = await csv_conversation_graph.process_csv_conversation(request)
        return response
    except Exception as e:
        logger.error(f"Error processing CSV via HTTP: {str(e)}")
        return CSVProcessingResponse(
            success=False,
            original_csv=request.csv_data,
            session_id=request.session_id,
            error_message=f"HTTP processing failed: {str(e)}"
        )


@router.post("/csv-conversation/approve")
async def approve_csv_transformation_http(request: CSVTransformationRequest) -> CSVProcessingResponse:
    """
    HTTP endpoint for approving CSV transformations.
    
    This endpoint handles transformation approval for clients using HTTP
    instead of WebSocket connections.
    """
    try:
        response = await csv_conversation_graph.handle_approval(request)
        return response
    except Exception as e:
        logger.error(f"Error handling CSV approval via HTTP: {str(e)}")
        return CSVProcessingResponse(
            success=False,
            original_csv="",
            session_id=request.session_id,
            error_message=f"HTTP approval failed: {str(e)}"
        )


# Initialize the file processing agent
file_processor = FileProcessingAgent()

# Initialize the AI-powered data quality agent
openai_client = get_openai_client()
quality_agent = DataQualityAgent(openai_client) if openai_client else None

# Initialize the transformation engine for Phase 2.5
transformation_engine = TransformationEngine()

# Initialize the suggestion converter for applying AI suggestions
suggestion_converter = SuggestionConverter()

# Initialize the EasyOCR processor for better OCR accuracy
from agents.dataclean.easyocr_processor import EasyOCRProcessor
easyocr_processor = EasyOCRProcessor(languages=['en'], gpu=False)  # CPU mode for compatibility

# Initialize in-memory data store
data_store = get_data_store()

# Initialize conversation system
from agents.dataclean.conversation.conversation_graph import ConversationGraph
conversation_graph = ConversationGraph()

# Initialize CSV conversation system (Task 2.1)
from agents.dataclean.conversation.csv_conversation_graph import CSVConversationGraph
csv_conversation_graph = CSVConversationGraph(openai_client)


@router.post("/process-file-complete", response_model=ProcessFileCompleteResponse)
async def process_file_complete(
    file: UploadFile = File(...),
    auto_apply_suggestions: bool = True,
    confidence_threshold: float = 0.7,
    max_suggestions_to_apply: int = 10,
    experiment_id: str = "demo-experiment",
    user_id: str = "demo-user",
    include_processing_details: bool = True,
    response_format: str = "json"  # "json" or "csv"
):
    """
    Complete end-to-end file processing: upload, analyze, clean, and return data.
    
    This endpoint handles the entire data cleaning workflow in a single call:
    1. Upload and process the file
    2. Run AI quality analysis
    3. Generate improvement suggestions
    4. Automatically apply high-confidence suggestions
    5. Return cleaned data in JSON or CSV format
    
    Args:
        file: The file to process
        auto_apply_suggestions: Whether to automatically apply AI suggestions
        confidence_threshold: Minimum confidence to apply suggestions (0.0-1.0)
        max_suggestions_to_apply: Maximum number of suggestions to apply
        experiment_id: ID of the experiment
        user_id: ID of the user
        include_processing_details: Whether to include detailed processing info
        response_format: Format for table data - "json" or "csv"
        
    Returns:
        ProcessFileCompleteResponse with cleaned data and processing summary
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ['.csv', '.xlsx', '.xls']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {file_extension}. Supported: .csv, .xlsx, .xls"
            )
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, f"complete_{uuid.uuid4()}_{file.filename}")
        
        # Save uploaded file
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create request object
        request = ProcessFileCompleteRequest(
            experiment_id=experiment_id,
            auto_apply_suggestions=auto_apply_suggestions,
            max_suggestions_to_apply=max_suggestions_to_apply,
            confidence_threshold=confidence_threshold,
            include_processing_details=include_processing_details,
            user_id=user_id
        )
        
        # Initialize complete processor
        complete_processor = CompleteFileProcessor(openai_client)
        
        # Process file completely
        response = await complete_processor.process_file_complete(
            file_path=temp_file_path,
            filename=file.filename,
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            request=request
        )
        
        # Convert to CSV format if requested
        if response_format.lower() == "csv" and response.success and response.cleaned_data:
            import pandas as pd
            import io
            
            # Convert cleaned_data to DataFrame then to CSV string
            df = pd.DataFrame(response.cleaned_data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_string = csv_buffer.getvalue()
            csv_buffer.close()
            
            # Replace cleaned_data with CSV string (keep everything else the same)
            response.cleaned_data = csv_string
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complete processing failed: {str(e)}")


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
        
        # Store in memory
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
        Success message with transformation details
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
    
    if request.action == "reject":
        # Remove the suggestion from the list
        artifact.suggestions = [s for s in artifact.suggestions if s.suggestion_id != request.suggestion_id]
        artifact.updated_at = datetime.now()
        await data_store.update_data_artifact(artifact)
        
        return {
            "status": "success",
            "message": f"Suggestion {request.suggestion_id} was rejected and removed"
        }
    
    elif request.action == "accept":
        try:
            # Get the current DataFrame
            df = await data_store.get_dataframe(request.artifact_id)
            if df is None:
                raise HTTPException(status_code=404, detail="Data not available for transformation")
            
            # Convert suggestion to transformation
            transformation = await suggestion_converter.convert_suggestion_to_transformation(
                suggestion, df, artifact.owner_id
            )
            
            # Apply the transformation
            transformed_df, data_version = await transformation_engine.apply_transformation(
                df, transformation, request.artifact_id, artifact.owner_id
            )
            
            # Update the stored DataFrame
            await data_store.save_dataframe(request.artifact_id, transformed_df)
            
            # Add transformation to artifact
            artifact.custom_transformations.append(transformation)
            
            # Update transformation history
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
            
            # Remove the applied suggestion from the list
            artifact.suggestions = [s for s in artifact.suggestions if s.suggestion_id != request.suggestion_id]
            
            # Update artifact timestamp
            artifact.updated_at = datetime.now()
            await data_store.update_data_artifact(artifact)
            
            return {
                "status": "success",
                "message": f"Suggestion {request.suggestion_id} was successfully applied",
                "transformation_id": transformation.transformation_id,
                "version": data_version.version_number,
                "can_undo": True,
                "affected_rows": len(transformed_df)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to apply suggestion: {str(e)}")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'reject'.")


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
    file: UploadFile = File(...)
):
    """
    Test EasyOCR processing directly without creating data artifacts.
    
    This endpoint is for testing OCR functionality. It processes the 
    image immediately and returns results using EasyOCR.
    
    Args:
        file: The uploaded image file
        
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
        
        # Use EasyOCR processor
        ocr_proc = EasyOCRProcessor(languages=['en'], gpu=False)
        
        # Process the image
        start_time = datetime.now()
        ocr_result = await ocr_proc.process_image(temp_file_path)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Clean up temporary file
        os.remove(temp_file_path)
        
        # Format response
        response = {
            "success": True,
            "processor_used": "easyocr",
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
        
        # Add EasyOCR-specific details
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
    Get information about the available OCR processor.
    
    Returns:
        Information about EasyOCR processor and its capabilities
    """
    try:
        # EasyOCR info
        try:
            easyocr_proc = EasyOCRProcessor(languages=['en'], gpu=False)
            processor_info = {
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
            }
        except Exception as e:
            processor_info = {
                "name": "easyocr",
                "status": "unavailable",
                "error": str(e)
            }
        
        return {
            "processor": processor_info,
            "available": processor_info.get("status") == "available"
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
        
        # Store in memory
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
    import math
    import json
    
    artifact = await data_store.get_data_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    # Get extracted DataFrame
    df = await data_store.get_dataframe(artifact_id)
    
    # Helper function to clean float values for JSON serialization
    def clean_float(value):
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                return 0.0
            return float(value)
        return value
    
    # Clean extracted data for JSON compliance
    extracted_data = []
    if df is not None and not df.empty:
        try:
            # Replace NaN/inf values with None for JSON compatibility
            df_clean = df.fillna('')
            extracted_data = df_clean.to_dict(orient="records")
        except Exception as e:
            print(f"Error converting DataFrame to dict: {e}")
            extracted_data = []
    
    return {
        "artifact_id": artifact_id,
        "status": artifact.status,
        "extracted_data": extracted_data,
        "data_shape": [df.shape[0], df.shape[1]] if df is not None else [0, 0],
        "quality_score": clean_float(artifact.quality_score),
        "suggestions": artifact.suggestions,
        "processing_notes": getattr(artifact, 'processing_notes', []),
        "ocr_confidence": clean_float(getattr(artifact, 'ocr_confidence', 0.0)),
        "created_at": artifact.created_at,
        "updated_at": artifact.updated_at
    }


@router.post("/reprocess-image")
async def reprocess_image(
    background_tasks: BackgroundTasks,
    artifact_id: str
):
    """
    Reprocess an image using EasyOCR.
    
    Args:
        artifact_id: ID of the data artifact
        
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
        artifact.original_file.path
    )
    
    return {
        "status": "success",
        "message": "Image reprocessing started"
    }


@router.get("/export-csv/{artifact_id}")
async def export_cleaned_data_as_csv(artifact_id: str):
    """
    Export the final cleaned and transformed data as a downloadable CSV file.
    
    This endpoint works for ALL data sources:
    - CSV uploads with transformations applied
    - OCR results from image processing
    - Any artifact with applied custom transformations
    
    Args:
        artifact_id: ID of the data artifact to export
        
    Returns:
        CSV file download with cleaned data
    """
    import io
    from fastapi.responses import StreamingResponse
    
    # Get the data artifact
    artifact = await data_store.get_data_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    # Get the current DataFrame (with all transformations applied)
    df = await data_store.get_dataframe(artifact_id)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data available for export")
    
    try:
        # Clean the DataFrame for CSV export
        df_export = df.copy()
        
        # Handle any remaining NaN values
        df_export = df_export.fillna('')
        
        # Convert DataFrame to CSV string
        csv_buffer = io.StringIO()
        df_export.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_content = csv_buffer.getvalue()
        csv_buffer.close()
        
        # Create filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cleaned_data_{artifact_id[:8]}_{timestamp}.csv"
        
        # Create streaming response for file download
        def generate_csv():
            yield csv_content.encode('utf-8')
        
        response = StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")


@router.get("/export-data/{artifact_id}")
async def get_cleaned_data_json(artifact_id: str):
    """
    Get the final cleaned data in JSON format for API consumption.
    
    This complements the CSV export endpoint by providing JSON access
    to the same cleaned and transformed data.
    
    Args:
        artifact_id: ID of the data artifact
        
    Returns:
        JSON object with cleaned data and metadata
    """
    import math
    
    # Get the data artifact
    artifact = await data_store.get_data_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Data artifact not found")
    
    # Get the current DataFrame (with all transformations applied)
    df = await data_store.get_dataframe(artifact_id)
    if df is None:
        raise HTTPException(status_code=404, detail="No data available")
    
    # Helper function to clean float values for JSON serialization
    def clean_float(value):
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            if math.isnan(value) or math.isinf(value):
                return 0.0
            return float(value)
        return value
    
    try:
        # Clean data for JSON export
        if df.empty:
            cleaned_data = []
        else:
            df_clean = df.fillna('')
            cleaned_data = df_clean.to_dict(orient="records")
        
        # Get transformation history summary
        transformation_summary = []
        if artifact.transformation_history:
            transformation_summary = [
                {
                    "version": version.version_number,
                    "description": version.description,
                    "transformations": version.transformations_applied,
                    "created_at": version.created_at
                }
                for version in artifact.transformation_history.versions
            ]
        
        return {
            "artifact_id": artifact_id,
            "status": artifact.status,
            "data": cleaned_data,
            "data_shape": [df.shape[0], df.shape[1]],
            "columns": list(df.columns),
            "quality_score": clean_float(artifact.quality_score),
            "ocr_confidence": clean_float(getattr(artifact, 'ocr_confidence', None)),
            "processing_notes": getattr(artifact, 'processing_notes', []),
            "transformation_history": transformation_summary,
            "export_timestamp": datetime.now(),
            "data_source": "OCR" if hasattr(artifact, 'ocr_confidence') else "File Upload"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data export failed: {str(e)}")


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


# === CONVERSATION API ENDPOINTS ===

@router.post("/conversation/start")
async def start_conversation(
    user_id: str = "demo-user",
    session_id: Optional[str] = None,
    artifact_id: Optional[str] = None,
    file_path: Optional[str] = None
):
    """
    Start a new conversation session for data cleaning.
    
    Args:
        user_id: User identifier
        session_id: Optional session ID for resuming
        artifact_id: Optional data artifact ID
        file_path: Optional file path for processing
        
    Returns:
        Session information and conversation state
    """
    try:
        result = await conversation_graph.start_conversation(
            user_id=user_id,
            session_id=session_id,
            artifact_id=artifact_id,
            file_path=file_path
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start conversation: {str(e)}")


# --- Updated conversation message endpoint ---
@router.post("/conversation/message", response_model=ConversationMessageResponseModel)
async def process_conversation_message(request: ConversationMessageRequest):
    """
    Process a user message in a conversation.
    
    Args:
        request: Pydantic model containing message details
        
    Returns:
        Conversation response with processing results
    """
    try:
        result = await conversation_graph.process_message(
            user_message=request.user_message,
            session_id=request.session_id,
            user_id=request.user_id,
            artifact_id=request.artifact_id
        )
        # Ensure a predictable boolean field for success
        if isinstance(result, dict) and "success" not in result:
            result["success"] = True
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.post("/conversation/confirm")
async def handle_conversation_confirmation(
    session_id: str,
    confirmed: bool,
    user_id: str = "demo-user"
):
    """
    Handle user confirmation for operations that require approval.
    
    Args:
        session_id: Session identifier
        confirmed: Whether the user confirmed the operation
        user_id: User identifier
        
    Returns:
        Confirmation response
    """
    try:
        result = await conversation_graph.handle_confirmation(
            session_id=session_id,
            user_id=user_id,
            confirmed=confirmed
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle confirmation: {str(e)}")


@router.get("/conversation/session/{session_id}")
async def get_conversation_session(session_id: str):
    """
    Get conversation session summary.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session summary information
    """
    try:
        result = await conversation_graph.get_session_summary(session_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message", "Session not found"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.get("/conversation/capabilities")
async def get_conversation_capabilities():
    """
    Get information about conversation capabilities.
    
    Returns:
        Conversation capabilities and supported intents
    """
    try:
        capabilities = conversation_graph.get_conversation_capabilities()
        return {
            "status": "success",
            "capabilities": capabilities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")


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
                            
                            # Save DataFrame to memory
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
                        
                        # Calculate quality score based on number of distinct issues found
                        total_rows = df_sample.shape[0]
                        num_issues = len(quality_issues)
                        # Score based on issue density with gradual penalty: 0.05 per issue, min score 0.1
                        quality_score = max(0.1, 1.0 - (num_issues * 0.05))
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


async def process_image_background(artifact_id: str, image_path: str):
    """
    Background task for processing uploaded images with EasyOCR.
    
    Args:
        artifact_id: ID of the data artifact
        image_path: Path to the uploaded image file
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
                    num_issues = len(quality_issues)
                    ai_quality_score = max(0.1, 1.0 - (num_issues * 0.05))
                    
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


@router.post("/csv-conversation/save-cleaned-data")
async def save_cleaned_data(
    session_id: str,
    cleaned_csv: str,
    db: Session = Depends(get_db)
):
    """
    Save cleaned CSV data to the database for persistent storage.
    
    This endpoint stores the cleaned CSV data so it can be retrieved later
    for validation, download, or further analysis.
    """
    try:
        from database import Experiment
        
        # Create or update experiment with cleaned CSV data
        experiment = db.query(Experiment).filter(Experiment.id == session_id).first()
        
        if not experiment:
            # Create new experiment record for this session
            experiment = Experiment(
                id=session_id,
                title=f"Cleaned Data Session {session_id}",
                description="Data cleaning session with applied transformations",
                csv_data=cleaned_csv
            )
            db.add(experiment)
        else:
            # Update existing experiment with cleaned data
            experiment.csv_data = cleaned_csv
            experiment.updated_at = datetime.now()
        
        db.commit()
        db.refresh(experiment)
        
        logger.info(f"Saved cleaned CSV data for session {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Cleaned data saved successfully",
            "experiment_id": experiment.id
        }
        
    except Exception as e:
        logger.error(f"Error saving cleaned data for session {session_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save cleaned data: {str(e)}"
        )


@router.get("/csv-conversation/get-cleaned-data/{session_id}")
async def get_cleaned_data(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve cleaned CSV data from the database.
    
    Returns the cleaned CSV data for the specified session if it exists.
    """
    try:
        from database import Experiment
        
        # Query experiment by session ID
        experiment = db.query(Experiment).filter(Experiment.id == session_id).first()
        
        if not experiment or not experiment.csv_data:
            raise HTTPException(
                status_code=404,
                detail=f"No cleaned data found for session {session_id}"
            )
        
        logger.info(f"Retrieved cleaned CSV data for session {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "cleaned_csv": experiment.csv_data,
            "last_updated": experiment.updated_at.isoformat() if experiment.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving cleaned data for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve cleaned data: {str(e)}"
        )


@router.get("/csv-conversation/download-cleaned-data/{session_id}")
async def download_cleaned_data(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Download cleaned CSV data as a file.
    
    Returns the cleaned CSV data as a downloadable file attachment.
    """
    try:
        from database import Experiment
        from fastapi.responses import Response
        
        # Query experiment by session ID
        experiment = db.query(Experiment).filter(Experiment.id == session_id).first()
        
        if not experiment or not experiment.csv_data:
            raise HTTPException(
                status_code=404,
                detail=f"No cleaned data found for session {session_id}"
            )
        
        logger.info(f"Downloading cleaned CSV data for session {session_id}")
        
        # Return CSV as downloadable file
        headers = {
            "Content-Disposition": f"attachment; filename=cleaned_data_{session_id}.csv"
        }
        
        return Response(
            content=experiment.csv_data,
            media_type="text/csv",
            headers=headers
        )


# === Header Generation Endpoint ===

@router.post("/generate-headers-from-plan", response_model=GenerateHeadersResponse)
async def generate_headers_from_plan(request: GenerateHeadersRequest) -> GenerateHeadersResponse:
    """
    Generate CSV headers from experimental plan using AI.
    
    Args:
        request: Contains experimental plan text and optional experiment ID
        
    Returns:
        Generated headers and CSV header row
    """
    try:
        # Verify OpenAI client is configured
        openai_client = get_openai_client()
        if not openai_client:
            raise HTTPException(
                status_code=500, 
                detail="OpenAI client not configured. Please check API key settings."
            )
        
        # Validate input
        if not request.plan or not request.plan.strip():
            return GenerateHeadersResponse(
                success=False,
                error_message="Experimental plan cannot be empty"
            )
        
        # Craft system prompt for header generation
        system_prompt = (
            "Given the following experimental plan, identify only the essential column headers needed for data collection. "
            "Return a single comma-separated line with concise, descriptive column names. "
            "Focus on the core measurements and variables mentioned in the plan. "
            "Limit to 6-10 columns maximum. Do NOT include derived metrics or analysis columns."
        )
        
        # Call OpenAI API (using async client)
        response = await openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Experimental plan:\n\n{request.plan}"}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        # Parse the response
        headers_line = response.choices[0].message.content.strip()
        
        # Sanity check the response
        if not headers_line:
            return GenerateHeadersResponse(
                success=False,
                error_message="AI generated empty response"
            )
        
        # Parse headers and validate
        headers = [h.strip() for h in headers_line.split(',')]
        headers = [h for h in headers if h]  # Remove empty headers
        
        if len(headers) == 0:
            return GenerateHeadersResponse(
                success=False,
                error_message="No valid headers generated"
            )
        
        if len(headers) > 15:
            return GenerateHeadersResponse(
                success=False,
                error_message="Too many headers generated (limit: 15)"
            )
        
        # Check for control characters
        for header in headers:
            if any(ord(c) < 32 and c not in '\t\n\r' for c in header):
                return GenerateHeadersResponse(
                    success=False,
                    error_message="Generated headers contain invalid characters"
                )
        
        # Build CSV data (headers only)
        csv_data = ','.join(headers) + '\n'
        
        # If experiment_id provided, update the experiment's CSV data
        if request.experiment_id:
            try:
                # Import here to avoid circular imports
                from database import get_db, Experiment
                from sqlalchemy.orm import Session
                
                # Get database session
                db_gen = get_db()
                db: Session = next(db_gen)
                
                try:
                    # Find and update experiment
                    experiment = db.query(Experiment).filter(Experiment.id == request.experiment_id).first()
                    if experiment:
                        experiment.csv_data = csv_data
                        experiment.updated_at = datetime.now()
                        db.commit()
                        print(f"Updated experiment {request.experiment_id} with generated headers")
                    else:
                        print(f"Experiment {request.experiment_id} not found, skipping database update")
                finally:
                    db.close()
            except Exception as e:
                print(f"Failed to update experiment database: {str(e)}")
                # Don't fail the whole request if database update fails
        
        return GenerateHeadersResponse(
            success=True,
            headers=headers,
            csv_data=csv_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating headers: {str(e)}")
        return GenerateHeadersResponse(
            success=False,
            error_message=f"Failed to generate headers: {str(e)}"
        ) 