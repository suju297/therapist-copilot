"""Enhanced speech-to-text endpoints supporting multiple providers."""

import logging
import os
import tempfile
from typing import Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from config import get_settings
from services.stt_adapter import transcribe_audio_file, get_stt_service

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
    provider: str = "unknown"
    segments: list = []


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Transcribe uploaded audio file to text using the best available STT service.
    
    Args:
        audio: Audio file (WAV, MP3, M4A, FLAC, etc.)
        
    Returns:
        Transcription result with text and metadata
    """
    try:
        # Validate file
        if not audio.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check if any STT service is available
        stt_service = get_stt_service()
        if not stt_service.is_available():
            raise HTTPException(
                status_code=503, 
                detail="No STT service available. Please configure Deepgram API key or Whisper model."
            )
        
        # Check file size (limit to 25MB for Deepgram compatibility)
        max_size = 25 * 1024 * 1024  # 25MB
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
                    raise HTTPException(status_code=413, detail="File too large (max 25MB)")
                temp_file.write(chunk)
            
            temp_file.close()
            
            logger.info(f"Transcribing uploaded file: {audio.filename} ({file_size} bytes) using {stt_service.get_active_provider()}")
            
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
                language=result.get("language", "en"),
                provider=result.get("provider", "unknown"),
                segments=result.get("segments", [])
            )
            
            logger.info(f"Transcription completed: {response.word_count} words, provider: {response.provider}")
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
    """Get information about available STT models and services."""
    stt_service = get_stt_service()
    service_info = stt_service.get_service_info()
    
    return {
        "active_provider": service_info["active_provider"],
        "configured_provider": service_info["configured_provider"],
        "available_services": service_info["available_services"],
        "supported_formats": [
            "wav", "mp3", "mp4", "m4a", "flac", "ogg", "webm", "amr"
        ]
    }


@router.get("/status")
async def get_stt_status():
    """Get comprehensive STT service status and configuration."""
    stt_service = get_stt_service()
    service_info = stt_service.get_service_info()
    
    return {
        "service_available": stt_service.is_available(),
        "active_provider": service_info["active_provider"],
        "configured_provider": service_info["configured_provider"],
        "available_services": service_info["available_services"],
        "audio_sample_rate": settings.audio_sample_rate,
        "temp_directory": settings.audio_temp_dir,
        "temp_directory_exists": os.path.exists(settings.audio_temp_dir),
        "temp_directory_writable": os.access(settings.audio_temp_dir, os.W_OK),
        "configuration": {
            "deepgram_configured": bool(settings.deepgram_api_key),
            "deepgram_model": settings.deepgram_model,
            "deepgram_language": settings.deepgram_language,
            "whisper_model_size": settings.whisper_model_size
        }
    }


@router.get("/providers")
async def get_provider_comparison():
    """Get comparison of available STT providers."""
    return {
        "providers": {
            "deepgram": {
                "name": "Deepgram",
                "type": "cloud_api",
                "features": [
                    "Real-time streaming",
                    "High accuracy",
                    "Multiple languages",
                    "Speaker diarization",
                    "Smart formatting",
                    "Punctuation"
                ],
                "pros": [
                    "Excellent real-time performance",
                    "High accuracy",
                    "Low latency",
                    "Scalable"
                ],
                "cons": [
                    "Requires API key",
                    "Usage-based pricing",
                    "Internet connection required"
                ],
                "best_for": "Production real-time applications"
            },
            "whisper": {
                "name": "OpenAI Whisper",
                "type": "local_model",
                "features": [
                    "Offline processing",
                    "Multiple languages",
                    "No API costs",
                    "Multiple model sizes"
                ],
                "pros": [
                    "Runs offline",
                    "No usage costs",
                    "Privacy-focused",
                    "Multiple model sizes"
                ],
                "cons": [
                    "Slower processing",
                    "No real-time streaming",
                    "Requires more compute resources",
                    "Higher latency"
                ],
                "best_for": "Offline processing or cost-sensitive applications"
            }
        },
        "recommendation": {
            "real_time": "deepgram",
            "batch_processing": "deepgram_or_whisper",
            "privacy_focused": "whisper",
            "cost_sensitive": "whisper",
            "high_accuracy": "deepgram"
        }
    }