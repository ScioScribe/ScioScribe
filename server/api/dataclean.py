"""
Data Cleaning API endpoints - Simplified version with streaming support

This module provides a clean, simple API for data cleaning operations
with WebSocket support for conversational interactions.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body, WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel
import logging
from uuid import uuid4
import time
import json
import asyncio

from agents.dataclean.simple_processor import SimpleDataProcessor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dataclean", tags=["dataclean"])


# Simple request/response models
class DataProcessRequest(BaseModel):
    """Request model for data processing."""
    action: Literal['analyze', 'clean', 'describe', 'add_row', 'delete_row']
    csv_data: str
    experiment_id: Optional[str] = None
    params: Optional[Dict[str, Any]] = {}


class DataProcessResponse(BaseModel):
    """Response model for data processing."""
    success: bool
    action: str
    csv_data: Optional[str] = None
    changes: Optional[list] = []
    analysis: Optional[Dict[str, Any]] = None
    description: Optional[Dict[str, Any]] = None
    ai_message: str = ""
    error: Optional[str] = None
    # Add compatibility fields for frontend
    response_type: Literal["text", "data_preview", "suggestion", "confirmation", "error"] = "text"
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    suggestions: Optional[list] = None
    next_steps: Optional[list] = None


# Initialize processor
processor = SimpleDataProcessor()

# Store active WebSocket sessions
active_sessions: Dict[str, Dict[str, Any]] = {}


class DatacleanSession:
    """Manages a dataclean conversation session"""
    
    def __init__(self, session_id: str, experiment_id: Optional[str] = None):
        self.session_id = session_id
        self.experiment_id = experiment_id
        self.csv_data: Optional[str] = None
        self.history: List[Dict[str, Any]] = []
        self.is_active = True
    
    def update_csv(self, csv_data: str):
        """Update the session's CSV data"""
        self.csv_data = csv_data
    
    def add_to_history(self, message: Dict[str, Any]):
        """Add a message to the session history"""
        self.history.append(message)


def detect_action_from_message(message: str) -> str:
    """Detect action from user message using keyword matching."""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['analyze', 'check', 'quality', 'issues']):
        return 'analyze'
    elif any(word in message_lower for word in ['clean', 'fix', 'repair']):
        return 'clean'
    elif any(word in message_lower for word in ['describe', 'overview', 'summary', 'what']):
        return 'describe'
    elif 'add' in message_lower and 'row' in message_lower:
        return 'add_row'
    elif any(word in message_lower for word in ['delete', 'remove']) and 'row' in message_lower:
        return 'delete_row'
    
    # Default to analyze
    return 'analyze'


def extract_params_from_message(message: str, action: str) -> Dict[str, Any]:
    """Extract parameters from user message based on action."""
    params = {}
    
    if action == 'add_row':
        # Extract key=value pairs
        import re
        matches = re.findall(r'(\w+)\s*=\s*([^,]+)', message)
        row_data = {}
        for key, value in matches:
            value = value.strip()
            # Try to parse as number
            try:
                value = float(value)
                if value.is_integer():
                    value = int(value)
            except ValueError:
                pass
            row_data[key] = value
        
        if row_data:
            params['row_data'] = row_data
    
    elif action == 'delete_row':
        # Extract where condition
        import re
        match = re.search(r'where\s+(\w+)\s*=\s*(.+)', message, re.IGNORECASE)
        if match:
            column = match.group(1).strip()
            value = match.group(2).strip()
            
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            
            # Try to parse as number
            try:
                value = float(value)
                if value.is_integer():
                    value = int(value)
            except ValueError:
                pass
            
            params['condition'] = {column: value}
    
    return params


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for streaming dataclean conversations.
    Handles real-time bidirectional communication for data operations.
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for session: {session_id}")
    
    # Create session
    session = DatacleanSession(session_id)
    active_sessions[session_id] = {
        "websocket": websocket,
        "session": session
    }
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "data": {
                "session_id": session_id,
                "message": "Connected to dataclean service",
                "capabilities": ["analyze", "clean", "describe", "add_row", "delete_row"]
            }
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            
            elif data.get("type") == "message":
                message_data = data.get("data", {})
                user_message = message_data.get("message", "")
                csv_data = message_data.get("csv_data", session.csv_data)
                
                # Update session CSV if provided
                if csv_data:
                    session.update_csv(csv_data)
                
                # Detect action from message (simple keyword matching)
                action = detect_action_from_message(user_message)
                params = extract_params_from_message(user_message, action)
                
                # Add user message to params for LLM processing
                params['user_message'] = user_message
                
                # Send thinking message
                await websocket.send_json({
                    "type": "thinking",
                    "data": {
                        "message": f"Processing {action} request..."
                    }
                })
                
                # Process the request
                try:
                    result = await processor.process(
                        action=action,
                        csv_data=csv_data or "",
                        experiment_id=session.experiment_id,
                        params=params
                    )
                    
                    # Stream the response
                    response_data = {
                        "session_id": session_id,
                        "action": action,
                        "ai_message": result.get('ai_message', ''),
                        "csv_data": result.get('csv_data'),
                        "changes": result.get('changes', []),
                        "success": True
                    }
                    
                    # Add action-specific data
                    if action == 'analyze':
                        # Extract analysis data from result
                        response_data['analysis'] = {
                            'issues': result.get('issues', []),
                            'total_issues': result.get('total_issues', 0),
                            'data_quality_score': result.get('data_quality_score', 100)
                        }
                    elif action == 'describe':
                        response_data['description'] = result.get('description', {})
                    
                    # Send the response
                    await websocket.send_json({
                        "type": "response",
                        "data": response_data
                    })
                    
                    # Update session CSV if changed
                    if result.get('csv_data'):
                        session.update_csv(result['csv_data'])
                    
                    # Add to history
                    session.add_to_history({
                        "user": user_message,
                        "assistant": result.get('ai_message', ''),
                        "action": action,
                        "timestamp": time.time()
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing request: {str(e)}")
                    await websocket.send_json({
                        "type": "error",
                        "data": {
                            "message": f"Error: {str(e)}",
                            "action": action
                        }
                    })
            
            elif data.get("type") == "session_recovery":
                # Handle session recovery
                await websocket.send_json({
                    "type": "session_recovered",
                    "data": {
                        "session_id": session_id,
                        "history_length": len(session.history)
                    }
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up session
        if session_id in active_sessions:
            del active_sessions[session_id]
        session.is_active = False


@router.post("/process")
async def process_data(request: DataProcessRequest) -> DataProcessResponse:
    """
    Main endpoint for all data processing operations.
    
    Actions:
    - analyze: Find data quality issues
    - clean: Apply standard cleaning operations
    - describe: Get data overview and statistics
    - add_row: Add a new row (params.row_data required)
    - delete_row: Delete rows by condition (params.condition required)
    """
    try:
        logger.info(f"Processing {request.action} request")
        
        # Process the request
        result = await processor.process(
            action=request.action,
            csv_data=request.csv_data,
            experiment_id=request.experiment_id,
            params=request.params
        )
        
        # Build response based on action
        response_data = {
            "success": True,
            "action": request.action,
            "ai_message": result.get('ai_message', ''),
            "message": result.get('ai_message', ''),  # For compatibility
            "csv_data": result.get('csv_data'),
            "changes": result.get('changes', []),
            "response_type": "text" if request.action != "analyze" else "data_preview"
        }
        
        # Add action-specific data
        if request.action == 'analyze':
            response_data['analysis'] = {
                'issues': result.get('issues', []),
                'total_issues': result.get('total_issues', 0),
                'data_quality_score': result.get('data_quality_score', 100)
            }
            # Convert analysis to suggestions for frontend
            if result.get('issues'):
                response_data['suggestions'] = [
                    {
                        'type': issue['type'],
                        'description': issue['fix'],
                        'confidence': 0.8 if issue['severity'] == 'high' else 0.6
                    }
                    for issue in result.get('issues', [])[:5]  # Top 5 issues
                ]
        elif request.action == 'describe':
            response_data['description'] = result.get('description', {})
            response_data['data'] = result.get('description', {})
        
        # Add data field for CSV changes
        if result.get('csv_data') and result.get('csv_data') != request.csv_data:
            response_data['data'] = {
                'cleaned_csv': result.get('csv_data'),
                'original_csv': request.csv_data,
                'changes_made': result.get('changes', [])
            }
        
        return DataProcessResponse(**response_data)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return DataProcessResponse(
            success=False,
            action=request.action,
            error=str(e),
            ai_message=f"❌ Error: {str(e)}",
            message=f"❌ Error: {str(e)}",
            response_type="error"
        )
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return DataProcessResponse(
            success=False,
            action=request.action,
            error=f"Failed to process {request.action}: {str(e)}",
            ai_message=f"❌ An unexpected error occurred. Please try again.",
            message=f"❌ An unexpected error occurred. Please try again.",
            response_type="error"
        )


@router.get("/health")
async def health_check():
    """Check if the data cleaning service is running."""
    return {"status": "healthy", "service": "dataclean", "version": "2.0-simple"}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    experiment_id: str = Query(default="demo-experiment"),
    response_format: str = Query(default="csv")
):
    """
    Upload and process a file (CSV, PDF, or image).
    Returns processed CSV data.
    """
    try:
        logger.info(f"Processing uploaded file: {file.filename}")
        
        # Read file content
        content = await file.read()
        
        # For now, we'll only handle CSV files
        # TODO: Add PDF and image processing later
        if file.filename.lower().endswith('.csv'):
            csv_content = content.decode('utf-8')
            
            # Process the CSV with clean action
            result = await processor.process(
                action='clean',
                csv_data=csv_content,
                experiment_id=experiment_id
            )
            
            return {
                "success": True,
                "artifact_id": f"artifact-{experiment_id}-{int(time.time())}",
                "cleaned_data": result.get('csv_data', csv_content),
                "data_shape": [len(csv_content.split('\n')) - 1, len(csv_content.split('\n')[0].split(','))]
            }
        else:
            return {
                "success": False,
                "artifact_id": "",
                "error_message": "Only CSV files are supported in the simplified version"
            }
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return {
            "success": False,
            "artifact_id": "",
            "error_message": str(e)
        }


@router.post("/generate-headers")
async def generate_headers_from_plan(request: Dict[str, Any] = Body(...)):
    """
    Generate CSV headers from an experimental plan using LLM.
    Uses AI to intelligently extract relevant column names.
    """
    try:
        plan = request.get('plan', '')
        experiment_id = request.get('experiment_id')
        
        if not plan:
            return {
                "success": False,
                "headers": [],
                "csv_data": "",
                "error_message": "No plan provided"
            }
        
        # Use LLM to generate headers from the experimental plan
        if processor.llm:
            try:
                prompt = f"""Generate minimal CSV column headers for this experimental plan. Be very precise and only include what is explicitly mentioned.

Experimental Plan:
"{plan}"

Requirements:
1. ONLY include variables/measurements explicitly mentioned in the plan
2. Always include: sample_id, timestamp
3. Add ONLY the specific measurements described in the plan
4. Use clear, descriptive names (snake_case format)  
5. Keep it minimal - no extra columns
6. Return ONLY a comma-separated list of headers

Be conservative - if something isn't clearly specified as data to be collected, don't include it.

Return format: sample_id,timestamp,measurement1,measurement2..."""

                response = await processor.llm.chat.completions.create(
                    model=processor.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=200
                )
                
                headers_text = response.choices[0].message.content.strip()
                
                # Parse headers from LLM response
                headers = [h.strip() for h in headers_text.split(',') if h.strip()]
                
                # Ensure minimal required headers are present
                required_headers = ['sample_id', 'timestamp']
                for header in required_headers:
                    if header not in headers:
                        if header == 'sample_id':
                            headers.insert(0, header)  # sample_id first
                        elif header == 'timestamp':
                            headers.insert(1 if 'sample_id' in headers else 0, header)  # timestamp second
                
                # Remove duplicates while preserving order
                seen = set()
                unique_headers = []
                for h in headers:
                    if h not in seen:
                        seen.add(h)
                        unique_headers.append(h)
                
                # Create CSV with headers
                csv_data = ','.join(unique_headers) + '\n'
                
                logger.info(f"✅ Generated {len(unique_headers)} headers using LLM")
                
                return {
                    "success": True,
                    "headers": unique_headers,
                    "csv_data": csv_data
                }
                
            except Exception as llm_error:
                logger.error(f"LLM header generation failed: {str(llm_error)}")
                # Fall back to keyword-based generation
        
        # Fallback: minimal keyword-based header generation
        logger.info("🔄 Using fallback keyword-based header generation")
        headers = []
        plan_lower = plan.lower()
        
        # Minimal required headers
        headers.extend(['sample_id', 'timestamp'])
        
        # Only add headers for measurements explicitly mentioned
        if 'temperature' in plan_lower and ('measure' in plan_lower or 'record' in plan_lower):
            headers.append('temperature')
        if 'pressure' in plan_lower and ('measure' in plan_lower or 'record' in plan_lower):
            headers.append('pressure')
        if 'ph' in plan_lower and ('measure' in plan_lower or 'test' in plan_lower or 'monitor' in plan_lower):
            headers.append('pH')
        if 'concentration' in plan_lower and ('measure' in plan_lower or 'determine' in plan_lower):
            headers.append('concentration')
        if ('reaction time' in plan_lower or 'duration' in plan_lower) and 'measure' in plan_lower:
            headers.append('reaction_time')
        if 'volume' in plan_lower and ('measure' in plan_lower or 'record' in plan_lower):
            headers.append('volume')
        if ('mass' in plan_lower or 'weight' in plan_lower) and ('measure' in plan_lower or 'weigh' in plan_lower):
            headers.append('mass')
        
        # Only add notes if there's a mention of recording observations
        if 'observ' in plan_lower or 'note' in plan_lower or 'record' in plan_lower:
            headers.append('notes')
        
        # Remove duplicates while preserving order
        seen = set()
        unique_headers = []
        for h in headers:
            if h not in seen:
                seen.add(h)
                unique_headers.append(h)
        
        # Create CSV with headers
        csv_data = ','.join(unique_headers) + '\n'
        
        return {
            "success": True,
            "headers": unique_headers,
            "csv_data": csv_data
        }
        
    except Exception as e:
        logger.error(f"Header generation error: {str(e)}")
        return {
            "success": False,
            "headers": [],
            "csv_data": "",
            "error_message": str(e)
        }


# Optional: Keep export endpoint for downloading results
@router.get("/export/{session_id}")
async def export_data(session_id: str, format: str = "csv"):
    """Export processed data (if needed)."""
    # This could be implemented if you need persistent export functionality
    return {"message": "Export functionality can be added if needed"} 