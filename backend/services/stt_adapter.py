"""Speech-to-text adapter supporting multiple providers (Deepgram, Whisper)."""

import logging
from typing import Dict, Any, Optional

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class STTService:
    """Unified STT service that can use different providers."""
    
    def __init__(self):
        self.settings = get_settings()
        self._deepgram_service = None
        self._whisper_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize available STT services."""
        try:
            # Try to initialize Deepgram service
            if self.settings.stt_provider == "deepgram" or self.settings.deepgram_api_key:
                from services.deepgram_service import get_deepgram_service
                self._deepgram_service = get_deepgram_service()
                if self._deepgram_service.is_available():
                    logger.info("Deepgram STT service initialized successfully")
                else:
                    logger.warning("Deepgram STT service not available")
                    
        except ImportError as e:
            logger.warning(f"Deepgram service not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram service: {e}")
        
        # Fallback to Whisper if configured
        if not self._deepgram_service or not self._deepgram_service.is_available():
            try:
                if self.settings.stt_provider == "whisper" or not self.settings.deepgram_api_key:
                    from services.whisper_service import get_whisper_service
                    self._whisper_service = get_whisper_service()
                    if self._whisper_service.is_available():
                        logger.info("Whisper STT service initialized as fallback")
                    
            except ImportError as e:
                logger.warning(f"Whisper service not available: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize Whisper service: {e}")
    
    def is_available(self) -> bool:
        """Check if any STT service is available."""
        if self._deepgram_service and self._deepgram_service.is_available():
            return True
        if self._whisper_service and self._whisper_service.is_available():
            return True
        return False
    
    def get_active_provider(self) -> str:
        """Get the currently active STT provider."""
        if self._deepgram_service and self._deepgram_service.is_available():
            return "deepgram"
        elif self._whisper_service and self._whisper_service.is_available():
            return "whisper"
        else:
            return "none"
    
    async def transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using the best available service."""
        # Try Deepgram first
        if self._deepgram_service and self._deepgram_service.is_available():
            try:
                result = await self._deepgram_service.transcribe_file(audio_file_path)
                result["provider"] = "deepgram"
                return result
            except Exception as e:
                logger.error(f"Deepgram transcription failed, trying fallback: {e}")
        
        # Fallback to Whisper
        if self._whisper_service and self._whisper_service.is_available():
            try:
                result = await self._whisper_service.transcribe_file(audio_file_path)
                result["provider"] = "whisper"
                return result
            except Exception as e:
                logger.error(f"Whisper transcription failed: {e}")
        
        # No service available
        return {
            "text": "",
            "has_speech": False,
            "confidence": 0.0,
            "word_count": 0,
            "duration": 0.0,
            "start_time": 0.0,
            "end_time": 0.0,
            "language": "en",
            "segments": [],
            "provider": "none",
            "error": "No STT service available"
        }
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about available STT services."""
        info = {
            "active_provider": self.get_active_provider(),
            "available_services": [],
            "configured_provider": self.settings.stt_provider
        }
        
        # Add Deepgram info
        if self._deepgram_service:
            deepgram_info = self._deepgram_service.get_model_info()
            deepgram_info["available"] = self._deepgram_service.is_available()
            info["available_services"].append(deepgram_info)
        
        # Add Whisper info
        if self._whisper_service:
            whisper_info = self._whisper_service.get_model_info()
            whisper_info["available"] = self._whisper_service.is_available()
            info["available_services"].append(whisper_info)
        
        return info


# Global service instance
_stt_service: Optional[STTService] = None


def get_stt_service() -> STTService:
    """Get global STT service instance."""
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService()
    return _stt_service


async def transcribe_audio_file(audio_file_path: str) -> Dict[str, Any]:
    """Transcribe audio file using the best available STT service."""
    stt_service = get_stt_service()
    return await stt_service.transcribe_file(audio_file_path)


def is_stt_available() -> bool:
    """Check if any STT service is available."""
    return get_stt_service().is_available()


# Backward compatibility functions
def get_whisper_service():
    """Get STT service (backward compatibility)."""
    return get_stt_service()


# Keep the old interface for backward compatibility
class WhisperSTTService:
    """Backward compatibility wrapper."""
    
    def __init__(self):
        self._stt_service = get_stt_service()
    
    def is_available(self) -> bool:
        return self._stt_service.is_available()
    
    async def transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        return await self._stt_service.transcribe_file(audio_file_path)
    
    def _estimate_confidence(self, text: str, segments: list) -> float:
        """Legacy method for backward compatibility."""
        return 0.9 if text else 0.0