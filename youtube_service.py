import yt_dlp
import os
import tempfile
import re
from urllib.parse import urlparse, parse_qs

class YouTubeService:
    """Service for extracting YouTube video information and audio"""
    
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
        }
    
    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        # Handle various YouTube URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def extract_playlist_id(self, url):
        """Extract playlist ID from YouTube URL"""
        parsed_url = urlparse(url)
        if 'playlist' in parsed_url.query:
            query_params = parse_qs(parsed_url.query)
            return query_params.get('list', [None])[0]
        return None
    
    def get_video_info(self, url):
        """Get video metadata without downloading"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'description': info.get('description'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                }
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")
    
    def get_playlist_videos(self, playlist_url, max_videos=50):
        """Get list of videos from a playlist"""
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'playlistend': max_videos
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
                videos = []
                for entry in playlist_info.get('entries', []):
                    if entry:
                        videos.append({
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                            'duration': entry.get('duration'),
                        })
                
                return {
                    'title': playlist_info.get('title'),
                    'videos': videos,
                    'total_count': len(videos)
                }
        except Exception as e:
            raise Exception(f"Failed to get playlist info: {str(e)}")
    
    def get_captions(self, url, language='en'):
        """Extract available captions from YouTube video"""
        try:
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [language, 'en'],  # Fallback to English
                'skip_download': True,
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Check for manual subtitles first
                subtitles = info.get('subtitles', {})
                auto_captions = info.get('automatic_captions', {})
                
                # Prefer manual subtitles, fall back to auto-generated
                captions_data = subtitles.get(language) or subtitles.get('en') or \
                               auto_captions.get(language) or auto_captions.get('en')
                
                if captions_data:
                    # Download the subtitle file
                    subtitle_url = None
                    for sub in captions_data:
                        if sub.get('ext') == 'vtt':
                            subtitle_url = sub.get('url')
                            break
                    
                    if subtitle_url:
                        import requests
                        response = requests.get(subtitle_url)
                        return self._parse_vtt_captions(response.text)
                
                return None
        except Exception as e:
            print(f"Error getting captions: {str(e)}")
            return None
    
    def download_audio(self, url, output_dir=None):
        """Download audio from YouTube video"""
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Find the downloaded file
                filename = ydl.prepare_filename(info)
                audio_file = filename.rsplit('.', 1)[0] + '.mp3'
                
                if os.path.exists(audio_file):
                    return audio_file
                else:
                    # Look for any audio file in the directory
                    for file in os.listdir(output_dir):
                        if file.endswith(('.mp3', '.m4a', '.wav')):
                            return os.path.join(output_dir, file)
                
                raise Exception("Audio file not found after download")
                
        except Exception as e:
            raise Exception(f"Failed to download audio: {str(e)}")
    
    def _parse_vtt_captions(self, vtt_content):
        """Parse VTT caption content to extract text"""
        lines = vtt_content.split('\n')
        captions = []
        current_caption = None
        
        for line in lines:
            line = line.strip()
            
            # Skip metadata and empty lines
            if not line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                continue
            
            # Check if line contains timestamp
            if '-->' in line:
                if current_caption:
                    captions.append(current_caption)
                
                times = line.split(' --> ')
                current_caption = {
                    'start': self._parse_timestamp(times[0]),
                    'end': self._parse_timestamp(times[1]),
                    'text': ''
                }
            elif current_caption and line:
                # Remove HTML tags and add text
                clean_text = re.sub('<[^<]+?>', '', line)
                if current_caption['text']:
                    current_caption['text'] += ' ' + clean_text
                else:
                    current_caption['text'] = clean_text
        
        # Add the last caption
        if current_caption:
            captions.append(current_caption)
        
        return captions
    
    def _parse_timestamp(self, timestamp):
        """Parse VTT timestamp to seconds"""
        # Format: 00:00:01.234 or 01:23.456
        parts = timestamp.split(':')
        
        if len(parts) == 3:  # HH:MM:SS.mmm
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:  # MM:SS.mmm
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(parts[0])