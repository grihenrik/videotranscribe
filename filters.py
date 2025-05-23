from datetime import datetime
import time

def timeago(dt, default="just now"):
    """
    Returns a human-readable relative timestamp.
    For example: "2 days ago", "just now", "1 hour ago"
    
    Args:
        dt: A datetime object or timestamp
        default: The string to return if dt is None
    
    Returns:
        A string describing the relative time difference
    """
    if dt is None:
        return default
        
    if isinstance(dt, int):
        dt = datetime.fromtimestamp(dt)
        
    now = datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    minutes = int(seconds / 60)
    hours = int(minutes / 60)
    days = int(hours / 24)
    
    if seconds < 10:
        return "just now"
    elif seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif dt.year == now.year:
        return dt.strftime('%b %d')
    else:
        return dt.strftime('%b %d, %Y')