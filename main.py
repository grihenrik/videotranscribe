"""
Main entry point for the FastAPI application.
"""
import os
import sys
import uvicorn
import subprocess
import threading
import time
from app import create_app

# Create the FastAPI application instance
app = create_app()

def start_correct_server():
    """Start the server with the correct ASGI configuration."""
    def run_server():
        try:
            # Kill any existing processes
            subprocess.run(["pkill", "-f", "gunicorn"], check=False, stderr=subprocess.DEVNULL)
            time.sleep(1)
            
            # Start with the correct uvicorn worker configuration
            cmd = [
                sys.executable, "-m", "gunicorn",
                "--bind", "0.0.0.0:5000",
                "--worker-class", "uvicorn.workers.UvicornWorker",
                "--workers", "1", 
                "--reload",
                "main:app"
            ]
            subprocess.run(cmd)
        except Exception:
            # Fallback to uvicorn directly
            uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
    
    # Run the server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

# Auto-start the correct server when imported
if os.environ.get('REPLIT_DEPLOYMENT') or os.environ.get('REPL_ID'):
    # We're in Replit, start the correct server
    start_correct_server()

if __name__ == "__main__":
    # For direct execution, use uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)