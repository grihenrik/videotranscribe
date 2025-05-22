"""
Transcription API routes.

This module handles the routes for transcribing YouTube videos.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import Dict, Any
import uuid
import os
import tempfile
import logging

from app.models.request import TranscriptionRequest
from app.models.response import TranscriptionResponse
from app.services.cache_service import CacheService, get_cache_service
from app.services import whisper_service
from app.api.progress_ws import broadcast_status_update

router = APIRouter()
logger = logging.getLogger(__name__)

# Dictionary to store job statuses in memory (in production, use a database)
job_statuses = {}

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(
    request: TranscriptionRequest,
    background_tasks: BackgroundTasks,
    cache_service: CacheService = Depends(get_cache_service),
):
    """
    Transcribe a YouTube video.
    
    - **url**: YouTube URL to transcribe
    - **mode**: Transcription mode (auto, captions, whisper)
    - **lang**: ISO639-1 language code (default: en)
    """
    # Extract video ID from URL
    video_id = request.url.split("v=")[-1].split("&")[0] if "v=" in request.url else request.url.split("youtu.be/")[-1].split("?")[0]
    
    # Create a cache key based on the video ID, mode, and language
    cache_key = f"transcription:{video_id}:{request.mode}:{request.lang}"
    
    # Check if result is cached
    cached_result = await cache_service.get(cache_key)
    if cached_result:
        logger.info(f"Cache hit for video {video_id}")
        # Create a job ID for the cached result
        job_id = str(uuid.uuid4())
        
        # Store job status as complete
        job_statuses[job_id] = {
            "status": "complete",
            "percent": 100,
            "video_id": video_id
        }
        
        # Return response with download links
        return TranscriptionResponse(
            job_id=job_id,
            status="complete",
            video_id=video_id,
            message="Transcription retrieved from cache",
            download_links={
                "txt": f"/api/download/{job_id}?format=txt",
                "srt": f"/api/download/{job_id}?format=srt",
                "vtt": f"/api/download/{job_id}?format=vtt"
            }
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Store initial job status
    job_statuses[job_id] = {
        "status": "queued",
        "percent": 0,
        "video_id": video_id
    }
    
    # Process the transcription in the background
    background_tasks.add_task(
        process_transcription,
        job_id,
        request,
        video_id,
        cache_key
    )
    
    # Return response with job ID
    return TranscriptionResponse(
        job_id=job_id,
        status="queued",
        video_id=video_id,
        message="Transcription job started",
        download_links={
            "txt": f"/api/download/{job_id}?format=txt",
            "srt": f"/api/download/{job_id}?format=srt",
            "vtt": f"/api/download/{job_id}?format=vtt"
        }
    )

@router.get("/job/{job_id}/status", response_model=Dict[str, Any])
async def get_job_status(job_id: str):
    """Get the status of a transcription job."""
    if job_id not in job_statuses:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_statuses[job_id]

async def process_transcription(
    job_id: str,
    request: TranscriptionRequest,
    video_id: str,
    cache_key: str
):
    """
    Process the transcription request in the background.
    
    Args:
        job_id: Unique job identifier
        request: Transcription request parameters
        video_id: YouTube video ID
        cache_key: Key for caching the result
    """
    try:
        # Update status to downloading
        job_statuses[job_id]["status"] = "downloading"
        job_statuses[job_id]["percent"] = 10
        await broadcast_status_update(job_id, job_statuses[job_id])
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download audio
            audio_path = whisper_service.download_audio_from_youtube(request.url, temp_dir)
            if not audio_path:
                raise Exception("Failed to download audio")
            
            # Update status to transcribing
            job_statuses[job_id]["status"] = "transcribing"
            job_statuses[job_id]["percent"] = 50
            await broadcast_status_update(job_id, job_statuses[job_id])
            
            # Transcribe audio
            transcription = whisper_service.transcribe_audio_file(audio_path, request.lang)
            if not transcription:
                raise Exception("Failed to transcribe audio")
            
            # Save transcription files
            files = await save_transcription_files(job_id, transcription)
            
            # Update status to complete
            job_statuses[job_id]["status"] = "complete"
            job_statuses[job_id]["percent"] = 100
            job_statuses[job_id]["files"] = files
            await broadcast_status_update(job_id, job_statuses[job_id])
            
            # Cache the result
            # Note: In a production environment, you'd want to cache the actual files,
            # not just the paths
            await get_cache_service().set(cache_key, {
                "files": files,
                "transcription": transcription
            })
            
    except Exception as e:
        logger.error(f"Error processing transcription: {e}")
        # Update status to error
        job_statuses[job_id]["status"] = "error"
        job_statuses[job_id]["error"] = str(e)
        job_statuses[job_id]["percent"] = 0
        await broadcast_status_update(job_id, job_statuses[job_id])

async def save_transcription_files(job_id: str, transcription):
    """
    Save transcription to temporary files in different formats.
    
    Args:
        job_id: Unique job identifier
        transcription: Transcription data with text, srt, and vtt formats
        
    Returns:
        Dictionary with file paths for different formats
    """
    # Create directory for files
    os.makedirs("tmp", exist_ok=True)
    job_dir = os.path.join("tmp", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save files in different formats
    files = {}
    
    # Plain text
    txt_path = os.path.join(job_dir, "transcription.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(transcription["text"])
    files["txt"] = txt_path
    
    # SRT format
    srt_path = os.path.join(job_dir, "transcription.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(transcription["srt"])
    files["srt"] = srt_path
    
    # VTT format
    vtt_path = os.path.join(job_dir, "transcription.vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(transcription["vtt"])
    files["vtt"] = vtt_path
    
    return files