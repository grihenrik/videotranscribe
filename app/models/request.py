"""
Request models for the API.
"""
from enum import Enum
from pydantic import BaseModel, Field, validator
import re

class TranscriptionMode(str, Enum):
    """Transcription mode enumeration."""
    AUTO = "auto"
    CAPTIONS = "captions"
    WHISPER = "whisper"

class TranscriptionRequest(BaseModel):
    """
    Request model for transcription.
    
    Attributes:
        url: YouTube URL to transcribe
        mode: Transcription mode (auto, captions, whisper)
        lang: ISO639-1 language code
    """
    url: str = Field(..., description="YouTube URL to transcribe")
    mode: TranscriptionMode = Field(default=TranscriptionMode.AUTO, description="Transcription mode")
    lang: str = Field(default="en", description="ISO639-1 language code")
    
    @validator('url')
    def validate_url(cls, v):
        """Validate YouTube URL."""
        if not v or not isinstance(v, str):
            raise ValueError("URL must be a non-empty string")
        
        # Check if it's a valid YouTube URL
        youtube_pattern = r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]{11}.*$'
        if not re.match(youtube_pattern, v):
            raise ValueError("Invalid YouTube URL")
        
        return v
    
    @validator('lang')
    def validate_lang(cls, v):
        """Validate language code."""
        if not v or not isinstance(v, str) or len(v) < 2:
            raise ValueError("Language code must be a non-empty string with at least 2 characters")
        
        # Simple check for ISO639-1 format
        if not re.match(r'^[a-z]{2,3}(-[A-Z]{2})?$', v):
            raise ValueError("Invalid language code format (expected ISO639-1)")
        
        return v