"""Speech-to-text endpoints for file upload transcription."""

import logging
import os
import tempfile
from typing import Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from config import get_settings
from services.stt_adapter import transcribe_audio_file, get_stt_adapter

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class TranscriptionResponse(BaseModel):
    """Response model for transcription results."""
    text: str
    has_speech: bool
    confidence: float
    word_count: int
    duration: float
    language: str = "en"


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe uploaded audio file to text.
    
    Args:
        audio: Audio file (WAV, MP3, M4A, etc.)
        
    Returns:
        Transcription result with text and metadata
    """
    try:
        # Validate file
        if not audio.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (limit to 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        file_size = 0
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            suffix=os.path.splitext(audio.filename)[1],
            dir=settings.audio_temp_dir,
            delete=False
        )
        
        try:
            # Write uploaded file to temporary location
            while chunk := await audio.read(8192):  # Read in 8KB chunks
                file_size += len(chunk)
                if file_size > max_size:
                    raise HTTPException(status_code=413, detail="File too large (max 10MB)")
                temp_file.write(chunk)
            
            temp_file.close()
            
            logger.info(f"Transcribing uploaded file: {audio.filename} ({file_size} bytes)")
            
            # Transcribe audio
            result = await transcribe_audio_file(temp_file.name)
            
            # Check for errors
            if "error" in result:
                raise HTTPException(status_code=500, detail=f"Transcription failed: {result['error']}")
            
            response = TranscriptionResponse(
                text=result["text"],
                has_speech=result["has_speech"],
                confidence=result["confidence"],
                word_count=result["word_count"],
                duration=result["duration"],
                language=result.get("language", "en")
            )
            
            logger.info(f"Transcription completed: {response.word_count} words")
            return response
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file.name)
            except:
                pass
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Transcription service error")


@router.get("/models")
async def get_available_models():
    """Get information about available STT models."""
    stt_adapter = get_stt_adapter()
    provider = stt_adapter.get_provider()
    
    if provider == "deepgram":
        return {
            "current_provider": "deepgram",
            "current_model": settings.deepgram_model,
            "available_models": [
                {
                    "name": "nova-2",
                    "description": "Latest Deepgram model with enhanced accuracy",
                    "language_support": "Multi-language"
                },
                {
                    "name": "nova",
                    "description": "High-accuracy general-purpose model",
                    "language_support": "Multi-language"
                },
                {
                    "name": "enhanced",
                    "description": "Enhanced accuracy for premium usage",
                    "language_support": "Multi-language"
                },
                {
                    "name": "base",
                    "description": "Balanced accuracy and cost",
                    "language_support": "Multi-language"
                }
            ],
            "supported_formats": [
                "wav", "mp3", "mp4", "m4a", "flac", "ogg", "webm"
            ],
            "language": settings.deepgram_language
        }
    else:
        # Whisper models
        return {
            "current_provider": "whisper",
            "current_model": settings.whisper_model_size,
            "available_models": [
                {
                    "name": "tiny",
                    "size": "~39 MB",
                    "speed": "~32x realtime",
                    "accuracy": "lowest"
                },
                {
                    "name": "base", 
                    "size": "~74 MB",
                    "speed": "~16x realtime", 
                    "accuracy": "good"
                },
                {
                    "name": "small",
                    "size": "~244 MB",
                    "speed": "~6x realtime",
                    "accuracy": "better"
                },
                {
                    "name": "medium", 
                    "size": "~769 MB",
                    "speed": "~2x realtime",
                    "accuracy": "very good"
                },
                {
                    "name": "large",
                    "size": "~1550 MB", 
                    "speed": "~1x realtime",
                    "accuracy": "best"
                }
            ],
            "supported_formats": [
                "wav", "mp3", "mp4", "m4a", "flac", "ogg"
            ]
        }


@router.get("/status")
async def get_stt_status():
    """Get STT service status and configuration."""
    stt_adapter = get_stt_adapter()
    
    return {
        "service_available": stt_adapter.is_available(),
        "provider": stt_adapter.get_provider(),
        "model": settings.deepgram_model if settings.stt_provider == "deepgram" else settings.whisper_model_size,
        "audio_sample_rate": settings.audio_sample_rate,
        "temp_directory": settings.audio_temp_dir,
        "temp_directory_exists": os.path.exists(settings.audio_temp_dir),
        "temp_directory_writable": os.access(settings.audio_temp_dir, os.W_OK),
        "language": settings.deepgram_language if settings.stt_provider == "deepgram" else "en"
    }