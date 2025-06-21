"""Deepgram service for speech-to-text transcription."""

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Dict, Any, Optional, Callable
from uuid import UUID

import websocket
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from deepgram.clients.prerecorded.v1 import PrerecordedResponse

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DeepgramSTTService:
    """Service for speech-to-text using Deepgram."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[DeepgramClient] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Deepgram client."""
        try:
            if not self.settings.deepgram_api_key:
                logger.warning("Deepgram API key not configured")
                return
            
            self.client = DeepgramClient(self.settings.deepgram_api_key)
            logger.info("Deepgram client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Deepgram service is available."""
        return self.client is not None and bool(self.settings.deepgram_api_key)
    
    async def transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Deepgram prerecorded API."""
        try:
            if not self.client:
                raise Exception("Deepgram client not available")
            
            if not os.path.exists(audio_file_path):
                raise Exception(f"Audio file not found: {audio_file_path}")
            
            logger.debug(f"Transcribing audio file: {audio_file_path}")
            
            # Read audio file
            with open(audio_file_path, "rb") as audio_file:
                buffer_data = audio_file.read()
            
            payload: FileSource = {
                "buffer": buffer_data,
            }
            
            # Configure options
            options = PrerecordedOptions(
                model=self.settings.deepgram_model,
                smart_format=True,
                punctuate=True,
                paragraphs=True,
                utterances=True,
                diarize=True,  # Speaker diarization
                language=self.settings.deepgram_language,
                detect_language=False,
            )
            
            # Make the API request
            response: PrerecordedResponse = self.client.listen.prerecorded.v("1").transcribe_file(
                payload, options
            )
            
            # Parse response
            result = response.to_dict()
            
            # Extract transcript
            transcript = ""
            confidence = 0.0
            duration = 0.0
            segments = []
            
            if "results" in result and "channels" in result["results"]:
                channel = result["results"]["channels"][0]
                
                if "alternatives" in channel and len(channel["alternatives"]) > 0:
                    alternative = channel["alternatives"][0]
                    transcript = alternative.get("transcript", "")
                    confidence = alternative.get("confidence", 0.0)
                    
                    # Extract segments/words for timing
                    words = alternative.get("words", [])
                    if words:
                        for word in words:
                            segments.append({
                                "start": word.get("start", 0.0),
                                "end": word.get("end", 0.0),
                                "text": word.get("word", ""),
                                "confidence": word.get("confidence", 0.0)
                            })
                        
                        # Calculate total duration
                        if segments:
                            duration = segments[-1]["end"]
            
            # Check if speech was detected
            has_speech = len(transcript.strip()) > 0
            word_count = len(transcript.split()) if transcript else 0
            
            response_data = {
                "text": transcript,
                "has_speech": has_speech,
                "confidence": confidence,
                "word_count": word_count,
                "duration": duration,
                "start_time": segments[0]["start"] if segments else 0.0,
                "end_time": segments[-1]["end"] if segments else duration,
                "language": self.settings.deepgram_language,
                "segments": segments,
                "provider": "deepgram"
            }
            
            logger.debug(f"Transcription completed: {word_count} words, confidence: {confidence:.2f}")
            return response_data
            
        except Exception as e:
            logger.error(f"Transcription failed for {audio_file_path}: {e}")
            return {
                "text": "",
                "has_speech": False,
                "confidence": 0.0,
                "word_count": 0,
                "duration": 0.0,
                "start_time": 0.0,
                "end_time": 0.0,
                "language": self.settings.deepgram_language,
                "segments": [],
                "provider": "deepgram",
                "error": str(e)
            }
    
    async def transcribe_bytes(self, audio_data: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """Transcribe audio from bytes."""
        if not self.client:
            raise Exception("Deepgram client not available")
        
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
        """Get information about available models."""
        return {
            "current_model": self.settings.deepgram_model,
            "provider": "deepgram",
            "service_available": self.is_available(),
            "available_models": [
                {
                    "name": "nova-2",
                    "description": "Latest and most accurate model",
                    "language_support": "30+ languages",
                    "features": ["punctuation", "diarization", "smart_format"]
                },
                {
                    "name": "nova",
                    "description": "Previous generation model",
                    "language_support": "30+ languages",
                    "features": ["punctuation", "diarization"]
                },
                {
                    "name": "enhanced",
                    "description": "Optimized for general use",
                    "language_support": "30+ languages",
                    "features": ["punctuation"]
                },
                {
                    "name": "base",
                    "description": "Fast and cost-effective",
                    "language_support": "30+ languages",
                    "features": ["basic_transcription"]
                }
            ],
            "supported_formats": [
                "wav", "mp3", "mp4", "m4a", "flac", "ogg", "webm", "amr"
            ]
        }


class DeepgramRealtimeClient:
    """Deepgram real-time streaming client for WebSocket audio."""
    
    def __init__(self, session_id: UUID, on_transcript: Callable[[Dict[str, Any]], None]):
        self.session_id = session_id
        self.on_transcript = on_transcript
        self.settings = get_settings()
        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_connected = False
        self.connection_params = {
            "model": self.settings.deepgram_model,
            "language": self.settings.deepgram_language,
            "smart_format": "true",
            "punctuate": "true",
            "interim_results": "true",
            "endpointing": "300",  # 300ms of silence to finalize
            "sample_rate": str(self.settings.audio_sample_rate),
            "channels": "1",
            "encoding": "linear16"
        }
        
        # Build WebSocket URL
        params = "&".join([f"{k}={v}" for k, v in self.connection_params.items()])
        self.ws_url = f"wss://api.deepgram.com/v1/listen?{params}"
        
        logger.info(f"Initialized Deepgram realtime client for session {session_id}")
    
    def connect(self):
        """Connect to Deepgram WebSocket."""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                header={"Authorization": f"Token {self.settings.deepgram_api_key}"},
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            
            # Run WebSocket in a separate thread
            import threading
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            timeout = 5.0
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.is_connected:
                raise Exception("Failed to connect to Deepgram within timeout")
            
            logger.info(f"Connected to Deepgram WebSocket for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram WebSocket: {e}")
            raise
    
    def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram."""
        if self.ws and self.is_connected:
            try:
                self.ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                logger.error(f"Failed to send audio data: {e}")
        else:
            logger.warning("WebSocket not connected, cannot send audio")
    
    def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            try:
                # Send close frame
                close_message = {"type": "CloseStream"}
                self.ws.send(json.dumps(close_message))
                time.sleep(0.1)  # Give time for message to send
                
                self.ws.close()
                
                # Wait for thread to finish
                if hasattr(self, 'ws_thread') and self.ws_thread.is_alive():
                    self.ws_thread.join(timeout=2.0)
                    
            except Exception as e:
                logger.error(f"Error closing Deepgram WebSocket: {e}")
        
        self.is_connected = False
        logger.info(f"Closed Deepgram WebSocket for session {self.session_id}")
    
    def _on_open(self, ws):
        """Called when WebSocket connection opens."""
        self.is_connected = True
        logger.debug(f"Deepgram WebSocket opened for session {self.session_id}")
    
    def _on_message(self, ws, message):
        """Called when receiving a message from Deepgram."""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if data.get("type") == "Results":
                channel = data.get("channel", {})
                alternatives = channel.get("alternatives", [])
                
                if alternatives:
                    transcript_data = alternatives[0]
                    transcript_text = transcript_data.get("transcript", "")
                    
                    if transcript_text.strip():  # Only process non-empty transcripts
                        confidence = transcript_data.get("confidence", 0.0)
                        is_final = channel.get("is_final", False)
                        
                        # Calculate duration and word count
                        words = transcript_data.get("words", [])
                        duration = 0.0
                        if words:
                            duration = words[-1].get("end", 0.0) - words[0].get("start", 0.0)
                        
                        result = {
                            "text": transcript_text,
                            "confidence": confidence,
                            "is_final": is_final,
                            "duration": duration,
                            "word_count": len(transcript_text.split()),
                            "words": words,
                            "provider": "deepgram"
                        }
                        
                        # Call the transcript callback
                        self.on_transcript(result)
                        
                        logger.debug(f"Transcript: {transcript_text} (final: {is_final}, confidence: {confidence:.2f})")
            
            elif data.get("type") == "Metadata":
                # Handle metadata messages
                logger.debug(f"Received metadata: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding Deepgram message: {e}")
        except Exception as e:
            logger.error(f"Error handling Deepgram message: {e}")
    
    def _on_error(self, ws, error):
        """Called when WebSocket error occurs."""
        logger.error(f"Deepgram WebSocket error for session {self.session_id}: {error}")
        self.is_connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Called when WebSocket connection closes."""
        self.is_connected = False
        logger.info(f"Deepgram WebSocket closed for session {self.session_id}: {close_status_code} - {close_msg}")


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


async def transcribe_audio_bytes(audio_data: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
    """Transcribe audio bytes using Deepgram service."""
    deepgram_service = get_deepgram_service()
    return await deepgram_service.transcribe_bytes(audio_data, filename)


def is_deepgram_available() -> bool:
    """Check if Deepgram service is available."""
    return get_deepgram_service().is_available()