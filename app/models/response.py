"""
Response models for the API.
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field

class JobStatus(BaseModel):
    """
    Job status model.
    
    Attributes:
        status: Job status (downloading, transcribing, complete, error)
        percent: Completion percentage
        error: Error message if status is 'error'
    """
    status: str = Field(..., description="Job status")
    percent: int = Field(..., description="Completion percentage", ge=0, le=100)
    error: Optional[str] = Field(None, description="Error message if status is 'error'")

class TranscriptionResponse(BaseModel):
    """
    Response model for transcription.
    
    Attributes:
        job_id: Unique job identifier
        status: Job status
        video_id: YouTube video ID
        message: Status message
        download_links: URLs to download transcription files
        error: Error message if status is 'error'
    """
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    video_id: str = Field(..., description="YouTube video ID")
    message: str = Field(..., description="Status message")
    download_links: Dict[str, str] = Field(
        ..., 
        description="URLs to download transcription files in different formats"
    )
    error: Optional[str] = Field(None, description="Error message if status is 'error'")

class CaptionItem(BaseModel):
    """
    Caption item model.
    
    Attributes:
        start: Start time
        end: End time
        text: Caption text
    """
    start: str = Field(..., description="Start time")
    end: str = Field(..., description="End time")
    text: str = Field(..., description="Caption text")

class Transcription(BaseModel):
    """
    Transcription model.
    
    Attributes:
        text: Plain text transcription
        srt: SRT format transcription
        vtt: VTT format transcription
    """
    text: str = Field(..., description="Plain text transcription")
    srt: str = Field(..., description="SRT format transcription")
    vtt: str = Field(..., description="VTT format transcription")