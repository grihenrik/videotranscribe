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
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from asgiref.wsgi import WsgiToAsgi

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
        convert_to_vtt,
        extract_playlist_videos,
        is_playlist_url,
        get_proxy_config
    )
    WHISPER_AVAILABLE = True
    logger.info("✅ Standalone Whisper service loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load Whisper service: {e}")
    logger.info("🔄 Falling back to mock transcription")
    WHISPER_AVAILABLE = False

# Try to import the advanced proxy manager
try:
    from proxy_manager import get_proxy_manager
    PROXY_MANAGER_AVAILABLE = True
    logger.info("✅ Advanced proxy manager loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load proxy manager: {e}")
    logger.info("🔄 Using basic proxy configuration")
    PROXY_MANAGER_AVAILABLE = False

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

def fallback_extract_playlist_videos(playlist_url):
    """Fallback playlist extraction for testing"""
    return [{
        'id': 'mock_video_1',
        'title': 'Mock Video 1',
        'url': 'https://www.youtube.com/watch?v=mock_video_1'
    }]

def fallback_is_playlist_url(url):
    """Fallback playlist detection"""
    return 'list=' in url or '/playlist?' in url

# Set fallback functions if Whisper is not available
if not WHISPER_AVAILABLE:
    transcribe_audio_file = fallback_transcribe_audio_file
    download_audio_from_youtube = fallback_download_audio_from_youtube
    extract_playlist_videos = fallback_extract_playlist_videos
    is_playlist_url = fallback_is_playlist_url
    get_proxy_config = lambda: None  # Fallback proxy function

def real_transcribe_playlist(job_id, playlist_url, mode, lang):
    """Transcribe all videos in a YouTube playlist"""
    try:
        logger.info(f"Starting playlist transcription for job {job_id}")
        
        # Create worker ID for sticky session (playlist jobs get consistent worker ID)
        worker_id = f"playlist_{job_id}"
        
        # Get proxy manager or fallback to basic proxy
        if PROXY_MANAGER_AVAILABLE:
            proxy_manager = get_proxy_manager()
            # Get sticky session for this worker
            session = proxy_manager.get_worker_session(worker_id)
            proxy = session.proxy_url
            logger.info(f"✅ Using sticky session for worker {worker_id} (proxy: {proxy[:50] if proxy else 'None'}...)")
        else:
            proxy = get_proxy_config() if WHISPER_AVAILABLE else None
            proxy_manager = None
            logger.info("Using basic proxy configuration")
        
        if proxy:
            logger.info(f"Using proxy: {proxy}")
        
        # Update status to extracting playlist
        job_statuses[job_id]['status'] = 'extracting_playlist'
        job_statuses[job_id]['percent'] = 5
        
        # Extract videos from playlist (with throttling if available)
        logger.info(f"Extracting videos from playlist: {playlist_url}")
        if proxy_manager:
            proxy_manager.pre_request_hook(worker_id)
        
        videos = extract_playlist_videos(playlist_url, proxy)
        
        if proxy_manager:
            proxy_manager.post_request_hook(worker_id, success=(videos is not None and len(videos) > 0))
        
        if not videos:
            raise Exception("No videos found in the playlist or playlist is private/unavailable.")
        
        logger.info(f"Found {len(videos)} videos in playlist")
        job_statuses[job_id]['total_videos'] = len(videos)
        job_statuses[job_id]['completed_videos'] = 0
        
        # Create save directory
        save_dir = os.path.join('tmp', job_id)
        os.makedirs(save_dir, exist_ok=True)
        
        # Process each video
        for i, video in enumerate(videos):
            try:
                logger.info(f"Processing video {i+1}/{len(videos)}: {video['title']}")
                
                # Update progress
                base_progress = 10 + (i * 80 // len(videos))
                job_statuses[job_id]['status'] = f'processing_video_{i+1}_of_{len(videos)}'
                job_statuses[job_id]['percent'] = base_progress
                job_statuses[job_id]['current_video'] = video['title']
                
                video_id = video.get('id')
                transcription_result = None
                
                # Try optimized transcription with proxy manager (using same worker ID for sticky session)
                if proxy_manager and video_id:
                    logger.info(f"Using optimized transcription for {video['title']} (sticky session: {worker_id})")
                    transcription_result = proxy_manager.get_optimized_transcription(
                        video_id=video_id,
                        mode=mode,
                        language=lang if lang != 'auto' else 'en',
                        worker_id=worker_id  # Use same worker ID for sticky session
                    )
                
                # Fallback to traditional audio download + Whisper
                if not transcription_result:
                    logger.info(f"Using traditional audio download for: {video['title']}")
                    
                    # Throttle request using worker ID for sticky session
                    if proxy_manager:
                        proxy_manager.pre_request_hook(worker_id)
                    
                    # Download audio for this video
                    temp_dir = tempfile.mkdtemp(dir='tmp')
                    
                    # Use sticky session proxy if available
                    download_proxy = proxy
                    if proxy_manager:
                        session = proxy_manager.get_worker_session(worker_id)
                        download_proxy = session.proxy_url
                    
                    audio_file = download_audio_from_youtube(video['url'], temp_dir, download_proxy)
                    
                    # Record request result using worker ID
                    if proxy_manager:
                        proxy_manager.post_request_hook(worker_id, success=(audio_file is not None))
                    
                    if not audio_file:
                        logger.warning(f"Failed to download audio for video: {video['title']}")
                        continue
                    
                    # Update progress
                    job_statuses[job_id]['percent'] = base_progress + 20
                    
                    # Transcribe using Whisper
                    logger.info(f"Transcribing: {video['title']}")
                    transcription_result = transcribe_audio_file(audio_file, lang if lang != 'auto' else None)
                    
                    # Cache result if we have proxy manager
                    if proxy_manager and transcription_result and video_id:
                        proxy_manager.cache.cache_video(
                            video_id=video_id,
                            etag="audio_whisper",
                            title=video['title'],
                            transcription_text=transcription_result['text'],
                            transcription_srt=transcription_result['srt'],
                            transcription_vtt=transcription_result['vtt']
                        )
                    
                    # Clean up temporary audio file
                    try:
                        if os.path.exists(audio_file):
                            os.remove(audio_file)
                        if os.path.exists(temp_dir):
                            os.rmdir(temp_dir)
                    except:
                        pass  # Don't fail if cleanup fails
                
                if not transcription_result:
                    logger.warning(f"Failed to transcribe video: {video['title']}")
                    continue
                
                # Update progress
                job_statuses[job_id]['percent'] = base_progress + 60
                
                # Save files with video title as filename
                safe_title = video['title'][:100]  # Limit filename length
                txt_path = os.path.join(save_dir, f"{safe_title}.txt")
                srt_path = os.path.join(save_dir, f"{safe_title}.srt")
                vtt_path = os.path.join(save_dir, f"{safe_title}.vtt")
                
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
                
                # Update completed count
                job_statuses[job_id]['completed_videos'] = i + 1
                logger.info(f"Completed transcription for: {video['title']}")
                
            except Exception as video_error:
                logger.error(f"Error processing video {video['title']}: {video_error}")
                # Continue with next video instead of failing entire playlist
                continue
        
        # Update status to complete
        job_statuses[job_id]['status'] = 'complete'
        job_statuses[job_id]['percent'] = 100
        
        completed_count = job_statuses[job_id]['completed_videos']
        logger.info(f"Completed playlist transcription for job {job_id}: {completed_count}/{len(videos)} videos")
        
    except Exception as e:
        logger.error(f"Error in playlist transcription job {job_id}: {e}")
        job_statuses[job_id]['status'] = 'error'
        job_statuses[job_id]['error'] = str(e)
        job_statuses[job_id]['percent'] = 100

# Real transcription function using optimized proxy manager with sticky sessions
def real_transcribe_audio(job_id, url, mode, lang, video_id):
    """Real transcription function using Whisper and yt-dlp with optimized proxy handling and sticky sessions"""
    try:
        logger.info(f"Starting real transcription for job {job_id}")
        
        # Create worker ID for sticky session (single jobs get unique worker ID based on job_id)
        worker_id = f"single_{job_id}"
        
        # Get proxy manager or fallback to basic proxy
        if PROXY_MANAGER_AVAILABLE:
            proxy_manager = get_proxy_manager()
            # Get sticky session for this worker
            session = proxy_manager.get_worker_session(worker_id)
            proxy = session.proxy_url
            logger.info(f"✅ Using sticky session for worker {worker_id} (proxy: {proxy[:50] if proxy else 'None'}...)")
        else:
            proxy = get_proxy_config() if WHISPER_AVAILABLE else None
            proxy_manager = None
            logger.info("Using basic proxy configuration")
        
        if proxy:
            logger.info(f"Using proxy: {proxy}")
        
        # Update status to starting
        job_statuses[job_id]['status'] = 'starting_transcription'
        job_statuses[job_id]['percent'] = 5
        
        transcription_result = None
        
        # Try optimized transcription with proxy manager (captions first, then audio)
        if proxy_manager and video_id:
            logger.info(f"Using optimized transcription for video {video_id} (sticky session: {worker_id})")
            transcription_result = proxy_manager.get_optimized_transcription(
                video_id=video_id,
                mode=mode,
                language=lang if lang != 'auto' else 'en',
                worker_id=worker_id  # Use worker ID for sticky session
            )
            
            if transcription_result:
                job_statuses[job_id]['status'] = 'transcription_complete_captions'
                job_statuses[job_id]['percent'] = 70
                logger.info(f"✅ Transcription completed using captions API (saved ~90% bandwidth)")
        
        # Fallback to traditional audio download + Whisper
        if not transcription_result:
            logger.info(f"Using traditional audio download + Whisper for video {video_id}")
            
            # Update status to downloading
            job_statuses[job_id]['status'] = 'downloading_audio'
            job_statuses[job_id]['percent'] = 10
            
            # Throttle request using worker ID for sticky session
            if proxy_manager:
                proxy_manager.pre_request_hook(worker_id)
            
            # Download audio from YouTube
            logger.info(f"Downloading audio for video {video_id} from URL: {url}")
            temp_dir = tempfile.mkdtemp(dir='tmp')
            
            # Use sticky session proxy if available
            download_proxy = proxy
            if proxy_manager:
                session = proxy_manager.get_worker_session(worker_id)
                download_proxy = session.proxy_url
            
            audio_file = download_audio_from_youtube(url, temp_dir, download_proxy)
            
            # Record request result using worker ID
            if proxy_manager:
                proxy_manager.post_request_hook(worker_id, success=(audio_file is not None))
            
            if not audio_file:
                raise Exception("Failed to download audio from YouTube. The video might be private, restricted, or unavailable.")
            
            logger.info(f"Audio downloaded successfully: {audio_file}")
            
            # Update status to transcribing
            job_statuses[job_id]['status'] = 'transcribing_audio'
            job_statuses[job_id]['percent'] = 40
            
            # Transcribe using Whisper
            logger.info(f"Transcribing audio with Whisper (mode: {mode}, language: {lang})")
            transcription_result = transcribe_audio_file(audio_file, lang if lang != 'auto' else None)
            
            # Cache result if we have proxy manager
            if proxy_manager and transcription_result and video_id:
                proxy_manager.cache.cache_video(
                    video_id=video_id,
                    etag="audio_whisper",
                    transcription_text=transcription_result['text'],
                    transcription_srt=transcription_result['srt'],
                    transcription_vtt=transcription_result['vtt']
                )
            
            # Clean up temporary audio file
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass  # Don't fail if cleanup fails
        
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

# Helper functions for file upload routing

def validate_file_upload(file):
    """Validate uploaded file type and size"""
    if not file or file.filename == '':
        raise ValueError('No file selected')

    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    max_size = 200 * 1024 * 1024
    if file_size > max_size:
        raise ValueError('File too large. Maximum size is 200MB.')

    allowed_extensions = {
        '.mp3', '.mp4', '.wav', '.m4a', '.flac', '.aac', '.ogg',
        '.webm', '.mov', '.avi', '.mkv', '.wma', '.3gp', '.amr'
    }

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise ValueError(f'Unsupported file type: {file_ext}')

    return file_size, file_ext


def save_uploaded_file(file, file_ext):
    """Save uploaded file to temporary directory and return path"""
    temp_dir = tempfile.mkdtemp(dir='tmp')
    temp_file_path = os.path.join(temp_dir, f'upload{file_ext}')
    file.save(temp_file_path)
    return temp_file_path, temp_dir


def real_transcribe_file(job_id, file_path, language, custom_name, original_filename):
    """Real file transcription function using Whisper directly"""
    try:
        logger.info(f"Starting file transcription for job {job_id}")
        
        # Update status to processing
        job_statuses[job_id]['status'] = 'processing_file'
        job_statuses[job_id]['percent'] = 10
        
        # Create save directory
        save_dir = os.path.join('tmp', job_id)
        os.makedirs(save_dir, exist_ok=True)
        
        # Determine final transcription source path
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        # Update progress
        job_statuses[job_id]['percent'] = 30
        job_statuses[job_id]['status'] = 'transcribing_file'
        
        # Transcribe using Whisper directly on the file
        logger.info(f"Transcribing file with Whisper")
        transcription_result = transcribe_audio_file(
            file_path,
            language if language != 'auto' else None
        )
        
        if not transcription_result:
            raise Exception("Failed to transcribe the uploaded file.")
        
        logger.info(f"File transcription completed successfully")
        
        # Update progress
        job_statuses[job_id]['percent'] = 80
        job_statuses[job_id]['status'] = 'saving_results'
        
        # Save files with custom name or original filename
        base_name = custom_name if custom_name else os.path.splitext(original_filename)[0]
        # Clean base name for safe filename
        import re
        base_name = re.sub(r'[<>:"/\\|?*]', '_', base_name)
        base_name = base_name.strip()
        
        # Save transcription files
        txt_path = os.path.join(save_dir, f"{base_name}.txt")
        srt_path = os.path.join(save_dir, f"{base_name}.srt")
        vtt_path = os.path.join(save_dir, f"{base_name}.vtt")
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(transcription_result['text'])
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(transcription_result['srt'])
        
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write(transcription_result['vtt'])
        
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            temp_dir = os.path.dirname(file_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass  # Don't fail if cleanup fails
        
        # Update status to complete
        job_statuses[job_id]['status'] = 'complete'
        job_statuses[job_id]['percent'] = 100
        job_statuses[job_id]['transcription_file'] = base_name
        
        logger.info(f"Completed file transcription for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error in file transcription job {job_id}: {e}")
        job_statuses[job_id]['status'] = 'error'
        job_statuses[job_id]['error'] = str(e)
        job_statuses[job_id]['percent'] = 100

# === Routes ===

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('static', 'index.html')

# API routes must be defined BEFORE the catch-all static files route,
# otherwise /upload-transcribe, /transcribe, etc. get matched as static file paths
# and return 405 Method Not Allowed for POST requests.

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
        
        # Check if this is a playlist URL
        if is_playlist_url(url):
            logger.info(f"Detected playlist URL: {url}")
            
            # Generate a job ID for playlist
            job_id = f"playlist_{int(time.time())}_{abs(hash(url)) % 10000}"
            
            logger.info(f"Received playlist transcription request: job_id={job_id}, mode={mode}, lang={lang}")
            
            # Set initial job status for playlist
            job_statuses[job_id] = {
                'status': 'queued',
                'percent': 0,
                'error': None,
                'is_playlist': True,
                'total_videos': 0,
                'completed_videos': 0
            }
            
            # Start playlist transcription in background thread
            thread = threading.Thread(
                target=real_transcribe_playlist,
                args=(job_id, url, mode, lang),
                daemon=True
            )
            thread.start()
            
            # Return job ID and playlist info
            response = {
                'job_id': job_id,
                'status': 'queued',
                'is_playlist': True,
                'message': 'Playlist transcription job started',
                'download_links': {
                    'zip': f"/download/{job_id}?format=zip"
                }
            }
            
            logger.info(f"Returning playlist response: {response}")
            return jsonify(response)
        
        # Handle single video URL
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

@app.route('/upload-transcribe', methods=['POST'])
def upload_transcribe():
    """Upload and transcribe audio/video file"""
    try:
        logger.info("File upload transcription request received")
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file upload and save temporarily
        try:
            file_size, file_ext = validate_file_upload(file)
            file_path, temp_dir = save_uploaded_file(file, file_ext)
        except ValueError as value_err:
            return jsonify({'error': str(value_err)}), 400
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            return jsonify({'error': 'Failed to save uploaded file'}), 500

        # Get additional parameters
        language = request.form.get('language', 'auto')
        custom_name = request.form.get('custom_name', '')

        # Generate job ID
        job_id = f"file_{int(time.time())}_{uuid.uuid4().hex[:4]}"
        
        logger.info(f"Processing file upload: {file.filename} (size: {file_size}, job: {job_id})")
        
        # Initialize job status
        job_statuses[job_id] = {
            'status': 'uploading',
            'percent': 0,
            'video_id': custom_name or os.path.splitext(file.filename)[0],
            'is_playlist': False,
            'file_upload': True,
            'original_filename': file.filename,
            'file_size': file_size
        }
        
        # Start transcription in background thread
        thread = threading.Thread(
            target=real_transcribe_file,
            args=(job_id, file_path, language, custom_name, file.filename)
        )
        thread.daemon = True
        thread.start()
        
        # Return immediate response
        response = {
            'job_id': job_id,
            'status': 'queued',
            'is_playlist': False,
            'file_upload': True,
            'message': 'File upload transcription job started',
            'original_filename': file.filename,
            'file_size': file_size
        }
        
        logger.info(f"File upload job started: {job_id}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in upload-transcribe endpoint: {e}")
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
        
        # Handle ZIP download for playlists
        if format == 'zip':
            import zipfile
            from io import BytesIO
            
            # If we have files but no job status, assume the job was completed
            if not status:
                logger.info(f"Playlist job {job_id} status lost but files exist - serving ZIP download")
            elif status.get('status') != 'complete':
                return f"Playlist transcription is not ready yet. Status: {status.get('status')}", 202
            
            # Create ZIP file in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add all transcription files to the ZIP
                for filename in os.listdir(job_dir):
                    if filename.endswith(('.txt', '.srt', '.vtt')):
                        file_path = os.path.join(job_dir, filename)
                        zip_file.write(file_path, filename)
            
            zip_buffer.seek(0)
            
            logger.info(f"Serving ZIP download for playlist job {job_id}")
            return Response(
                zip_buffer.getvalue(),
                mimetype='application/zip',
                headers={
                    'Content-Disposition': f'attachment; filename="playlist_transcriptions_{job_id}.zip"'
                }
            )
        
        # Handle individual file downloads (single videos)
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

@app.route('/<path:filename>')
def static_files(filename):
    """Serve static files (must be last - catch-all for non-API paths)"""
    return send_from_directory('static', filename)

if __name__ == "__main__":
    logger.info("Starting simple YouTube transcription server...")
    logger.info("Access the app at: http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=True)

# ASGI entrypoint for Uvicorn
asgi_app = WsgiToAsgi(app)
