"""
LLM configuration and initialization for planning agents.

This module provides utilities for creating and configuring OpenAI LLM instances
with proper settings for different agent types and use cases.
"""

import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
except ImportError:
    raise ImportError(
        "Required LangChain packages not installed. Install with: "
        "pip install langchain-openai langchain-core"
    )

from config import get_settings, setup_environment_variables, get_openai_config, validate_required_settings
from .debug import StateDebugger, performance_monitor


logger = logging.getLogger(__name__)


class LLMConfigError(Exception):
    """Custom exception for LLM configuration errors."""
    pass


class LLMManager:
    """
    Manages LLM instances and configurations for planning agents.
    
    This class provides a centralized way to create and configure OpenAI LLM
    instances with appropriate settings for different agent types.
    """
    
    def __init__(self, debugger: Optional[StateDebugger] = None):
        """
        Initialize the LLM manager.
        
        Args:
            debugger: Optional StateDebugger instance for logging
        """
        self.debugger = debugger
        self.settings = get_settings()
        self.logger = logging.getLogger(f"planning.llm_manager")
        
        # Validate configuration
        missing_settings = validate_required_settings()
        if missing_settings:
            raise LLMConfigError(f"Missing required settings: {', '.join(missing_settings)}")
        
        # Set up environment variables
        setup_environment_variables()
        
        self.logger.info("LLM manager initialized successfully")
    
    @lru_cache(maxsize=10)
    def create_llm(
        self,
        agent_type: str = "default",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None
    ) -> ChatOpenAI:
        """
        Create a configured OpenAI LLM instance.
        
        Args:
            agent_type: Type of agent (affects configuration)
            temperature: Override default temperature
            max_tokens: Override default max tokens
            timeout: Override default timeout
            max_retries: Override default max retries
            
        Returns:
            Configured ChatOpenAI instance
            
        Raises:
            LLMConfigError: If configuration is invalid
        """
        try:
            config = get_openai_config()
            
            # Apply overrides
            if temperature is not None:
                config["temperature"] = temperature
            if max_tokens is not None:
                config["max_tokens"] = max_tokens
            if timeout is not None:
                config["timeout"] = timeout
            if max_retries is not None:
                config["max_retries"] = max_retries
            
            # Agent-specific configurations
            agent_config = self._get_agent_specific_config(agent_type)
            config.update(agent_config)
            
            # Create LLM instance
            llm = ChatOpenAI(**config)
            
            self.logger.info(f"Created LLM instance for {agent_type} agent")
            return llm
            
        except Exception as e:
            error_msg = f"Failed to create LLM instance for {agent_type}: {str(e)}"
            self.logger.error(error_msg)
            raise LLMConfigError(error_msg) from e
    
    def _get_agent_specific_config(self, agent_type: str) -> Dict[str, Any]:
        """
        Get agent-specific configuration overrides.
        
        Args:
            agent_type: Type of agent
            
        Returns:
            Configuration overrides for the agent type
        """
        agent_configs = {
            "objective": {
                "temperature": 0.7,
                "max_tokens": 1500,
                "model": self.settings.openai_model
            },
            "variable": {
                "temperature": 0.6,
                "max_tokens": 1800,
                "model": self.settings.openai_model
            },
            "design": {
                "temperature": 0.5,
                "max_tokens": 2000,
                "model": self.settings.openai_model
            },
            "methodology": {
                "temperature": 0.4,
                "max_tokens": 2500,
                "model": self.settings.openai_model
            },
            "data": {
                "temperature": 0.5,
                "max_tokens": 2000,
                "model": self.settings.openai_model
            },
            "review": {
                "temperature": 0.6,
                "max_tokens": 1800,
                "model": self.settings.openai_model
            },
            "default": {
                "temperature": self.settings.openai_temperature,
                "max_tokens": self.settings.openai_max_tokens,
                "model": self.settings.openai_model
            }
        }
        
        return agent_configs.get(agent_type, agent_configs["default"])
    
    def create_prompt_template(
        self,
        agent_type: str,
        system_prompt: str,
        include_history: bool = True,
        include_state: bool = True
    ) -> ChatPromptTemplate:
        """
        Create a standardized prompt template for agents.
        
        Args:
            agent_type: Type of agent
            system_prompt: System message content
            include_history: Whether to include chat history
            include_state: Whether to include state information
            
        Returns:
            Configured ChatPromptTemplate
        """
        messages = [
            SystemMessage(content=system_prompt)
        ]
        
        if include_history:
            messages.append(MessagesPlaceholder(variable_name="chat_history"))
        
        if include_state:
            messages.append(MessagesPlaceholder(variable_name="state_info"))
        
        messages.append(HumanMessage(content="{user_input}"))
        
        return ChatPromptTemplate.from_messages(messages)
    
    @performance_monitor
    def invoke_llm(
        self,
        llm: ChatOpenAI,
        messages: List[BaseMessage],
        agent_type: str = "unknown"
    ) -> str:
        """
        Invoke LLM with performance monitoring and error handling.
        
        Args:
            llm: LLM instance to invoke
            messages: List of messages to send
            agent_type: Type of agent for logging
            
        Returns:
            LLM response content
            
        Raises:
            LLMConfigError: If invocation fails
        """
        try:
            self.logger.debug(f"Invoking LLM for {agent_type} agent")
            
            # Log to debugger if available
            if self.debugger:
                self.debugger.log_agent_interaction(
                    agent_type,
                    "llm_invoke",
                    {"message_count": len(messages)},
                    {}
                )
            
            response = llm.invoke(messages)
            
            self.logger.debug(f"LLM response received for {agent_type} agent")
            return response.content
            
        except Exception as e:
            error_msg = f"LLM invocation failed for {agent_type}: {str(e)}"
            self.logger.error(error_msg)
            raise LLMConfigError(error_msg) from e
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model": self.settings.openai_model,
            "temperature": self.settings.openai_temperature,
            "max_tokens": self.settings.openai_max_tokens,
            "timeout": self.settings.openai_timeout,
            "max_retries": self.settings.openai_max_retries,
            "provider": "OpenAI"
        }


# Global LLM manager instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager(debugger: Optional[StateDebugger] = None) -> LLMManager:
    """
    Get the global LLM manager instance.
    
    Args:
        debugger: Optional StateDebugger instance
        
    Returns:
        LLMManager instance
    """
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager(debugger=debugger)
    return _llm_manager


def create_agent_llm(
    agent_type: str,
    debugger: Optional[StateDebugger] = None,
    **kwargs
) -> ChatOpenAI:
    """
    Convenience function to create an LLM instance for a specific agent type.
    
    Args:
        agent_type: Type of agent
        debugger: Optional StateDebugger instance
        **kwargs: Additional configuration overrides
        
    Returns:
        Configured ChatOpenAI instance
    """
    manager = get_llm_manager(debugger)
    return manager.create_llm(agent_type=agent_type, **kwargs)


def create_standard_prompt(
    agent_type: str,
    system_prompt: str,
    debugger: Optional[StateDebugger] = None,
    **kwargs
) -> ChatPromptTemplate:
    """
    Convenience function to create a standardized prompt template.
    
    Args:
        agent_type: Type of agent
        system_prompt: System message content
        debugger: Optional StateDebugger instance
        **kwargs: Additional template options
        
    Returns:
        Configured ChatPromptTemplate
    """
    manager = get_llm_manager(debugger)
    return manager.create_prompt_template(agent_type, system_prompt, **kwargs)


def test_llm_connection() -> Dict[str, Any]:
    """
    Test the LLM connection and configuration.
    
    Returns:
        Dictionary with test results
    """
    try:
        manager = get_llm_manager()
        llm = manager.create_llm("test")
        
        # Test with a simple message
        test_message = HumanMessage(content="Hello, this is a test message.")
        response = manager.invoke_llm(llm, [test_message], "test")
        
        return {
            "success": True,
            "model_info": manager.get_model_info(),
            "response_length": len(response),
            "message": "LLM connection test successful"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "LLM connection test failed"
        }


def get_llm_usage_stats() -> Dict[str, Any]:
    """
    Get LLM usage statistics (placeholder for future implementation).
    
    Returns:
        Dictionary with usage statistics
    """
    return {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "average_response_time": 0.0,
        "total_tokens_used": 0,
        "message": "Usage statistics not yet implemented"
    } 