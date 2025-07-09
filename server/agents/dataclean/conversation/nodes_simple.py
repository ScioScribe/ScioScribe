"""
Simplified LangGraph Nodes for Initial Testing

This is a simplified version of the nodes for testing the basic LangGraph
workflow without complex dependencies.
"""

import asyncio
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from .state_schema import ConversationState, Intent, FileFormat

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
        
        # Basic intent classification
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
    Load data context from existing memory store and file system.
    
    This node retrieves the current data artifact and file context.
    """
    try:
        session_id = state["session_id"]
        artifact_id = state.get("artifact_id")
        
        logger.info(f"Loading context for session: {session_id}")
        
        # For now, return basic context
        data_context = {
            "artifact_id": artifact_id,
            "status": "loaded" if artifact_id else "no_data",
            "session_id": session_id
        }
        
        return {
            **state,
            "data_context": data_context,
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
        
        # Basic routing logic
        if intent == Intent.SHOW_DATA:
            operation_result = {"status": "success", "message": "Data display requested"}
            
        elif intent == Intent.ANALYZE:
            operation_result = {"status": "success", "message": "Data analysis requested"}
            
        elif intent == Intent.DESCRIBE:
            operation_result = {"status": "success", "message": "Data description requested"}
            
        elif intent in [Intent.CLEAN, Intent.FIX, Intent.REMOVE]:
            operation_result = {"status": "confirmation_required", "message": "Data cleaning requested"}
            
        else:
            operation_result = {
                "status": "unsupported",
                "message": f"Intent '{intent}' is not yet supported",
                "supported_intents": [intent.value for intent in Intent if intent != Intent.UNKNOWN]
            }
        
        confirmation_required = operation_result.get("status") == "confirmation_required"
        
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
            "operation_result": {"status": "error", "message": f"Processing failed: {str(e)}"},
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
        operation_result = state.get("operation_result", {})
        error_message = state.get("error_message")
        
        if error_message:
            response = f"I encountered an issue: {error_message}"
            response_type = "error"
        elif state.get("confirmation_required"):
            response = "This operation requires confirmation. Would you like to proceed?"
            response_type = "confirmation"
        else:
            response = await _generate_success_response(operation_result, intent)
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


# Helper functions

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
    
    return parameters


async def _generate_success_response(operation_result: Dict[str, Any], intent: Intent) -> str:
    """Generate success response based on operation result."""
    if not operation_result:
        return "Operation completed successfully."
    
    message = operation_result.get("message", "")
    
    if intent == Intent.SHOW_DATA:
        return f"I understand you want to view your data. {message}"
    
    elif intent == Intent.DESCRIBE:
        return f"I can help you understand your data structure. {message}"
    
    elif intent == Intent.ANALYZE:
        return f"I'll analyze your data quality. {message}"
    
    elif intent == Intent.SELECT_SHEET:
        return f"I can help you select a sheet from your Excel file. {message}"
    
    elif intent == Intent.DETECT_DELIMITER:
        return f"I can detect the delimiter in your CSV file. {message}"
    
    return f"I understand your request. {message}" 