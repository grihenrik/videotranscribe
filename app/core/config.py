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
    WHISPER_MAX_FILE_SIZE_MB: int = 25  # 25MB limit for Whisper API

    # File storage settings
    TEMP_DIR: str = "tmp"

    # File upload settings
    MAX_FILE_SIZE_MB: int = 1000  # 1GB default for file uploads

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

# Create a wrapper class with helper methods
class ConfigHelper:
    def __init__(self, settings):
        self._settings = settings

    @property
    def MAX_FILE_SIZE_MB(self):
        return self._settings.MAX_FILE_SIZE_MB

    @property
    def WHISPER_MAX_FILE_SIZE_MB(self):
        return self._settings.WHISPER_MAX_FILE_SIZE_MB

    def get_max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self._settings.MAX_FILE_SIZE_MB * 1024 * 1024

    def get_whisper_max_file_size_bytes(self) -> int:
        """Get Whisper max file size in bytes."""
        return self._settings.WHISPER_MAX_FILE_SIZE_MB * 1024 * 1024

# Create helper instance
settings_helper = ConfigHelper(settings)