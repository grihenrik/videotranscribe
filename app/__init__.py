from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.transcribe import router as transcribe_router
from app.api.download import router as download_router
from app.api.progress_ws import router as websocket_router
from app.api.upload_legacy import router as upload_legacy_router
from app.core.logging import setup_logging

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="YouTube Transcription API",
        description="API to transcribe YouTube videos using captions or Whisper",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Setup logging
    setup_logging()

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(transcribe_router, prefix="/api", tags=["transcription"])
    app.include_router(download_router, prefix="/api", tags=["download"])
    app.include_router(websocket_router, prefix="/api", tags=["websocket"])
    # Legacy routes for static frontend (must be before static mount)
    app.include_router(upload_legacy_router, tags=["legacy"])

    # Mount static files (catch-all, must be last)
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    return app

# Create the FastAPI application instance
app = create_app()
