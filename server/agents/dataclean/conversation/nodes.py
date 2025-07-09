"""
LangGraph Nodes for Conversational Data Cleaning

This module defines the processing nodes that form the LangGraph workflow.
Each node wraps existing components to provide conversational orchestration.
"""

import asyncio
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import pandas as pd
import csv

from .state_schema import ConversationState, Intent, FileFormat, MessageContext
from ..memory_store import MemoryDataStore, get_data_store
from ..complete_processor import CompleteFileProcessor
from ..quality_agent import DataQualityAgent
from ..file_processor import FileProcessingAgent
from ..transformation_engine import TransformationEngine
import sys
sys.path.append('..')
from config import get_openai_client

logger = logging.getLogger(__name__)


async def message_parser_node(state: ConversationState) -> ConversationState:
    """
    Parse user message and extract intent, parameters, and context.
    
    This node analyzes the user's natural language input to determine
    their intent and extract relevant parameters for data operations.
    """
    try:
        user_message = state["user_message"]
        logger.info(f"Parsing message: {user_message}")
        
        # Basic intent classification (will be enhanced in Phase 2.5)
        intent = await _classify_intent(user_message)
        
        # Extract parameters from the message
        parameters = await _extract_parameters(user_message, intent)
        
        # Update conversation history
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "content": user_message,
            "intent": intent.value
        })
        
        return {
            **state,
            "intent": intent,
            "conversation_history": conversation_history,
            "extracted_parameters": parameters,
            "error_message": None,
            "error_type": None
        }
        
    except Exception as e:
        logger.error(f"Error in message_parser_node: {str(e)}")
        return {
            **state,
            "intent": Intent.UNKNOWN,
            "error_message": f"Failed to parse message: {str(e)}",
            "error_type": "parsing_error"
        }


async def context_loader_node(state: ConversationState) -> ConversationState:
    """
    Load conversation context and data artifact state.
    
    This node retrieves the current data context from the memory store
    and enriches the conversation state with relevant information.
    """
    try:
        logger.info("Loading conversation context")
        
        artifact_id = state.get("artifact_id")
        
        # Get global memory store instance
        memory_store = get_data_store()
        
        data_context = None
        dataframe_info = None
        file_format = None
        file_path = None
        
        # Load existing data artifact if available
        if artifact_id:
            data_artifact = await memory_store.get_data_artifact(artifact_id)
            if data_artifact:
                # Load basic artifact context
                data_context = {
                    "artifact_id": artifact_id,
                    "status": data_artifact.status.value,
                    "created_at": data_artifact.created_at.isoformat(),
                    "updated_at": data_artifact.updated_at.isoformat(),
                    "quality_score": data_artifact.quality_score,
                    "suggestions_count": len(data_artifact.suggestions)
                }
                
                # Get current dataframe from memory store
                current_df = await memory_store.get_dataframe(artifact_id)
                if current_df is not None:
                    dataframe_info = {
                        "shape": current_df.shape,
                        "columns": current_df.columns.tolist(),
                        "dtypes": current_df.dtypes.astype(str).to_dict(),
                        "null_counts": current_df.isnull().sum().to_dict(),
                        "sample_data": current_df.head(3).to_dict('records')
                    }
                    
                    # Determine file format from file path
                    if data_artifact.original_file:
                        file_path = data_artifact.original_file.path
                        if file_path.endswith('.csv'):
                            file_format = FileFormat.CSV
                        elif file_path.endswith(('.xlsx', '.xls')):
                            file_format = FileFormat.EXCEL
        
        return {
            **state,
            "data_context": data_context,
            "dataframe_info": dataframe_info,
            "file_format": file_format,
            "file_path": file_path,
            "error_message": None,
            "error_type": None
        }
        
    except Exception as e:
        logger.error(f"Error in context_loader_node: {str(e)}")
        return {
            **state,
            "data_context": None,
            "error_message": f"Failed to load context: {str(e)}",
            "error_type": "context_error"
        }


async def processing_router_node(state: ConversationState) -> ConversationState:
    """
    Route processing requests to appropriate existing components.
    
    This node determines the appropriate processing component based on
    the user's intent and routes the request accordingly.
    """
    try:
        intent = state["intent"]
        logger.info(f"Routing processing for intent: {intent}")
        
        # Initialize components with proper dependencies
        memory_store = get_data_store()
        openai_client = get_openai_client()
        
        # Initialize processors with proper parameters
        complete_processor = CompleteFileProcessor(openai_client) if openai_client else None
        quality_agent = DataQualityAgent(openai_client) if openai_client else None
        file_processor = FileProcessingAgent()
        transformation_engine = TransformationEngine()
        
        operation_result = None
        confirmation_required = False
        
        # Route based on intent
        if intent == Intent.SHOW_DATA:
            operation_result = await _handle_show_data(state, memory_store)
            
        elif intent == Intent.ANALYZE:
            if quality_agent:
                operation_result = await _handle_analyze_data(state, quality_agent, memory_store)
            else:
                operation_result = {"status": "error", "message": "AI analysis not available. Please check OpenAI configuration."}
            
        elif intent == Intent.DESCRIBE:
            operation_result = await _handle_describe_data(state, memory_store)
            
        elif intent in [Intent.CLEAN, Intent.REMOVE]:
            # These operations require confirmation
            confirmation_required = True
            if complete_processor:
                operation_result = await _prepare_cleaning_operation(state, complete_processor)
            else:
                operation_result = {"status": "error", "message": "Data cleaning not available. Please check OpenAI configuration."}
            
        elif intent == Intent.SELECT_SHEET:
            operation_result = await _handle_sheet_selection(state, file_processor)
            
        elif intent == Intent.DETECT_DELIMITER:
            operation_result = await _handle_delimiter_detection(state, file_processor)
            
        else:
            operation_result = {
                "status": "unsupported",
                "message": f"Intent '{intent.value}' is not yet supported",
                "supported_intents": [intent.value for intent in Intent if intent != Intent.UNKNOWN]
            }
        
        return {
            **state,
            "operation_result": operation_result,
            "confirmation_required": confirmation_required,
            "error_message": None,
            "error_type": None
        }
        
    except Exception as e:
        logger.error(f"Error in processing_router_node: {str(e)}")
        return {
            **state,
            "operation_result": {
                "status": "error",
                "message": f"Processing failed: {str(e)}"
            },
            "error_message": f"Processing failed: {str(e)}",
            "error_type": "processing_error"
        }


async def response_generator_node(state: ConversationState) -> ConversationState:
    """
    Generate conversational responses based on processing results.
    
    This node formats the processing results into natural language
    responses that maintain conversational context.
    """
    try:
        logger.info("Generating conversational response")
        
        intent = state["intent"]
        operation_result = state.get("operation_result")
        error_message = state.get("error_message")
        
        if error_message:
            response = await _generate_error_response(error_message, state)
            response_type = "error"
        elif state.get("confirmation_required"):
            response = await _generate_confirmation_response(operation_result or {}, state)
            response_type = "confirmation"
        else:
            response = await _generate_success_response(operation_result or {}, intent, state)
            response_type = "result"
        
        # Update conversation history
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "content": response,
            "type": response_type
        })
        
        return {
            **state,
            "response": response,
            "response_type": response_type,
            "conversation_history": conversation_history
        }
        
    except Exception as e:
        logger.error(f"Error in response_generator_node: {str(e)}")
        return {
            **state,
            "response": "I apologize, but I encountered an error while processing your request. Please try again.",
            "response_type": "error"
        }


# Helper functions for intent classification and parameter extraction

async def _classify_intent(message: str) -> Intent:
    """Basic intent classification based on keywords."""
    message_lower = message.lower()
    
    # Data exploration intents
    if any(keyword in message_lower for keyword in ["show", "display", "view", "first", "head"]):
        return Intent.SHOW_DATA
    elif any(keyword in message_lower for keyword in ["describe", "info", "summary", "overview"]):
        return Intent.DESCRIBE
    elif any(keyword in message_lower for keyword in ["analyze", "analysis", "check quality", "issues"]):
        return Intent.ANALYZE
    
    # Data cleaning intents
    elif any(keyword in message_lower for keyword in ["clean", "fix", "correct"]):
        return Intent.CLEAN
    elif any(keyword in message_lower for keyword in ["remove", "delete", "drop"]):
        return Intent.REMOVE
    
    # File-specific intents
    elif any(keyword in message_lower for keyword in ["sheet", "tab", "switch"]):
        return Intent.SELECT_SHEET
    elif any(keyword in message_lower for keyword in ["delimiter", "separator", "comma"]):
        return Intent.DETECT_DELIMITER
    
    return Intent.UNKNOWN


async def _extract_parameters(message: str, intent: Intent) -> Dict[str, Any]:
    """Extract parameters from user message based on intent."""
    parameters = {}
    
    if intent == Intent.SHOW_DATA:
        # Extract number of rows if specified
        import re
        numbers = re.findall(r'\d+', message)
        if numbers:
            parameters["n_rows"] = int(numbers[0])
        else:
            parameters["n_rows"] = 10
    
    elif intent == Intent.SELECT_SHEET:
        # Extract sheet name if specified
        import re
        sheet_matches = re.findall(r'sheet\s+(["\']?)(\w+)\1', message.lower())
        if sheet_matches:
            parameters["sheet_name"] = sheet_matches[0][1]
    
    return parameters


# Helper functions for processing operations

async def _handle_show_data(state: ConversationState, memory_store: MemoryDataStore) -> Dict[str, Any]:
    """Handle show data requests using real data from memory store."""
    artifact_id = state.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "No data loaded. Please upload a file first."}
    
    try:
        # Get current dataframe from memory store
        current_df = await memory_store.get_dataframe(artifact_id)
        if current_df is None:
            return {"status": "error", "message": "No data available to display."}
        
        # Get requested number of rows
        n_rows = state.get("extracted_parameters", {}).get("n_rows", 10)
        
        # Prepare data for display
        display_data = current_df.head(n_rows)
        
        return {
            "status": "success",
            "data": display_data.to_dict('records'),
            "shape": current_df.shape,
            "columns": current_df.columns.tolist(),
            "n_rows_shown": len(display_data)
        }
        
    except Exception as e:
        logger.error(f"Error in _handle_show_data: {str(e)}")
        return {"status": "error", "message": f"Failed to retrieve data: {str(e)}"}


async def _handle_analyze_data(state: ConversationState, quality_agent: DataQualityAgent, memory_store: MemoryDataStore) -> Dict[str, Any]:
    """Handle data analysis requests using real quality agent."""
    artifact_id = state.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "No data loaded for analysis."}
    
    if not quality_agent:
        return {"status": "error", "message": "AI analysis not available. Please check OpenAI configuration."}
    
    try:
        # Get current dataframe
        current_df = await memory_store.get_dataframe(artifact_id)
        if current_df is None:
            return {"status": "error", "message": "No data available for analysis."}
        
        # Analyze data quality using existing quality agent
        quality_issues = await quality_agent.analyze_data(current_df)
        
        # Generate suggestions based on issues
        suggestions = await quality_agent.generate_suggestions(quality_issues, current_df)
        
        return {
            "status": "success",
            "issues_found": len(quality_issues),
            "suggestions_generated": len(suggestions),
            "quality_issues": [
                {
                    "column": issue.column,
                    "issue_type": issue.issue_type,
                    "description": issue.description,
                    "severity": issue.severity,
                    "affected_rows": issue.affected_rows
                }
                for issue in quality_issues[:5]  # Show first 5 issues
            ],
            "suggestions": [
                {
                    "description": suggestion.description,
                    "confidence": suggestion.confidence,
                    "risk_level": suggestion.risk_level,
                    "column": suggestion.column
                }
                for suggestion in suggestions[:3]  # Show first 3 suggestions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in _handle_analyze_data: {str(e)}")
        return {"status": "error", "message": f"Analysis failed: {str(e)}"}


async def _handle_describe_data(state: ConversationState, memory_store: MemoryDataStore) -> Dict[str, Any]:
    """Handle data description requests using real dataframe info."""
    artifact_id = state.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "No data loaded to describe."}
    
    try:
        # Get current dataframe
        current_df = await memory_store.get_dataframe(artifact_id)
        if current_df is None:
            return {"status": "error", "message": "No data available to describe."}
        
        # Generate comprehensive description
        description = {
            "shape": current_df.shape,
            "columns": current_df.columns.tolist(),
            "dtypes": current_df.dtypes.astype(str).to_dict(),
            "null_counts": current_df.isnull().sum().to_dict(),
            "memory_usage": current_df.memory_usage(deep=True).to_dict(),
            "numeric_stats": {}
        }
        
        # Add statistics for numeric columns
        numeric_columns = current_df.select_dtypes(include=['number']).columns
        if len(numeric_columns) > 0:
            description["numeric_stats"] = current_df[numeric_columns].describe().to_dict()
        
        return {
            "status": "success",
            "description": description
        }
        
    except Exception as e:
        logger.error(f"Error in _handle_describe_data: {str(e)}")
        return {"status": "error", "message": f"Failed to describe data: {str(e)}"}


async def _prepare_cleaning_operation(state: ConversationState, complete_processor: CompleteFileProcessor) -> Dict[str, Any]:
    """Prepare cleaning operation for confirmation."""
    if not complete_processor:
        return {
            "status": "error",
            "message": "Data cleaning not available. Please check OpenAI configuration."
        }
    
    artifact_id = state.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "No data loaded for cleaning."}
    
    return {
        "status": "confirmation_required",
        "message": "This operation will modify your data. Would you like to proceed?",
        "operation": "data_cleaning",
        "artifact_id": artifact_id,
        "parameters": state.get("extracted_parameters", {})
    }


async def _handle_sheet_selection(state: ConversationState, file_processor: FileProcessingAgent) -> Dict[str, Any]:
    """Handle Excel sheet selection using real file processor."""
    file_path = state.get("file_path")
    if not file_path or not file_path.endswith(('.xlsx', '.xls')):
        return {"status": "error", "message": "Sheet selection is only available for Excel files."}
    
    try:
        # Get available sheets using pandas
        xl_file = pd.ExcelFile(file_path)
        sheets = xl_file.sheet_names
        
        # Check if specific sheet was requested
        requested_sheet = state.get("extracted_parameters", {}).get("sheet_name")
        if requested_sheet:
            if requested_sheet in sheets:
                return {
                    "status": "success",
                    "selected_sheet": requested_sheet,
                    "available_sheets": sheets,
                    "message": f"Selected sheet: {requested_sheet}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Sheet '{requested_sheet}' not found. Available sheets: {', '.join(sheets)}"
                }
        
        return {
            "status": "success",
            "available_sheets": sheets,
            "message": f"Found {len(sheets)} sheets: {', '.join(sheets)}"
        }
        
    except Exception as e:
        logger.error(f"Error in _handle_sheet_selection: {str(e)}")
        return {"status": "error", "message": f"Failed to read Excel file: {str(e)}"}


async def _handle_delimiter_detection(state: ConversationState, file_processor: FileProcessingAgent) -> Dict[str, Any]:
    """Handle CSV delimiter detection using real file processor."""
    file_path = state.get("file_path")
    if not file_path or not file_path.endswith('.csv'):
        return {"status": "error", "message": "Delimiter detection is only available for CSV files."}
    
    try:
        # Use pandas CSV sniffer to detect delimiter
        with open(file_path, 'r', encoding='utf-8') as f:
            sample = f.read(1024)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
        
        return {
            "status": "success",
            "delimiter": delimiter,
            "message": f"Detected delimiter: '{delimiter}'"
        }
        
    except Exception as e:
        logger.error(f"Error in _handle_delimiter_detection: {str(e)}")
        return {"status": "error", "message": f"Failed to detect delimiter: {str(e)}"}


# Response generation helpers

async def _generate_error_response(error_message: str, state: ConversationState) -> str:
    """Generate user-friendly error response."""
    return f"I encountered an issue: {error_message}. Please try rephrasing your request or check if your data is properly loaded."


async def _generate_confirmation_response(operation_result: Dict[str, Any], state: ConversationState) -> str:
    """Generate confirmation response for risky operations."""
    if operation_result and operation_result.get("status") == "confirmation_required":
        return operation_result.get("message", "This operation requires confirmation. Would you like to proceed?")
    return "This operation requires confirmation. Please confirm to proceed."


async def _generate_success_response(operation_result: Dict[str, Any], intent: Intent, state: ConversationState) -> str:
    """Generate success response based on operation result."""
    if not operation_result:
        return "Operation completed successfully."
    
    status = operation_result.get("status")
    if status == "error":
        return f"I encountered an error: {operation_result.get('message', 'Unknown error')}"
    
    if intent == Intent.SHOW_DATA:
        n_rows_shown = operation_result.get("n_rows_shown", 0)
        shape = operation_result.get("shape", (0, 0))
        return f"Here are the first {n_rows_shown} rows of your data (total: {shape[0]} rows, {shape[1]} columns):"
    
    elif intent == Intent.DESCRIBE:
        description = operation_result.get("description", {})
        shape = description.get("shape", (0, 0))
        columns = len(description.get("columns", []))
        return f"Your data has {shape[0]} rows and {columns} columns. I've analyzed the structure, data types, and missing values."
    
    elif intent == Intent.ANALYZE:
        issues_found = operation_result.get("issues_found", 0)
        suggestions_generated = operation_result.get("suggestions_generated", 0)
        return f"Data quality analysis completed! Found {issues_found} issues and generated {suggestions_generated} suggestions for improvement."
    
    elif intent == Intent.SELECT_SHEET:
        sheets = operation_result.get("available_sheets", [])
        selected = operation_result.get("selected_sheet")
        if selected:
            return f"Selected sheet '{selected}' from {len(sheets)} available sheets."
        return f"Found {len(sheets)} sheets in your Excel file: {', '.join(sheets)}"
    
    elif intent == Intent.DETECT_DELIMITER:
        delimiter = operation_result.get("delimiter", "unknown")
        return f"The detected delimiter for your CSV file is: '{delimiter}'"
    
    return "Operation completed successfully."


# Helper functions for enhanced nodes
def _format_processing_result(processing_result: Dict[str, Any], intent: str) -> str:
    """Format processing result for display in conversation."""
    if not processing_result:
        return "I'm ready to help with your data cleaning task!"
    
    if not processing_result.get("success"):
        error_msg = processing_result.get("error_message", "Unknown error")
        return f"I encountered an issue: {error_msg}"
    
    message = processing_result.get("message", "")
    if message:
        return message
    
    # Default formatting based on intent
    if intent == "show_data":
        data_shape = processing_result.get("data_shape", (0, 0))
        return f"Here's your data (shape: {data_shape[0]} rows, {data_shape[1]} columns):"
    elif intent == "analyze":
        issues = processing_result.get("quality_issues", [])
        suggestions = processing_result.get("suggestions", [])
        return f"Analysis complete! Found {len(issues)} quality issues and {len(suggestions)} suggestions."
    elif intent == "clean":
        applied = processing_result.get("transformations_applied", 0)
        return f"Data cleaning complete! Applied {applied} transformations."
    elif intent == "describe":
        description = processing_result.get("description", {})
        return f"Data description complete! Analyzed {len(description)} columns."
    
    return "Operation completed successfully."


def _update_conversation_history(
    conversation_history: List[Dict[str, Any]], 
    role: str, 
    content: str, 
    **kwargs
) -> List[Dict[str, Any]]:
    """Update conversation history with new message."""
    new_entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content,
        **kwargs
    }
    
    conversation_history.append(new_entry)
    return conversation_history


def _prepare_response(state: ConversationState) -> ConversationState:
    """Prepare final response for the conversation."""
    response = state.get("response", "I'm ready to help with your data cleaning task!")
    
    return {
        **state,
        "response": response
    }


# Additional nodes for enhanced conversation graph
async def data_processor(state: ConversationState) -> ConversationState:
    """Process data operations using existing components."""
    # This is a wrapper around the existing processing logic
    return await processing_router_node(state)


async def response_formatter(state: ConversationState) -> ConversationState:
    """Format response for conversation output."""
    # This is a wrapper around the existing response generation logic
    return await response_generator_node(state)


async def conversation_finalizer(state: ConversationState) -> ConversationState:
    """Finalize conversation turn and prepare for next interaction."""
    try:
        logger.info("Finalizing conversation turn")
        
        # Ensure response is set
        if not state.get("response"):
            state["response"] = "I'm ready to help with your data cleaning task!"
        
        # Update conversation history if not already done
        conversation_history = state.get("conversation_history", [])
        
        # Check if assistant response is already in history
        if not conversation_history or conversation_history[-1].get("role") != "assistant":
            conversation_history = _update_conversation_history(
                conversation_history,
                "assistant",
                state["response"],
                type="response"
            )
            state["conversation_history"] = conversation_history
        
        # Return the finalized state
        return state
        
    except Exception as e:
        logger.error(f"Error in conversation_finalizer: {str(e)}")
        return {
            **state,
            "response": "I'm ready to help with your data cleaning task!"
        } 