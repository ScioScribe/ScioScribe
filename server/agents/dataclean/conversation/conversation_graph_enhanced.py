"""
Enhanced LangGraph Conversation Orchestrator with Advanced Intent Classification

This module provides the enhanced conversation workflow that incorporates
Phase 1.3 advanced intent classification capabilities.
"""

from typing import Dict, Any, Optional
import logging
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .state_schema import ConversationState, Intent
from .conversation_session_manager import ConversationSessionManager
from .nodes_enhanced import (
    enhanced_message_parser_node,
    enhanced_context_loader_node,
    enhanced_processing_router_node,
    enhanced_response_generator_node,
)

logger = logging.getLogger(__name__)


class EnhancedConversationGraph:
    """
    Enhanced conversation orchestrator with Phase 1.3 intent classification.
    
    This class provides:
    - Advanced intent classification with confidence scoring
    - Parameter extraction from natural language
    - CSV/Excel specific intent handling
    - Intelligent fallback and suggestions
    - Enhanced context-aware responses
    """
    
    def __init__(self):
        """Initialize the enhanced conversation graph with session manager."""
        self.graph = self._build_enhanced_graph()
        self.compiled_graph = None
        self.session_manager = ConversationSessionManager()
        
    def _build_enhanced_graph(self) -> StateGraph:
        """
        Build the enhanced LangGraph conversation workflow.
        
        The enhanced graph follows this flow:
        1. Enhanced message parsing with advanced intent classification
        2. Enhanced context loading with CSV/Excel specifics
        3. Enhanced processing routing with parameter handling
        4. Enhanced response generation with confidence awareness
        """
        # Initialize the state graph
        workflow = StateGraph(ConversationState)
        
        # Add enhanced processing nodes
        workflow.add_node("enhanced_message_parser", enhanced_message_parser_node)
        workflow.add_node("enhanced_context_loader", enhanced_context_loader_node)
        workflow.add_node("enhanced_processing_router", enhanced_processing_router_node)
        workflow.add_node("enhanced_response_generator", enhanced_response_generator_node)
        
        # Define the enhanced conversation flow
        workflow.set_entry_point("enhanced_message_parser")
        
        # Enhanced flow with better processing
        workflow.add_edge("enhanced_message_parser", "enhanced_context_loader")
        workflow.add_edge("enhanced_context_loader", "enhanced_processing_router")
        workflow.add_edge("enhanced_processing_router", "enhanced_response_generator")
        workflow.add_edge("enhanced_response_generator", END)
        
        return workflow
    
    def compile(self) -> CompiledStateGraph:
        """
        Compile the enhanced conversation graph for execution.
        
        Returns:
            CompiledStateGraph: The compiled enhanced graph ready for execution
        """
        if self.compiled_graph is None:
            self.compiled_graph = self.graph.compile()
        return self.compiled_graph
    
    async def start_conversation(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new enhanced conversation session or resume an existing one.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID for resuming
            artifact_id: Optional data artifact ID
            file_path: Optional file path for processing
            
        Returns:
            Dict containing session information with enhanced capabilities
        """
        try:
            # Try to get existing session first
            if session_id:
                existing_session = await self.session_manager.get_session(session_id)
                if existing_session:
                    logger.info(f"Resumed existing enhanced session {session_id}")
                    return {
                        "session_id": session_id,
                        "resumed": True,
                        "status": "active",
                        "message": "Enhanced session resumed successfully",
                        "capabilities": "Advanced intent classification enabled"
                    }
            
            # Create new session
            session_state = await self.session_manager.create_session(
                user_id=user_id,
                session_id=session_id,
                artifact_id=artifact_id,
                file_path=file_path
            )
            
            session_id = session_state["session_id"]
            logger.info(f"Started new enhanced conversation session {session_id}")
            
            return {
                "session_id": session_id,
                "resumed": False,
                "status": "active",
                "message": "New enhanced conversation session started",
                "capabilities": "Advanced intent classification, parameter extraction, CSV/Excel support",
                "data_context": session_state.get("data_context"),
                "file_format": session_state.get("file_format")
            }
            
        except Exception as e:
            logger.error(f"Error starting enhanced conversation: {str(e)}")
            return {
                "session_id": session_id,
                "resumed": False,
                "status": "error",
                "message": f"Failed to start enhanced conversation: {str(e)}"
            }
    
    async def process_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        artifact_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a user message through the enhanced conversation workflow.
        
        Args:
            user_message: The user's natural language input
            session_id: Session identifier
            user_id: User identifier
            artifact_id: Optional data artifact ID
            **kwargs: Additional context parameters
            
        Returns:
            Dict containing enhanced conversation response with confidence and parameters
        """
        try:
            logger.info(f"Processing enhanced message for session {session_id}: {user_message}")
            
            # Get or create session
            session_state = await self.session_manager.get_session(session_id)
            if not session_state:
                # Create new session if not found
                session_state = await self.session_manager.create_session(
                    user_id=user_id,
                    session_id=session_id,
                    artifact_id=artifact_id,
                    file_path=kwargs.get("file_path")
                )
            
            # Initialize enhanced state fields
            initial_state = {
                **session_state,
                "user_message": user_message,
                "artifact_id": artifact_id or session_state.get("artifact_id"),
                
                # Enhanced fields for Phase 1.3
                "intent_confidence": 0.0,
                "intent_reasoning": "",
                "alternative_intents": [],
                "csv_excel_context": session_state.get("csv_excel_context", {}),
                
                **kwargs
            }
            
            # Compile and execute the enhanced graph
            compiled_graph = self.compile()
            result = await compiled_graph.ainvoke(initial_state)
            
            # Update session with enhanced results
            await self.session_manager.update_session(session_id, result)
            
            # Add enhanced conversation turn to history
            await self.session_manager.add_conversation_turn(
                session_id=session_id,
                user_message=user_message,
                assistant_response=result.get("response", ""),
                intent=result.get("intent", Intent.UNKNOWN),
                response_type=result.get("response_type", "info"),
                metadata={
                    "operation_result": result.get("operation_result"),
                    "confirmation_required": result.get("confirmation_required", False),
                    "intent_confidence": result.get("intent_confidence", 0.0),
                    "intent_reasoning": result.get("intent_reasoning", ""),
                    "extracted_parameters": result.get("extracted_parameters", {}),
                    "alternative_intents": result.get("alternative_intents", [])
                }
            )
            
            # Extract enhanced response data
            response_data = {
                "response": result.get("response", "I apologize, but I couldn't process your request."),
                "response_type": result.get("response_type", "error"),
                "intent": result.get("intent", Intent.UNKNOWN).value,
                "session_id": session_id,
                "conversation_history": result.get("conversation_history", []),
                "confirmation_required": result.get("confirmation_required", False),
                "operation_result": result.get("operation_result"),
                "error_message": result.get("error_message"),
                "data_context": result.get("data_context"),
                "next_steps": result.get("next_steps"),
                "suggestions": result.get("suggestions"),
                
                # Enhanced Phase 1.3 fields
                "intent_confidence": result.get("intent_confidence", 0.0),
                "intent_reasoning": result.get("intent_reasoning", ""),
                "extracted_parameters": result.get("extracted_parameters", {}),
                "alternative_intents": result.get("alternative_intents", []),
                
                "csv_excel_context": {
                    "file_format": result.get("file_format"),
                    "delimiter": result.get("delimiter"),
                    "encoding": result.get("encoding"),
                    "sheet_name": result.get("sheet_name"),
                    "context_info": result.get("csv_excel_context", {})
                }
            }
            
            logger.info(f"Successfully processed enhanced message for session {session_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing enhanced message for session {session_id}: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "response_type": "error",
                "intent": Intent.UNKNOWN.value,
                "session_id": session_id,
                "error_message": str(e),
                "conversation_history": [],
                "confirmation_required": False,
                "operation_result": None,
                "data_context": None,
                "next_steps": None,
                "suggestions": None,
                
                # Enhanced error fields
                "intent_confidence": 0.0,
                "intent_reasoning": f"Processing failed: {str(e)}",
                "extracted_parameters": {},
                "alternative_intents": [],
                "csv_excel_context": {}
            }
    
    async def handle_confirmation(
        self,
        session_id: str,
        user_id: str,
        confirmed: bool,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Handle user confirmation with enhanced context awareness.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            confirmed: Whether the user confirmed the operation
            **kwargs: Additional context parameters
            
        Returns:
            Dict containing enhanced confirmation response
        """
        try:
            logger.info(f"Handling enhanced confirmation for session {session_id}: {confirmed}")
            
            # Get current session
            session_state = await self.session_manager.get_session(session_id)
            if not session_state:
                return {
                    "response": "Session not found. Please start a new conversation.",
                    "response_type": "error",
                    "intent": "error",
                    "session_id": session_id,
                    "confirmation_required": False,
                    "operation_result": None,
                    "error_message": "Session not found",
                    "intent_confidence": 0.0
                }
            
            # Get the pending operation context
            pending_operation = session_state.get("pending_operation", {})
            extracted_parameters = session_state.get("extracted_parameters", {})
            
            if confirmed:
                # Process the confirmed operation with enhanced context
                response_text = "Operation confirmed and will be executed."
                if extracted_parameters:
                    param_info = ", ".join([f"{k}: {v}" for k, v in extracted_parameters.items()])
                    response_text += f" Parameters: {param_info}."
                
                operation_result = {
                    "status": "success", 
                    "message": "Operation confirmed",
                    "parameters": extracted_parameters
                }
                
                # Add enhanced conversation turn
                await self.session_manager.add_conversation_turn(
                    session_id=session_id,
                    user_message="Yes, proceed with the operation",
                    assistant_response=response_text,
                    intent=Intent.CLEAN,  # Assuming most confirmations are for cleaning
                    response_type="result",
                    metadata={
                        "confirmed": True,
                        "parameters": extracted_parameters,
                        "operation": pending_operation
                    }
                )
                
                return {
                    "response": response_text,
                    "response_type": "result",
                    "intent": "confirmation",
                    "session_id": session_id,
                    "confirmation_required": False,
                    "operation_result": operation_result,
                    "error_message": None,
                    "intent_confidence": 1.0,
                    "extracted_parameters": extracted_parameters
                }
            else:
                # Operation was cancelled
                response_text = "Operation cancelled. Is there anything else I can help you with?"
                operation_result = {
                    "status": "cancelled", 
                    "message": "Operation cancelled by user",
                    "cancelled_parameters": extracted_parameters
                }
                
                # Add enhanced conversation turn
                await self.session_manager.add_conversation_turn(
                    session_id=session_id,
                    user_message="No, cancel the operation",
                    assistant_response=response_text,
                    intent=Intent.CLEAN,
                    response_type="info",
                    metadata={
                        "confirmed": False,
                        "cancelled_parameters": extracted_parameters
                    }
                )
                
                return {
                    "response": response_text,
                    "response_type": "info",
                    "intent": "cancellation",
                    "session_id": session_id,
                    "confirmation_required": False,
                    "operation_result": operation_result,
                    "error_message": None,
                    "intent_confidence": 1.0,
                    "extracted_parameters": {}
                }
                
        except Exception as e:
            logger.error(f"Error handling enhanced confirmation for session {session_id}: {str(e)}")
            return {
                "response": "I encountered an error while processing your confirmation. Please try again.",
                "response_type": "error",
                "intent": "error",
                "session_id": session_id,
                "confirmation_required": False,
                "operation_result": None,
                "error_message": str(e),
                "intent_confidence": 0.0,
                "extracted_parameters": {}
            }
    
    def get_enhanced_capabilities(self) -> Dict[str, Any]:
        """
        Get information about enhanced conversation capabilities.
        
        Returns:
            Dict containing enhanced capability information
        """
        return {
            "phase_1_3_features": {
                "advanced_intent_classification": True,
                "confidence_scoring": True,
                "parameter_extraction": True,
                "csv_excel_specific_handling": True,
                "fallback_suggestions": True,
                "alternative_intent_suggestions": True
            },
            "supported_intents": [intent.value for intent in Intent if intent != Intent.UNKNOWN],
            "supported_file_formats": ["csv", "excel"],
            "enhanced_features": {
                "session_management": [
                    "Create and resume sessions",
                    "Session state persistence", 
                    "Enhanced conversation history tracking",
                    "CSV/Excel context management with confidence"
                ],
                "intent_classification": [
                    "Pattern-based intent recognition",
                    "Confidence scoring (0-1)",
                    "Parameter extraction from natural language",
                    "CSV/Excel specific intent handling",
                    "Alternative intent suggestions",
                    "Intelligent fallback handling"
                ],
                "data_exploration": [
                    "Show data with extracted row counts",
                    "Describe data structure with confidence",
                    "Analyze data quality with parameters"
                ],
                "data_cleaning": [
                    "Clean data with column extraction",
                    "Fix data problems with confidence scoring",
                    "Remove invalid entries with parameter handling"
                ],
                "file_operations": [
                    "Excel sheet selection with name extraction",
                    "CSV delimiter detection with preferences",
                    "Encoding detection and handling"
                ],
                "conversation_features": [
                    "Multi-turn conversations with context",
                    "Context awareness with confidence tracking",
                    "Operation confirmation with parameter details",
                    "Error recovery with intelligent suggestions"
                ]
            },
            "confidence_thresholds": {
                "high_confidence": ">= 0.8",
                "medium_confidence": "0.5 - 0.7",
                "low_confidence": "0.3 - 0.5",
                "fallback": "< 0.3"
            },
            "conversation_flow": [
                "Enhanced message parsing with intent classification",
                "Enhanced context loading with CSV/Excel specifics",
                "Enhanced processing routing with parameter handling",
                "Enhanced response generation with confidence awareness"
            ]
        }


# Enhanced convenience functions

async def start_enhanced_conversation_session(
    user_id: str,
    session_id: Optional[str] = None,
    artifact_id: Optional[str] = None,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start a new enhanced conversation session with Phase 1.3 capabilities.
    
    Args:
        user_id: User identifier
        session_id: Optional session ID for resuming
        artifact_id: Optional existing data artifact ID
        file_path: Optional path to data file
        
    Returns:
        Dict containing enhanced session information
    """
    conversation_graph = EnhancedConversationGraph()
    return await conversation_graph.start_conversation(
        user_id=user_id,
        session_id=session_id,
        artifact_id=artifact_id,
        file_path=file_path
    )


async def process_enhanced_conversation_message(
    user_message: str,
    session_id: str,
    user_id: str,
    artifact_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Process a conversation message with enhanced Phase 1.3 capabilities.
    
    Args:
        user_message: The user's natural language input
        session_id: Session identifier
        user_id: User identifier
        artifact_id: Optional data artifact ID
        **kwargs: Additional context parameters
        
    Returns:
        Dict containing enhanced conversation response
    """
    conversation_graph = EnhancedConversationGraph()
    return await conversation_graph.process_message(
        user_message=user_message,
        session_id=session_id,
        user_id=user_id,
        artifact_id=artifact_id,
        **kwargs
    ) 