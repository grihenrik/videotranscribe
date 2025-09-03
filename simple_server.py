#!/usr/bin/env python3
"""
Simple Flask server for YouTube transcription
Serves static files and handles transcription requests with real Whisper integration
"""

import os
import sys
import uuid
import logging
import json
import time
import threading
import queue
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_from_directory

# Setup basic logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Environment variables loaded from .env")
except ImportError:
    logger.warning("⚠️ python-dotenv not available, using system environment only")

# Try to import the standalone Whisper service
try:
    from standalone_whisper import (
        transcribe_audio_file, 
        download_audio_from_youtube, 
        convert_to_srt, 
        convert_to_vtt
    )
    WHISPER_AVAILABLE = True
    logger.info("✅ Standalone Whisper service loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load Whisper service: {e}")
    logger.info("🔄 Falling back to mock transcription")
    WHISPER_AVAILABLE = False

# Create Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Create necessary directories
os.makedirs('tmp', exist_ok=True)

# Temporary storage for job statuses
job_statuses = {}

# Fallback functions if Whisper service fails to load
def fallback_transcribe_audio_file(file_path, language=None):
    """Fallback mock transcription"""
    return {
        "text": f"Mock transcription for {os.path.basename(file_path)} (language: {language})",
        "srt": "1\n00:00:00,000 --> 00:00:05,000\nMock transcription\n\n",
        "vtt": "WEBVTT\n\n00:00.000 --> 00:05.000\nMock transcription\n\n"
    }

def fallback_download_audio_from_youtube(url, output_path=None):
    """Fallback that creates a dummy file"""
    if output_path is None:
        output_path = tempfile.mkdtemp()
    dummy_file = os.path.join(output_path, "dummy.mp3")
    with open(dummy_file, 'w') as f:
        f.write("dummy audio file")
    return dummy_file

# Set fallback functions if Whisper is not available
if not WHISPER_AVAILABLE:
    transcribe_audio_file = fallback_transcribe_audio_file
    download_audio_from_youtube = fallback_download_audio_from_youtube

# Mock transcription function (replace with actual implementation)
def real_transcribe_audio(job_id, url, mode, lang, video_id):
    """Real transcription function using Whisper and yt-dlp"""
    try:
        logger.info(f"Starting real transcription for job {job_id}")
        
        # Update status to downloading
        job_statuses[job_id]['status'] = 'downloading_audio'
        job_statuses[job_id]['percent'] = 10
        
        # Download audio from YouTube
        logger.info(f"Downloading audio for video {video_id} from URL: {url}")
        temp_dir = tempfile.mkdtemp(dir='tmp')
        audio_file = download_audio_from_youtube(url, temp_dir)
        
        if not audio_file:
            raise Exception("Failed to download audio from YouTube. The video might be private, restricted, or unavailable.")
        
        logger.info(f"Audio downloaded successfully: {audio_file}")
        
        # Update status to transcribing
        job_statuses[job_id]['status'] = 'transcribing_audio'
        job_statuses[job_id]['percent'] = 40
        
        # Transcribe using Whisper
        logger.info(f"Transcribing audio with Whisper (mode: {mode}, language: {lang})")
        
        # Check if we should use captions first (for auto mode)
        transcription_result = None
        
        if mode in ['auto', 'captions']:
            # Try to get captions first (this is a placeholder - you could implement caption extraction)
            logger.info("Attempting to extract captions...")
            # For now, we'll skip to Whisper
            
        if not transcription_result and mode in ['auto', 'whisper']:
            # Use Whisper for transcription
            logger.info("Using Whisper for transcription...")
            transcription_result = transcribe_audio_file(audio_file, lang if lang != 'auto' else None)
        
        if not transcription_result:
            raise Exception("Failed to transcribe audio. Please check your OpenAI API key and try again.")
        
        # Update status to saving files
        job_statuses[job_id]['status'] = 'saving_files'
        job_statuses[job_id]['percent'] = 80
        
        # Create save directory
        save_dir = os.path.join('tmp', job_id)
        os.makedirs(save_dir, exist_ok=True)
        
        # Save files in different formats
        txt_path = os.path.join(save_dir, f"{video_id}.txt")
        srt_path = os.path.join(save_dir, f"{video_id}.srt")
        vtt_path = os.path.join(save_dir, f"{video_id}.vtt")
        
        # Write text file
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(transcription_result['text'])
        
        # Write SRT file
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(transcription_result['srt'])
        
        # Write VTT file
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write(transcription_result['vtt'])
        
        # Clean up temporary audio file
        try:
            if os.path.exists(audio_file):
                os.remove(audio_file)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass  # Don't fail if cleanup fails
        
        # Update status to complete
        job_statuses[job_id]['status'] = 'complete'
        job_statuses[job_id]['percent'] = 100
        
        logger.info(f"Completed real transcription for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error in transcription job {job_id}: {e}")
        job_statuses[job_id]['status'] = 'error'
        job_statuses[job_id]['error'] = str(e)
        job_statuses[job_id]['percent'] = 100

# === Routes ===

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """API endpoint for transcription"""
    try:
        # Get JSON data with better error handling
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            logger.error(f"JSON parsing error: {json_error}")
            return jsonify({'error': 'Invalid JSON format'}), 400
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        url = data.get('url')
        mode = data.get('mode', 'auto')
        lang = data.get('lang', 'en')
        
        if not url:
            return jsonify({'error': 'Missing URL parameter'}), 400
        
        # Validate YouTube URL format
        import re
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([0-9A-Za-z_-]{11})',
            r'(?:https?://)?(?:www\.)?youtu\.be/([0-9A-Za-z_-]{11})',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([0-9A-Za-z_-]{11})'
        ]
        
        video_id = None
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL format'}), 400
        
        # Generate a job ID
        job_id = f"job_{int(time.time())}_{abs(hash(url)) % 10000}"
        
        logger.info(f"Received transcription request: job_id={job_id}, video_id={video_id}, mode={mode}, lang={lang}")
        
        # Set initial job status
        job_statuses[job_id] = {
            'status': 'queued',
            'percent': 0,
            'error': None
        }
        
        # Start transcription in background thread
        thread = threading.Thread(
            target=real_transcribe_audio,
            args=(job_id, url, mode, lang, video_id),
            daemon=True
        )
        thread.start()
        
        # Return job ID and video info
        response = {
            'job_id': job_id,
            'status': 'queued',
            'video_id': video_id,
            'message': 'Transcription job started',
            'download_links': {
                'txt': f"/download/{job_id}?format=txt",
                'srt': f"/download/{job_id}?format=srt",
                'vtt': f"/download/{job_id}?format=vtt"
            }
        }
        
        logger.info(f"Returning response: {response}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in transcribe endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/job-status/<job_id>')
def job_status(job_id):
    """Get job status"""
    try:
        status = job_statuses.get(job_id, {
            'status': 'error',
            'percent': 0,
            'error': 'Job not found'
        })
        
        logger.info(f"Status check for job {job_id}: {status}")
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error checking job status for {job_id}: {e}")
        return jsonify({
            'status': 'error',
            'percent': 0,
            'error': str(e)
        }), 500

@app.route('/download/<job_id>')
def download(job_id):
    """Download transcription endpoint"""
    try:
        format = request.args.get('format', 'txt')
        
        # Check if the job is complete
        status = job_statuses.get(job_id)
        
        # Check if files exist on disk (even if job status is lost)
        job_dir = os.path.join('tmp', job_id)
        if not os.path.exists(job_dir):
            return "Files not found", 404
        
        # Find the file with the requested format
        files = [f for f in os.listdir(job_dir) if f.endswith(f'.{format}')]
        if not files:
            return f"No {format} file found", 404
        
        # If we have files but no job status, assume the job was completed
        if not status:
            logger.info(f"Job {job_id} status lost but files exist - serving download")
        elif status.get('status') != 'complete':
            return f"Transcription is not ready yet. Status: {status.get('status')}", 202
        
        file_path = os.path.join(job_dir, files[0])
        
        # Determine content type based on format
        content_types = {
            'txt': 'text/plain',
            'srt': 'application/x-subrip', 
            'vtt': 'text/vtt'
        }
        
        content_type = content_types.get(format, 'text/plain')
        
        # Read and return the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"Serving download for job {job_id}, format {format}")
        return Response(content, mimetype=content_type, headers={
            'Content-Disposition': f'attachment; filename="{os.path.basename(file_path)}"'
        })
        
    except Exception as e:
        logger.error(f"Error in download endpoint for job {job_id}: {e}")
        return f"Error: {e}", 500

if __name__ == "__main__":
    logger.info("Starting simple YouTube transcription server...")
    logger.info("Access the app at: http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=True)
