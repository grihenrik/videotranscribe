"""
Download API routes.

This module handles the routes for downloading transcription files.
"""
from fastapi import APIRouter, Query, HTTPException 
from fastapi.responses import FileResponse
from typing import Optional
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Import job_statuses from the transcribe module
from app.api.transcribe import job_statuses

@router.get("/download/{job_id}")
async def download_transcription(job_id: str, format: Optional[str] = Query("txt")):
    """
    Download a transcription file.
    
    Args:
        job_id: Unique job identifier
        format: File format (txt, srt, vtt)
        
    Returns:
        File response with the requested transcription file
    """
    # Check if job exists and is complete
    if job_id not in job_statuses:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_status = job_statuses[job_id]
    if job_status["status"] != "complete":
        raise HTTPException(status_code=400, detail="Transcription not complete")
    
    # Check if files are available
    if "files" not in job_status:
        raise HTTPException(status_code=404, detail="Transcription files not found")
    
    # Validate format
    if format not in ["txt", "srt", "vtt"]:
        raise HTTPException(status_code=400, detail="Invalid format. Supported formats: txt, srt, vtt")
    
    # Get file path
    file_path = job_status["files"].get(format)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Transcription file in {format} format not found")
    
    # Get video ID
    video_id = job_status.get("video_id", "video")
    
    # Return file
    return FileResponse(
        path=file_path,
        filename=f"{video_id}.{format}",
        media_type="text/plain"
    )