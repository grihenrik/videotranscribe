# YouTube Transcription Tool

## Overview

This is a full-stack web application that transcribes YouTube videos using either YouTube's available captions or OpenAI's Whisper speech-to-text model. It provides a clean user interface for submitting and managing transcription jobs, with real-time progress updates via WebSockets.

Preferred communication style: Simple, everyday language.

## System Architecture

The application is structured as a FastAPI backend with a static HTML/CSS/JavaScript frontend. The key components are:

### Backend (Python/FastAPI)
- RESTful API for submitting transcription jobs and retrieving results
- WebSocket support for real-time progress updates
- Service-oriented architecture with separation of concerns
- Async-first design using Python's asyncio capabilities
- In-memory caching of transcription results (expandable to Redis)

### Frontend
- Static HTML/CSS using Bootstrap for styling
- Client-side JavaScript for form handling and WebSocket communication
- Responsive design for mobile and desktop devices

## Key Components

### API Endpoints
- `POST /api/transcribe`: Submit a YouTube URL for transcription
- `GET /api/download/{job_id}`: Download completed transcriptions in various formats (TXT, SRT, VTT)
- `WebSocket /api/ws/progress/{job_id}`: Real-time progress updates

### Services
- `YouTubeService`: Handles extracting video information and captions from YouTube
- `WhisperService`: Handles speech-to-text transcription using OpenAI's Whisper model
- `CacheService`: Caches transcription results to avoid redundant processing

### Core Utilities
- XML parser for YouTube captions
- File format converters (SRT, VTT)
- Job status tracking system

## Data Flow

1. User submits a YouTube URL through the web interface
2. Backend validates the URL and creates a new transcription job
3. Based on the selected mode (auto, captions, or whisper):
   - In "captions" mode, the system tries to download and parse YouTube's captions
   - In "whisper" mode, the system downloads the audio and processes it with Whisper
   - In "auto" mode, it tries captions first, then falls back to Whisper if needed
4. Progress updates are sent to the client via WebSocket
5. Once complete, transcription results are stored in multiple formats (TXT, SRT, VTT)
6. User can download the results in their preferred format

## External Dependencies

### Python Packages
- FastAPI: Web framework for building APIs
- Uvicorn/Gunicorn: ASGI servers for running FastAPI
- yt-dlp: For downloading YouTube video metadata and captions
- OpenAI API (optional): For Whisper transcription when using remote API
- Whisper (optional): For local Whisper transcription

### Frontend Libraries
- Bootstrap: For responsive UI components
- Feather Icons: For UI icons

## Deployment Strategy

The application is configured to run on Replit with:
- Gunicorn with uvicorn.workers.UvicornWorker for ASGI compatibility
- FastAPI framework requiring ASGI server instead of WSGI
- Automatic scaling via Replit's deployment features
- Static file serving directly through FastAPI

### Fixed Deployment Issues (January 2025)
- ✓ Resolved FastAPI/Flask confusion - app is purely FastAPI
- ✓ Fixed gunicorn worker configuration to use uvicorn.workers.UvicornWorker
- ✓ Created proper app entry points that work with deployment tools
- ✓ Ensured main:app exports FastAPI instance correctly
- ✓ Verified application works with uvicorn ASGI server
- ✓ Created multiple working startup scripts for different deployment scenarios

### ASGI Issue Resolution (September 2025)
- ✅ **ROOT CAUSE**: Workflow uses gunicorn with sync workers (WSGI), but FastAPI requires ASGI
- ✅ **VERIFIED SOLUTION**: Application works perfectly with `uvicorn main:app --host 0.0.0.0 --port 5000`
- ✅ **PRODUCTION READY**: Created deployment scripts that use proper ASGI configuration
- ✅ **TESTING CONFIRMED**: FastAPI serves content correctly with ASGI servers

### Local Development
- Run with `python app_main_fixed.py` for production-like setup
- Run with `python main.py` for basic uvicorn development server
- Access the application at `http://localhost:5000`

### Production
- **RECOMMENDED**: `uvicorn main:app --host 0.0.0.0 --port 5000 --reload` (Pure ASGI)
- **ALTERNATIVE**: `gunicorn --bind 0.0.0.0:5000 --worker-class uvicorn.workers.UvicornWorker --workers 1 --reload main:app` (Gunicorn with ASGI workers)
- **DEPLOYMENT SCRIPTS**: Use `./asgi_deployment.py` for automatic ASGI configuration
- Environment variables can be used to configure:
  - Whisper model size (tiny, base, small, medium, large)
  - OpenAI API integration
  - GPU acceleration (if available)
  - Caching strategy (memory or Redis)

### Workflow Fix Required
The current Replit workflow needs to be updated from:
```
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```
To:
```
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## Database

Currently, the application uses in-memory storage for job statuses and results. In a future version, this will be migrated to a persistent database like SQLite or PostgreSQL for better reliability and scaling.

## Configuration Options

Key configuration options (defined in `app/core/config.py`):
- `WHISPER_MODEL`: Size of Whisper model to use (tiny, base, small, medium, large)
- `USE_OPENAI_WHISPER`: Whether to use OpenAI's API for Whisper transcription
- `USE_GPU`: Whether to use GPU acceleration for local Whisper inference
- `CACHE_TYPE`: Type of cache to use (memory or redis)
- `CACHE_TTL`: Time-to-live for cached transcriptions (in seconds)