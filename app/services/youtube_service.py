import os
import re
import asyncio
import logging
import tempfile
from typing import Optional, Dict, Any, Tuple
import xml.etree.ElementTree as ET

import yt_dlp

from app.core.config import settings
from app.utils.xml_parser import parse_xml_captions
from app.utils.file_manager import convert_to_vtt, convert_to_srt

logger = logging.getLogger(__name__)


class YouTubeService:
    """Service for interacting with YouTube videos."""
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from a YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            YouTube video ID or None if not found
        """
        # Patterns for YouTube URLs
        patterns = [
            r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """
        Get information about a YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary with video information
        """
        logger.info(f"Getting info for video: {video_id}")
        
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'quiet': True,
        }
        
        loop = asyncio.get_event_loop()
        
        def _extract_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        
        # Run yt_dlp in a thread pool executor to avoid blocking
        info = await loop.run_in_executor(None, _extract_info)
        
        if not info:
            logger.error(f"Could not get info for video {video_id}")
            raise ValueError(f"Could not get info for video {video_id}")
        
        return info
    
    async def download_captions(self, video_id: str, lang: str = "en") -> Optional[str]:
        """
        Download captions for a YouTube video.
        
        Args:
            video_id: YouTube video ID
            lang: Language code
            
        Returns:
            Captions XML content or None if not found
        """
        logger.info(f"Downloading captions for video {video_id} in language {lang}")
        
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [lang],
            'subtitlesformat': 'ttml',
            'quiet': True,
            'outtmpl': os.path.join(tempfile.gettempdir(), '%(id)s'),
        }
        
        loop = asyncio.get_event_loop()
        
        def _download_captions():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                
                # Check if subtitles are available
                if not info.get('subtitles') and not info.get('automatic_captions'):
                    logger.warning(f"No captions found for video {video_id}")
                    return None
                
                # Try to download subtitles
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
                
                # Check for downloaded subtitle files
                subtitle_files = []
                base_name = os.path.join(tempfile.gettempdir(), video_id)
                
                # Check manual subtitles first
                for ext in [f'.{lang}.ttml', f'.{lang}.vtt', f'.{lang}.srt']:
                    if os.path.exists(base_name + ext):
                        subtitle_files.append(base_name + ext)
                
                # Then check auto-generated
                if not subtitle_files:
                    for ext in [f'.{lang}.ttml', f'.{lang}.vtt', f'.{lang}.srt']:
                        if os.path.exists(base_name + ext):
                            subtitle_files.append(base_name + ext)
                
                if not subtitle_files:
                    return None
                
                # Read subtitle file
                with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                    return f.read()
        
        # Run yt_dlp in a thread pool executor to avoid blocking
        captions = await loop.run_in_executor(None, _download_captions)
        
        return captions
    
    async def download_audio(self, video_id: str) -> str:
        """
        Download audio from a YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Path to downloaded audio file
        """
        logger.info(f"Downloading audio for video {video_id}")
        
        # Create temp directory if it doesn't exist
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        
        # Output file path
        output_path = os.path.join(settings.TEMP_DIR, f"{video_id}.mp3")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(settings.TEMP_DIR, f"{video_id}"),
            'quiet': True,
        }
        
        loop = asyncio.get_event_loop()
        
        def _download_audio():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
                return output_path
        
        # Run yt_dlp in a thread pool executor to avoid blocking
        file_path = await loop.run_in_executor(None, _download_audio)
        
        if not os.path.exists(file_path):
            logger.error(f"Failed to download audio for video {video_id}")
            raise ValueError(f"Failed to download audio for video {video_id}")
        
        return file_path
    
    async def process_captions(self, captions_content: str) -> Dict[str, str]:
        """
        Process captions into different formats.
        
        Args:
            captions_content: Captions content (XML, VTT, or SRT)
            
        Returns:
            Dictionary with captions in different formats (text, srt, vtt)
        """
        # Determine format based on content
        if captions_content.strip().startswith('<?xml') or captions_content.strip().startswith('<tt'):
            # Process XML captions
            parsed_captions = parse_xml_captions(captions_content)
            
            # Generate output in different formats
            text = "\n".join([f"{entry['text']}" for entry in parsed_captions])
            srt = convert_to_srt(parsed_captions)
            vtt = convert_to_vtt(parsed_captions)
            
        elif captions_content.strip().startswith('WEBVTT'):
            # Process VTT captions
            # Convert VTT to our internal format
            lines = captions_content.strip().split('\n')
            parsed_captions = []
            current_entry = None
            
            for line in lines:
                if line.strip() == 'WEBVTT' or not line.strip():
                    continue
                elif '-->' in line:
                    # Time line
                    if current_entry:
                        parsed_captions.append(current_entry)
                    
                    start, end = line.split('-->')
                    current_entry = {
                        'start': start.strip(),
                        'end': end.strip(),
                        'text': ''
                    }
                elif current_entry:
                    # Text line
                    current_entry['text'] += line.strip() + ' '
            
            # Add the last entry
            if current_entry:
                parsed_captions.append(current_entry)
            
            # Generate output in different formats
            text = "\n".join([entry['text'].strip() for entry in parsed_captions])
            srt = convert_to_srt(parsed_captions)
            vtt = captions_content  # Already in VTT format
            
        elif re.match(r'^\d+\s+\d{2}:\d{2}:\d{2},\d{3}', captions_content.strip()):
            # Process SRT captions
            # Convert SRT to our internal format
            blocks = re.split(r'\n\s*\n', captions_content.strip())
            parsed_captions = []
            
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    # Extract index, timestamp, and text
                    index = lines[0].strip()
                    timestamp = lines[1].strip()
                    text = ' '.join([line.strip() for line in lines[2:]])
                    
                    # Parse timestamp
                    match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', timestamp)
                    if match:
                        start, end = match.groups()
                        parsed_captions.append({
                            'start': start,
                            'end': end,
                            'text': text
                        })
            
            # Generate output in different formats
            text = "\n".join([entry['text'] for entry in parsed_captions])
            srt = captions_content  # Already in SRT format
            vtt = convert_to_vtt(parsed_captions)
            
        else:
            # Unknown format, treat as plain text
            text = captions_content
            
            # Create a simple entry for SRT and VTT
            parsed_captions = [{
                'start': '00:00:00,000',
                'end': '99:59:59,999',
                'text': text
            }]
            
            srt = convert_to_srt(parsed_captions)
            vtt = convert_to_vtt(parsed_captions)
        
        return {
            "text": text,
            "srt": srt,
            "vtt": vtt
        }
