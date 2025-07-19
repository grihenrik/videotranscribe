#!/usr/bin/env python3
"""
Server startup script that handles both development and production modes.
This script ensures the FastAPI application runs with the correct ASGI server.
"""

import os
import sys
import subprocess

def main():
    """Main entry point for starting the server."""
    
    # Set environment variables
    os.environ.setdefault('HOST', '0.0.0.0')
    os.environ.setdefault('PORT', '5000')
    
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting FastAPI server on {host}:{port}")
    
    # Use gunicorn with uvicorn workers for production-like setup
    cmd = [
        sys.executable, '-m', 'gunicorn',
        '--bind', f'{host}:{port}',
        '--worker-class', 'uvicorn.workers.UvicornWorker',
        '--workers', '1',
        '--reload',
        'main:app'
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        # Use exec to replace the current process
        os.execvp(sys.executable, cmd)
    except Exception as e:
        print(f"Failed to start server: {e}")
        # Fallback to uvicorn directly
        print("Falling back to uvicorn...")
        fallback_cmd = [
            sys.executable, '-m', 'uvicorn',
            'main:app',
            '--host', host,
            '--port', str(port),
            '--reload'
        ]
        os.execvp(sys.executable, fallback_cmd)

if __name__ == '__main__':
    main()