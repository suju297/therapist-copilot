"""Whisper service for speech-to-text transcription."""

import logging
import os
import tempfile
from typing import Dict, Any, Optional

import whisper

from config import get_settings

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for speech-to-text using OpenAI Whisper."""
    
    def __init__(self):
        self.settings = get_settings()
        self.model: Optional[whisper.Whisper] = None
        self.model_size = os.environ.get("WHISPER_MODEL_SIZE", "base")
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model on initialization."""
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
            logger.info(f"Whisper model '{self.model_size}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if Whisper model is available."""
        return self.model is not None
    
    async def transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper."""
        if not self.model:
            raise Exception("Whisper model not available")
        
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        try:
            logger.debug(f"Transcribing audio file: {audio_file_path}")
            
            # Transcribe using Whisper
            result = self.model.transcribe(
                audio_file_path,
                language="en",
                task="transcribe",
                fp16=False,  # Use fp32 for better compatibility
                verbose=False
            )
            
            # Extract segments
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                    "text": segment.get("text", "").strip()
                })
            
            # Get text and calculate metrics
            text = result["text"].strip()
            word_count = len(text.split()) if text else 0
            has_speech = bool(text.strip())
            
            # Calculate confidence (heuristic since Whisper doesn't provide it directly)
            confidence = 0.8 if has_speech else 0.0
            if word_count < 3 and has_speech:
                confidence = 0.6  # Lower confidence for very short transcripts
            
            transcription_result = {
                "text": text,
                "language": result.get("language", "en"),
                "duration": result.get("duration", 0.0),
                "segments": segments,
                "confidence": confidence,
                "word_count": word_count,
                "has_speech": has_speech,
                "start_time": segments[0]["start"] if segments else 0.0,
                "end_time": segments[-1]["end"] if segments else result.get("duration", 0.0)
            }
            
            logger.info(f"Transcription completed: '{text[:100]}...' (confidence: {confidence})")
            return transcription_result
            
        except Exception as e:
            logger.error(f"Transcription failed for {audio_file_path}: {e}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    async def transcribe_bytes(self, audio_data: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """Transcribe audio from bytes."""
        if not self.model:
            raise Exception("Whisper model not available")
        
        # Save bytes to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data)
            tmp_file_path = tmp_file.name
        
        try:
            # Transcribe the temporary file
            result = await self.transcribe_file(tmp_file_path)
            return result
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {tmp_file_path}: {e}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        available_models = [
            "tiny", "tiny.en", "base", "base.en", 
            "small", "small.en", "medium", "medium.en", 
            "large-v1", "large-v2", "large-v3", "large"
        ]
        
        return {
            "current_model": self.model_size,
            "model_loaded": self.model is not None,
            "available_models": available_models,
            "model_info": {
                "tiny": "~39 MB, fastest",
                "base": "~74 MB, good balance",
                "small": "~244 MB, better accuracy", 
                "medium": "~769 MB, high accuracy",
                "large": "~1550 MB, best accuracy"
            }
        }


# Global service instance
_whisper_service = WhisperService()


async def transcribe_audio_file(audio_file_path: str) -> Dict[str, Any]:
    """Transcribe audio file using global service."""
    return await _whisper_service.transcribe_file(audio_file_path)


async def transcribe_audio_bytes(audio_data: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
    """Transcribe audio bytes using global service."""
    return await _whisper_service.transcribe_bytes(audio_data, filename)


def get_whisper_service() -> WhisperService:
    """Get the global whisper service instance."""
    return _whisper_service


def is_whisper_available() -> bool:
    """Check if Whisper service is available."""
    return _whisper_service.is_available()