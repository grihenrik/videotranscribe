import asyncio
import logging
import os
import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models.request import TranscriptionRequest
from app.models.response import TranscriptionResponse, JobStatus
from app.services.youtube_service import YouTubeService
from app.services.whisper_service import WhisperService
from app.services.cache_service import get_cache_service, CacheService

router = APIRouter()
logger = logging.getLogger(__name__)

# Dictionary to store job status information
# In a production environment, this should be stored in a persistent database
job_statuses: Dict[str, Dict[str, Any]] = {}


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
    try:
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Check if result is already in cache
        youtube_service = YouTubeService()
        video_id = youtube_service.extract_video_id(request.url)
        
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        cache_key = f"{video_id}_{request.mode}_{request.lang}"
        cached_result = await cache_service.get(cache_key)
        
        if cached_result:
            logger.info(f"Found cached transcription for video {video_id}")
            return TranscriptionResponse(
                job_id=job_id,
                status="complete",
                video_id=video_id,
                message="Transcription found in cache",
                download_links={
                    "txt": f"/api/download/{job_id}?format=txt",
                    "srt": f"/api/download/{job_id}?format=srt",
                    "vtt": f"/api/download/{job_id}?format=vtt",
                }
            )
        
        # Initialize job status
        job_statuses[job_id] = {
            "status": "downloading",
            "percent": 0,
            "video_id": video_id,
            "mode": request.mode,
            "lang": request.lang,
            "results": None,
            "error": None
        }
        
        # Start background task for transcription
        background_tasks.add_task(
            process_transcription,
            job_id,
            request,
            video_id,
            cache_key
        )
        
        return TranscriptionResponse(
            job_id=job_id,
            status="processing",
            video_id=video_id,
            message="Transcription started",
            download_links={
                "txt": f"/api/download/{job_id}?format=txt",
                "srt": f"/api/download/{job_id}?format=srt",
                "vtt": f"/api/download/{job_id}?format=vtt",
            }
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in transcribe_video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a transcription job."""
    if job_id not in job_statuses:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status_data = job_statuses[job_id]
    return JobStatus(
        status=status_data["status"],
        percent=status_data["percent"],
        error=status_data.get("error")
    )


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
        youtube_service = YouTubeService()
        whisper_service = WhisperService()
        cache_service = get_cache_service()
        
        # Update job status
        job_statuses[job_id]["status"] = "downloading"
        job_statuses[job_id]["percent"] = 10
        
        # Process based on mode
        if request.mode == "captions" or request.mode == "auto":
            try:
                # Try to get captions first
                job_statuses[job_id]["percent"] = 30
                captions = await youtube_service.download_captions(video_id, request.lang)
                
                if captions:
                    job_statuses[job_id]["status"] = "transcribing"
                    job_statuses[job_id]["percent"] = 70
                    
                    # Get transcription in different formats
                    transcription = await youtube_service.process_captions(captions)
                    
                    # Save to temporary files
                    file_paths = await save_transcription_files(job_id, transcription)
                    
                    # Update job status
                    job_statuses[job_id]["status"] = "complete"
                    job_statuses[job_id]["percent"] = 100
                    job_statuses[job_id]["results"] = file_paths
                    
                    # Cache the result
                    await cache_service.set(cache_key, file_paths)
                    return
                
                # If captions not found and mode is "captions", raise error
                if request.mode == "captions":
                    raise HTTPException(status_code=404, detail="No captions found for this video")
                
            except Exception as e:
                if request.mode == "captions":
                    logger.error(f"Error getting captions: {str(e)}")
                    job_statuses[job_id]["status"] = "error"
                    job_statuses[job_id]["error"] = f"Failed to get captions: {str(e)}"
                    return
        
        # If mode is "whisper" or captions failed in "auto" mode
        if request.mode == "whisper" or (request.mode == "auto" and not job_statuses[job_id].get("results")):
            try:
                # Download audio
                job_statuses[job_id]["status"] = "downloading"
                job_statuses[job_id]["percent"] = 40
                
                audio_path = await youtube_service.download_audio(video_id)
                
                # Process with Whisper
                job_statuses[job_id]["status"] = "transcribing"
                job_statuses[job_id]["percent"] = 60
                
                transcription = await whisper_service.transcribe_audio(audio_path, request.lang)
                
                # Save to temporary files
                file_paths = await save_transcription_files(job_id, transcription)
                
                # Update job status
                job_statuses[job_id]["status"] = "complete"
                job_statuses[job_id]["percent"] = 100
                job_statuses[job_id]["results"] = file_paths
                
                # Cache the result
                await cache_service.set(cache_key, file_paths)
                
                # Clean up audio file
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                
            except Exception as e:
                logger.error(f"Error in Whisper transcription: {str(e)}")
                job_statuses[job_id]["status"] = "error"
                job_statuses[job_id]["error"] = f"Failed to transcribe with Whisper: {str(e)}"
    
    except Exception as e:
        logger.error(f"Error in process_transcription: {str(e)}")
        job_statuses[job_id]["status"] = "error"
        job_statuses[job_id]["error"] = str(e)


async def save_transcription_files(job_id: str, transcription):
    """
    Save transcription to temporary files in different formats.
    
    Args:
        job_id: Unique job identifier
        transcription: Transcription data with text, srt, and vtt formats
        
    Returns:
        Dictionary with file paths for different formats
    """
    # Create directory for job files
    os.makedirs("tmp", exist_ok=True)
    job_dir = os.path.join("tmp", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save files in different formats
    file_paths = {}
    
    # Text format
    txt_path = os.path.join(job_dir, "transcription.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(transcription["text"])
    file_paths["txt"] = txt_path
    
    # SRT format
    srt_path = os.path.join(job_dir, "transcription.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(transcription["srt"])
    file_paths["srt"] = srt_path
    
    # VTT format
    vtt_path = os.path.join(job_dir, "transcription.vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(transcription["vtt"])
    file_paths["vtt"] = vtt_path
    
    return file_paths
