#!/usr/bin/env python3
"""
Direct ASGI server runner - bypasses workflow issues.
This ensures the FastAPI app runs with proper ASGI configuration.
"""

import os
import sys
import subprocess
import time
import signal
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_existing_servers():
    """Kill any existing gunicorn/uvicorn processes."""
    try:
        subprocess.run(['pkill', '-f', 'gunicorn'], check=False, capture_output=True)
        subprocess.run(['pkill', '-f', 'uvicorn'], check=False, capture_output=True)
        time.sleep(1)
        logger.info("Cleaned up existing server processes")
    except Exception as e:
        logger.warning(f"Cleanup error: {e}")

def run_uvicorn_server():
    """Run the FastAPI app with uvicorn ASGI server."""
    logger.info("Starting FastAPI application with uvicorn...")
    
    # Change to the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Cleanup first
    cleanup_existing_servers()
    
    # Build uvicorn command
    cmd = [
        sys.executable, '-m', 'uvicorn',
        'main:app',
        '--host', '0.0.0.0',
        '--port', '5000',
        '--reload',
        '--log-level', 'info'
    ]
    
    logger.info(f"Command: {' '.join(cmd)}")
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        cleanup_existing_servers()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the server
    try:
        logger.info("Starting uvicorn server...")
        process = subprocess.Popen(cmd, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT, 
                                 universal_newlines=True,
                                 bufsize=1)
        
        # Print output in real-time
        if process.stdout:
            for line in process.stdout:
                print(line.strip())
        
        process.wait()
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        cleanup_existing_servers()
    except Exception as e:
        logger.error(f"Server error: {e}")
        cleanup_existing_servers()

if __name__ == "__main__":
    print("=" * 50)
    print("FastAPI ASGI Server")
    print("=" * 50)
    run_uvicorn_server()