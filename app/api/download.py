import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from app.api.transcribe import job_statuses

router = APIRouter()
logger = logging.getLogger(__name__)

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
    try:
        # Check if job exists
        if job_id not in job_statuses:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = job_statuses[job_id]
        
        # Check if job is complete
        if job_data["status"] != "complete":
            if job_data["status"] == "error":
                raise HTTPException(
                    status_code=500, 
                    detail=f"Transcription failed: {job_data.get('error', 'Unknown error')}"
                )
            else:
                raise HTTPException(
                    status_code=202, 
                    detail=f"Transcription is still in progress ({job_data['percent']}% complete)"
                )
        
        # Check if results exist
        if not job_data.get("results"):
            raise HTTPException(status_code=404, detail="No transcription results found")
        
        # Check if requested format is available
        if format not in job_data["results"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Format '{format}' not available. Available formats: {', '.join(job_data['results'].keys())}"
            )
        
        file_path = job_data["results"][format]
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Transcription file not found")
        
        # Determine media type based on format
        media_type = {
            "txt": "text/plain",
            "srt": "application/x-subrip",
            "vtt": "text/vtt"
        }.get(format, "text/plain")
        
        # Return file
        return FileResponse(
            path=file_path,
            filename=f"transcription.{format}",
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
