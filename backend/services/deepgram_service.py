"""Deepgram service for real-time speech-to-text transcription."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
from uuid import UUID

from deepgram import DeepgramClient, DeepgramClientOptions, LiveTranscriptionEvents
from deepgram.clients.live.v1 import LiveOptions

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DeepgramSTTService:
    """Service for real-time speech-to-text using Deepgram."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[DeepgramClient] = None
        self.connections: Dict[UUID, Any] = {}  # session_id -> connection
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Deepgram client."""
        try:
            if not self.settings.deepgram_api_key:
                logger.error("DEEPGRAM_API_KEY not found in environment variables")
                return
            
            config = DeepgramClientOptions(
                api_key=self.settings.deepgram_api_key,
                verbose=self.settings.debug
            )
            
            self.client = DeepgramClient(config)
            logger.info("Deepgram client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Deepgram service is available."""
        return self.client is not None and bool(self.settings.deepgram_api_key)
    
    async def start_real_time_transcription(
        self,
        session_id: UUID,
        on_message_callback: Callable[[Dict[str, Any]], None],
        on_error_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Start real-time transcription for a session."""
        
        if not self.is_available():
            logger.error("Deepgram service not available")
            return False
        
        try:
            # Configure live transcription options
            options = LiveOptions(
                model=self.settings.deepgram_model,
                language=self.settings.deepgram_language,
                encoding=self.settings.deepgram_encoding,
                sample_rate=self.settings.deepgram_sample_rate,
                channels=1,
                punctuate=True,
                smart_format=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                endpointing=300
            )
            
            # Create live connection
            dg_connection = self.client.listen.live.v("1")
            
            # Set up event handlers
            def on_open(self, open, **kwargs):
                logger.info(f"Deepgram connection opened for session {session_id}")
            
            def on_message(self, result, **kwargs):
                try:
                    sentence = result.channel.alternatives[0].transcript
                    
                    if sentence:
                        transcript_data = {
                            "text": sentence,
                            "is_final": result.is_final,
                            "confidence": result.channel.alternatives[0].confidence,
                            "start": result.start,
                            "duration": result.duration,
                            "session_id": str(session_id),
                            "timestamp": result.metadata.request_id if result.metadata else None
                        }
                        
                        # Call the callback function
                        if on_message_callback:
                            on_message_callback(transcript_data)
                
                except Exception as e:
                    logger.error(f"Error processing Deepgram message: {e}")
            
            def on_error(self, error, **kwargs):
                logger.error(f"Deepgram error for session {session_id}: {error}")
                if on_error_callback:
                    on_error_callback(str(error))
            
            def on_close(self, close, **kwargs):
                logger.info(f"Deepgram connection closed for session {session_id}")
            
            # Register event handlers
            dg_connection.on(LiveTranscriptionEvents.Open, on_open)
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            
            # Start the connection (not async)
            if not dg_connection.start(options):
                logger.error(f"Failed to start Deepgram connection for session {session_id}")
                return False
            
            # Store connection
            self.connections[session_id] = dg_connection
            
            logger.info(f"Deepgram real-time transcription started for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Deepgram transcription for session {session_id}: {e}")
            return False
    
    async def send_audio(self, session_id: UUID, audio_data: bytes) -> bool:
        """Send audio data to Deepgram for transcription."""
        
        if session_id not in self.connections:
            logger.error(f"No Deepgram connection found for session {session_id}")
            return False
        
        try:
            connection = self.connections[session_id]
            connection.send(audio_data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio to Deepgram for session {session_id}: {e}")
            return False
    
    async def stop_transcription(self, session_id: UUID):
        """Stop transcription for a session."""
        
        if session_id in self.connections:
            try:
                connection = self.connections[session_id]
                connection.finish()  # Not async
                del self.connections[session_id]
                logger.info(f"Stopped Deepgram transcription for session {session_id}")
                
            except Exception as e:
                logger.error(f"Error stopping Deepgram transcription for session {session_id}: {e}")
    
    async def transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe an audio file using Deepgram (for file uploads)."""
        
        if not self.is_available():
            return {"error": "Deepgram service not available"}
        
        try:
            with open(audio_file_path, "rb") as audio_file:
                buffer_data = audio_file.read()
            
            payload = {"buffer": buffer_data}
            
            options = {
                "model": self.settings.deepgram_model,
                "language": self.settings.deepgram_language,
                "punctuate": True,
                "smart_format": True,
                "paragraphs": True,
                "utterances": True,
                "diarize": True
            }
            
            response = self.client.listen.prerecorded.v("1").transcribe_file(payload, options)
            
            # Extract transcript
            if response.results and response.results.channels:
                channel = response.results.channels[0]
                if channel.alternatives:
                    transcript = channel.alternatives[0].transcript
                    confidence = channel.alternatives[0].confidence
                    
                    # Calculate metrics
                    word_count = len(transcript.split()) if transcript else 0
                    has_speech = bool(transcript.strip())
                    
                    # Get timing information
                    start_time = 0.0
                    end_time = 0.0
                    if response.results.utterances:
                        start_time = response.results.utterances[0].start
                        end_time = response.results.utterances[-1].end
                    
                    return {
                        "text": transcript,
                        "confidence": confidence,
                        "has_speech": has_speech,
                        "word_count": word_count,
                        "duration": end_time - start_time,
                        "start_time": start_time,
                        "end_time": end_time,
                        "language": self.settings.deepgram_language
                    }
            
            return {
                "text": "",
                "confidence": 0.0,
                "has_speech": False,
                "word_count": 0,
                "duration": 0.0,
                "start_time": 0.0,
                "end_time": 0.0,
                "language": self.settings.deepgram_language
            }
            
        except Exception as e:
            logger.error(f"Deepgram file transcription failed: {e}")
            return {"error": str(e)}
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.connections)
    
    async def cleanup_all_connections(self):
        """Cleanup all active connections."""
        session_ids = list(self.connections.keys())
        for session_id in session_ids:
            await self.stop_transcription(session_id)


# Global service instance
_deepgram_service: Optional[DeepgramSTTService] = None


def get_deepgram_service() -> DeepgramSTTService:
    """Get global Deepgram STT service instance."""
    global _deepgram_service
    if _deepgram_service is None:
        _deepgram_service = DeepgramSTTService()
    return _deepgram_service


async def transcribe_audio_file(audio_file_path: str) -> Dict[str, Any]:
    """Transcribe audio file using Deepgram service."""
    deepgram_service = get_deepgram_service()
    return await deepgram_service.transcribe_file(audio_file_path)