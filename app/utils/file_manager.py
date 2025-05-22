import os
import re
from typing import List, Dict, Any, Optional

import logging

logger = logging.getLogger(__name__)


def convert_to_srt(captions: List[Dict[str, Any]]) -> str:
    """
    Convert captions to SRT format.
    
    Args:
        captions: List of caption entries with start time, end time, and text
        
    Returns:
        SRT formatted string
    """
    srt_lines = []
    
    for i, caption in enumerate(captions, 1):
        # Format start and end times for SRT
        start = caption['start']
        end = caption['end']
        
        # Ensure times are in correct format (HH:MM:SS,mmm)
        start = ensure_srt_timestamp_format(start)
        end = ensure_srt_timestamp_format(end)
        
        # Add entry to SRT
        srt_lines.append(str(i))
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(caption['text'])
        srt_lines.append("")
    
    return "\n".join(srt_lines)


def convert_to_vtt(captions: List[Dict[str, Any]]) -> str:
    """
    Convert captions to WebVTT format.
    
    Args:
        captions: List of caption entries with start time, end time, and text
        
    Returns:
        WebVTT formatted string
    """
    vtt_lines = ["WEBVTT", ""]
    
    for caption in captions:
        # Format start and end times for VTT
        start = caption['start']
        end = caption['end']
        
        # Convert timestamps from SRT to VTT format
        start = convert_timestamp_to_vtt(start)
        end = convert_timestamp_to_vtt(end)
        
        # Add entry to VTT
        vtt_lines.append(f"{start} --> {end}")
        vtt_lines.append(caption['text'])
        vtt_lines.append("")
    
    return "\n".join(vtt_lines)


def ensure_srt_timestamp_format(timestamp: str) -> str:
    """
    Ensure timestamp is in SRT format (HH:MM:SS,mmm).
    
    Args:
        timestamp: Timestamp to format
        
    Returns:
        Formatted timestamp
    """
    # Check if timestamp is already in correct format
    if re.match(r'^\d{2}:\d{2}:\d{2},\d{3}$', timestamp):
        return timestamp
    
    # Convert from "HH:MM:SS.mmm" to "HH:MM:SS,mmm"
    if re.match(r'^\d{2}:\d{2}:\d{2}\.\d{3}$', timestamp):
        return timestamp.replace('.', ',')
    
    # Convert from seconds to "HH:MM:SS,mmm"
    if re.match(r'^\d+(\.\d+)?$', timestamp):
        seconds = float(timestamp)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{int((seconds % 1) * 1000):03d}"
    
    # Return as is if format is unknown
    return timestamp


def convert_timestamp_to_vtt(timestamp: str) -> str:
    """
    Convert a timestamp from SRT to VTT format.
    
    Args:
        timestamp: Timestamp in SRT format "HH:MM:SS,mmm"
        
    Returns:
        Timestamp in VTT format "HH:MM:SS.mmm"
    """
    # Convert from "HH:MM:SS,mmm" to "HH:MM:SS.mmm"
    return timestamp.replace(',', '.')
