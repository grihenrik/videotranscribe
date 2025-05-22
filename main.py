from flask import Flask, send_from_directory, request, jsonify, redirect, Response
import os
import logging
import json
import time
import threading
import tempfile
import shutil
import queue
from werkzeug.serving import run_simple

# Import our Whisper service
import whisper_service

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='static')

# Temporary storage for job statuses and transcriptions
job_statuses = {}
transcriptions = {}

# Create a transcription job queue
transcription_queue = queue.Queue()
MAX_CONCURRENT_JOBS = 2  # Limit concurrent jobs
active_jobs = 0
queue_lock = threading.Lock()

# Rate limiting
OPENAI_CALLS_PER_MINUTE = 15  # Limit OpenAI API calls to 15 per minute
openai_call_timestamps = []
rate_limit_lock = threading.Lock()

# Batch processing
batch_jobs = {}  # Store batches by batch_id

# Flag to track if worker thread is running
worker_running = False

# Create a directory for temporary files
TEMP_DIR = os.path.join(tempfile.gettempdir(), "youtube_transcription")
os.makedirs(TEMP_DIR, exist_ok=True)

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

# Start the worker thread if not already running
def ensure_worker_thread():
    """Ensure the worker thread is running"""
    global worker_running
    if not worker_running:
        worker_thread = threading.Thread(target=process_queue)
        worker_thread.daemon = True
        worker_thread.start()
        worker_running = True
        logger.info("Started transcription queue worker thread")

def process_queue():
    """Process jobs from the transcription queue"""
    global active_jobs
    while True:
        try:
            # Get the next job from the queue
            job_data = transcription_queue.get(block=True, timeout=60)
            
            # Process the job
            with queue_lock:
                active_jobs += 1
            
            process_transcription(**job_data)
            
            # Mark the job as done
            with queue_lock:
                active_jobs -= 1
                
            # Mark the queue task as done
            transcription_queue.task_done()
            
        except queue.Empty:
            # No jobs for 60 seconds, continue waiting
            pass
        except Exception as e:
            logger.error(f"Error in queue processing: {e}")
            # Reduce active job count on error
            with queue_lock:
                active_jobs = max(0, active_jobs - 1)

# API endpoints for transcription
@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """API endpoint for transcription"""
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
    
    # Get transcription mode and language
    mode = data.get("mode", "auto")
    lang = data.get("lang", "en")
    
    # Store job status (initially queued)
    job_statuses[job_id] = {
        "status": "queued",
        "percent": 5,
        "video_id": video_id,
        "mode": mode,
        "lang": lang,
        "queued_at": time.time()
    }
    
    # Create job data for the queue
    job_data = {
        "job_id": job_id,
        "url": url,
        "mode": mode,
        "lang": lang,
        "video_id": video_id
    }
    
    # Add job to queue
    transcription_queue.put(job_data)
    
    # Ensure worker thread is running
    ensure_worker_thread()
    
    # Return response
    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "video_id": video_id,
        "message": "Transcription queued",
        "download_links": {
            "txt": f"/api/download/{job_id}?format=txt",
            "srt": f"/api/download/{job_id}?format=srt",
            "vtt": f"/api/download/{job_id}?format=vtt"
        }
    })

def check_rate_limit():
    """
    Check if we've hit the OpenAI API rate limit.
    Returns True if we should wait, False if we can proceed.
    """
    with rate_limit_lock:
        # Remove timestamps older than 1 minute
        current_time = time.time()
        one_minute_ago = current_time - 60
        global openai_call_timestamps
        openai_call_timestamps = [t for t in openai_call_timestamps if t > one_minute_ago]
        
        # Check if we've hit the rate limit
        if len(openai_call_timestamps) >= OPENAI_CALLS_PER_MINUTE:
            return True
        
        # Add current timestamp
        openai_call_timestamps.append(current_time)
        return False

def wait_for_rate_limit():
    """Wait until we're under the rate limit"""
    while check_rate_limit():
        # If we hit the rate limit, wait and then try again
        logger.info("Rate limit hit, waiting before processing next job...")
        time.sleep(5)

def process_transcription(job_id, url, mode, lang, video_id, batch_id=None):
    """Process a single transcription job"""
    job_dir = None
    try:
        # Update status to downloading
        job_statuses[job_id]["status"] = "downloading"
        job_statuses[job_id]["percent"] = 20
        
        # Create job directory
        job_dir = os.path.join(TEMP_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # Download audio
        logger.info(f"Downloading audio for job {job_id}")
        audio_file = whisper_service.download_audio_from_youtube(url, job_dir)
        
        if not audio_file:
            raise Exception("Failed to download audio")
        
        # Update status to transcribing
        job_statuses[job_id]["status"] = "transcribing"
        job_statuses[job_id]["percent"] = 50
        
        # Check rate limit before calling OpenAI API
        wait_for_rate_limit()
        
        # Transcribe with Whisper
        logger.info(f"Transcribing audio for job {job_id}")
        result = whisper_service.transcribe_audio_file(audio_file, lang)
        
        if not result:
            raise Exception("Failed to transcribe audio")
        
        # Save transcription files
        transcriptions[job_id] = result
        
        # Update status to complete
        job_statuses[job_id]["status"] = "complete"
        job_statuses[job_id]["percent"] = 100
        job_statuses[job_id]["completed_at"] = time.time()
        
        logger.info(f"Transcription complete for job {job_id}")
        
        # Update batch status if part of a batch
        if batch_id and batch_id in batch_jobs:
            batch_jobs[batch_id]["completed"] += 1
            if batch_jobs[batch_id]["completed"] == batch_jobs[batch_id]["total"]:
                logger.info(f"Batch {batch_id} complete")
                batch_jobs[batch_id]["status"] = "complete"
        
    except Exception as e:
        logger.error(f"Error in transcription job {job_id}: {e}")
        # Update status to error
        job_statuses[job_id]["status"] = "error"
        job_statuses[job_id]["error"] = str(e)
        job_statuses[job_id]["percent"] = 0
        
        # Update batch status if part of a batch
        if batch_id and batch_id in batch_jobs:
            batch_jobs[batch_id]["failed"] += 1
    finally:
        # Clean up temporary files (in production, keep them longer)
        try:
            if job_dir and os.path.exists(job_dir):
                shutil.rmtree(job_dir)
        except Exception as e:
            logger.error(f"Error cleaning up job directory: {e}")

# Batch processing endpoint
@app.route('/api/batch', methods=['POST'])
def batch_transcribe():
    """API endpoint for batch transcription"""
    data = request.json
    logger.info(f"Batch transcription request received: {data}")
    
    # Extract URLs, mode, and language
    urls = data.get("urls", [])
    mode = data.get("mode", "auto")
    lang = data.get("lang", "en")
    
    if not urls or not isinstance(urls, list):
        return jsonify({"error": "Invalid URLs provided"}), 400
    
    # Generate batch ID
    batch_id = f"batch-{int(time.time())}"
    
    # Create batch record
    batch_jobs[batch_id] = {
        "status": "processing",
        "total": len(urls),
        "completed": 0,
        "failed": 0,
        "created_at": time.time(),
        "job_ids": []
    }
    
    # Process each URL in the batch
    for url in urls:
        # Generate job ID
        job_id = f"job-{int(time.time())}-{len(batch_jobs[batch_id]['job_ids'])}"
        
        # Extract video ID from URL
        video_id = "demo"
        if "v=" in url:
            video_id = url.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
        
        # Store job status (initially queued)
        job_statuses[job_id] = {
            "status": "queued",
            "percent": 5,
            "video_id": video_id,
            "mode": mode,
            "lang": lang,
            "queued_at": time.time(),
            "batch_id": batch_id
        }
        
        # Add job ID to batch
        batch_jobs[batch_id]["job_ids"].append(job_id)
        
        # Create job data for the queue
        job_data = {
            "job_id": job_id,
            "url": url,
            "mode": mode,
            "lang": lang,
            "video_id": video_id,
            "batch_id": batch_id
        }
        
        # Add job to queue
        transcription_queue.put(job_data)
    
    # Ensure worker thread is running
    ensure_worker_thread()
    
    # Return response
    return jsonify({
        "batch_id": batch_id,
        "status": "processing",
        "total": len(urls),
        "message": f"Batch transcription started with {len(urls)} videos",
        "jobs": batch_jobs[batch_id]["job_ids"]
    })

# Batch status endpoint
@app.route('/api/batch/<batch_id>/status')
def batch_status(batch_id):
    """Get batch status"""
    if batch_id not in batch_jobs:
        return jsonify({"error": "Batch not found"}), 404
    
    batch = batch_jobs[batch_id]
    
    # Calculate overall progress
    if batch["total"] > 0:
        total_progress = 0
        for job_id in batch["job_ids"]:
            if job_id in job_statuses:
                total_progress += job_statuses[job_id]["percent"]
        
        overall_percent = int(total_progress / batch["total"])
    else:
        overall_percent = 0
    
    return jsonify({
        "status": batch["status"],
        "total": batch["total"],
        "completed": batch["completed"],
        "failed": batch["failed"],
        "percent": overall_percent,
        "jobs": batch["job_ids"]
    })

@app.route('/api/job/<job_id>/status')
def job_status(job_id):
    """Get job status"""
    if job_id not in job_statuses:
        return jsonify({"error": "Job not found"}), 404
    
    status = job_statuses[job_id]
    response = {
        "status": status["status"],
        "percent": status["percent"],
        "error": status.get("error")
    }
    
    # Include batch info if part of a batch
    if "batch_id" in status:
        response["batch_id"] = status["batch_id"]
    
    return jsonify(response)

@app.route('/api/download/<job_id>')
def download(job_id):
    """Download transcription endpoint"""
    if job_id not in job_statuses:
        return jsonify({"error": "Job not found"}), 404
    
    # Check if job is complete
    status = job_statuses[job_id]
    if status["status"] != "complete":
        return jsonify({"error": "Transcription not complete"}), 400
    
    # Get transcription data
    if job_id not in transcriptions:
        return jsonify({"error": "Transcription data not found"}), 404
    
    format_type = request.args.get('format', 'txt')
    data = transcriptions[job_id]
    
    # Return appropriate format
    if format_type == 'txt':
        return Response(
            data["text"],
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment;filename={status['video_id']}.txt"}
        )
    elif format_type == 'srt':
        return Response(
            data["srt"],
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment;filename={status['video_id']}.srt"}
        )
    elif format_type == 'vtt':
        return Response(
            data["vtt"],
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment;filename={status['video_id']}.vtt"}
        )
    else:
        return jsonify({"error": "Invalid format"}), 400

# Clean up old jobs (would be a scheduled task in production)
def cleanup_old_jobs():
    """Clean up old jobs and transcriptions"""
    current_time = time.time()
    cutoff_time = current_time - 3600  # 1 hour
    
    for job_id in list(job_statuses.keys()):
        job_time = int(job_id.split("-")[1])
        if job_time < cutoff_time:
            if job_id in job_statuses:
                del job_statuses[job_id]
            if job_id in transcriptions:
                del transcriptions[job_id]

# This is the app that Gunicorn will use
application = app

if __name__ == '__main__':
    # Run with Werkzeug development server
    run_simple('0.0.0.0', 5000, app, use_reloader=True, use_debugger=True)
