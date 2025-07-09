"""
Configuration settings for ScioScribe backend.

This module handles all configuration settings including API keys,
database connections, and other environment variables for the AI research co-pilot.
"""

import os
import logging
from typing import Optional, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    """
    
    # OpenAI API Configuration
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for LLM interactions"
    )
    openai_model: str = Field(
        default="gpt-4.1",
        description="OpenAI model to use for agent interactions"
    )
    openai_max_tokens: int = Field(
        default=2000,
        description="Maximum tokens for OpenAI responses"
    )
    openai_temperature: float = Field(
        default=0.7,
        description="Temperature setting for OpenAI responses (0.0-2.0)"
    )
    openai_timeout: int = Field(
        default=60,
        description="Timeout for OpenAI API calls (seconds)"
    )
    openai_max_retries: int = Field(
        default=3,
        description="Maximum retries for OpenAI API calls"
    )
    
    # Tavily API Configuration
    tavily_api_key: Optional[str] = Field(
        default=None,
        description="Tavily API key for web search functionality"
    )
    
    # FastAPI Configuration
    app_name: str = Field(
        default="ScioScribe API",
        description="Application name"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
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
    
    # CORS Configuration
    cors_origins: str = Field(
        default="*",
        description="CORS origins (configure for production)"
    )
    
    # File Upload Configuration
    max_file_size: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        description="Maximum file size for uploads"
    )
    allowed_file_types: str = Field(
        default=".csv,.xlsx,.xls,.png,.jpg,.jpeg,.pdf",
        description="Allowed file types for upload"
    )
    
    # Temporary Storage
    temp_dir: str = Field(
        default="/tmp",
        description="Temporary directory for file processing"
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
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # LangSmith Configuration (optional)
    langsmith_api_key: Optional[str] = Field(
        default=None,
        description="LangSmith API key for tracing"
    )
    langsmith_project: Optional[str] = Field(
        default="scio-scribe",
        description="LangSmith project name"
    )
    
    @field_validator('openai_temperature')
    def validate_temperature(cls, v):
        """Validate OpenAI temperature is within valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError('OpenAI temperature must be between 0.0 and 2.0')
        return v
    
    @field_validator('openai_max_tokens')
    def validate_max_tokens(cls, v):
        """Validate max tokens is positive."""
        if v <= 0:
            raise ValueError('Max tokens must be positive')
        return v
    
    @field_validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def validate_required_settings() -> list[str]:
    """
    Validate that required settings are configured.
    
    Returns:
        List of missing required settings
    """
    missing = []
    settings = get_settings()
    
    # Check for OpenAI API key
    if not settings.openai_api_key:
        missing.append("OpenAI API key (OPENAI_API_KEY environment variable)")
    
    return missing


def setup_environment_variables() -> None:
    """Set up environment variables for LangChain/LangGraph."""
    settings = get_settings()
    
    # Set OpenAI API key if available
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    
    # Set Tavily API key if available
    if settings.tavily_api_key:
        os.environ["TAVILY_API_KEY"] = settings.tavily_api_key
    
    # Set LangSmith tracing if configured
    if settings.langsmith_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        if settings.langsmith_project:
            os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    
    # Set debug mode
    if settings.debug:
        os.environ["LANGCHAIN_VERBOSE"] = "true"
        os.environ["LANGCHAIN_DEBUG"] = "true"


def get_openai_config() -> Dict[str, Any]:
    """
    Get OpenAI configuration dictionary for LangChain initialization.
    
    Returns:
        Dictionary with OpenAI configuration parameters
    """
    settings = get_settings()
    return {
        "model": settings.openai_model,
        "temperature": settings.openai_temperature,
        "max_tokens": settings.openai_max_tokens,
        "timeout": settings.openai_timeout,
        "max_retries": settings.openai_max_retries,
        "api_key": settings.openai_api_key
    }


def get_openai_client():
    """Get OpenAI client if configured."""
    settings = get_settings()
    if not settings.openai_api_key:
        print("OpenAI API key not configured.")
        return None
    
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        return client
    except Exception as e:
        print(f"Failed to initialize OpenAI client: {e}")
        return None


def validate_openai_config() -> bool:
    """Validate OpenAI configuration synchronously."""
    settings = get_settings()
    
    # Basic validation - check if API key is present
    if not settings.openai_api_key:
        return False
    
    # Check if API key format is reasonable (starts with 'sk-')
    if not settings.openai_api_key.startswith('sk-'):
        return False
    
    return True


async def validate_openai_config_async() -> bool:
    """Validate OpenAI configuration asynchronously with API call."""
    client = get_openai_client()
    if not client:
        return False
    
    try:
        # Test with a simple API call
        response = await client.models.list()
        return True
    except Exception as e:
        print(f"OpenAI configuration validation failed: {e}")
        return False


def initialize_logging() -> None:
    """Initialize logging configuration based on settings."""
    settings = get_settings()
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scio_scribe.log') if not settings.debug else logging.NullHandler()
        ]
    )
    
    # Set specific loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    if settings.debug:
        logging.getLogger('langgraph').setLevel(logging.DEBUG)
        logging.getLogger('langchain').setLevel(logging.DEBUG)
    else:
        logging.getLogger('langgraph').setLevel(logging.INFO)
        logging.getLogger('langchain').setLevel(logging.INFO)


def create_llm_instance():
    """
    Create and configure an OpenAI LLM instance for use in agents.
    
    Returns:
        Configured OpenAI LLM instance
        
    Raises:
        ValueError: If OpenAI API key is not configured
    """
    settings = get_settings()
    
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError("langchain-openai package not installed. Install with: pip install langchain-openai")
    
    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
    
    # Ensure environment variables are set
    setup_environment_variables()
    
    # Create LLM instance with configuration
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        timeout=settings.openai_timeout,
        max_retries=settings.openai_max_retries,
        api_key=settings.openai_api_key
    )
    
    return llm


def get_system_info() -> Dict[str, Any]:
    """
    Get system configuration information for debugging.
    
    Returns:
        Dictionary with system configuration details
    """
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "openai_model": settings.openai_model,
        "openai_temperature": settings.openai_temperature,
        "openai_max_tokens": settings.openai_max_tokens,
        "debug": settings.debug,
        "log_level": settings.log_level,
        "api_host": settings.api_host,
        "api_port": settings.api_port,
        "use_firestore": settings.use_firestore,
        "max_execution_time": settings.max_execution_time,
        "max_iterations": settings.max_iterations,
        "max_file_size": settings.max_file_size,
        "allowed_file_types": settings.allowed_file_types,
        "has_openai_key": bool(settings.openai_api_key),
        "has_tavily_key": bool(settings.tavily_api_key),
        "has_langsmith_key": bool(settings.langsmith_api_key)
    }
