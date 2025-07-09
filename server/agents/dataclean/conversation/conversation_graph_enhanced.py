"""
Enhanced conversation graph with advanced features for Phase 3.

This module provides enhanced conversation management with multi-turn context,
branching, error recovery, proactive suggestions, and simplified templates.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from langgraph.graph import StateGraph, END

from .state_schema import ConversationState, Intent
from .conversation_session_manager import ConversationSessionManager
from .intent_classifier import EnhancedIntentClassifier
from .nodes_enhanced import (
    enhanced_context_loader,
    enhanced_response_composer,
    enhanced_error_recovery,
    conversation_branch_handler,
    template_suggestion_handler,
    conversation_flow_coordinator,
    enhanced_data_processing
)
from .nodes import (
    data_processor,
    response_formatter,
    conversation_finalizer,
    _prepare_response,
    _update_conversation_history
)
from config import get_openai_client

logger = logging.getLogger(__name__)


class EnhancedConversationGraph:
    """
    Enhanced conversation graph with advanced features for Phase 3.
    
    Features:
    - Multi-turn conversation context management
    - Conversation branching and flow control
    - Proactive suggestions and next-step recommendations
    - Enhanced error recovery with intelligent fallback strategies
    - Conversation summarization for long conversations
    - Simplified template suggestions (no complex workflows)
    """
    
    def __init__(self):
        """Initialize the enhanced conversation graph."""
        self.session_manager = ConversationSessionManager()
        self.intent_classifier = EnhancedIntentClassifier()
        self.graph = self._build_enhanced_graph()
        self.compiled_graph = self.graph.compile()
        
        logger.info("Enhanced conversation graph initialized")
    
    def _build_enhanced_graph(self) -> StateGraph:
        """Build the enhanced conversation graph with advanced features."""
        # Create the graph
        graph = StateGraph(ConversationState)
        
        # Add enhanced nodes
        graph.add_node("enhanced_context_loader", enhanced_context_loader)
        graph.add_node("intent_classifier", self._enhanced_intent_classification)
        graph.add_node("conversation_branch_handler", conversation_branch_handler)
        graph.add_node("enhanced_data_processing", enhanced_data_processing)
        graph.add_node("enhanced_error_recovery", enhanced_error_recovery)
        graph.add_node("template_suggestion_handler", template_suggestion_handler)
        graph.add_node("conversation_flow_coordinator", conversation_flow_coordinator)
        graph.add_node("enhanced_response_composer", enhanced_response_composer)
        graph.add_node("conversation_finalizer", conversation_finalizer)
        
        # Define the enhanced conversation flow
        graph.set_entry_point("enhanced_context_loader")
        
        # Context loading to intent classification
        graph.add_edge("enhanced_context_loader", "intent_classifier")
        
        # Intent classification to conversation branching
        graph.add_edge("intent_classifier", "conversation_branch_handler")
        
        # Conditional edges from conversation branching
        graph.add_conditional_edges(
            "conversation_branch_handler",
            self._route_conversation_path,
            {
                "normal": "enhanced_data_processing",
                "error_recovery": "enhanced_error_recovery",
                "confirmation": "conversation_flow_coordinator",
                "multi_step": "conversation_flow_coordinator"
            }
        )
        
        # Data processing to template suggestions
        graph.add_edge("enhanced_data_processing", "template_suggestion_handler")
        
        # Template suggestions to response composition
        graph.add_edge("template_suggestion_handler", "enhanced_response_composer")
        
        # Error recovery to response composition
        graph.add_edge("enhanced_error_recovery", "enhanced_response_composer")
        
        # Flow coordination to response composition
        graph.add_edge("conversation_flow_coordinator", "enhanced_response_composer")
        
        # Response composition to finalization
        graph.add_edge("enhanced_response_composer", "conversation_finalizer")
        
        # Finalization to end
        graph.add_edge("conversation_finalizer", END)
        
        return graph
    
    def _route_conversation_path(self, state: ConversationState) -> str:
        """Route conversation based on the determined path."""
        conversation_path = state.get("conversation_path", "normal")
        
        if conversation_path == "error_recovery":
            return "error_recovery"
        elif conversation_path in ["confirmation", "multi_step"]:
            return conversation_path
        else:
            return "normal"
    
    async def _enhanced_intent_classification(self, state: ConversationState) -> Dict[str, Any]:
        """Enhanced intent classification with conversation context."""
        try:
            logger.info("Performing enhanced intent classification")
            
            user_message = state.get("user_message", "")
            conversation_history = state.get("conversation_history", [])
            data_context = state.get("data_context", {})
            
            # Classify intent with enhanced context
            intent_result = await self.intent_classifier.classify_intent(
                message=user_message,
                context={
                    "conversation_history": conversation_history,
                    "data_context": data_context
                }
            )
            
            # Update state with classification results
            state["intent"] = intent_result.intent
            state["intent_confidence"] = intent_result.confidence
            state["extracted_parameters"] = intent_result.extracted_parameters
            state["confirmation_required"] = intent_result.confidence < 0.5
            
            if intent_result.confidence < 0.5:
                state["confirmation_message"] = f"I'm not sure what you want to do. Could you rephrase your request?"
            
            logger.info(f"Intent classified as: {intent_result.intent} (confidence: {intent_result.confidence:.2f})")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in enhanced intent classification: {str(e)}")
            # Fallback to basic classification
            state["intent"] = Intent.UNKNOWN.value
            state["confidence"] = 0.0
            return state
    
    async def start_conversation(
        self, 
        user_id: str, 
        session_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new enhanced conversation session.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID for resuming
            artifact_id: Optional data artifact ID
            file_path: Optional file path for processing
            
        Returns:
            Session information and welcome message
        """
        try:
            logger.info(f"Starting enhanced conversation for user: {user_id}")
            
            # Create or resume session
            if session_id:
                session_info = await self.session_manager.get_session(session_id)
                if session_info:
                    logger.info(f"Resuming session: {session_id}")
                else:
                    session_info = await self.session_manager.create_session(user_id)
                    logger.info(f"Session not found, created new session: {session_info['session_id']}")
            else:
                session_info = await self.session_manager.create_session(user_id)
                logger.info(f"Created new session: {session_info['session_id']}")
            
            # Initialize conversation state
            initial_state = {
                "session_id": session_info["session_id"],
                "user_id": user_id,
                "artifact_id": artifact_id,
                "conversation_history": session_info.get("conversation_history", []),
                "data_context": {},
                "context_loaded": False,
                "conversation_path": "normal"
            }
            
            # Generate welcome message with simplified templates
            welcome_message = "👋 **Welcome to ScioScribe Data Cleaning Assistant!**\n\n"
            
            if artifact_id:
                welcome_message += "I can see you have data ready to work with. "
            else:
                welcome_message += "Upload a CSV or Excel file to get started. "
            
            welcome_message += "I'm here to help you clean, analyze, and explore your data through natural conversation.\n\n"
            welcome_message += "**Quick start:**\n"
            welcome_message += "• *\"show me the data\"* - View your data\n"
            welcome_message += "• *\"analyze the data quality\"* - Check for issues\n"
            welcome_message += "• *\"clean the data\"* - Fix common problems\n"
            welcome_message += "• *\"describe the data\"* - Get data overview\n\n"
            welcome_message += "💡 **Pro tip:** You can ask me questions in natural language!"
            
            return {
                "success": True,
                "session_id": session_info["session_id"],
                "user_id": user_id,
                "message": welcome_message,
                "capabilities": self.get_conversation_capabilities(),
                "conversation_active": True
            }
            
        except Exception as e:
            logger.error(f"Error starting enhanced conversation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to start conversation session"
            }
    
    async def process_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        artifact_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user message through the enhanced conversation graph.
        
        Args:
            user_message: User's natural language input
            session_id: Session identifier
            user_id: User identifier
            artifact_id: Optional data artifact ID
            
        Returns:
            Enhanced conversation response
        """
        try:
            logger.info(f"Processing enhanced message for session: {session_id}")
            
            # Get session info
            session_info = await self.session_manager.get_session(session_id)
            if not session_info:
                return {
                    "success": False,
                    "error": "Session not found",
                    "message": "Session expired. Please start a new conversation."
                }
            
            # Initialize conversation state
            state = {
                "session_id": session_id,
                "user_id": user_id,
                "artifact_id": artifact_id or session_info.get("artifact_id"),
                "user_message": user_message,
                "conversation_history": session_info.get("conversation_history", []),
                "data_context": {},
                "context_loaded": False,
                "conversation_path": "normal"
            }
            
            # Process through enhanced graph
            final_state = await self.compiled_graph.ainvoke(state)
            
            # Extract response
            response = final_state.get("response", "I'm ready to help with your data cleaning task!")
            
            # Update session with final state
            await self.session_manager.update_session(session_id, final_state)
            
            return {
                "success": True,
                "response": response,
                "session_id": session_id,
                "intent": final_state.get("intent"),
                "confidence": final_state.get("confidence", 0.0),
                "suggestions_provided": final_state.get("suggestions_provided", False),
                "conversation_active": True,
                "processing_result": final_state.get("processing_result", {})
            }
            
        except Exception as e:
            logger.error(f"Error processing enhanced message: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "I encountered an error processing your message. Please try again."
            }
    
    async def handle_confirmation(
        self, 
        session_id: str, 
        user_id: str, 
        confirmed: bool
    ) -> Dict[str, Any]:
        """
        Handle user confirmation for operations that require approval.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            confirmed: Whether the user confirmed the operation
            
        Returns:
            Confirmation response
        """
        try:
            logger.info(f"Handling confirmation for session: {session_id}")
            
            # Get session info
            session_info = await self.session_manager.get_session(session_id)
            if not session_info:
                return {
                    "success": False,
                    "error": "Session not found",
                    "message": "Session expired. Please start a new conversation."
                }
            
            # Process confirmation
            if confirmed:
                response = "✅ **Confirmed!** I'll proceed with the requested operation."
                # Here you would typically trigger the actual operation
            else:
                response = "❌ **Cancelled.** The operation has been cancelled. What would you like to do next?"
            
            return {
                "success": True,
                "response": response,
                "session_id": session_id,
                "confirmed": confirmed,
                "conversation_active": True
            }
            
        except Exception as e:
            logger.error(f"Error handling confirmation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error processing confirmation"
            }
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of the conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary information
        """
        try:
            session_info = await self.session_manager.get_session(session_id)
            if not session_info:
                return {
                    "status": "error",
                    "message": "Session not found"
                }
            
            conversation_history = session_info.get("conversation_history", [])
            
            return {
                "status": "success",
                "session_id": session_id,
                "user_id": session_info.get("user_id"),
                "artifact_id": session_info.get("artifact_id"),
                "conversation_turns": len(conversation_history),
                "created_at": session_info.get("created_at"),
                "last_activity": session_info.get("last_activity"),
                "conversation_active": True
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_conversation_capabilities(self) -> Dict[str, Any]:
        """
        Get information about enhanced conversation capabilities.
        
        Returns:
            Conversation capabilities and supported intents
        """
        return {
            "supported_intents": [
                {
                    "intent": "show_data",
                    "description": "Display data samples and structure",
                    "examples": ["show me the data", "display first 10 rows"]
                },
                {
                    "intent": "analyze",
                    "description": "Analyze data quality and identify issues",
                    "examples": ["analyze the data quality", "find data issues"]
                },
                {
                    "intent": "clean",
                    "description": "Clean and fix data quality issues",
                    "examples": ["clean the data", "fix the issues"]
                },
                {
                    "intent": "describe",
                    "description": "Get data description and statistics",
                    "examples": ["describe the data", "data overview"]
                },
                {
                    "intent": "transform",
                    "description": "Transform and modify data",
                    "examples": ["convert dates", "standardize formats"]
                },
                {
                    "intent": "save",
                    "description": "Save and export processed data",
                    "examples": ["save the data", "export to CSV"]
                }
            ],
            "features": [
                "Multi-turn conversation context",
                "Proactive suggestions",
                "Enhanced error recovery",
                "Conversation summarization",
                "Simplified helpful templates",
                "Natural language understanding",
                "Confirmation workflows"
            ],
            "supported_file_formats": ["CSV", "Excel (.xlsx, .xls)"],
            "conversation_types": [
                "Data exploration",
                "Quality analysis",
                "Data cleaning",
                "Format standardization",
                "Export and save"
            ]
        }


# Global instance
_enhanced_conversation_graph = None

def get_enhanced_conversation_graph() -> EnhancedConversationGraph:
    """Get the global enhanced conversation graph instance."""
    global _enhanced_conversation_graph
    if _enhanced_conversation_graph is None:
        _enhanced_conversation_graph = EnhancedConversationGraph()
    return _enhanced_conversation_graph 