from app import app
import auth  # This imports and initializes the authentication system
import routes  # This imports and registers all routes
import os
import logging
import tempfile
import json
import time
import threading
import queue
import whisper_service

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

# Ensure the worker thread is started
ensure_worker_thread()

# Check if this script is run directly
if __name__ == "__main__":
    # Update any daily stats
    routes.update_daily_stats()
    
    # Start the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)