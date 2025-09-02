#!/usr/bin/env python3
"""
Direct uvicorn starter that bypasses workflow issues.
Run this instead of the problematic gunicorn workflow.
"""

import subprocess
import sys
import os

def main():
    # Kill any existing servers
    subprocess.run(['pkill', '-f', 'gunicorn'], check=False, capture_output=True)
    subprocess.run(['pkill', '-f', 'uvicorn'], check=False, capture_output=True)
    
    # Change to project directory
    os.chdir('/home/runner/workspace')
    
    # Start uvicorn with proper ASGI configuration
    cmd = [
        sys.executable, '-m', 'uvicorn',
        'main:app',
        '--host', '0.0.0.0',
        '--port', '5000',
        '--reload'
    ]
    
    print("Starting FastAPI with uvicorn ASGI server...")
    print(f"Command: {' '.join(cmd)}")
    
    # Execute uvicorn
    subprocess.run(cmd)

if __name__ == "__main__":
    main()