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
    
    # Firebase Configuration (for later use)
    firebase_credentials_path: Optional[str] = None
    firebase_project_id: Optional[str] = None
    firebase_storage_bucket: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Make environment variable names case insensitive
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Returns:
        Settings instance
    """
    return Settings()


def validate_openai_config() -> bool:
    """
    Validate OpenAI configuration.
    
    Returns:
        True if OpenAI is properly configured
    """
    settings = get_settings()
    
    if not settings.openai_api_key:
        print("⚠️  Warning: OPENAI_API_KEY not set. AI features will be disabled.")
        return False
    
    if not settings.openai_api_key.startswith('sk-'):
        print("⚠️  Warning: OPENAI_API_KEY appears to be invalid.")
        return False
    
    return True


def get_openai_client():
    """
    Get OpenAI client instance.
    
    Returns:
        AsyncOpenAI client or None if not configured
    """
    settings = get_settings()
    
    if not validate_openai_config():
        return None
    
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
        )
        
        return client
        
    except ImportError:
        print("⚠️  Warning: OpenAI package not installed. Install with: pip install openai")
        return None
    except Exception as e:
        print(f"⚠️  Warning: Error creating OpenAI client: {str(e)}")
        return None 