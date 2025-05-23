import os
import uuid
import logging
import json
import time
import threading
import queue
import tempfile
import whisper_service
from datetime import datetime

# Import Flask components
from flask import render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import current_user

# Import app and database
from app import app, db
from models import User, Transcription, Notification, DailyStats, OAuth

# Import auth components
import auth
auth.register_oauth_providers()

# Import routes
from user_routes import user_bp
from admin_routes import admin_bp

# Register blueprints
app.register_blueprint(auth.auth_bp, url_prefix='/auth')
app.register_blueprint(user_bp, url_prefix='/user')
app.register_blueprint(admin_bp, url_prefix='/admin')

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create necessary directories
os.makedirs('tmp', exist_ok=True)

# Temporary storage for job statuses and transcriptions
job_statuses = {}
transcriptions = {}

# Create a transcription job queue
transcription_queue = queue.Queue()

# Worker thread for processing transcription jobs
worker_thread = None
worker_running = False

# Utility functions
def format_duration(seconds):
    """Format seconds into human-readable duration (HH:MM:SS)"""
    if not seconds:
        return "--:--"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

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
                    transcription_id = track_transcription(
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
                    update_transcription_status(transcription_id, 'completed')
                
            except Exception as e:
                logger.error(f"Error processing job {job_id}: {e}")
                job_statuses[job_id] = {
                    'status': 'error',
                    'percent': 100,
                    'error': str(e)
                }
                
                # Update database status if needed
                if transcription_id:
                    update_transcription_status(transcription_id, 'failed', str(e))
            
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

# === Helper functions for tracking transcriptions ===

def track_transcription(video_id, video_title, url, mode, lang, user_id=None, status='pending', duration=None, batch_id=None):
    """Record a transcription in the database"""
    transcription = Transcription(
        user_id=user_id,
        video_id=video_id,
        video_title=video_title,
        url=url,
        mode=mode,
        language=lang,
        duration=duration,
        status=status,
        batch_id=batch_id
    )
    
    db.session.add(transcription)
    db.session.commit()
    
    # If there's a user, send them a notification
    if user_id:
        user = User.query.get(user_id)
        if user and user.notification_site:
            notification = Notification(
                user_id=user_id,
                message=f"Transcription for '{video_title}' has been started."
            )
            db.session.add(notification)
            db.session.commit()
    
    return transcription.id

def update_transcription_status(transcription_id, status, error=None):
    """Update the status of a transcription"""
    transcription = Transcription.query.get(transcription_id)
    if not transcription:
        return False
    
    transcription.status = status
    if status == 'completed':
        transcription.completed_at = datetime.now()
    
    db.session.commit()
    
    # If the transcription is complete and the user has notifications enabled, send a notification
    if status == 'completed' and transcription.user_id:
        user = User.query.get(transcription.user_id)
        if user and user.notification_site:
            notification = Notification(
                user_id=transcription.user_id,
                message=f"Transcription for '{transcription.video_title}' is now complete!"
            )
            db.session.add(notification)
            db.session.commit()
    
    return True

def update_daily_stats():
    """Update daily statistics for admin dashboard"""
    today = datetime.now().date()
    
    # Check if we already have stats for today
    daily_stats = DailyStats.query.filter_by(date=today).first()
    
    if not daily_stats:
        daily_stats = DailyStats(date=today)
        db.session.add(daily_stats)
    
    # Update the stats
    today_transcriptions = Transcription.query.filter(
        db.func.date(Transcription.created_at) == today
    )
    
    daily_stats.total_transcriptions = today_transcriptions.count()
    
    # Count by mode
    daily_stats.whisper_count = today_transcriptions.filter_by(mode='whisper').count()
    daily_stats.captions_count = today_transcriptions.filter_by(mode='captions').count()
    daily_stats.auto_count = today_transcriptions.filter_by(mode='auto').count()
    
    # Count batch and playlist
    daily_stats.batch_count = today_transcriptions.filter(Transcription.batch_id.isnot(None)).count()
    
    # Calculate total duration
    daily_stats.total_duration = today_transcriptions.with_entities(
        db.func.sum(Transcription.duration)
    ).scalar() or 0
    
    # Calculate success rate
    completed_count = today_transcriptions.filter_by(status='completed').count()
    daily_stats.success_rate = (completed_count / daily_stats.total_transcriptions * 100) if daily_stats.total_transcriptions > 0 else 0
    
    db.session.commit()
    
    return daily_stats

# === Main Application Routes ===

@app.route('/')
def index():
    """Home page with single video transcription form"""
    return render_template('index.html')

@app.route('/batch')
def batch():
    """Batch processing page"""
    return render_template('batch.html')

@app.route('/playlist')
def playlist():
    """Playlist processing page"""
    return render_template('playlist.html')

# Redirects to user routes with proper URL structure
@app.route('/settings')
def settings_redirect():
    return redirect(url_for('user.settings'))

@app.route('/history')
def history_redirect():
    return redirect(url_for('user.history'))

@app.route('/notifications')
def notifications_redirect():
    return redirect(url_for('user.notifications'))

@app.route('/admin')
def admin_redirect():
    return redirect(url_for('admin.dashboard'))

# === API Routes ===

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
        return jsonify({'error': 'Missing URL parameter'}), 400
    
    # Generate a job ID
    job_id = f"job_{int(time.time())}_{abs(hash(url)) % 10000}"
    
    # Extract video ID from URL
    import re
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if not video_id_match:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
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
    
    return jsonify(response)

@app.route('/job-status/<job_id>')
def job_status(job_id):
    """Get job status"""
    status = job_statuses.get(job_id, {
        'status': 'error',
        'percent': 0,
        'error': 'Job not found'
    })
    
    return jsonify(status)

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

# Ensure the worker thread is started
ensure_worker_thread()

# Update daily stats on startup
update_daily_stats()

# Main entry point
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)