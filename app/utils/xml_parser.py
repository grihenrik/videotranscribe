import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

import logging

logger = logging.getLogger(__name__)


def parse_xml_captions(xml_content: str) -> List[Dict[str, Any]]:
    """
    Parse XML captions from YouTube.
    
    Args:
        xml_content: XML content of captions
        
    Returns:
        List of caption entries with start time, end time, and text
    """
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Extract namespace
        namespace = ''
        match = re.match(r'{(.*)}', root.tag)
        if match:
            namespace = '{' + match.group(1) + '}'
        
        # Find all text elements
        captions = []
        
        # Try different formats based on the XML structure
        if namespace:
            # Handle TTML format (with namespace)
            body = root.find(f'.//{namespace}body')
            if body is not None:
                for p in body.findall(f'.//{namespace}p'):
                    begin = p.get('begin')
                    end = p.get('end')
                    text = ''.join(p.itertext()).strip()
                    
                    if begin and end and text:
                        captions.append({
                            'start': convert_timestamp_to_srt(begin),
                            'end': convert_timestamp_to_srt(end),
                            'text': text
                        })
        else:
            # Handle TTML format (without namespace)
            body = root.find('.//body')
            if body is not None:
                for p in body.findall('.//p'):
                    begin = p.get('begin')
                    end = p.get('end')
                    text = ''.join(p.itertext()).strip()
                    
                    if begin and end and text:
                        captions.append({
                            'start': convert_timestamp_to_srt(begin),
                            'end': convert_timestamp_to_srt(end),
                            'text': text
                        })
        
        # If no captions found, try another format
        if not captions:
            # Handle YT format
            for text_element in root.findall('.//text'):
                start = text_element.get('start')
                dur = text_element.get('dur')
                
                if start and dur:
                    start_float = float(start)
                    end_float = start_float + float(dur)
                    
                    start = format_seconds_to_timestamp(start_float)
                    end = format_seconds_to_timestamp(end_float)
                    text = text_element.text or ''
                    
                    captions.append({
                        'start': start,
                        'end': end,
                        'text': text.strip()
                    })
        
        return captions
    except Exception as e:
        logger.error(f"Error parsing XML captions: {str(e)}")
        raise ValueError(f"Failed to parse captions XML: {str(e)}")


def convert_timestamp_to_srt(timestamp: str) -> str:
    """
    Convert a timestamp to SRT format.
    
    Args:
        timestamp: Timestamp in format "HH:MM:SS.mmm" or "S.mmm"
        
    Returns:
        Timestamp in SRT format "HH:MM:SS,mmm"
    """
    # Check if timestamp is in seconds format
    if re.match(r'^\d+(\.\d+)?$', timestamp):
        seconds = float(timestamp)
        return format_seconds_to_timestamp(seconds)
    
    # Convert from "HH:MM:SS.mmm" to "HH:MM:SS,mmm"
    return timestamp.replace('.', ',')


def format_seconds_to_timestamp(seconds: float) -> str:
    """
    Format seconds to timestamp.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Timestamp in format "HH:MM:SS,mmm"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{int((seconds % 1) * 1000):03d}"
