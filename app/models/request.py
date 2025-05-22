from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl, Field, validator


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
    
    @validator("url")
    def validate_url(cls, v):
        """Validate YouTube URL."""
        if not v:
            raise ValueError("URL cannot be empty")
        
        # Simple validation for YouTube URL
        if "youtube.com" not in v and "youtu.be" not in v:
            raise ValueError("URL must be a valid YouTube URL")
        
        return v
    
    @validator("lang")
    def validate_lang(cls, v):
        """Validate language code."""
        if not v:
            return "en"
        
        # Simple validation for ISO639-1 code
        if len(v) != 2:
            raise ValueError("Language code must be a 2-letter ISO639-1 code")
        
        return v
