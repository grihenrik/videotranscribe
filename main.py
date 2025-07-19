"""
Main entry point for the FastAPI application.
This module provides the 'app' object that deployment tools expect.
"""
import os
import sys
import uvicorn
from app import create_app

# Create the FastAPI application instance for deployment
app = create_app()

def run_with_uvicorn():
    """Run the application with uvicorn directly."""
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)

def run_with_gunicorn():
    """Run the application with gunicorn using uvicorn workers."""
    import subprocess
    cmd = [
        sys.executable, "-m", "gunicorn",
        "--bind", "0.0.0.0:5000",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--workers", "1",
        "--reload",
        "main:app"
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
    # For direct execution, try gunicorn with uvicorn workers first
    try:
        run_with_gunicorn()
    except Exception as e:
        print(f"Gunicorn failed, falling back to uvicorn: {e}")
        run_with_uvicorn()