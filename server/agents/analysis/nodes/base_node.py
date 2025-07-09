"""
Base Node Class for Analysis Agent

This module provides the base class that all analysis nodes inherit from,
ensuring consistent interface and common functionality.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


class BaseNode(ABC):
    """
    Base class for all analysis nodes
    
    Provides common functionality and enforces consistent interface
    for all nodes in the analysis pipeline.
    """
    
    def __init__(self, llm: Optional[Any] = None, role_context: Optional[Dict[str, Any]] = None):
        """
        Initialize the base node
        
        Args:
            llm: Language model instance for LLM operations
            role_context: Optional role context for specialized agent behavior
        """
        self.llm = llm
        self.role_context = role_context or {}
        self.node_name = self.__class__.__name__
        
    @abstractmethod
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the state and return updates
        
        Args:
            state: Current analysis state
            
        Returns:
            Dictionary containing state updates
        """
        pass
    
    def log_info(self, message: str):
        """Log info message with node name prefix"""
        logger.info(f"{self.node_name}: {message}")
    
    def log_error(self, message: str):
        """Log error message with node name prefix"""
        logger.error(f"{self.node_name}: {message}")
    
    def log_warning(self, message: str):
        """Log warning message with node name prefix"""
        logger.warning(f"{self.node_name}: {message}")
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle errors consistently across nodes
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
            
        Returns:
            Dictionary with error information
        """
        error_msg = f"{self.node_name} Error"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"
        
        self.log_error(error_msg)
        
        return {
            "error_message": error_msg
        } 