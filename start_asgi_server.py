#!/usr/bin/env python3
"""
ASGI server starter for FastAPI application.
This ensures the application runs with proper ASGI configuration.
"""

import os
import sys
import subprocess
import signal
import time

def start_asgi_server():
    """Start FastAPI with proper ASGI configuration."""
    
    # Kill any existing processes first
    try:
        subprocess.run(["pkill", "-f", "gunicorn"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
    except:
        pass
    
    print("Starting FastAPI application with ASGI support...")
    
    # Use gunicorn with uvicorn workers for production
    cmd = [
        sys.executable, "-m", "gunicorn",
        "--bind", "0.0.0.0:5000",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--workers", "1",
        "--timeout", "120",
        "--reload",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "main:app"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Replace current process with gunicorn
    try:
        os.execvp(cmd[0], cmd)
    except Exception as e:
        print(f"Failed to start with gunicorn: {e}")
        # Fallback to uvicorn directly
        print("Falling back to uvicorn...")
        os.execvp("uvicorn", ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"])

if __name__ == "__main__":
    start_asgi_server()