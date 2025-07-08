"""
Configuration settings for ScioScribe backend.

This module handles all configuration settings including API keys,
database connections, and other environment variables.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
import firebase_admin
from firebase_admin import credentials, firestore, storage


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
    
    # Firebase Configuration
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
    """Get cached settings instance."""
    return Settings()


def get_openai_client():
    """Get OpenAI client if configured."""
    settings = get_settings()
    if not settings.openai_api_key:
        print("⚠️  OpenAI API key not configured. AI features will be disabled.")
        return None
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        return client
    except Exception as e:
        print(f"⚠️  Failed to initialize OpenAI client: {e}")
        return None


def validate_openai_config() -> bool:
    """Validate OpenAI configuration."""
    client = get_openai_client()
    if not client:
        return False
    
    try:
        # Test with a simple API call
        response = client.models.list()
        return True
    except Exception as e:
        print(f"OpenAI configuration validation failed: {e}")
        return False


# Global Firebase instances
_firebase_app = None
_firestore_client = None
_storage_client = None


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    
    Returns:
        Tuple of (firestore_client, storage_client) or (None, None) if not configured
    """
    global _firebase_app, _firestore_client, _storage_client
    
    if _firebase_app is not None:
        return _firestore_client, _storage_client
    
    settings = get_settings()
    
    # Check if Firebase is configured
    if not settings.firebase_credentials_path or not settings.firebase_project_id:
        print("⚠️  Firebase not configured. Using in-memory storage.")
        return None, None
    
    # Check if credentials file exists
    if not os.path.exists(settings.firebase_credentials_path):
        print(f"⚠️  Firebase credentials file not found: {settings.firebase_credentials_path}")
        return None, None
    
    try:
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(settings.firebase_credentials_path)
        _firebase_app = firebase_admin.initialize_app(cred, {
            'projectId': settings.firebase_project_id,
            'storageBucket': settings.firebase_storage_bucket or f"{settings.firebase_project_id}.appspot.com"
        })
        
        # Initialize Firestore client
        _firestore_client = firestore.client()
        
        # Initialize Storage client
        _storage_client = storage.bucket()
        
        print("✅ Firebase initialized successfully")
        return _firestore_client, _storage_client
        
    except Exception as e:
        print(f"❌ Failed to initialize Firebase: {e}")
        return None, None


def get_firestore_client():
    """Get Firestore client instance."""
    client, _ = initialize_firebase()
    return client


def get_storage_client():
    """Get Firebase Storage client instance."""
    _, client = initialize_firebase()
    return client


def validate_firebase_config() -> bool:
    """Validate Firebase configuration."""
    try:
        firestore_client, storage_client = initialize_firebase()
        if not firestore_client or not storage_client:
            return False
        
        # Test Firestore connection
        firestore_client.collection('test').limit(1).get()
        print("✅ Firebase configuration validated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Firebase configuration validation failed: {e}")
        return False 