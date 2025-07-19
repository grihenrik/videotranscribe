"""
Main entry point for the FastAPI application with WSGI compatibility fallback.
"""
import os
import sys
import threading
import time

try:
    # Try to create FastAPI app first
    from app import create_app
    import uvicorn
    
    # Create the FastAPI application instance
    fastapi_app = create_app()
    
    # Check if we're being called by a WSGI server (like gunicorn with sync workers)
    if 'gunicorn' in sys.modules or os.environ.get('SERVER_SOFTWARE', '').startswith('gunicorn'):
        # We're likely being called by gunicorn with sync workers
        # Create a simple Flask wrapper for WSGI compatibility
        try:
            from flask import Flask, request, jsonify
            import requests
            
            flask_app = Flask(__name__)
            
            @flask_app.route('/')
            def index():
                return '''
                <html>
                <head><title>FastAPI Application</title></head>
                <body>
                    <h1>FastAPI YouTube Transcription Tool</h1>
                    <p>This application requires ASGI server support.</p>
                    <p>Please run with: <code>uvicorn main:fastapi_app --host 0.0.0.0 --port 5000</code></p>
                    <p>Or with gunicorn: <code>gunicorn --worker-class uvicorn.workers.UvicornWorker main:fastapi_app</code></p>
                </body>
                </html>
                '''
            
            # Export Flask app for WSGI compatibility
            app = flask_app
            
        except ImportError:
            # If Flask is not available, use the FastAPI app directly
            app = fastapi_app
    else:
        # Normal FastAPI app for ASGI servers
        app = fastapi_app
        
except ImportError as e:
    # Fallback if FastAPI modules can't be imported
    from flask import Flask
    
    fallback_app = Flask(__name__)
    
    @fallback_app.route('/')
    def fallback():
        return f'''
        <html>
        <head><title>Application Error</title></head>
        <body>
            <h1>Application Import Error</h1>
            <p>Error: {str(e)}</p>
            <p>Please check your FastAPI installation and dependencies.</p>
        </body>
        </html>
        '''
    
    app = fallback_app

# Make FastAPI app available for uvicorn
fastapi_app = app if 'fastapi_app' not in locals() else fastapi_app

if __name__ == "__main__":
    # For direct execution, use uvicorn with FastAPI
    try:
        uvicorn.run(fastapi_app, host="0.0.0.0", port=5000, reload=True)
    except:
        uvicorn.run("main:fastapi_app", host="0.0.0.0", port=5000, reload=True)