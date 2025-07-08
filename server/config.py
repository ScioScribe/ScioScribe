"""
Configuration management for ScioScribe Planning Agent.

This module handles environment variables, API keys, and other configuration
settings for the experiment planning agent system.
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Configuration settings for the planning agent."""
    
    # API Keys
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for LLM interactions"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key for Claude interactions"
    )
    tavily_api_key: Optional[str] = Field(
        default=None,
        description="Tavily API key for web search functionality"
    )
    
    # LLM Configuration
    default_llm_provider: str = Field(
        default="openai",
        description="Default LLM provider (openai, anthropic)"
    )
    default_model: str = Field(
        default="gpt-4o-mini",
        description="Default model to use for agent interactions"
    )
    llm_temperature: float = Field(
        default=0.7,
        description="Temperature setting for LLM responses"
    )
    max_tokens: int = Field(
        default=2000,
        description="Maximum tokens for LLM responses"
    )
    
    # LangGraph Configuration
    max_execution_time: int = Field(
        default=300,
        description="Maximum execution time for graph workflows (seconds)"
    )
    max_iterations: int = Field(
        default=50,
        description="Maximum iterations for agent loops"
    )
    
    # Database Configuration
    firestore_project_id: Optional[str] = Field(
        default=None,
        description="Firebase project ID for data persistence"
    )
    use_firestore: bool = Field(
        default=False,
        description="Enable Firestore for data persistence"
    )
    
    # Development Settings
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # API Configuration
    api_host: str = Field(
        default="localhost",
        description="API server host"
    )
    api_port: int = Field(
        default=8000,
        description="API server port"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def validate_required_settings() -> list[str]:
    """
    Validate that required settings are configured.
    
    Returns:
        List of missing required settings
    """
    missing = []
    
    # Check for at least one LLM provider
    if not settings.openai_api_key and not settings.anthropic_api_key:
        missing.append("At least one LLM API key (OpenAI or Anthropic)")
    
    # Check for specific provider key if selected
    if settings.default_llm_provider == "openai" and not settings.openai_api_key:
        missing.append("OpenAI API key (required for selected provider)")
    elif settings.default_llm_provider == "anthropic" and not settings.anthropic_api_key:
        missing.append("Anthropic API key (required for selected provider)")
    
    return missing


def setup_environment_variables():
    """Set up environment variables for LangChain/LangGraph."""
    
    # Set OpenAI API key if available
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    
    # Set Anthropic API key if available
    if settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    
    # Set Tavily API key if available
    if settings.tavily_api_key:
        os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
    
    # Set LangSmith tracing if configured
    if os.getenv("LANGCHAIN_TRACING_V2"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    
    # Set debug mode
    if settings.debug:
        os.environ["LANGCHAIN_VERBOSE"] = "true"
        os.environ["LANGCHAIN_DEBUG"] = "true" 