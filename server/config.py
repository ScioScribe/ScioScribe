"""
Configuration settings for ScioScribe backend.

This module handles all configuration settings including API keys,
database connections, and other environment variables.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    """
    
    # OpenAI API Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.1
    
    # FastAPI Configuration
    app_name: str = "ScioScribe API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # CORS Configuration
    cors_origins: str = "*"  # Configure for production
    
    # File Upload Configuration
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: str = ".csv,.xlsx,.xls,.png,.jpg,.jpeg,.pdf"
    
    # Temporary Storage
    temp_dir: str = "/tmp"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Make environment variable names case insensitive
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


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


async def validate_openai_config() -> bool:
    """Validate OpenAI configuration."""
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