"""
Utility functions for working with YouTube videos.
"""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from a URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID or None if not found
    """
    if not url:
        return None
    
    # Regular expressions for different YouTube URL formats
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',  # Standard and short URLs
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',  # Embedded videos
        r'youtube\.com/v/([a-zA-Z0-9_-]{11})',  # Legacy URLs
        r'youtube\.com/user/\w+/\w+/([a-zA-Z0-9_-]{11})',  # User uploads
        r'youtube\.com/\w+/\w+/([a-zA-Z0-9_-]{11})'  # Other formats
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def parse_time_parameter(time_param: Optional[str]) -> Optional[float]:
    """
    Parse a YouTube time parameter (t=XX) into seconds.
    
    Args:
        time_param: Time parameter from URL (e.g., '1h2m3s', '123', '1:23')
        
    Returns:
        Time in seconds or None if invalid
    """
    if not time_param:
        return None
    
    try:
        # Check if it's a simple number of seconds
        if time_param.isdigit():
            return float(time_param)
        
        # Check for HH:MM:SS format
        if ':' in time_param:
            parts = time_param.split(':')
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        
        # Check for 1h2m3s format
        hours = re.search(r'(\d+)h', time_param)
        minutes = re.search(r'(\d+)m', time_param)
        seconds = re.search(r'(\d+)s', time_param)
        
        total_seconds = 0
        if hours:
            total_seconds += int(hours.group(1)) * 3600
        if minutes:
            total_seconds += int(minutes.group(1)) * 60
        if seconds:
            total_seconds += int(seconds.group(1))
        
        return float(total_seconds) if total_seconds > 0 else None
    
    except Exception as e:
        logger.error(f"Error parsing time parameter: {e}")
        return None

def extract_video_info(url: str) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """
    Extract video ID and time parameters from YouTube URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        Tuple of (video_id, start_time, end_time)
    """
    video_id = extract_video_id(url)
    
    if not video_id:
        return None, None, None
    
    # Extract start time
    start_time_match = re.search(r'[?&]t=([^&]+)', url) or re.search(r'[?&]start=([^&]+)', url)
    start_time = parse_time_parameter(start_time_match.group(1)) if start_time_match else None
    
    # Extract end time
    end_time_match = re.search(r'[?&]end=([^&]+)', url)
    end_time = parse_time_parameter(end_time_match.group(1)) if end_time_match else None
    
    return video_id, start_time, end_time