"""
WSGI-compatible version of the FastAPI application.
This creates a bridge that allows FastAPI to work with WSGI servers.
"""

from flask import Flask
import json
import requests
import subprocess
import threading
import time
import os
import sys

# Create a simple Flask app that proxies to FastAPI
flask_app = Flask(__name__)

# Global variable to track if FastAPI server is running
fastapi_server = None
fastapi_port = 5001  # Use different port to avoid conflicts

def start_fastapi_server():
    """Start FastAPI server on a different port."""
    global fastapi_server
    if fastapi_server is None:
        def run_fastapi():
            import uvicorn
            from app import create_app
            app = create_app()
            uvicorn.run(app, host="127.0.0.1", port=fastapi_port, log_level="warning")
        
        fastapi_server = threading.Thread(target=run_fastapi, daemon=True)
        fastapi_server.start()
        time.sleep(3)  # Give server time to start

@flask_app.before_first_request
def initialize():
    """Initialize FastAPI server when Flask app starts."""
    start_fastapi_server()

@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/<path:path>')
def proxy_to_fastapi(path):
    """Proxy all requests to the FastAPI server."""
    try:
        # Ensure FastAPI server is running
        if fastapi_server is None:
            start_fastapi_server()
        
        # Forward the request to FastAPI
        url = f"http://127.0.0.1:{fastapi_port}/{path}"
        
        if request.method == 'GET':
            response = requests.get(url, params=request.args)
        elif request.method == 'POST':
            response = requests.post(url, json=request.json, params=request.args)
        else:
            response = requests.request(request.method, url, data=request.data, params=request.args)
        
        return response.content, response.status_code, dict(response.headers)
    
    except Exception as e:
        return f"<html><body><h1>FastAPI Bridge Error</h1><p>Error: {str(e)}</p><p>Please use: <code>uvicorn main:app --host 0.0.0.0 --port 5000</code></p></body></html>", 500

# Export the Flask app for WSGI compatibility
app = flask_app

if __name__ == "__main__":
    # For direct execution, start FastAPI properly
    print("Starting FastAPI with uvicorn...")
    from app import create_app
    import uvicorn
    fastapi_app = create_app()
    uvicorn.run(fastapi_app, host="0.0.0.0", port=5000, reload=True)