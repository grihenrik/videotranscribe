import os
import asyncio
import logging
import tempfile
from typing import Dict, Optional, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for speech-to-text using OpenAI's Whisper."""
    
    def __init__(self):
        """Initialize the Whisper service."""
        self.model_name = settings.WHISPER_MODEL
        self.use_openai = settings.USE_OPENAI_WHISPER
        self.use_gpu = settings.USE_GPU
        
        # Load whisper lazily to improve startup time
        self._whisper = None
        self._openai = None
    
    async def _load_whisper(self):
        """
        Load the Whisper model.
        """
        if self.use_openai:
            # Load OpenAI client
            if self._openai is None:
                import openai
                
                openai.api_key = settings.OPENAI_API_KEY
                self._openai = openai
        else:
            # Load local Whisper model
            if self._whisper is None:
                try:
                    import whisper
                    import torch
                    
                    # Determine device
                    device = "cuda" if self.use_gpu and torch.cuda.is_available() else "cpu"
                    logger.info(f"Using Whisper on {device} device")
                    
                    # Load model
                    self._whisper = whisper.load_model(self.model_name, device=device)
                    
                except ImportError:
                    logger.error("Failed to import whisper or torch. Please make sure they are installed.")
                    raise ValueError("Whisper dependencies are not installed")
    
    async def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict[str, str]:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_path: Path to audio file
            language: Language code (optional)
            
        Returns:
            Dictionary with transcription in different formats (text, srt, vtt)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        loop = asyncio.get_event_loop()
        
        if self.use_openai:
            return await self._transcribe_with_openai(audio_path, language)
        else:
            return await self._transcribe_with_local_whisper(audio_path, loop, language)
    
    async def _transcribe_with_openai(self, audio_path: str, language: Optional[str] = None) -> Dict[str, str]:
        """
        Transcribe audio using OpenAI's Whisper API.
        
        Args:
            audio_path: Path to audio file
            language: Language code (optional)
            
        Returns:
            Dictionary with transcription in different formats (text, srt, vtt)
        """
        logger.info(f"Transcribing audio with OpenAI Whisper API: {audio_path}")
        
        # Load OpenAI client
        await self._load_whisper()
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is not set")
        
        loop = asyncio.get_event_loop()
        
        def _transcribe():
            with open(audio_path, "rb") as audio_file:
                # For local testing, could use the OpenAI Whisper API
                # This will require the OpenAI API key
                # In a production environment, you would want to handle rate limiting
                # and errors appropriately
                from openai import OpenAI
                
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                
                options = {}
                if language:
                    options["language"] = language
                
                # Define response formats based on required output
                result = {}
                
                # Get text transcription
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    **options
                )
                result["text"] = response.text
                
                # Reset file pointer for next read
                audio_file.seek(0)
                
                # Get SRT format
                response_srt = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="srt",
                    **options
                )
                result["srt"] = response_srt
                
                # Reset file pointer for next read
                audio_file.seek(0)
                
                # Get VTT format
                response_vtt = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="vtt",
                    **options
                )
                result["vtt"] = response_vtt
                
                return result
        
        # Run OpenAI API in a thread pool executor to avoid blocking
        result = await loop.run_in_executor(None, _transcribe)
        
        return result
    
    async def _transcribe_with_local_whisper(self, audio_path: str, loop: asyncio.AbstractEventLoop, language: Optional[str] = None) -> Dict[str, str]:
        """
        Transcribe audio using local Whisper model.
        
        Args:
            audio_path: Path to audio file
            loop: Asyncio event loop
            language: Language code (optional)
            
        Returns:
            Dictionary with transcription in different formats (text, srt, vtt)
        """
        logger.info(f"Transcribing audio with local Whisper model: {audio_path}")
        
        # Load Whisper model
        await self._load_whisper()
        
        def _transcribe():
            # Transcribe with options
            options = {}
            if language:
                options["language"] = language
            
            result = self._whisper.transcribe(audio_path, **options)
            
            # Extract text from result
            text = result["text"]
            
            # Create SRT and VTT files using the segments
            # Create temporary files for SRT and VTT output
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".srt") as srt_file, \
                 tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".vtt") as vtt_file:
                
                # Write SRT format
                for i, segment in enumerate(result["segments"], 1):
                    start = int(segment["start"] * 1000)
                    end = int(segment["end"] * 1000)
                    
                    # Format SRT timestamps
                    start_str = f"{start//3600000:02d}:{(start//60000)%60:02d}:{(start//1000)%60:02d},{start%1000:03d}"
                    end_str = f"{end//3600000:02d}:{(end//60000)%60:02d}:{(end//1000)%60:02d},{end%1000:03d}"
                    
                    # Write SRT entry
                    srt_file.write(f"{i}\n")
                    srt_file.write(f"{start_str} --> {end_str}\n")
                    srt_file.write(f"{segment['text'].strip()}\n\n")
                
                # Write VTT format
                vtt_file.write("WEBVTT\n\n")
                for i, segment in enumerate(result["segments"]):
                    start = int(segment["start"] * 1000)
                    end = int(segment["end"] * 1000)
                    
                    # Format VTT timestamps
                    start_str = f"{start//3600000:02d}:{(start//60000)%60:02d}:{(start//1000)%60:02d}.{start%1000:03d}"
                    end_str = f"{end//3600000:02d}:{(end//60000)%60:02d}:{(end//1000)%60:02d}.{end%1000:03d}"
                    
                    # Write VTT entry
                    vtt_file.write(f"{start_str} --> {end_str}\n")
                    vtt_file.write(f"{segment['text'].strip()}\n\n")
            
            # Read back the files
            with open(srt_file.name, "r") as f:
                srt_content = f.read()
            with open(vtt_file.name, "r") as f:
                vtt_content = f.read()
            
            # Clean up temporary files
            os.unlink(srt_file.name)
            os.unlink(vtt_file.name)
            
            return {
                "text": text,
                "srt": srt_content,
                "vtt": vtt_content
            }
        
        # Run Whisper in a thread pool executor to avoid blocking
        result = await loop.run_in_executor(None, _transcribe)
        
        return result
