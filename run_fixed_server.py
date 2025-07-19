#!/usr/bin/env python3
"""
Fixed server runner that ensures proper ASGI configuration.
This bypasses the problematic workflow configuration.
"""

import os
import sys
import subprocess
import signal
import time

def run_server():
    """Run the server with correct configuration."""
    
    # Kill any existing processes
    try:
        subprocess.run(["pkill", "-f", "gunicorn"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except:
        pass
    
    print("Starting FastAPI server with uvicorn workers...")
    
    # Use exec to replace this process
    os.execvp("gunicorn", [
        "gunicorn",
        "--bind", "0.0.0.0:5000",
        "--worker-class", "uvicorn.workers.UvicornWorker",
        "--workers", "1",
        "--timeout", "120",
        "--reload",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "main:app"
    ])

if __name__ == "__main__":
    run_server()