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
    
    These settings are loaded from environment variables and provide
    default values when environment variables are not set.
    """
    
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "YouTube Transcription API"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Cache settings
    CACHE_TYPE: str = os.getenv("CACHE_TYPE", "memory")  # memory or redis
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "86400"))  # 24 hours in seconds
    
    # Whisper settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    USE_OPENAI_WHISPER: bool = os.getenv("USE_OPENAI_WHISPER", "true").lower() == "true"
    
    # File storage settings
    TEMP_DIR: str = os.getenv("TEMP_DIR", "tmp")
    
    # Hardware settings
    USE_GPU: bool = os.getenv("USE_GPU", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create a settings instance
settings = Settings()