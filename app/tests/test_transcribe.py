import pytest
import os
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app import create_app
from app.api.transcribe import process_transcription
from app.models.request import TranscriptionRequest


# Setup test client
@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# Test URL extraction
def test_youtube_url_extraction():
    from app.services.youtube_service import YouTubeService
    
    service = YouTubeService()
    
    # Test standard YouTube URL
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert service.extract_video_id(url) == "dQw4w9WgXcQ"
    
    # Test short YouTube URL
    url = "https://youtu.be/dQw4w9WgXcQ"
    assert service.extract_video_id(url) == "dQw4w9WgXcQ"
    
    # Test YouTube URL with extra parameters
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=0s"
    assert service.extract_video_id(url) == "dQw4w9WgXcQ"
    
    # Test YouTube shorts URL
    url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    assert service.extract_video_id(url) == "dQw4w9WgXcQ"
    
    # Test invalid URL
    url = "https://example.com/video"
    assert service.extract_video_id(url) is None


# Test the /transcribe endpoint
@patch('app.services.youtube_service.YouTubeService.extract_video_id')
def test_transcribe_endpoint(mock_extract_video_id, client):
    # Mock the extract_video_id method to return a specific video ID
    mock_extract_video_id.return_value = "dQw4w9WgXcQ"
    
    # Test successful request
    response = client.post(
        "/api/transcribe",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "mode": "auto",
            "lang": "en"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"
    assert data["video_id"] == "dQw4w9WgXcQ"
    
    # Test invalid URL
    mock_extract_video_id.return_value = None
    
    response = client.post(
        "/api/transcribe",
        json={
            "url": "https://example.com/video",
            "mode": "auto",
            "lang": "en"
        }
    )
    
    assert response.status_code == 400
    
    # Test invalid mode
    response = client.post(
        "/api/transcribe",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "mode": "invalid",
            "lang": "en"
        }
    )
    
    assert response.status_code == 422  # Validation error


# Test the transcription process function
@pytest.mark.asyncio
@patch('app.services.youtube_service.YouTubeService.download_captions')
@patch('app.services.youtube_service.YouTubeService.process_captions')
@patch('app.services.cache_service.get_cache_service')
async def test_process_transcription_captions(mock_get_cache_service, mock_process_captions, mock_download_captions):
    # Mock cache service
    mock_cache_service = MagicMock()
    mock_get_cache_service.return_value = mock_cache_service
    
    # Mock download_captions to return some captions
    mock_download_captions.return_value = "<xml>captions</xml>"
    
    # Mock process_captions to return transcription data
    mock_process_captions.return_value = {
        "text": "Sample transcription",
        "srt": "1\n00:00:00,000 --> 00:00:05,000\nSample transcription",
        "vtt": "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nSample transcription"
    }
    
    # Create a job ID and request
    job_id = "test-job-id"
    request = TranscriptionRequest(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        mode="captions",
        lang="en"
    )
    video_id = "dQw4w9WgXcQ"
    cache_key = f"{video_id}_captions_en"
    
    # Process transcription
    from app.api.transcribe import job_statuses
    
    # Initialize job status
    job_statuses[job_id] = {
        "status": "downloading",
        "percent": 0,
        "video_id": video_id,
        "mode": "captions",
        "lang": "en",
        "results": None,
        "error": None
    }
    
    # Call the function
    await process_transcription(job_id, request, video_id, cache_key)
    
    # Check if job status was updated correctly
    assert job_statuses[job_id]["status"] == "complete"
    assert job_statuses[job_id]["percent"] == 100
    assert job_statuses[job_id]["results"] is not None
    
    # Cleanup
    for format_key in job_statuses[job_id]["results"]:
        file_path = job_statuses[job_id]["results"][format_key]
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # Cleanup job dir
    job_dir = os.path.dirname(job_statuses[job_id]["results"]["txt"])
    if os.path.exists(job_dir):
        os.rmdir(job_dir)


# Test the job status endpoint
@patch('app.api.transcribe.job_statuses')
def test_job_status_endpoint(mock_job_statuses, client):
    # Mock job_statuses
    mock_job_statuses.get.return_value = {
        "status": "transcribing",
        "percent": 50,
        "video_id": "dQw4w9WgXcQ",
        "mode": "auto",
        "lang": "en",
        "results": None,
        "error": None
    }
    
    # Test job found
    job_id = "test-job-id"
    mock_job_statuses.__contains__.return_value = True
    mock_job_statuses.__getitem__.return_value = {
        "status": "transcribing",
        "percent": 50,
        "error": None
    }
    
    response = client.get(f"/api/job/{job_id}/status")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "transcribing"
    assert data["percent"] == 50
    
    # Test job not found
    mock_job_statuses.__contains__.return_value = False
    
    response = client.get("/api/job/nonexistent-job/status")
    
    assert response.status_code == 404
