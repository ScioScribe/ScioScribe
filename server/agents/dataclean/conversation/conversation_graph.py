"""
Main conversation graph for data cleaning operations.

This module provides the primary conversation interface that delegates to
the enhanced conversation graph with advanced features.
"""

import logging
from typing import Dict, Any, Optional

from .conversation_graph_enhanced import get_enhanced_conversation_graph

logger = logging.getLogger(__name__)


class ConversationGraph:
    """
    Main conversation graph that delegates to the enhanced conversation system.
    
    This provides a simplified interface to the enhanced conversation features
    including multi-turn context, proactive suggestions, error recovery,
    and simplified template recommendations.
    """
    
    def __init__(self):
        """Initialize the conversation graph."""
        self.enhanced_graph = get_enhanced_conversation_graph()
        logger.info("Conversation graph initialized with enhanced features")
    
    async def start_conversation(
        self, 
        user_id: str, 
        session_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new conversation session.
        
        Args:
            user_id: User identifier
            session_id: Optional session ID for resuming
            artifact_id: Optional data artifact ID
            file_path: Optional file path for processing
            
        Returns:
            Session information and welcome message
        """
        return await self.enhanced_graph.start_conversation(
            user_id=user_id,
            session_id=session_id,
            artifact_id=artifact_id,
            file_path=file_path
        )
    
    async def process_message(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        artifact_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user message through the conversation system.
        
        Args:
            user_message: User's natural language input
            session_id: Session identifier
            user_id: User identifier
            artifact_id: Optional data artifact ID
            
        Returns:
            Conversation response with enhanced features
        """
        return await self.enhanced_graph.process_message(
            user_message=user_message,
            session_id=session_id,
            user_id=user_id,
            artifact_id=artifact_id
        )
    
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
        return await self.enhanced_graph.handle_confirmation(
            session_id=session_id,
            user_id=user_id,
            confirmed=confirmed
        )
    
    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of the conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary information
        """
        return await self.enhanced_graph.get_session_summary(session_id)
    
    def get_conversation_capabilities(self) -> Dict[str, Any]:
        """
        Get information about conversation capabilities.
        
        Returns:
            Conversation capabilities and supported intents
        """
        return self.enhanced_graph.get_conversation_capabilities()


# Global instance
_conversation_graph = None

def get_conversation_graph() -> ConversationGraph:
    """Get the global conversation graph instance."""
    global _conversation_graph
    if _conversation_graph is None:
        _conversation_graph = ConversationGraph()
    return _conversation_graph 