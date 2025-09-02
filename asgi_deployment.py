#!/usr/bin/env python3
"""
ASGI deployment solution for FastAPI application.
This script ensures proper ASGI server configuration.
"""

import os
import sys
import subprocess
import threading
import time
import signal

def cleanup_processes():
    """Clean up any existing server processes."""
    try:
        subprocess.run(["pkill", "-f", "gunicorn"], check=False, capture_output=True)
        subprocess.run(["pkill", "-f", "uvicorn"], check=False, capture_output=True)
        time.sleep(1)
    except:
        pass

def start_with_uvicorn():
    """Start the application with uvicorn ASGI server."""
    print("Starting FastAPI application with uvicorn ASGI server...")
    
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Clean up first
    cleanup_processes()
    
    # Start uvicorn server
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "5000",
        "--reload",
        "--log-level", "info"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        cleanup_processes()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the server
    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        cleanup_processes()

def start_with_gunicorn_asgi():
    """Start with gunicorn using uvicorn workers."""
    print("Starting FastAPI application with gunicorn + uvicorn workers...")
    
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Clean up first
    cleanup_processes()
    
    # Start gunicorn with uvicorn workers
    cmd = [
        sys.executable, "-m", "gunicorn",
        "--bind", "0.0.0.0:5000",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--workers", "1",
        "--timeout", "120",
        "--reload",
        "main:app"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        cleanup_processes()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the server
    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except Exception as e:
        print(f"Gunicorn failed: {e}")
        print("Falling back to uvicorn...")
        start_with_uvicorn()

if __name__ == "__main__":
    print("FastAPI ASGI Deployment Manager")
    print("=" * 40)
    
    # Try gunicorn with uvicorn workers first, fallback to uvicorn
    try:
        start_with_gunicorn_asgi()
    except Exception as e:
        print(f"Gunicorn approach failed: {e}")
        print("Using uvicorn directly...")
        start_with_uvicorn()