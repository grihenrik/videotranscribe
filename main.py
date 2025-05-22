from flask import Flask, send_from_directory, request, jsonify, redirect
import os
import logging
import json
import time
from werkzeug.serving import run_simple

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='static')

# Temporary storage for demo job statuses
job_statuses = {}

# Serve static files
@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')

@app.route('/css/<path:path>')
def serve_css(path):
    """Serve CSS files"""
    return send_from_directory('static/css', path)

@app.route('/js/<path:path>')
def serve_js(path):
    """Serve JavaScript files"""
    return send_from_directory('static/js', path)

# Basic API for demo
@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """Demo API endpoint for transcription"""
    data = request.json
    logger.info(f"Transcription request received: {data}")
    
    # Generate job ID
    job_id = f"job-{int(time.time())}"
    
    # Extract video ID from URL
    url = data.get("url", "")
    video_id = "demo"
    if "v=" in url:
        video_id = url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0]
    
    # Store job status
    job_statuses[job_id] = {
        "status": "processing",
        "percent": 10,
        "video_id": video_id,
        "mode": data.get("mode", "auto"),
        "lang": data.get("lang", "en")
    }
    
    # Return response
    return jsonify({
        "job_id": job_id,
        "status": "processing",
        "video_id": video_id,
        "message": "Transcription started",
        "download_links": {
            "txt": f"/api/download/{job_id}?format=txt",
            "srt": f"/api/download/{job_id}?format=srt",
            "vtt": f"/api/download/{job_id}?format=vtt"
        }
    })

@app.route('/api/job/<job_id>/status')
def job_status(job_id):
    """Get job status"""
    if job_id not in job_statuses:
        return jsonify({"error": "Job not found"}), 404
    
    # For demo, gradually increase progress
    status = job_statuses[job_id]
    if status["status"] == "processing" and status["percent"] < 100:
        status["percent"] += 20
        if status["percent"] >= 100:
            status["status"] = "complete"
            status["percent"] = 100
    
    return jsonify({
        "status": status["status"],
        "percent": status["percent"]
    })

@app.route('/api/download/<job_id>')
def download(job_id):
    """Demo download endpoint"""
    if job_id not in job_statuses:
        return jsonify({"error": "Job not found"}), 404
    
    format_type = request.args.get('format', 'txt')
    status = job_statuses[job_id]
    
    # Sample content based on format
    if format_type == 'txt':
        content = f"Transcription for video {status['video_id']} in plain text format.\n\nThis is a demo transcription."
    elif format_type == 'srt':
        content = "1\n00:00:00,000 --> 00:00:05,000\nThis is a demo subtitle in SRT format.\n\n2\n00:00:05,000 --> 00:00:10,000\nThe actual transcription feature is coming soon."
    elif format_type == 'vtt':
        content = "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nThis is a demo subtitle in WebVTT format.\n\n00:00:05.000 --> 00:00:10.000\nThe actual transcription feature is coming soon."
    else:
        return jsonify({"error": "Invalid format"}), 400
    
    return content

# This is the app that Gunicorn will use
application = app

if __name__ == '__main__':
    # Run with Werkzeug development server
    run_simple('0.0.0.0', 5000, app, use_reloader=True, use_debugger=True)
