#!/usr/bin/env python3
"""
Production server starter that ensures FastAPI runs with correct ASGI configuration.
This script replaces the problematic gunicorn sync worker setup.
"""

import os
import sys
import signal
import subprocess
import time
import threading
from pathlib import Path

def cleanup_existing_servers():
    """Clean up any existing server processes."""
    try:
        subprocess.run(["pkill", "-f", "gunicorn"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-f", "uvicorn"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except Exception:
        pass

def start_uvicorn_server():
    """Start the server with uvicorn directly."""
    os.chdir(Path(__file__).parent)
    
    # Clean up first
    cleanup_existing_servers()
    
    # Configure environment
    host = "0.0.0.0"
    port = 5000
    
    print(f"🚀 Starting FastAPI application on {host}:{port}")
    print("📡 Using uvicorn ASGI server for optimal FastAPI performance")
    
    # Use uvicorn directly for FastAPI
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", host,
        "--port", str(port),
        "--reload",
        "--log-level", "info"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        cleanup_existing_servers()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start the server - this will run indefinitely
        result = subprocess.run(cmd)
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        cleanup_existing_servers()
        return 0
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1

def monitor_and_restart():
    """Monitor the server and restart if needed."""
    while True:
        try:
            returncode = start_uvicorn_server()
            if returncode != 0:
                print(f"⚠️ Server exited with code {returncode}, restarting in 5 seconds...")
                time.sleep(5)
            else:
                break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print("🔧 FastAPI Production Server Starter")
    print("=" * 50)
    monitor_and_restart()