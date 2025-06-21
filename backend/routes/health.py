"""Health check endpoint for the simplified API."""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter

from config import get_settings
from services.stt_adapter import get_whisper_service
from services.audio_buffer import get_buffer_stats

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint that reports system status.
    
    Returns:
        System health information including service availability
    """
    settings = get_settings()
    
    # Check Whisper service
    whisper_service = get_whisper_service()
    whisper_available = whisper_service.is_available()
    
    # Check Gemini API configuration
    gemini_configured = bool(settings.gemini_api_key and len(settings.gemini_api_key) > 10)
    
    # Get audio buffer statistics
    buffer_stats = get_buffer_stats()
    
    # Determine overall health
    healthy = whisper_available and gemini_configured
    
    health_data = {
        "status": "healthy" if healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "whisper_stt": {
                "available": whisper_available,
                "model_size": settings.whisper_model_size,
                "status": "healthy" if whisper_available else "unavailable"
            },
            "gemini_api": {
                "configured": gemini_configured,
                "model": settings.llm_model_risk,
                "status": "configured" if gemini_configured else "not_configured"
            },
            "audio_processing": {
                "active_buffers": buffer_stats["active_buffers"],
                "sample_rate": settings.audio_sample_rate,
                "chunk_ms": settings.ws_chunk_ms,
                "status": "healthy"
            }
        },
        "configuration": {
            "risk_threshold": settings.risk_threshold,
            "session_timeout_hours": settings.session_timeout_hours,
            "audio_temp_dir": settings.audio_temp_dir,
            "debug_mode": settings.debug
        },
        "features": {
            "real_time_transcription": whisper_available,
            "risk_assessment": gemini_configured,
            "websocket_streaming": True,
            "session_management": True
        }
    }
    
    # Add warnings for missing services
    warnings = []
    if not whisper_available:
        warnings.append("Whisper STT service is not available - transcription will fail")
    if not gemini_configured:
        warnings.append("Gemini API key not configured - risk assessment will fail")
    
    if warnings:
        health_data["warnings"] = warnings
    
    logger.info(f"Health check: {health_data['status']}")
    return health_data


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with extended system information.
    
    Returns:
        Detailed system health and configuration information
    """
    import os
    import sys
    
    basic_health = await health_check()
    
    # Add system information (without psutil to avoid dependency)
    basic_health["system"] = {
        "python_version": sys.version,
        "platform": sys.platform
    }
    
    # Add environment information
    basic_health["environment"] = {
        "audio_temp_dir_exists": os.path.exists(get_settings().audio_temp_dir),
        "audio_temp_dir_writable": os.access(get_settings().audio_temp_dir, os.W_OK) if os.path.exists(get_settings().audio_temp_dir) else False
    }
    
    return basic_health