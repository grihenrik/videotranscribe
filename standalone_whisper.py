"""
Standalone Whisper service implementation for the simple server.
This version doesn't depend on FastAPI or pydantic-settings.
"""
import os
import math
import json
import tempfile
import subprocess
import re
from openai import OpenAI

# OpenAI Whisper API has a 25MB file size limit
WHISPER_MAX_FILE_SIZE = 25 * 1024 * 1024
CHUNK_TARGET_SIZE = 20 * 1024 * 1024


def _get_audio_duration(file_path):
    """Get audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr or result.stdout}")
    return float(result.stdout.strip())


def _split_audio_into_chunks(file_path, output_dir):
    """Split audio file into chunks under 25MB using ffmpeg."""
    file_size = os.path.getsize(file_path)
    duration = _get_audio_duration(file_path)
    if duration <= 0:
        raise ValueError("Invalid audio duration")

    bytes_per_second = file_size / duration
    chunk_duration_sec = CHUNK_TARGET_SIZE / bytes_per_second
    num_chunks = max(1, math.ceil(duration / chunk_duration_sec))
    actual_chunk_duration = duration / num_chunks

    chunk_paths = []
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    ext = os.path.splitext(file_path)[1] or ".mp3"

    for i in range(num_chunks):
        start_time = i * actual_chunk_duration
        chunk_path = os.path.join(output_dir, f"{base_name}_chunk{i:03d}{ext}")

        cmd = [
            "ffmpeg", "-y", "-i", file_path,
            "-ss", str(start_time), "-t", str(actual_chunk_duration),
            "-acodec", "copy", "-vn", chunk_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg split failed: {result.stderr}")

        chunk_size = os.path.getsize(chunk_path)
        if chunk_size > WHISPER_MAX_FILE_SIZE:
            mp3_path = chunk_path.replace(ext, ".mp3")
            subprocess.run(
                ["ffmpeg", "-y", "-i", chunk_path, "-acodec", "libmp3lame", "-b:a", "128k", mp3_path],
                capture_output=True, timeout=300
            )
            os.remove(chunk_path)
            chunk_path = mp3_path

        chunk_paths.append(chunk_path)
    return chunk_paths


def _transcribe_single_file(file_path, client, language):
    """Transcribe a single file and return the text."""
    with open(file_path, "rb") as audio_file:
        args = {"model": "whisper-1", "file": audio_file}
        if language:
            args["language"] = language
        response = client.audio.transcriptions.create(**args)
    return response.text or ""

def get_proxy_config():
    """
    Get proxy configuration from environment variables or proxy_config.py.
    
    Returns:
        str or None: Proxy URL if configured, None otherwise
    """
    # First try to import from proxy_config.py
    try:
        from proxy_config import get_proxy_url
        proxy = get_proxy_url()
        if proxy:
            return proxy
    except ImportError:
        pass
    
    # Fallback to environment variables
    proxy = (
        os.getenv('YOUTUBE_PROXY') or
        os.getenv('HTTP_PROXY') or 
        os.getenv('HTTPS_PROXY') or
        os.getenv('http_proxy') or
        os.getenv('https_proxy')
    )
    
    return proxy

def get_openai_client():
    """Get OpenAI client with proper API key handling."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your environment variables or .env file")
    return OpenAI(api_key=api_key)

def extract_playlist_videos(playlist_url, proxy=None, proxy_options=None):
    """
    Extract individual video URLs and titles from a YouTube playlist.
    
    Args:
        playlist_url (str): YouTube playlist URL
        proxy (str, optional): Proxy URL (e.g., 'http://proxy:port' or 'socks5://proxy:port')
        proxy_options (list, optional): Additional yt-dlp options for advanced proxy handling
        
    Returns:
        list: List of dictionaries with 'url', 'title', and 'id' for each video
    """
    try:
        # Use yt-dlp to extract playlist information
        cmd = [
            'yt-dlp',
            '--flat-playlist',
            '--print', '%(id)s|%(title)s|%(webpage_url)s',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--extractor-retries', '3',
            '--socket-timeout', '30',
            '--sleep-interval', '1',
            '--max-sleep-interval', '3'
        ]
        
        # Add advanced proxy options if provided (from proxy manager)
        if proxy_options:
            cmd.extend(proxy_options)
        # Add basic proxy if provided
        elif proxy:
            cmd.extend(['--proxy', proxy])
            
        cmd.append(playlist_url)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|', 2)
                if len(parts) >= 3:
                    video_id = parts[0]
                    title = parts[1]
                    url = parts[2]
                    
                    # Clean up title for filename usage
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    safe_title = safe_title.strip()
                    
                    videos.append({
                        'id': video_id,
                        'title': safe_title,
                        'url': url
                    })
        
        return videos
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        
        # Check for specific YouTube errors
        if "does not exist" in error_msg:
            raise Exception(f"Playlist not found or is private. Please check: 1) Playlist URL is correct, 2) Playlist is public, 3) You have access to view it.")
        elif "private" in error_msg.lower():
            raise Exception(f"Playlist is private. Please make sure the playlist is public or you have access to it.")
        elif "unavailable" in error_msg.lower():
            raise Exception(f"Playlist is unavailable. This might be due to geographic restrictions or the playlist being deleted.")
        else:
            raise Exception(f"Failed to extract playlist videos: {error_msg}")
    except Exception as e:
        raise Exception(f"Error extracting playlist: {str(e)}")
        
        videos = []
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|', 2)
                if len(parts) >= 3:
                    video_id = parts[0]
                    title = parts[1]
                    url = parts[2]
                    
                    # Clean up title for filename usage
                    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
                    safe_title = safe_title.strip()
                    
                    videos.append({
                        'id': video_id,
                        'title': safe_title,
                        'url': url
                    })
        
        return videos
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to extract playlist videos: {e.stderr}")
    except Exception as e:
        raise Exception(f"Error extracting playlist: {str(e)}")

def is_playlist_url(url):
    """
    Check if a URL contains a playlist parameter.
    
    Args:
        url (str): YouTube URL to check
        
    Returns:
        bool: True if URL contains playlist parameter
    """
    return 'list=' in url or '/playlist?' in url

def transcribe_audio_file(file_path, language=None):
    """
    Transcribe an audio file using OpenAI's Whisper API.
    Files larger than 25MB are automatically split into chunks.
    
    Args:
        file_path (str): Path to the audio file
        language (str, optional): Language code (ISO 639-1)
        
    Returns:
        dict: Transcription in multiple formats (text, srt, vtt)
    """
    try:
        client = get_openai_client()
        file_size = os.path.getsize(file_path)

        if file_size <= WHISPER_MAX_FILE_SIZE:
            transcription_text = _transcribe_single_file(file_path, client, language)
        else:
            print(f"File {file_size / (1024*1024):.1f}MB exceeds 25MB limit, chunking for Whisper API")
            with tempfile.TemporaryDirectory() as chunk_dir:
                chunk_paths = _split_audio_into_chunks(file_path, chunk_dir)
                print(f"Split into {len(chunk_paths)} chunks")
                texts = []
                for chunk_path in chunk_paths:
                    text = _transcribe_single_file(chunk_path, client, language)
                    texts.append(text)
                transcription_text = "\n\n".join(t.strip() for t in texts if t.strip())

        srt_content = convert_to_srt(transcription_text)
        vtt_content = convert_to_vtt(transcription_text)

        return {
            "text": transcription_text,
            "srt": srt_content,
            "vtt": vtt_content
        }
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None

def download_audio_from_youtube(url, output_path=None, proxy=None, proxy_options=None):
    """
    Download audio from a YouTube video using yt-dlp.
    
    Args:
        url (str): YouTube URL
        output_path (str, optional): Output directory
        proxy (str, optional): Proxy URL (e.g., 'http://proxy:port' or 'socks5://proxy:port')
        proxy_options (list, optional): Additional yt-dlp options for advanced proxy handling
        
    Returns:
        str: Path to downloaded audio file
    """
    try:
        # Create a temporary directory if no output path provided
        if output_path is None:
            output_dir = tempfile.mkdtemp()
        else:
            output_dir = output_path
            
        # Prepare the output template
        output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
        
        # Set up yt-dlp options for audio extraction
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",  # Best quality
            "--output", output_template,
            "--no-playlist",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--extractor-retries", "3",
            "--socket-timeout", "30",
            "--sleep-interval", "1",
            "--max-sleep-interval", "3"
        ]
        
        # Add advanced proxy options if provided (from proxy manager)
        if proxy_options:
            cmd.extend(proxy_options)
        # Add basic proxy if provided
        elif proxy:
            cmd.extend(["--proxy", proxy])
            
        cmd.append(url)
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            
            # Check for specific YouTube errors
            if "private" in error_msg.lower():
                raise Exception(f"Video is private or unavailable.")
            elif "not available" in error_msg.lower():
                raise Exception(f"Video is not available. This might be due to geographic restrictions.")
            elif "copyright" in error_msg.lower():
                raise Exception(f"Video is blocked due to copyright restrictions.")
            else:
                raise Exception(f"yt-dlp failed: {error_msg}")
        
        # Find the downloaded file
        for file in os.listdir(output_dir):
            if file.endswith(".mp3"):
                return os.path.join(output_dir, file)
        
        raise Exception("No audio file found after download")
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

def convert_to_srt(text, chunk_duration=5):
    """
    Convert plain text to SRT format.
    
    Args:
        text (str): Plain text transcription
        chunk_duration (int): Duration of each subtitle chunk in seconds
        
    Returns:
        str: SRT formatted text
    """
    # Split text into chunks (simple implementation)
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= 10:  # ~10 words per chunk
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    # Generate SRT
    srt = ""
    for i, chunk in enumerate(chunks):
        start_time = i * chunk_duration
        end_time = (i + 1) * chunk_duration
        
        # Format start and end times (HH:MM:SS,mmm)
        start_formatted = format_time_srt(start_time)
        end_formatted = format_time_srt(end_time)
        
        srt += f"{i + 1}\n{start_formatted} --> {end_formatted}\n{chunk}\n\n"
    
    return srt

def convert_to_vtt(text, chunk_duration=5):
    """
    Convert plain text to WebVTT format.
    
    Args:
        text (str): Plain text transcription
        chunk_duration (int): Duration of each subtitle chunk in seconds
        
    Returns:
        str: WebVTT formatted text
    """
    # Start with WebVTT header
    vtt = "WEBVTT\n\n"
    
    # Split text into chunks (simple implementation)
    words = text.split()
    chunks = []
    current_chunk = []
    
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= 10:  # ~10 words per chunk
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    # Generate VTT cues
    for i, chunk in enumerate(chunks):
        start_time = i * chunk_duration
        end_time = (i + 1) * chunk_duration
        
        # Format start and end times (HH:MM:SS.mmm)
        start_formatted = format_time_vtt(start_time)
        end_formatted = format_time_vtt(end_time)
        
        vtt += f"{start_formatted} --> {end_formatted}\n{chunk}\n\n"
    
    return vtt

def format_time_srt(seconds):
    """Format seconds to SRT timestamp (HH:MM:SS,mmm)"""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def format_time_vtt(seconds):
    """Format seconds to WebVTT timestamp (HH:MM:SS.mmm)"""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
