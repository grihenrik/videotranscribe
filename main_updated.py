import os
import logging
import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define the SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize the Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # For proper URL generation behind proxies

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize SQLAlchemy
db = SQLAlchemy(app, model_class=Base)

# Import models (after db is defined)
from models import User, Transcription, Notification, DailyStats, OAuth

# Initialize LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Register the timeago template filter
from filters import timeago

@app.template_filter('timeago')
def timeago_filter(dt):
    return timeago(dt)

# Set up context processors for template globals
@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.datetime.now().year,
        'unread_notifications_count': get_unread_notifications_count()
    }

def get_unread_notifications_count():
    """Get count of unread notifications for the current user"""
    if current_user.is_authenticated:
        return Notification.query.filter_by(
            user_id=current_user.id, 
            read=False
        ).count()
    return 0

# Create necessary tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created")

# Import and register authentication blueprint
import auth
from auth import admin_required

# Import and register route handlers
import routes

# Import the original transcription logic
import whisper_service
import time
import threading
import queue
import tempfile
import json

# Create temp directory if it doesn't exist
os.makedirs('tmp', exist_ok=True)

# Temporary storage for job statuses and transcriptions (for backwards compatibility)
job_statuses = {}
transcriptions = {}

# Create a transcription job queue
transcription_queue = queue.Queue()

# Worker thread for processing transcription jobs
worker_thread = None
worker_running = False

def process_queue():
    """Process jobs from the transcription queue"""
    global worker_running
    
    logger.info("Worker thread started")
    worker_running = True
    
    while worker_running:
        try:
            # Get a job from the queue with a timeout
            try:
                job = transcription_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            # Extract job details
            job_id = job.get('job_id')
            url = job.get('url')
            mode = job.get('mode')
            lang = job.get('lang')
            video_id = job.get('video_id')
            batch_id = job.get('batch_id')
            user_id = job.get('user_id')
            
            # Process the job
            logger.info(f"Processing job {job_id} for video {video_id}")
            
            try:
                # Track in database if user is logged in
                transcription_id = None
                if user_id:
                    # Get video title
                    video_title = job.get('video_title', f"YouTube Video {video_id}")
                    transcription_id = routes.track_transcription(
                        video_id=video_id,
                        video_title=video_title,
                        url=url,
                        mode=mode,
                        lang=lang,
                        user_id=user_id,
                        batch_id=batch_id
                    )
                
                # Process using the existing function
                process_transcription(job_id, url, mode, lang, video_id, batch_id)
                
                # Update database status if needed
                if transcription_id:
                    routes.update_transcription_status(transcription_id, 'completed')
                
            except Exception as e:
                logger.error(f"Error processing job {job_id}: {e}")
                job_statuses[job_id] = {
                    'status': 'error',
                    'percent': 100,
                    'error': str(e)
                }
                
                # Update database status if needed
                if transcription_id:
                    routes.update_transcription_status(transcription_id, 'failed', str(e))
            
            # Mark task as done
            transcription_queue.task_done()
            
        except Exception as e:
            logger.error(f"Error in worker thread: {e}")
            time.sleep(1)  # Avoid busy waiting in case of persistent errors
    
    logger.info("Worker thread stopped")

def ensure_worker_thread():
    """Ensure the worker thread is running"""
    global worker_thread, worker_running
    
    if worker_thread is None or not worker_thread.is_alive():
        worker_running = True
        worker_thread = threading.Thread(target=process_queue, daemon=True)
        worker_thread.start()

def process_transcription(job_id, url, mode, lang, video_id, batch_id=None):
    """Process a single transcription job"""
    try:
        # Update status to downloading
        job_statuses[job_id] = {
            'status': 'downloading',
            'percent': 10,
            'error': None
        }
        
        # Check if we already have this transcription cached
        cache_key = f"{video_id}_{mode}_{lang}"
        if cache_key in transcriptions:
            logger.info(f"Using cached transcription for {video_id}")
            job_statuses[job_id] = {
                'status': 'complete',
                'percent': 100,
                'error': None
            }
            return
        
        # Download audio from YouTube
        logger.info(f"Downloading audio for {video_id}")
        temp_dir = tempfile.mkdtemp(dir='tmp')
        audio_file = whisper_service.download_audio_from_youtube(url, temp_dir)
        
        if not audio_file:
            raise Exception("Failed to download audio from YouTube")
        
        # Update status to transcribing
        job_statuses[job_id] = {
            'status': 'transcribing',
            'percent': 40,
            'error': None
        }
        
        # Get transcription based on mode
        transcription_text = ""
        
        if mode == 'whisper':
            # Use OpenAI Whisper for transcription
            logger.info(f"Transcribing {video_id} with Whisper")
            result = whisper_service.transcribe_audio_file(audio_file, lang)
            if not result:
                raise Exception("Whisper transcription failed")
            
            transcription_text = result.get('text', '')
            
            # Get different formats
            srt_content = result.get('srt') or whisper_service.convert_to_srt(transcription_text)
            vtt_content = result.get('vtt') or whisper_service.convert_to_vtt(transcription_text)
            
        elif mode == 'captions':
            # Try to use YouTube's captions
            # This would typically be implemented in the YouTube service
            # For now, we'll just convert the text to the required formats
            transcription_text = "Captions not implemented yet"
            srt_content = whisper_service.convert_to_srt(transcription_text)
            vtt_content = whisper_service.convert_to_vtt(transcription_text)
            
        else:  # Auto mode - try captions first, then fall back to Whisper
            # For now, just use Whisper
            logger.info(f"Transcribing {video_id} with Whisper (auto mode)")
            result = whisper_service.transcribe_audio_file(audio_file, lang)
            if not result:
                raise Exception("Whisper transcription failed")
            
            transcription_text = result.get('text', '')
            srt_content = result.get('srt') or whisper_service.convert_to_srt(transcription_text)
            vtt_content = result.get('vtt') or whisper_service.convert_to_vtt(transcription_text)
        
        # Create save directory
        save_dir = os.path.join('tmp', job_id)
        os.makedirs(save_dir, exist_ok=True)
        
        # Save files
        txt_path = os.path.join(save_dir, f"{video_id}.txt")
        srt_path = os.path.join(save_dir, f"{video_id}.srt")
        vtt_path = os.path.join(save_dir, f"{video_id}.vtt")
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(transcription_text)
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write(vtt_content)
        
        # Cache the results
        transcriptions[cache_key] = {
            'text': transcription_text,
            'srt': srt_content,
            'vtt': vtt_content,
            'files': {
                'txt': txt_path,
                'srt': srt_path,
                'vtt': vtt_path
            }
        }
        
        # Update status to complete
        job_statuses[job_id] = {
            'status': 'complete',
            'percent': 100,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error processing transcription for {video_id}: {e}")
        job_statuses[job_id] = {
            'status': 'error',
            'percent': 100,
            'error': str(e)
        }
        raise

# Add API routes from original app
@app.route('/transcribe', methods=['POST'])
def transcribe():
    """API endpoint for transcription"""
    # Check if we got JSON or form data
    if request.is_json:
        data = request.json
    else:
        data = request.form
    
    url = data.get('url')
    mode = data.get('mode', 'auto')
    lang = data.get('lang', 'en')
    
    if not url:
        return json.dumps({'error': 'Missing URL parameter'}), 400
    
    # Generate a job ID
    job_id = f"job_{int(time.time())}_{hash(url) % 10000}"
    
    # Extract video ID from URL
    import re
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if not video_id_match:
        return json.dumps({'error': 'Invalid YouTube URL'}), 400
    
    video_id = video_id_match.group(1)
    
    # Get title (this would normally come from yt-dlp)
    video_title = f"YouTube Video ({video_id})"
    
    # Add to job queue
    job_data = {
        'job_id': job_id,
        'url': url,
        'mode': mode,
        'lang': lang,
        'video_id': video_id,
        'video_title': video_title
    }
    
    # Add user ID if logged in
    if current_user.is_authenticated:
        job_data['user_id'] = current_user.id
    
    # Add job to queue
    transcription_queue.put(job_data)
    
    # Ensure worker thread is running
    ensure_worker_thread()
    
    # Set initial job status
    job_statuses[job_id] = {
        'status': 'downloading',
        'percent': 0,
        'error': None
    }
    
    # Return job ID and video info
    response = {
        'job_id': job_id,
        'video_id': video_id,
        'video_title': video_title,
        'message': 'Transcription job started',
        'download_links': {
            'txt': f"/download/{job_id}?format=txt",
            'srt': f"/download/{job_id}?format=srt",
            'vtt': f"/download/{job_id}?format=vtt"
        }
    }
    
    return json.dumps(response)

@app.route('/job-status/<job_id>')
def job_status(job_id):
    """Get job status"""
    status = job_statuses.get(job_id, {
        'status': 'error',
        'percent': 0,
        'error': 'Job not found'
    })
    
    return json.dumps(status)

@app.route('/download/<job_id>')
def download(job_id):
    """Download transcription endpoint"""
    format = request.args.get('format', 'txt')
    
    # Check if the job is complete
    status = job_statuses.get(job_id)
    if not status or status.get('status') != 'complete':
        return f"Transcription is not ready yet. Status: {status.get('status') if status else 'unknown'}"
    
    # Find the video ID from job details in transcription queue
    video_id = None
    for cache_key, data in transcriptions.items():
        if job_id in cache_key:
            video_id = cache_key.split('_')[0]
            break
    
    if not video_id:
        # If we can't find by cache key, use job_id directory name
        files = os.listdir(os.path.join('tmp', job_id))
        if files:
            # Extract video ID from filename
            video_id = files[0].split('.')[0]
    
    if not video_id:
        return "Could not find video ID for this job"
    
    # Determine content type based on format
    content_types = {
        'txt': 'text/plain',
        'srt': 'application/x-subrip',
        'vtt': 'text/vtt'
    }
    
    content_type = content_types.get(format, 'text/plain')
    
    # Path to the file
    file_path = os.path.join('tmp', job_id, f"{video_id}.{format}")
    
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Return the content with appropriate Content-Type
    return Response(content, mimetype=content_type)

# Register OAuth providers and set up the auth blueprint
auth.register_oauth_providers()
app.register_blueprint(auth.auth_bp, url_prefix='/auth')

# Ensure the worker thread is started
ensure_worker_thread()

# Main entry point
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)