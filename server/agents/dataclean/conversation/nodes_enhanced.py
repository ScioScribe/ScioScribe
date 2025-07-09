"""
Enhanced conversation nodes with advanced features for Phase 3.

This module provides enhanced nodes for multi-turn conversations, proactive suggestions,
error recovery, and simplified template recommendations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .state_schema import ConversationState, Intent
from ..models import ProcessingStatus
from .nodes import _format_processing_result, _update_conversation_history, _prepare_response
from .conversation_templates import get_simple_conversation_templates
from .proactive_suggestions import ProactiveSuggestionsEngine
from .error_recovery_engine import EnhancedErrorRecoveryEngine
from .conversation_summarizer import ConversationSummarizer
from ..models import DataArtifact
from ..complete_processor import CompleteFileProcessor
from ..quality_agent import DataQualityAgent
from ..transformation_engine import TransformationEngine
from ..memory_store import get_data_store
from config import get_openai_client

logger = logging.getLogger(__name__)


async def enhanced_context_loader(state: ConversationState) -> Dict[str, Any]:
    """
    Enhanced context loader with conversation history management and summarization.
    
    Handles automatic conversation summarization when history gets too long.
    """
    try:
        logger.info("Loading enhanced conversation context")
        
        # Get current conversation history
        conversation_history = state.get("conversation_history", [])
        session_id = state.get("session_id", "")
        
        # Check if we need to summarize conversation
        if len(conversation_history) > 20:  # More than 20 turns
            logger.info(f"Conversation history has {len(conversation_history)} turns, summarizing...")
            
            # Summarize using the conversation summarizer
            summarizer = ConversationSummarizer(get_openai_client())
            summary_result = await summarizer.summarize_conversation(conversation_history)
            
            if summary_result["success"]:
                # Keep recent turns + summary
                recent_turns = conversation_history[-8:]  # Keep last 8 turns
                
                # Create summary entry
                summary_entry = {
                    "role": "system",
                    "content": f"[CONVERSATION SUMMARY: {summary_result['summary']}]",
                    "timestamp": datetime.now().isoformat(),
                    "type": "summary"
                }
                
                # Update conversation history
                state["conversation_history"] = [summary_entry] + recent_turns
                
                logger.info("Conversation summarized successfully")
            else:
                logger.warning("Failed to summarize conversation, keeping full history")
        
        # Load data context
        data_context = {}
        artifact_id = state.get("artifact_id")
        
        if artifact_id:
            data_store = get_data_store()
            artifact = await data_store.get_data_artifact(artifact_id)
            
            if artifact:
                df = await data_store.get_dataframe(artifact_id)
                data_context = {
                    "artifact_id": artifact_id,
                    "has_data": df is not None and not df.empty,
                    "data_shape": df.shape if df is not None else None,
                    "columns": list(df.columns) if df is not None else [],
                    "quality_score": artifact.quality_score,
                    "processing_status": artifact.status.value,
                    "suggestions_count": len(artifact.suggestions),
                    "transformations_count": len(artifact.custom_transformations or [])
                }
        
        # Update state with loaded context
        state["data_context"] = data_context
        state["context_loaded"] = True
        
        logger.info("Enhanced context loaded successfully")
        return state
        
    except Exception as e:
        logger.error(f"Error loading enhanced context: {str(e)}")
        state["context_loaded"] = False
        state["data_context"] = {}
        return state


async def enhanced_response_composer(state: ConversationState) -> Dict[str, Any]:
    """
    Enhanced response composer with proactive suggestions and template recommendations.
    """
    try:
        logger.info("Composing enhanced response")
        
        # Get basic response from processing
        response = state.get("response", "")
        intent = state.get("intent", "")
        processing_result = state.get("processing_result", {})
        
        # Initialize suggestion engines
        proactive_engine = ProactiveSuggestionsEngine(get_openai_client())
        templates_engine = get_simple_conversation_templates()
        
        # Format main response
        main_response = _format_processing_result(processing_result, intent)
        
        # Generate proactive suggestions
        suggestions = await proactive_engine.generate_proactive_suggestions(state)
        
        # Get relevant templates
        template_suggestions = templates_engine.get_templates_for_context(state)
        
        # Build enhanced response
        enhanced_response = main_response
        
        # Add proactive suggestions if available
        if suggestions.get("success") and suggestions.get("suggestions"):
            enhanced_response += f"\n\n**💡 Suggestions:**\n"
            for suggestion in suggestions["suggestions"][:3]:  # Top 3 suggestions
                enhanced_response += f"• {suggestion}\n"
        
        # Add template recommendations if appropriate
        if template_suggestions and len(template_suggestions) > 0:
            enhanced_response += f"\n\n**📋 Common next steps:**\n"
            for template in template_suggestions:
                # Show just the first suggestion from each template
                if template.get("suggestions"):
                    first_suggestion = template["suggestions"][0]
                    enhanced_response += f"• Try: *\"{first_suggestion['example']}\"* - {first_suggestion['why']}\n"
        
        # Add helpful hints for new users
        data_context = state.get("data_context", {})
        if not data_context.get("has_data"):
            enhanced_response += f"\n\n**🔄 Getting started:** Upload a CSV or Excel file to begin data cleaning!"
        
        # Update state
        state["response"] = enhanced_response
        state["suggestions_provided"] = True
        
        logger.info("Enhanced response composed successfully")
        return state
        
    except Exception as e:
        logger.error(f"Error composing enhanced response: {str(e)}")
        # Fall back to basic response
        state["response"] = state.get("response", "I'm ready to help with your data cleaning task!")
        return state


async def enhanced_error_recovery(state: ConversationState) -> Dict[str, Any]:
    """
    Enhanced error recovery with intelligent error analysis and recovery strategies.
    """
    try:
        logger.info("Handling enhanced error recovery")
        
        error_message = state.get("error_message", "")
        if not error_message:
            return state
        
        # Initialize error recovery engine
        recovery_engine = EnhancedErrorRecoveryEngine(get_openai_client())
        
        # Analyze error and get recovery recommendation
        recovery_result = await recovery_engine.analyze_error_and_recover(
            error_message=error_message,
            conversation_state=state
        )
        
        if recovery_result["success"]:
            # Apply recovery strategy
            recovery_strategy = recovery_result["recovery_strategy"]
            
            if recovery_strategy == "retry_same":
                # Retry the same operation
                state["retry_operation"] = True
                state["response"] = f"I encountered an issue, but let me try that again. {recovery_result['explanation']}"
                
            elif recovery_strategy == "retry_modified":
                # Retry with modifications
                state["retry_operation"] = True
                state["operation_modifications"] = recovery_result.get("modifications", {})
                state["response"] = f"Let me try a different approach. {recovery_result['explanation']}"
                
            elif recovery_strategy == "alternative_method":
                # Suggest alternative method
                state["response"] = f"That approach didn't work, but here's an alternative: {recovery_result['explanation']}"
                
            elif recovery_strategy == "user_guidance":
                # Ask for user guidance
                state["awaiting_user_input"] = True
                state["response"] = f"I need your help to resolve this: {recovery_result['explanation']}"
                
            elif recovery_strategy == "graceful_reset":
                # Reset conversation state
                state["conversation_reset"] = True
                state["response"] = f"Let's start fresh. {recovery_result['explanation']}"
                
            else:
                # Default fallback
                state["response"] = f"I encountered an issue: {recovery_result['explanation']}"
            
            logger.info(f"Applied recovery strategy: {recovery_strategy}")
        else:
            # Basic error handling
            state["response"] = f"I encountered an error: {error_message}. Let me know if you'd like to try something else."
        
        # Clear error state
        state["error_message"] = ""
        state["error_recovered"] = True
        
        return state
        
    except Exception as e:
        logger.error(f"Error in enhanced error recovery: {str(e)}")
        # Ultimate fallback
        state["response"] = "I encountered an issue. Please try rephrasing your request or let me know if you need help."
        return state


async def conversation_branch_handler(state: ConversationState) -> Dict[str, Any]:
    """
    Handle conversation branching and flow control for complex operations.
    """
    try:
        logger.info("Handling conversation branching")
        
        # Check for branching conditions
        processing_result = state.get("processing_result", {})
        
        # Determine next conversation path
        if processing_result.get("confirmation_required"):
            # Branch to confirmation flow
            state["conversation_path"] = "confirmation"
            state["awaiting_confirmation"] = True
            state["response"] = processing_result.get("confirmation_message", "Do you want to proceed?")
            
        elif processing_result.get("error_occurred"):
            # Branch to error recovery flow
            state["conversation_path"] = "error_recovery"
            state["error_message"] = processing_result.get("error_message", "")
            
        elif processing_result.get("multi_step_operation"):
            # Branch to multi-step flow
            state["conversation_path"] = "multi_step"
            state["multi_step_context"] = processing_result.get("multi_step_context", {})
            
        else:
            # Continue normal flow
            state["conversation_path"] = "normal"
        
        logger.info(f"Conversation branched to: {state.get('conversation_path', 'normal')}")
        return state
        
    except Exception as e:
        logger.error(f"Error in conversation branching: {str(e)}")
        state["conversation_path"] = "normal"
        return state


async def template_suggestion_handler(state: ConversationState) -> Dict[str, Any]:
    """
    Handle simplified template suggestions without complex workflow management.
    """
    try:
        logger.info("Providing template suggestions")
        
        # Get templates engine
        templates_engine = get_simple_conversation_templates()
        
        # Get relevant templates based on context
        template_suggestions = templates_engine.get_templates_for_context(state)
        
        if template_suggestions:
            # Format template suggestions for display
            template_text = "\n\n**🎯 Helpful suggestions:**\n"
            
            for template in template_suggestions:
                template_text += f"\n{templates_engine.format_template_for_display(template)}\n"
            
            # Add to response
            current_response = state.get("response", "")
            state["response"] = current_response + template_text
            
            logger.info(f"Added {len(template_suggestions)} template suggestions")
        else:
            logger.info("No relevant template suggestions found")
        
        return state
        
    except Exception as e:
        logger.error(f"Error providing template suggestions: {str(e)}")
        return state


async def conversation_flow_coordinator(state: ConversationState) -> Dict[str, Any]:
    """
    Coordinate conversation flow and handle complex multi-turn operations.
    """
    try:
        logger.info("Coordinating conversation flow")
        
        # Get conversation path
        conversation_path = state.get("conversation_path", "normal")
        
        if conversation_path == "confirmation":
            # Handle confirmation workflow
            if state.get("user_confirmed"):
                # User confirmed - proceed with operation
                state["confirmation_handled"] = True
                state["proceed_with_operation"] = True
                state["response"] = "Great! I'll proceed with the operation."
            else:
                # User declined or unclear - ask for clarification
                state["response"] = "I need your confirmation to proceed. Please say 'yes' to continue or 'no' to cancel."
                
        elif conversation_path == "multi_step":
            # Handle multi-step operations
            multi_step_context = state.get("multi_step_context", {})
            current_step = multi_step_context.get("current_step", 1)
            total_steps = multi_step_context.get("total_steps", 1)
            
            if current_step < total_steps:
                # Continue to next step
                state["multi_step_context"]["current_step"] = current_step + 1
                state["response"] = f"Step {current_step + 1} of {total_steps}: {multi_step_context.get('next_step_description', 'Continuing...')}"
            else:
                # Multi-step operation complete
                state["conversation_path"] = "normal"
                state["response"] = "Multi-step operation completed successfully!"
        
        logger.info(f"Conversation flow coordinated for path: {conversation_path}")
        return state
        
    except Exception as e:
        logger.error(f"Error coordinating conversation flow: {str(e)}")
        return state


# Enhanced processing functions (reuse existing logic with real components)
async def enhanced_data_processing(state: ConversationState) -> Dict[str, Any]:
    """Enhanced data processing with real component integration."""
    try:
        logger.info("Processing enhanced data operation")
        
        # Get processing parameters
        intent = state.get("intent", "")
        artifact_id = state.get("artifact_id")
        
        if not artifact_id:
            return {
                **state,
                "processing_result": {
                    "success": False,
                    "error_message": "No data artifact available for processing"
                }
            }
        
        # Get data store and components
        data_store = get_data_store()
        openai_client = get_openai_client()
        
        # Initialize processors
        complete_processor = CompleteFileProcessor(openai_client)
        quality_agent = DataQualityAgent(openai_client)
        transformation_engine = TransformationEngine()
        
        # Get current data
        artifact = await data_store.get_data_artifact(artifact_id)
        df = await data_store.get_dataframe(artifact_id)
        
        if df is None or df.empty:
            return {
                **state,
                "processing_result": {
                    "success": False,
                    "error_message": "No data available for processing"
                }
            }
        
        # Process based on intent
        if intent == Intent.ANALYZE.value:
            # Real quality analysis
            quality_issues = await quality_agent.analyze_data(df)
            suggestions = await quality_agent.generate_suggestions(quality_issues, df)
            
            # Update artifact with new suggestions
            artifact.suggestions = suggestions
            await data_store.update_data_artifact(artifact)
            
            result = {
                "success": True,
                "message": f"Found {len(quality_issues)} quality issues with {len(suggestions)} suggestions",
                "quality_issues": quality_issues,
                "suggestions": suggestions
            }
            
        elif intent == Intent.CLEAN.value:
            # Real data cleaning
            if artifact.suggestions:
                # Apply high-confidence suggestions
                high_confidence_suggestions = [s for s in artifact.suggestions if s.confidence > 0.7]
                applied_count = 0
                
                for suggestion in high_confidence_suggestions[:5]:  # Apply top 5
                    try:
                        # Convert and apply suggestion
                        from ..suggestion_converter import SuggestionConverter
                        converter = SuggestionConverter()
                        transformation = await converter.convert_suggestion_to_transformation(
                            suggestion, df, artifact.owner_id
                        )
                        
                        df, _ = await transformation_engine.apply_transformation(
                            df, transformation, artifact_id, artifact.owner_id
                        )
                        applied_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to apply suggestion {suggestion.suggestion_id}: {str(e)}")
                
                # Save updated DataFrame
                await data_store.save_dataframe(artifact_id, df)
                
                result = {
                    "success": True,
                    "message": f"Applied {applied_count} cleaning suggestions",
                    "transformations_applied": applied_count,
                    "data_shape": df.shape
                }
            else:
                result = {
                    "success": False,
                    "message": "No cleaning suggestions available. Try analyzing the data first."
                }
        
        elif intent == Intent.SHOW_DATA.value:
            # Real data display
            sample_data = df.head(10).to_dict('records')
            result = {
                "success": True,
                "message": f"Showing first 10 rows of {df.shape[0]} total rows",
                "sample_data": sample_data,
                "data_shape": df.shape,
                "columns": list(df.columns)
            }
            
        elif intent == Intent.DESCRIBE.value:
            # Real data description
            description = df.describe(include='all').to_dict()
            result = {
                "success": True,
                "message": f"Data description for {df.shape[0]} rows and {df.shape[1]} columns",
                "description": description,
                "data_types": df.dtypes.to_dict(),
                "missing_values": df.isnull().sum().to_dict()
            }
            
        else:
            result = {
                "success": False,
                "message": f"Enhanced processing not available for intent: {intent}"
            }
        
        return {
            **state,
            "processing_result": result
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced data processing: {str(e)}")
        return {
            **state,
            "processing_result": {
                "success": False,
                "error_message": str(e)
            }
        } 