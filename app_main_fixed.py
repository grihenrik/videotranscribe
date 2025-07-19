"""
Production-ready entry point for the FastAPI application.
This file ensures the application runs with proper ASGI configuration.
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path

def kill_existing_servers():
    """Kill any existing gunicorn or uvicorn processes on port 5000."""
    try:
        subprocess.run(["pkill", "-f", "gunicorn"], check=False)
        subprocess.run(["pkill", "-f", "uvicorn"], check=False)
        time.sleep(1)
    except Exception:
        pass

def start_server():
    """Start the server with proper ASGI configuration."""
    # Change to the project directory
    os.chdir(Path(__file__).parent)
    
    # Kill existing servers first
    kill_existing_servers()
    
    # Configure environment
    os.environ.setdefault('HOST', '0.0.0.0')
    os.environ.setdefault('PORT', '5000')
    
    host = os.environ.get('HOST', '0.0.0.0')
    port = os.environ.get('PORT', '5000')
    
    print(f"Starting FastAPI server on {host}:{port}")
    
    # Use gunicorn with uvicorn workers for production
    cmd = [
        sys.executable, '-m', 'gunicorn',
        '--bind', f'{host}:{port}',
        '--worker-class', 'uvicorn.workers.UvicornWorker',
        '--workers', '1',
        '--timeout', '120',
        '--keep-alive', '5',
        '--reload',
        'main:app'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        # Start the server
        process = subprocess.Popen(cmd)
        
        # Handle shutdown signals
        def signal_handler(signum, frame):
            print(f"Received signal {signum}, shutting down...")
            process.terminate()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Wait for the process
        process.wait()
        
    except Exception as e:
        print(f"Error starting server: {e}")
        # Fallback to uvicorn
        print("Falling back to uvicorn...")
        fallback_cmd = [
            sys.executable, '-m', 'uvicorn',
            'main:app',
            '--host', host,
            '--port', port,
            '--reload'
        ]
        subprocess.run(fallback_cmd)

if __name__ == '__main__':
    start_server()