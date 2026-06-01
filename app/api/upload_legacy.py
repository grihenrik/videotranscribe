"""
Legacy API routes for compatibility with the static frontend.
These routes match the simple_server Flask API (no /api prefix).
"""
import os
import re
import time
import uuid
import tempfile
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.models.request import TranscriptionRequest
from app.services import whisper_service
from app.api.transcribe import job_statuses, process_transcription
from app.core.config import settings_helper

MAX_FILE_SIZE = settings_helper.get_max_file_size_bytes()

router = APIRouter()
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)

ALLOWED_EXTENSIONS = {
    '.mp3', '.mp4', '.wav', '.m4a', '.flac', '.aac', '.ogg',
    '.webm', '.mov', '.avi', '.mkv', '.wma', '.3gp', '.amr'
}


def _transcribe_file_task(job_id: str, file_path: str, language: str, custom_name: str, original_filename: str):
    """Background task to transcribe an uploaded file."""
    try:
        job_statuses[job_id]["status"] = "processing_file"
        job_statuses[job_id]["percent"] = 10

        save_dir = os.path.join("tmp", job_id)
        os.makedirs(save_dir, exist_ok=True)

        job_statuses[job_id]["percent"] = 30
        job_statuses[job_id]["status"] = "transcribing_file"

        transcription_result = whisper_service.transcribe_audio_file(
            file_path,
            language if language != "auto" else None
        )

        if not transcription_result:
            raise Exception("Failed to transcribe the uploaded file.")

        job_statuses[job_id]["percent"] = 80
        job_statuses[job_id]["status"] = "saving_results"

        base_name = custom_name or Path(original_filename).stem
        base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name).strip()

        txt_path = os.path.join(save_dir, f"{base_name}.txt")
        srt_path = os.path.join(save_dir, f"{base_name}.srt")
        vtt_path = os.path.join(save_dir, f"{base_name}.vtt")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(transcription_result["text"])
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(transcription_result["srt"])
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(transcription_result["vtt"])

        job_statuses[job_id]["status"] = "complete"
        job_statuses[job_id]["percent"] = 100
        job_statuses[job_id]["files"] = {"txt": txt_path, "srt": srt_path, "vtt": vtt_path}
        job_statuses[job_id]["transcription_file"] = base_name

        try:
            os.remove(file_path)
        except OSError:
            pass

        logger.info(f"Completed file transcription for job {job_id}")
    except Exception as e:
        logger.error(f"Error in file transcription job {job_id}: {e}")
        job_statuses[job_id]["status"] = "error"
        job_statuses[job_id]["error"] = str(e)
        job_statuses[job_id]["percent"] = 100
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass


@router.post("/transcribe")
async def transcribe(background_tasks: BackgroundTasks, request: TranscriptionRequest):
    """Transcribe YouTube video (legacy endpoint for static frontend)."""
    video_id = request.url.split("v=")[-1].split("&")[0] if "v=" in request.url else request.url.split("youtu.be/")[-1].split("?")[0]
    job_id = str(uuid.uuid4())

    job_statuses[job_id] = {
        "status": "queued",
        "percent": 0,
        "video_id": video_id,
    }

    cache_key = f"transcription:{video_id}:{request.mode}:{request.lang}"
    background_tasks.add_task(process_transcription, job_id, request, video_id, cache_key)

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "video_id": video_id,
        "message": "Transcription job started",
        "download_links": {
            "txt": f"/download/{job_id}?format=txt",
            "srt": f"/download/{job_id}?format=srt",
            "vtt": f"/download/{job_id}?format=vtt",
        },
    })


@router.post("/upload-transcribe")
async def upload_transcribe(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    custom_name: str = Form(""),
):
    """Upload and transcribe audio/video file (legacy endpoint for static frontend)."""
    if not file.filename or file.filename == "":
        raise HTTPException(status_code=400, detail="No file selected")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")

    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 200MB.")

    job_id = f"file_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    video_id = custom_name or os.path.splitext(file.filename)[0]

    job_statuses[job_id] = {
        "status": "uploading",
        "percent": 0,
        "video_id": video_id,
        "is_playlist": False,
        "file_upload": True,
        "original_filename": file.filename,
        "file_size": file_size,
    }

    os.makedirs("tmp", exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir="tmp")
    temp_file_path = os.path.join(temp_dir, f"upload{file_ext}")
    with open(temp_file_path, "wb") as f:
        f.write(content)

    executor.submit(
        _transcribe_file_task,
        job_id,
        temp_file_path,
        language,
        custom_name,
        file.filename,
    )

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "video_id": video_id,
        "is_playlist": False,
        "file_upload": True,
        "message": "File upload transcription job started",
        "original_filename": file.filename,
        "file_size": file_size,
        "download_links": {
            "txt": f"/download/{job_id}?format=txt",
            "srt": f"/download/{job_id}?format=srt",
            "vtt": f"/download/{job_id}?format=vtt",
        },
    })


@router.get("/job-status/{job_id}")
async def job_status(job_id: str):
    """Get job status (legacy endpoint)."""
    status = job_statuses.get(job_id, {
        "status": "error",
        "percent": 0,
        "error": "Job not found",
    })
    return JSONResponse(status)


@router.get("/download/{job_id}")
async def download(job_id: str, format: str = "txt"):
    """Download transcription file (legacy endpoint)."""
    from fastapi.responses import FileResponse

    if job_id not in job_statuses:
        raise HTTPException(status_code=404, detail="Job not found")

    job_dir = os.path.join("tmp", job_id)
    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Files not found")

    status = job_statuses[job_id]
    if status.get("status") != "complete":
        raise HTTPException(status_code=202, detail=f"Transcription not ready. Status: {status.get('status')}")

    files = [f for f in os.listdir(job_dir) if f.endswith(f".{format}")]
    if not files:
        raise HTTPException(status_code=404, detail=f"No {format} file found")

    file_path = os.path.join(job_dir, files[0])
    content_types = {"txt": "text/plain", "srt": "application/x-subrip", "vtt": "text/vtt"}
    return FileResponse(
        file_path,
        media_type=content_types.get(format, "text/plain"),
        filename=files[0],
    )
