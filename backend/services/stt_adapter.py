"""Speech-to-text adapter supporting multiple providers."""

import logging
from typing import Dict, Any, Optional

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class STTAdapter:
    """Unified STT adapter supporting multiple providers."""
    
    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.stt_provider
        self._service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the STT service based on provider."""
        try:
            if self.provider == "assemblyai":
                from services.assemblyai_service import get_assemblyai_service
                self._service = get_assemblyai_service()
                logger.info("Initialized AssemblyAI STT service")
                
            elif self.provider == "deepgram":
                from services.deepgram_service import get_deepgram_service
                self._service = get_deepgram_service()
                logger.info("Initialized Deepgram STT service")
                
            elif self.provider == "whisper":
                from services.whisper_service import get_whisper_service
                self._service = get_whisper_service()
                logger.info("Initialized Whisper STT service")
                
            else:
                logger.error(f"Unknown STT provider: {self.provider}")
                # Fallback to AssemblyAI
                from services.assemblyai_service import get_assemblyai_service
                self._service = get_assemblyai_service()
                
        except Exception as e:
            logger.error(f"Failed to initialize STT service: {e}")
            self._service = None
    
    def is_available(self) -> bool:
        """Check if STT service is available."""
        return self._service is not None and self._service.is_available()
    
    async def transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file."""
        if not self.is_available():
            return {
                "text": "",
                "confidence": 0.0,
                "has_speech": False,
                "word_count": 0,
                "duration": 0.0,
                "error": "STT service not available"
            }
        
        try:
            if self.provider == "assemblyai":
                return await self._service.transcribe_file(audio_file_path)
            elif self.provider == "deepgram":
                return await self._service.transcribe_file(audio_file_path)
            elif self.provider == "whisper":
                return await self._service.transcribe_file(audio_file_path)
            else:
                return {"error": f"Unsupported provider: {self.provider}"}
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {"error": str(e)}
    
    def get_service(self):
        """Get the underlying STT service."""
        return self._service
    
    def get_provider(self) -> str:
        """Get current provider name."""
        return self.provider


# Global adapter instance
_stt_adapter: Optional[STTAdapter] = None


def get_stt_adapter() -> STTAdapter:
    """Get global STT adapter instance."""
    global _stt_adapter
    if _stt_adapter is None:
        _stt_adapter = STTAdapter()
    return _stt_adapter


def get_whisper_service():
    """Get STT service (for backwards compatibility)."""
    adapter = get_stt_adapter()
    return adapter.get_service()


async def transcribe_audio_file(audio_file_path: str) -> Dict[str, Any]:
    """Transcribe audio file using configured STT provider."""
    adapter = get_stt_adapter()
    return await adapter.transcribe_file(audio_file_path)