"""
Application settings module.

This module contains the configuration settings for the application,
loaded from environment variables with default values.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings.
    
    These settings are loaded from environment variables and .env files,
    with default values when neither are set.
    """
    
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "YouTube Transcription API"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Cache settings
    CACHE_TYPE: str = "memory"  # memory or redis
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    CACHE_TTL: int = 86400  # 24 hours in seconds
    
    # Whisper settings
    WHISPER_MODEL: str = "base"  # tiny, base, small, medium, large
    OPENAI_API_KEY: Optional[str] = None
    USE_OPENAI_WHISPER: bool = True
    
    # File storage settings
    TEMP_DIR: str = "tmp"
    
    # Hardware settings
    USE_GPU: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Allow extra fields and ignore if .env file doesn't exist
        extra = "ignore"


# Create a settings instance
settings = Settings()