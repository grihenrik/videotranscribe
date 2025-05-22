"""
Simple Whisper service implementation using OpenAI's API.
"""
import os
import json
import tempfile
import subprocess
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def transcribe_audio_file(file_path, language=None):
    """
    Transcribe an audio file using OpenAI's Whisper API.
    
    Args:
        file_path (str): Path to the audio file
        language (str, optional): Language code (ISO 639-1)
        
    Returns:
        dict: Transcription in multiple formats (text, srt, vtt)
    """
    try:
        # Open the audio file
        with open(file_path, "rb") as audio_file:
            # Call OpenAI's Whisper API
            transcription_args = {
                "model": "whisper-1",
                "file": audio_file
            }
            
            # Only add language parameter if it's provided and not None
            if language:
                transcription_args["language"] = language
                
            response = client.audio.transcriptions.create(**transcription_args)
        
        # Get the transcription text
        transcription_text = response.text
        
        # Convert to SRT and VTT formats
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

def download_audio_from_youtube(url, output_path=None):
    """
    Download audio from a YouTube video using yt-dlp.
    
    Args:
        url (str): YouTube URL
        output_path (str, optional): Output directory
        
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
            url
        ]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"yt-dlp failed: {result.stderr}")
        
        # Find the downloaded file
        for file in os.listdir(output_dir):
            if file.endswith(".mp3"):
                return os.path.join(output_dir, file)
        
        raise Exception("No audio file found after download")
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None
        
def extract_videos_from_playlist(playlist_url):
    """
    Extract video URLs from a YouTube playlist.
    
    Args:
        playlist_url (str): YouTube playlist URL
        
    Returns:
        list: List of video URLs in the playlist
    """
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
            
        # Set up yt-dlp options to get playlist info
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--get-id",
            playlist_url
        ]
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"yt-dlp failed: {result.stderr}")
        
        # Extract video IDs and convert to URLs
        video_ids = result.stdout.strip().split('\n')
        video_urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids if video_id]
        
        return video_urls
    except Exception as e:
        print(f"Error extracting playlist videos: {e}")
        return []

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
    seconds = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def format_time_vtt(seconds):
    """Format seconds to WebVTT timestamp (HH:MM:SS.mmm)"""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"