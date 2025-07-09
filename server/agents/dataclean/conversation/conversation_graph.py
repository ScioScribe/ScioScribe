"""
LangGraph Conversation Orchestrator for Data Cleaning

This module defines the main conversation workflow that orchestrates
all the processing nodes for conversational data cleaning operations.
"""

from typing import Dict, Any, Optional
import logging
from langgraph.graph import StateGraph, END

from .state_schema import ConversationState, Intent
from .conversation_session_manager import ConversationSessionManager
from .nodes_enhanced import (
    enhanced_message_parser_node,
    enhanced_context_loader_node,
    enhanced_processing_router_node,
    enhanced_response_generator_node,
)

logger = logging.getLogger(__name__)


class ConversationGraph:
    """
    Main conversation orchestrator using LangGraph with enhanced state management.
    
    This class manages the conversation flow and coordinates all processing
    nodes to provide a seamless conversational data cleaning experience.
    """
    
    def __init__(self):
        """Initialize the conversation graph with session manager."""
        self.graph = self._build_graph()
        self.compiled_graph = None
        self.session_manager = ConversationSessionManager()
        
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph conversation workflow.
        
        The graph follows this flow:
        1. Parse user message and extract intent
        2. Load data context from memory store
        3. Route to appropriate processing component
        4. Generate conversational response
        """
        # Initialize the state graph
        workflow = StateGraph(ConversationState)
        
        # Add enhanced processing nodes
        workflow.add_node("message_parser", enhanced_message_parser_node)
        workflow.add_node("context_loader", enhanced_context_loader_node)
        workflow.add_node("processing_router", enhanced_processing_router_node)
        workflow.add_node("response_generator", enhanced_response_generator_node)
        
        # Define the conversation flow
        workflow.set_entry_point("message_parser")
        
        # Linear flow for basic implementation
        workflow.add_edge("message_parser", "context_loader")
        workflow.add_edge("context_loader", "processing_router")
        workflow.add_edge("processing_router", "response_generator")
        workflow.add_edge("response_generator", END)
        
        return workflow
    
    def compile(self):
        """
        Compile the conversation graph for execution.
        
        Returns:
            The compiled graph ready for execution
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
        Start a new conversation session or resume an existing one.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID for resuming
            artifact_id: Optional data artifact ID
            file_path: Optional file path for processing
            
        Returns:
            Dict containing session information
        """
        try:
            # Try to get existing session first
            if session_id:
                existing_session = await self.session_manager.get_session(session_id)
                if existing_session:
                    logger.info(f"Resumed existing session {session_id}")
                    return {
                        "session_id": session_id,
                        "resumed": True,
                        "status": "active",
                        "message": "Session resumed successfully"
                    }
            
            # Create new session
            session_state = await self.session_manager.create_session(
                user_id=user_id,
                session_id=session_id,
                artifact_id=artifact_id,
                file_path=file_path
            )
            
            session_id = session_state["session_id"]
            logger.info(f"Started new conversation session {session_id}")
            
            return {
                "session_id": session_id,
                "resumed": False,
                "status": "active",
                "message": "New conversation session started",
                "data_context": session_state.get("data_context"),
                "file_format": session_state.get("file_format")
            }
            
        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return {
                "session_id": session_id,
                "resumed": False,
                "status": "error",
                "message": f"Failed to start conversation: {str(e)}"
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
        Process a user message through the conversation workflow with session management.
        
        Args:
            user_message: The user's natural language input
            session_id: Session identifier
            user_id: User identifier
            artifact_id: Optional data artifact ID
            **kwargs: Additional context parameters
            
        Returns:
            Dict containing the conversation response and updated state
        """
        try:
            logger.info(f"Processing message for session {session_id}: {user_message}")
            
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
            
            # Update session with current message
            initial_state = {
                **session_state,
                "user_message": user_message,
                "artifact_id": artifact_id or session_state.get("artifact_id"),
                **kwargs
            }
            
            # Compile and execute the graph
            compiled_graph = self.compile()
            result = await compiled_graph.ainvoke(initial_state)
            
            # Update session with results
            await self.session_manager.update_session(session_id, result)
            
            # Add conversation turn to history
            await self.session_manager.add_conversation_turn(
                session_id=session_id,
                user_message=user_message,
                assistant_response=result.get("response", ""),
                intent=result.get("intent", Intent.UNKNOWN),
                response_type=result.get("response_type", "info"),
                metadata={
                    "operation_result": result.get("operation_result"),
                    "confirmation_required": result.get("confirmation_required", False)
                }
            )
            
            # Extract response data
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
                "csv_excel_context": {
                    "file_format": result.get("file_format"),
                    "delimiter": result.get("delimiter"),
                    "encoding": result.get("encoding"),
                    "sheet_name": result.get("sheet_name")
                }
            }
            
            logger.info(f"Successfully processed message for session {session_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing message for session {session_id}: {str(e)}")
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
        Handle user confirmation for operations that require approval.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            confirmed: Whether the user confirmed the operation
            **kwargs: Additional context parameters
            
        Returns:
            Dict containing the confirmation response
        """
        try:
            logger.info(f"Handling confirmation for session {session_id}: {confirmed}")
            
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
                    "error_message": "Session not found"
                }
            
            if confirmed:
                # Process the confirmed operation
                # This will be enhanced in Phase 2 to actually execute the operation
                response_text = "Operation confirmed and will be executed."
                operation_result = {"status": "success", "message": "Operation confirmed"}
                
                # Add conversation turn
                await self.session_manager.add_conversation_turn(
                    session_id=session_id,
                    user_message="Yes, proceed with the operation",
                    assistant_response=response_text,
                    intent=Intent.CLEAN,  # Assuming most confirmations are for cleaning
                    response_type="result",
                    metadata={"confirmed": True}
                )
                
                return {
                    "response": response_text,
                    "response_type": "result",
                    "intent": "confirmation",
                    "session_id": session_id,
                    "confirmation_required": False,
                    "operation_result": operation_result,
                    "error_message": None
                }
            else:
                # Operation was cancelled
                response_text = "Operation cancelled. Is there anything else I can help you with?"
                operation_result = {"status": "cancelled", "message": "Operation cancelled by user"}
                
                # Add conversation turn
                await self.session_manager.add_conversation_turn(
                    session_id=session_id,
                    user_message="No, cancel the operation",
                    assistant_response=response_text,
                    intent=Intent.CLEAN,
                    response_type="info",
                    metadata={"confirmed": False}
                )
                
                return {
                    "response": response_text,
                    "response_type": "info",
                    "intent": "cancellation",
                    "session_id": session_id,
                    "confirmation_required": False,
                    "operation_result": operation_result,
                    "error_message": None
                }
                
        except Exception as e:
            logger.error(f"Error handling confirmation for session {session_id}: {str(e)}")
            return {
                "response": "I encountered an error while processing your confirmation. Please try again.",
                "response_type": "error",
                "intent": "error",
                "session_id": session_id,
                "confirmation_required": False,
                "operation_result": None,
                "error_message": str(e)
            }
    
    async def update_csv_excel_context(
        self,
        session_id: str,
        delimiter: Optional[str] = None,
        encoding: Optional[str] = None,
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update CSV/Excel specific context for a session.
        
        Args:
            session_id: Session identifier
            delimiter: CSV delimiter
            encoding: File encoding
            sheet_name: Excel sheet name
            
        Returns:
            Dict containing update status
        """
        try:
            success = await self.session_manager.update_csv_excel_context(
                session_id=session_id,
                delimiter=delimiter,
                encoding=encoding,
                sheet_name=sheet_name
            )
            
            if success:
                return {
                    "status": "success",
                    "message": "CSV/Excel context updated successfully",
                    "session_id": session_id,
                    "context": {
                        "delimiter": delimiter,
                        "encoding": encoding,
                        "sheet_name": sheet_name
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to update CSV/Excel context",
                    "session_id": session_id,
                    "error": "Session not found or update failed"
                }
                
        except Exception as e:
            logger.error(f"Error updating CSV/Excel context: {str(e)}")
            return {
                "status": "error",
                "message": "Error updating CSV/Excel context",
                "session_id": session_id,
                "error": str(e)
            }
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of the conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict containing session summary
        """
        try:
            summary = await self.session_manager.get_session_summary(session_id)
            if summary:
                return {
                    "status": "success",
                    "session_summary": summary
                }
            else:
                return {
                    "status": "error",
                    "message": "Session not found",
                    "session_id": session_id
                }
                
        except Exception as e:
            logger.error(f"Error getting session summary: {str(e)}")
            return {
                "status": "error",
                "message": "Error retrieving session summary",
                "session_id": session_id,
                "error": str(e)
            }
    
    async def link_artifact_to_session(
        self,
        session_id: str,
        artifact_id: str,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Link a data artifact to an existing conversation session.
        
        Args:
            session_id: Session identifier
            artifact_id: Data artifact ID
            file_path: Optional file path
            
        Returns:
            Dict containing link status
        """
        try:
            success = await self.session_manager.link_artifact_to_session(
                session_id=session_id,
                artifact_id=artifact_id,
                file_path=file_path
            )
            
            if success:
                return {
                    "status": "success",
                    "message": "Artifact linked to session successfully",
                    "session_id": session_id,
                    "artifact_id": artifact_id,
                    "file_path": file_path
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to link artifact to session",
                    "session_id": session_id,
                    "artifact_id": artifact_id,
                    "error": "Session not found or linking failed"
                }
                
        except Exception as e:
            logger.error(f"Error linking artifact to session: {str(e)}")
            return {
                "status": "error",
                "message": "Error linking artifact to session",
                "session_id": session_id,
                "artifact_id": artifact_id,
                "error": str(e)
            }
    
    def get_supported_intents(self) -> list[str]:
        """
        Get list of supported intents for the conversation system.
        
        Returns:
            List of supported intent values
        """
        return [intent.value for intent in Intent if intent != Intent.UNKNOWN]
    
    def get_conversation_capabilities(self) -> Dict[str, Any]:
        """
        Get information about conversation capabilities.
        
        Returns:
            Dict containing capability information
        """
        return {
            "supported_intents": self.get_supported_intents(),
            "supported_file_formats": ["csv", "excel"],
            "features": {
                "session_management": [
                    "Create and resume sessions",
                    "Session state persistence",
                    "Conversation history tracking",
                    "CSV/Excel context management"
                ],
                "data_exploration": [
                    "Show data samples",
                    "Describe data structure",
                    "Analyze data quality"
                ],
                "data_cleaning": [
                    "Clean data issues",
                    "Fix data problems",
                    "Remove invalid entries"
                ],
                "file_operations": [
                    "Excel sheet selection",
                    "CSV delimiter detection",
                    "Encoding detection"
                ],
                "conversation_features": [
                    "Multi-turn conversations",
                    "Context awareness",
                    "Operation confirmation",
                    "Error recovery"
                ]
            },
            "conversation_flow": [
                "Message parsing",
                "Context loading",
                "Processing routing",
                "Response generation"
            ]
        }


# Enhanced convenience functions

async def start_conversation_session(
    user_id: str,
    session_id: Optional[str] = None,
    artifact_id: Optional[str] = None,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start a new conversation session with enhanced state management.
    
    Args:
        user_id: User identifier
        session_id: Optional session ID for resuming
        artifact_id: Optional existing data artifact ID
        file_path: Optional path to data file
        
    Returns:
        Dict containing session information
    """
    conversation_graph = ConversationGraph()
    return await conversation_graph.start_conversation(
        user_id=user_id,
        session_id=session_id,
        artifact_id=artifact_id,
        file_path=file_path
    )


async def process_conversation_message(
    user_message: str,
    session_id: str,
    user_id: str,
    artifact_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Process a conversation message with session management.
    
    Args:
        user_message: The user's natural language input
        session_id: Session identifier
        user_id: User identifier
        artifact_id: Optional data artifact ID
        **kwargs: Additional context parameters
        
    Returns:
        Dict containing the conversation response
    """
    conversation_graph = ConversationGraph()
    return await conversation_graph.process_message(
        user_message=user_message,
        session_id=session_id,
        user_id=user_id,
        artifact_id=artifact_id,
        **kwargs
    ) 