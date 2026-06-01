"""
Simple Whisper service implementation using OpenAI's API.
"""

import os
import math
import logging
import tempfile
import subprocess
from typing import Optional
from openai import OpenAI
from app.core.config import settings, settings_helper

logger = logging.getLogger(__name__)

# Use configured Whisper max file size
WHISPER_MAX_FILE_SIZE = settings_helper.get_whisper_max_file_size_bytes()
# Target chunk size (20MB) to stay safely under the limit
CHUNK_TARGET_SIZE = 20 * 1024 * 1024


def _get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr or result.stdout}")
    return float(result.stdout.strip())


def _split_audio_into_chunks(file_path: str, output_dir: str) -> list[str]:
    """
    Split audio file into chunks under 25MB using ffmpeg.
    Returns list of paths to chunk files.
    """
    file_size = os.path.getsize(file_path)
    duration = _get_audio_duration(file_path)
    if duration <= 0:
        raise ValueError("Invalid audio duration")

    # Bytes per second - used to estimate chunk duration for target size
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
            "ffmpeg",
            "-y",  # Overwrite
            "-i",
            file_path,
            "-ss",
            str(start_time),
            "-t",
            str(actual_chunk_duration),
            "-acodec",
            "copy",  # No re-encode for speed
            "-vn",  # No video
            chunk_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg split failed: {result.stderr}")

        chunk_size = os.path.getsize(chunk_path)
        if chunk_size > WHISPER_MAX_FILE_SIZE:
            # Chunk still too large (e.g. variable bitrate), re-encode to MP3
            logger.warning(
                f"Chunk {i} is {chunk_size/1e6:.1f}MB, re-encoding to compress"
            )
            mp3_path = chunk_path.replace(ext, ".mp3")
            cmd_compress = [
                "ffmpeg",
                "-y",
                "-i",
                chunk_path,
                "-acodec",
                "libmp3lame",
                "-b:a",
                "128k",
                mp3_path,
            ]
            subprocess.run(cmd_compress, capture_output=True, timeout=300)
            os.remove(chunk_path)
            chunk_path = mp3_path

        chunk_paths.append(chunk_path)

    return chunk_paths


def _transcribe_single_file(file_path: str, client, language: Optional[str]) -> str:
    """Transcribe a single file and return the text."""
    with open(file_path, "rb") as audio_file:
        args = {"model": "whisper-1", "file": audio_file}
        if language:
            args["language"] = language
        response = client.audio.transcriptions.create(**args)
    return response.text or ""


# Initialize OpenAI client using settings configuration
def get_openai_client():
    """Get OpenAI client with proper API key handling."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Please set OPENAI_API_KEY in your environment variables or .env file"
        )
    return OpenAI(api_key=api_key)


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
        file_size = os.path.getsize(file_path)
        client = get_openai_client()

        if file_size <= WHISPER_MAX_FILE_SIZE:
            # File fits - transcribe directly
            transcription_text = _transcribe_single_file(file_path, client, language)
        else:
            # File too large - chunk and transcribe each part
            logger.info(
                f"File {file_size / (1024*1024):.1f}MB exceeds 25MB limit, chunking for Whisper API"
            )
            with tempfile.TemporaryDirectory() as chunk_dir:
                chunk_paths = _split_audio_into_chunks(file_path, chunk_dir)
                logger.info(f"Split into {len(chunk_paths)} chunks")
                texts = []
                for i, chunk_path in enumerate(chunk_paths):
                    text = _transcribe_single_file(chunk_path, client, language)
                    texts.append(text)
                transcription_text = "\n\n".join(t.strip() for t in texts if t.strip())

        # Convert to SRT and VTT formats
        srt_content = convert_to_srt(transcription_text)
        vtt_content = convert_to_vtt(transcription_text)

        return {"text": transcription_text, "srt": srt_content, "vtt": vtt_content}
    except Exception as e:
        logger.error(f"Error transcribing audio {file_path}: {e}", exc_info=True)
        raise  # Re-raise so caller gets the actual error message


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
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",  # Best quality
            "--output",
            output_template,
            "--no-playlist",
            url,
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
    Extract video URLs and titles from a YouTube playlist.

    Args:
        playlist_url (str): YouTube playlist URL

    Returns:
        dict: Dictionary with playlist info, video URLs and titles
    """
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()

        # First get the playlist title
        title_cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--print",
            "%(playlist_title)s",
            "--playlist-items",
            "1",
            playlist_url,
        ]

        title_result = subprocess.run(title_cmd, capture_output=True, text=True)
        playlist_title = title_result.stdout.strip() or "YouTube Playlist"

        # Get video IDs, titles, and URLs
        info_cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--print",
            "%(id)s:%(title)s",
            playlist_url,
        ]

        info_result = subprocess.run(info_cmd, capture_output=True, text=True)

        if info_result.returncode != 0:
            raise Exception(f"yt-dlp failed: {info_result.stderr}")

        # Parse the output to get video IDs and titles
        videos = []
        video_lines = info_result.stdout.strip().split("\n")

        for line in video_lines:
            if ":" in line:
                parts = line.split(":", 1)  # Split only on first colon
                video_id = parts[0].strip()
                video_title = parts[1].strip()

                if video_id:
                    videos.append(
                        {
                            "id": video_id,
                            "title": video_title,
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                        }
                    )

        return {"title": playlist_title, "videos": videos, "count": len(videos)}
    except Exception as e:
        print(f"Error extracting playlist videos: {e}")
        return {"title": "YouTube Playlist", "videos": [], "count": 0}


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
