import os
import tempfile
from openai import OpenAI
import json

class WhisperService:
    """Service for transcribing audio using OpenAI's Whisper API"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    def transcribe_audio(self, audio_file_path, language=None):
        """
        Transcribe audio file using OpenAI's Whisper API
        
        Args:
            audio_file_path: Path to the audio file
            language: Language code (optional, Whisper will auto-detect if not provided)
        
        Returns:
            Dictionary with transcription text and segments
        """
        try:
            with open(audio_file_path, 'rb') as audio_file:
                # Use Whisper API for transcription
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Extract text and segments
            transcription_text = response.text
            segments = []
            
            # Convert segments to our format
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    segments.append({
                        'start': segment.start,
                        'end': segment.end,
                        'text': segment.text.strip()
                    })
            
            return {
                'text': transcription_text,
                'segments': segments,
                'language': getattr(response, 'language', language or 'en')
            }
            
        except Exception as e:
            raise Exception(f"Whisper transcription failed: {str(e)}")
    
    def format_as_txt(self, transcription_data):
        """Format transcription as plain text"""
        return transcription_data['text']
    
    def format_as_srt(self, transcription_data):
        """Format transcription as SRT subtitles"""
        if not transcription_data.get('segments'):
            # If no segments, create one large segment
            return f"1\n00:00:00,000 --> 99:99:99,999\n{transcription_data['text']}\n"
        
        srt_content = ""
        for i, segment in enumerate(transcription_data['segments'], 1):
            start_time = self._seconds_to_srt_time(segment['start'])
            end_time = self._seconds_to_srt_time(segment['end'])
            
            srt_content += f"{i}\n{start_time} --> {end_time}\n{segment['text']}\n\n"
        
        return srt_content
    
    def format_as_vtt(self, transcription_data):
        """Format transcription as WebVTT subtitles"""
        vtt_content = "WEBVTT\n\n"
        
        if not transcription_data.get('segments'):
            # If no segments, create one large segment
            vtt_content += "00:00:00.000 --> 99:99:99.999\n"
            vtt_content += f"{transcription_data['text']}\n"
            return vtt_content
        
        for segment in transcription_data['segments']:
            start_time = self._seconds_to_vtt_time(segment['start'])
            end_time = self._seconds_to_vtt_time(segment['end'])
            
            vtt_content += f"{start_time} --> {end_time}\n{segment['text']}\n\n"
        
        return vtt_content
    
    def _seconds_to_srt_time(self, seconds):
        """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _seconds_to_vtt_time(self, seconds):
        """Convert seconds to VTT time format (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    
    def process_captions_data(self, captions_data):
        """Process YouTube captions data into our standard format"""
        if not captions_data:
            return None
        
        # Combine all caption text
        full_text = " ".join([caption['text'] for caption in captions_data])
        
        # Convert to our segment format
        segments = []
        for caption in captions_data:
            segments.append({
                'start': caption['start'],
                'end': caption['end'],
                'text': caption['text']
            })
        
        return {
            'text': full_text,
            'segments': segments,
            'language': 'en'  # Default, could be detected
        }