"""
Enhanced LangGraph Nodes with LLM-Powered Prompt Engineering

This module defines enhanced processing nodes that use LLM prompts for:
- Intent classification with context awareness
- Natural language parameter extraction  
- Context-aware response generation
- Conversational state management

Phase 2.5 Implementation: Prompt Engineering Enhancement
"""

import asyncio
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import json

from .state_schema import ConversationState, Intent, FileFormat
from ..memory_store import get_data_store
from ..complete_processor import CompleteFileProcessor
from ..quality_agent import DataQualityAgent
from ..file_processor import FileProcessingAgent
from ..transformation_engine import TransformationEngine
import sys
sys.path.append('..')
from config import get_openai_client

logger = logging.getLogger(__name__)


async def enhanced_message_parser_node(state: ConversationState) -> ConversationState:
    """
    Enhanced message parser using LLM for intent classification and parameter extraction.
    
    This node uses sophisticated prompts to understand user intent with full context
    awareness, including conversation history and data state.
    """
    try:
        user_message = state["user_message"]
        logger.info(f"Enhanced parsing message: {user_message}")
        
        # Get OpenAI client for LLM processing
        openai_client = get_openai_client()
        if not openai_client:
            logger.warning("OpenAI client not available, falling back to pattern matching")
            return await _fallback_message_parser(state)
        
        # Build context for LLM
        context = await _build_conversation_context(state)
        
        # Use LLM for intent classification
        intent, confidence = await _llm_classify_intent(
            user_message, context, openai_client
        )
        
        # Use LLM for parameter extraction
        parameters = await _llm_extract_parameters(
            user_message, intent, context, openai_client
        )
        
        # Update conversation history
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "content": user_message,
            "intent": intent.value,
            "confidence": confidence,
            "extracted_parameters": parameters
        })
        
        return {
            **state,
            "intent": intent,
            "conversation_history": conversation_history,
            "extracted_parameters": parameters,
            "intent_confidence": confidence,
            "error_message": None,
            "error_type": None
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced_message_parser_node: {str(e)}")
        return {
            **state,
            "intent": Intent.UNKNOWN,
            "error_message": f"Failed to parse message: {str(e)}",
            "error_type": "parsing_error"
        }


async def enhanced_context_loader_node(state: ConversationState) -> ConversationState:
    """
    Enhanced context loader with comprehensive data context building.
    
    This node loads and enriches context with detailed information about
    the current data state, conversation history, and available operations.
    """
    try:
        session_id = state["session_id"]
        artifact_id = state.get("artifact_id")
        
        logger.info(f"Enhanced loading context for session: {session_id}")
        
        # Get global memory store instance
        memory_store = get_data_store()
        
        # Build comprehensive data context
        data_context = await _build_enhanced_data_context(
            artifact_id, session_id, memory_store
        )
        
        # Add conversation context
        conversation_context = await _build_conversation_summary(
            state.get("conversation_history", [])
        )
        
        # Determine available operations based on current state
        available_operations = await _determine_available_operations(
            data_context, state.get("intent")
        )
        
        return {
            **state,
            "data_context": data_context,
            "conversation_context": conversation_context,
            "available_operations": available_operations,
            "error_message": None,
            "error_type": None
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced_context_loader_node: {str(e)}")
        return {
            **state,
            "data_context": None,
            "error_message": f"Failed to load context: {str(e)}",
            "error_type": "context_error"
        }


async def enhanced_processing_router_node(state: ConversationState) -> ConversationState:
    """
    Enhanced processing router with intelligent component selection.
    
    This node uses the enhanced context to route requests to the most
    appropriate processing components with optimized parameters.
    """
    try:
        intent = state["intent"]
        logger.info(f"Enhanced routing processing for intent: {intent}")
        
        # Initialize components with proper dependencies
        memory_store = get_data_store()
        openai_client = get_openai_client()
        
        # Initialize processors based on intent requirements
        processors = await _initialize_processors(intent, openai_client)
        
        # Route to appropriate processing with enhanced context
        operation_result = await _route_enhanced_processing(
            intent, state, processors, memory_store
        )
        
        # Determine if confirmation is needed using LLM
        confirmation_required = await _llm_assess_confirmation_needed(
            intent, operation_result, state, openai_client
        )
        
        return {
            **state,
            "operation_result": operation_result,
            "confirmation_required": confirmation_required,
            "error_message": None,
            "error_type": None
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced_processing_router_node: {str(e)}")
        return {
            **state,
            "operation_result": {
                "status": "error",
                "message": f"Enhanced processing failed: {str(e)}"
            },
            "error_message": f"Enhanced processing failed: {str(e)}",
            "error_type": "processing_error"
        }


async def enhanced_response_generator_node(state: ConversationState) -> ConversationState:
    """
    Enhanced response generator with LLM-powered conversational responses.
    
    This node generates natural, contextual responses that maintain conversation
    flow and provide helpful guidance for next steps.
    """
    try:
        logger.info("Generating enhanced conversational response")
        
        # Get OpenAI client for response generation
        openai_client = get_openai_client()
        if not openai_client:
            logger.warning("OpenAI client not available, falling back to template responses")
            return await _fallback_response_generator(state)
        
        # Generate contextual response using LLM
        response = await _llm_generate_response(state, openai_client)
        
        # Determine response type and next steps
        response_type = await _determine_response_type(state)
        next_steps = await _suggest_next_steps(state, openai_client)
        
        # Update conversation history with enhanced metadata
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "role": "assistant",
            "content": response,
            "type": response_type,
            "intent_addressed": state.get("intent", Intent.UNKNOWN).value,
            "confidence": state.get("intent_confidence", 0.0),
            "next_steps": next_steps,
            "operation_result": state.get("operation_result"),
            "confirmation_required": state.get("confirmation_required", False)
        })
        
        return {
            **state,
            "response": response,
            "response_type": response_type,
            "conversation_history": conversation_history,
            "next_steps": next_steps
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced_response_generator_node: {str(e)}")
        return {
            **state,
            "response": "I apologize, but I encountered an error while generating my response. Please try rephrasing your request.",
            "response_type": "error"
        }


# Enhanced LLM-Powered Helper Functions

async def _llm_classify_intent(
    message: str, 
    context: Dict[str, Any], 
    openai_client
) -> tuple[Intent, float]:
    """
    Use LLM to classify user intent with context awareness.
    
    This function uses a carefully crafted prompt to understand user intent
    considering conversation history, data state, and available operations.
    """
    try:
        # Build comprehensive context for intent classification
        data_state = context.get("data_context", {})
        conversation_history = context.get("conversation_history", [])
        
        # Create the intent classification prompt
        prompt = f"""You are an expert data cleaning assistant. Analyze the user's message and classify their intent.

CONTEXT:
- Current Data State: {data_state.get('status', 'unknown')}
- Available Data: {'Yes' if data_state.get('artifact_id') else 'No'}
- Recent Conversation: {conversation_history[-3:] if conversation_history else 'None'}

USER MESSAGE: "{message}"

AVAILABLE INTENTS:
- show_data: User wants to view/display data samples
- describe: User wants to understand data structure/overview
- analyze: User wants data quality analysis/insights
- clean: User wants to clean/fix data issues
- remove: User wants to remove/delete data elements
- select_sheet: User wants to select Excel sheet
- detect_delimiter: User wants to detect CSV delimiter
- unknown: Cannot determine intent

RESPONSE FORMAT (JSON):
{{
    "intent": "<intent_name>",
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>",
    "parameters_detected": {{<key>: <value>}}
}}

Classify the intent with high confidence only if you're certain. Consider context and conversation flow."""

        # Call OpenAI for intent classification
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise intent classifier for data cleaning conversations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        result = json.loads(response_text)
        
        # Map intent string to Intent enum
        intent_map = {
            "show_data": Intent.SHOW_DATA,
            "describe": Intent.DESCRIBE,
            "analyze": Intent.ANALYZE,
            "clean": Intent.CLEAN,
            "remove": Intent.REMOVE,
            "select_sheet": Intent.SELECT_SHEET,
            "detect_delimiter": Intent.DETECT_DELIMITER,
            "unknown": Intent.UNKNOWN
        }
        
        intent = intent_map.get(result["intent"], Intent.UNKNOWN)
        confidence = float(result["confidence"])
        
        logger.info(f"LLM Intent Classification: {intent.value} (confidence: {confidence:.2f})")
        logger.info(f"Reasoning: {result.get('reasoning', 'N/A')}")
        
        return intent, confidence
        
    except Exception as e:
        logger.error(f"Error in LLM intent classification: {str(e)}")
        # Fallback to pattern matching
        return await _fallback_classify_intent(message), 0.5


async def _llm_extract_parameters(
    message: str, 
    intent: Intent, 
    context: Dict[str, Any], 
    openai_client
) -> Dict[str, Any]:
    """
    Use LLM to extract parameters from natural language.
    
    This function understands natural language requests and extracts
    relevant parameters for data operations.
    """
    try:
        # Build parameter extraction prompt based on intent
        prompt = f"""Extract parameters from the user's message for a {intent.value} operation.

USER MESSAGE: "{message}"
INTENT: {intent.value}
CONTEXT: {context}

Extract relevant parameters based on the intent:

For show_data: number of rows, columns, filters
For describe: specific columns, detail level
For analyze: analysis type, columns, metrics
For clean: cleaning method, columns, rules
For remove: what to remove, conditions
For select_sheet: sheet name, sheet number
For detect_delimiter: sample text, format hints

RESPONSE FORMAT (JSON):
{{
    "parameters": {{<key>: <value>}},
    "confidence": <0.0-1.0>,
    "ambiguities": ["<any unclear aspects>"]
}}

Extract only clear, actionable parameters. If unclear, note ambiguities."""

        # Call OpenAI for parameter extraction
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a parameter extraction specialist for data operations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        result = json.loads(response_text)
        
        parameters = result.get("parameters", {})
        logger.info(f"LLM Parameter Extraction: {parameters}")
        
        return parameters
        
    except Exception as e:
        logger.error(f"Error in LLM parameter extraction: {str(e)}")
        # Fallback to basic extraction
        return await _fallback_extract_parameters(message, intent)


async def _llm_generate_response(
    state: ConversationState, 
    openai_client
) -> str:
    """
    Generate natural, contextual response using LLM.
    
    This function creates conversational responses that maintain context
    and provide helpful guidance for the user's data cleaning journey.
    """
    try:
        intent = state.get("intent", Intent.UNKNOWN)
        operation_result = state.get("operation_result", {})
        data_context = state.get("data_context", {})
        confirmation_required = state.get("confirmation_required", False)
        error_message = state.get("error_message")
        
        # Build response generation prompt
        prompt = f"""Generate a natural, helpful response for a data cleaning conversation.

USER INTENT: {intent.value}
OPERATION RESULT: {operation_result}
DATA CONTEXT: {data_context}
CONFIRMATION REQUIRED: {confirmation_required}
ERROR: {error_message}

CONVERSATION STYLE:
- Professional but friendly
- Clear and actionable
- Contextual to the data cleaning workflow
- Helpful next steps when appropriate

RESPONSE GUIDELINES:
- For show_data: Describe what data is being shown
- For analyze: Explain analysis results and insights
- For clean: Explain cleaning actions and impacts
- For confirmation: Clearly state what will happen
- For errors: Provide clear guidance on resolution

Generate a response that feels natural and maintains conversation flow."""

        # Call OpenAI for response generation
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful data cleaning assistant with expertise in conversational AI."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        response_text = response.choices[0].message.content
        logger.info(f"LLM Generated Response: {response_text[:100]}...")
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error in LLM response generation: {str(e)}")
        # Fallback to template response
        return await _fallback_generate_response(state)


async def _llm_assess_confirmation_needed(
    intent: Intent, 
    operation_result: Dict[str, Any], 
    state: ConversationState, 
    openai_client
) -> bool:
    """
    Use LLM to assess if confirmation is needed for the operation.
    
    This function intelligently determines when operations require
    user confirmation based on risk assessment and data impact.
    """
    try:
        # Build risk assessment prompt
        prompt = f"""Assess if user confirmation is needed for this data operation.

OPERATION INTENT: {intent.value}
OPERATION RESULT: {operation_result}
DATA STATE: {state.get('data_context', {})}

RISK FACTORS:
- Data modification operations (clean, remove, transform)
- Large-scale changes affecting many rows
- Irreversible operations
- Operations on original data without backup

CONFIRMATION NEEDED IF:
- Operation modifies data permanently
- Operation affects >10% of dataset
- Operation removes data
- Operation has high risk of data loss
- User hasn't explicitly confirmed destructive action

RESPONSE FORMAT (JSON):
{{
    "confirmation_required": <true/false>,
    "risk_level": "<low/medium/high>",
    "reasoning": "<brief explanation>"
}}

Assess the risk and confirmation needs."""

        # Call OpenAI for risk assessment
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a data safety specialist assessing operation risks."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        result = json.loads(response_text)
        
        confirmation_required = result.get("confirmation_required", False)
        logger.info(f"LLM Confirmation Assessment: {confirmation_required} (Risk: {result.get('risk_level', 'unknown')})")
        
        return confirmation_required
        
    except Exception as e:
        logger.error(f"Error in LLM confirmation assessment: {str(e)}")
        # Fallback to conservative assessment
        return intent in [Intent.CLEAN, Intent.REMOVE, Intent.FIX]


async def _suggest_next_steps(
    state: ConversationState, 
    openai_client
) -> List[str]:
    """
    Use LLM to suggest helpful next steps for the user.
    
    This function provides intelligent suggestions for what the user
    might want to do next in their data cleaning workflow.
    """
    try:
        intent = state.get("intent", Intent.UNKNOWN)
        operation_result = state.get("operation_result", {})
        data_context = state.get("data_context", {})
        
        # Build next steps suggestion prompt
        prompt = f"""Suggest 2-3 helpful next steps for the user's data cleaning workflow.

CURRENT INTENT: {intent.value}
OPERATION RESULT: {operation_result}
DATA CONTEXT: {data_context}

SUGGEST NEXT STEPS BASED ON:
- Current operation success/failure
- Data cleaning workflow progression
- User's likely next needs
- Available operations

RESPONSE FORMAT (JSON):
{{
    "next_steps": [
        "Step 1 description",
        "Step 2 description",
        "Step 3 description"
    ]
}}

Provide practical, actionable next steps."""

        # Call OpenAI for next steps
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a workflow guidance specialist for data cleaning."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=200
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        result = json.loads(response_text)
        
        next_steps = result.get("next_steps", [])
        logger.info(f"LLM Next Steps: {next_steps}")
        
        return next_steps
        
    except Exception as e:
        logger.error(f"Error in LLM next steps suggestion: {str(e)}")
        return []


# Enhanced Context Building Functions

async def _build_conversation_context(state: ConversationState) -> Dict[str, Any]:
    """Build comprehensive context for LLM processing."""
    return {
        "session_id": state.get("session_id"),
        "user_id": state.get("user_id"),
        "conversation_history": state.get("conversation_history", [])[-5:],  # Last 5 turns
        "data_context": state.get("data_context", {}),
        "current_intent": state.get("intent"),
        "extracted_parameters": state.get("extracted_parameters", {}),
        "confirmation_required": state.get("confirmation_required", False)
    }


async def _build_enhanced_data_context(
    artifact_id: Optional[str], 
    session_id: str, 
    memory_store
) -> Dict[str, Any]:
    """Build enhanced data context with comprehensive information."""
    try:
        if not artifact_id:
            return {
                "artifact_id": None,
                "status": "no_data",
                "session_id": session_id,
                "message": "No data artifact available"
            }
        
        # Get data artifact
        artifact = await memory_store.get_data_artifact(artifact_id)
        if not artifact:
            return {
                "artifact_id": artifact_id,
                "status": "artifact_not_found",
                "session_id": session_id
            }
        
        # Get current dataframe
        current_df = await memory_store.get_dataframe(artifact_id)
        if current_df is None:
            return {
                "artifact_id": artifact_id,
                "status": "data_not_loaded",
                "session_id": session_id
            }
        
        # Build comprehensive context
        return {
            "artifact_id": artifact_id,
            "status": "loaded",
            "session_id": session_id,
            "shape": current_df.shape,
            "columns": current_df.columns.tolist(),
            "dtypes": current_df.dtypes.astype(str).to_dict(),
            "null_counts": current_df.isnull().sum().to_dict(),
            "quality_score": artifact.quality_score,
            "suggestions_count": len(artifact.suggestions),
            "created_at": artifact.created_at.isoformat(),
            "updated_at": artifact.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error building enhanced data context: {str(e)}")
        return {
            "artifact_id": artifact_id,
            "status": "error",
            "session_id": session_id,
            "error": str(e)
        }


async def _build_conversation_summary(conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build summary of conversation for context."""
    if not conversation_history:
        return {"total_turns": 0, "recent_intents": [], "summary": "No conversation history"}
    
    # Extract recent intents
    recent_intents = [
        turn.get("intent", "unknown") 
        for turn in conversation_history[-5:] 
        if turn.get("role") == "user"
    ]
    
    return {
        "total_turns": len(conversation_history),
        "recent_intents": recent_intents,
        "summary": f"Conversation with {len(conversation_history)} turns, recent intents: {', '.join(recent_intents)}"
    }


async def _determine_available_operations(
    data_context: Dict[str, Any], 
    current_intent: Optional[Intent]
) -> List[str]:
    """Determine available operations based on current data state."""
    operations = []
    
    if data_context.get("status") == "loaded":
        operations.extend([
            "show_data", "describe", "analyze", 
            "clean", "remove", "export"
        ])
    
    if data_context.get("status") == "no_data":
        operations.extend([
            "upload_file", "select_sheet", "detect_delimiter"
        ])
    
    return operations


async def _initialize_processors(intent: Intent, openai_client) -> Dict[str, Any]:
    """Initialize required processors based on intent."""
    processors = {}
    
    if intent in [Intent.ANALYZE, Intent.CLEAN] and openai_client:
        processors["complete_processor"] = CompleteFileProcessor(openai_client)
        processors["quality_agent"] = DataQualityAgent(openai_client)
    
    if intent in [Intent.SELECT_SHEET, Intent.DETECT_DELIMITER]:
        processors["file_processor"] = FileProcessingAgent()
    
    processors["transformation_engine"] = TransformationEngine()
    
    return processors


async def _route_enhanced_processing(
    intent: Intent, 
    state: ConversationState, 
    processors: Dict[str, Any], 
    memory_store
) -> Dict[str, Any]:
    """Route processing with enhanced context and processors."""
    try:
        if intent == Intent.SHOW_DATA:
            return await _handle_enhanced_show_data(state, memory_store)
        elif intent == Intent.ANALYZE:
            return await _handle_enhanced_analyze(state, processors.get("quality_agent"), memory_store)
        elif intent == Intent.DESCRIBE:
            return await _handle_enhanced_describe(state, memory_store)
        elif intent == Intent.CLEAN:
            return await _handle_enhanced_clean(state, processors.get("complete_processor"))
        else:
            return {
                "status": "success",
                "message": f"Enhanced processing for {intent.value} completed",
                "intent": intent.value
            }
            
    except Exception as e:
        logger.error(f"Error in enhanced processing routing: {str(e)}")
        return {
            "status": "error",
            "message": f"Enhanced processing failed: {str(e)}"
        }


# Enhanced processing handlers
async def _handle_enhanced_show_data(state: ConversationState, memory_store) -> Dict[str, Any]:
    """Handle show data with enhanced context."""
    artifact_id = state.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "No data available to display"}
    
    parameters = state.get("extracted_parameters", {})
    n_rows = parameters.get("n_rows", 10)
    
    try:
        current_df = await memory_store.get_dataframe(artifact_id)
        if current_df is None:
            return {"status": "error", "message": "Data not accessible"}
        
        display_data = current_df.head(n_rows)
        
        return {
            "status": "success",
            "data_preview": display_data.to_dict('records'),
            "total_rows": len(current_df),
            "displayed_rows": len(display_data),
            "columns": current_df.columns.tolist(),
            "message": f"Showing first {len(display_data)} rows of {len(current_df)} total rows"
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to display data: {str(e)}"}


async def _handle_enhanced_analyze(
    state: ConversationState, 
    quality_agent: Optional[DataQualityAgent], 
    memory_store
) -> Dict[str, Any]:
    """Handle data analysis with enhanced quality agent."""
    if not quality_agent:
        return {"status": "error", "message": "Analysis not available without AI configuration"}
    
    artifact_id = state.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "No data available for analysis"}
    
    try:
        current_df = await memory_store.get_dataframe(artifact_id)
        if current_df is None:
            return {"status": "error", "message": "Data not accessible for analysis"}
        
        # Perform enhanced analysis
        quality_issues = await quality_agent.analyze_data(current_df)
        suggestions = await quality_agent.generate_suggestions(quality_issues, current_df)
        
        return {
            "status": "success",
            "quality_issues": [
                {
                    "column": issue.column,
                    "issue_type": issue.issue_type,
                    "description": issue.description,
                    "severity": issue.severity,
                    "affected_rows": issue.affected_rows
                }
                for issue in quality_issues[:5]
            ],
            "suggestions": [
                {
                    "description": suggestion.description,
                    "confidence": suggestion.confidence,
                    "risk_level": suggestion.risk_level
                }
                for suggestion in suggestions[:3]
            ],
            "summary": f"Found {len(quality_issues)} quality issues with {len(suggestions)} improvement suggestions"
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Analysis failed: {str(e)}"}


async def _handle_enhanced_describe(state: ConversationState, memory_store) -> Dict[str, Any]:
    """Handle data description with enhanced context."""
    artifact_id = state.get("artifact_id")
    if not artifact_id:
        return {"status": "error", "message": "No data available to describe"}
    
    try:
        current_df = await memory_store.get_dataframe(artifact_id)
        if current_df is None:
            return {"status": "error", "message": "Data not accessible for description"}
        
        # Enhanced description
        description = {
            "shape": current_df.shape,
            "columns": current_df.columns.tolist(),
            "dtypes": current_df.dtypes.astype(str).to_dict(),
            "null_counts": current_df.isnull().sum().to_dict(),
            "memory_usage": current_df.memory_usage(deep=True).sum(),
            "numeric_summary": {}
        }
        
        # Add numeric statistics
        numeric_columns = current_df.select_dtypes(include=['number']).columns
        if len(numeric_columns) > 0:
            description["numeric_summary"] = current_df[numeric_columns].describe().to_dict()
        
        return {
            "status": "success",
            "description": description,
            "message": f"Dataset with {description['shape'][0]} rows and {description['shape'][1]} columns"
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Description failed: {str(e)}"}


async def _handle_enhanced_clean(
    state: ConversationState, 
    complete_processor: Optional[CompleteFileProcessor]
) -> Dict[str, Any]:
    """Handle data cleaning with enhanced processor."""
    if not complete_processor:
        return {"status": "error", "message": "Data cleaning not available without AI configuration"}
    
    return {
        "status": "confirmation_required",
        "message": "Data cleaning operation prepared. This will modify your data.",
        "operation": "clean",
        "parameters": state.get("extracted_parameters", {}),
        "risk_level": "medium"
    }


# Fallback functions for when OpenAI is not available

async def _fallback_message_parser(state: ConversationState) -> ConversationState:
    """Fallback to simple pattern matching when LLM is not available."""
    from .nodes_simple import message_parser_node
    return await message_parser_node(state)


async def _fallback_response_generator(state: ConversationState) -> ConversationState:
    """Fallback to template responses when LLM is not available."""
    from .nodes_simple import response_generator_node
    return await response_generator_node(state)


async def _fallback_classify_intent(message: str) -> Intent:
    """Fallback intent classification using pattern matching."""
    from .nodes_simple import _classify_intent
    return await _classify_intent(message)


async def _fallback_extract_parameters(message: str, intent: Intent) -> Dict[str, Any]:
    """Fallback parameter extraction using basic patterns."""
    from .nodes_simple import _extract_parameters
    return await _extract_parameters(message, intent)


async def _fallback_generate_response(state: ConversationState) -> str:
    """Fallback response generation using templates."""
    intent = state.get("intent", Intent.UNKNOWN)
    operation_result = state.get("operation_result", {})
    
    if intent == Intent.SHOW_DATA:
        return "Here's your data display (enhanced features require AI configuration)"
    elif intent == Intent.ANALYZE:
        return "Data analysis complete (enhanced insights require AI configuration)"
    elif intent == Intent.DESCRIBE:
        return "Data description available (enhanced summaries require AI configuration)"
    else:
        return "Operation processed (enhanced responses require AI configuration)"


async def _determine_response_type(state: ConversationState) -> str:
    """Determine the type of response based on state."""
    if state.get("error_message"):
        return "error"
    elif state.get("confirmation_required"):
        return "confirmation"
    else:
        return "result" 