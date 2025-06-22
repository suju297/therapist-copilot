# assemblyai_service.py
"""AssemblyAI service for real-time speech-to-text transcription."""

import asyncio
import json
import logging
import websockets
import os
import inspect
from typing import Dict, Any, Optional, Callable
from uuid import UUID
from urllib.parse import urlencode
import httpx

from config import get_settings

logger = logging.getLogger(__name__)


class AssemblyAISTTService:
    """Service for real-time speech-to-text using AssemblyAI."""
    
    def __init__(self):
        self.settings = get_settings()
        # Also try to get from environment directly as fallback
        self.api_key = self.settings.assemblyai_api_key or os.getenv('ASSEMBLYAI_API_KEY', '')
        self.connections: Dict[UUID, Any] = {}  # session_id -> connection info
        self.websockets: Dict[UUID, Any] = {}  # session_id -> websocket
        
        if self.api_key:
            logger.info(f"AssemblyAI API key configured (length: {len(self.api_key)})")
        else:
            logger.error("AssemblyAI API key not found!")
    
    def is_available(self) -> bool:
        """Check if AssemblyAI service is available."""
        is_available = bool(self.api_key and len(self.api_key) > 10)
        if not is_available:
            logger.error(f"AssemblyAI not available - API key missing or too short (length: {len(self.api_key) if self.api_key else 0})")
        return is_available
    
    async def start_real_time_transcription(
        self,
        session_id: UUID,
        on_message_callback: Callable[[Dict[str, Any]], None],
        on_error_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Start real-time transcription for a session."""
        
        if not self.is_available():
            logger.error("AssemblyAI service not available - check API key")
            return False
        
        try:
            # Use v3 URL with query parameters (free tier)
            connection_params = {
                "sample_rate": self.settings.assemblyai_sample_rate,
                "format_turns": self.settings.assemblyai_format_turns,
            }
            
            # Build WebSocket URL with query parameters
            base_url = "wss://streaming.assemblyai.com/v3/ws"
            ws_url = f"{base_url}?{urlencode(connection_params)}"
            
            # Connection parameters
            connect_kwargs = dict(
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10,
            )
            
            # Use extra_headers for modern websockets
            connect_kwargs["extra_headers"] = [("Authorization", self.api_key)]
            logger.debug("Using extra_headers for auth (websockets >= 10.x)")
            
            logger.info(f"Connecting to AssemblyAI WebSocket v3...")
            
            # Connect to AssemblyAI WebSocket
            websocket = await websockets.connect(ws_url, **connect_kwargs)
            
            try:
                # v3 returns its first control frame in < 50 ms - wait for "Begin" or "error"
                first_response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                data = json.loads(first_response)
                
                if data.get("type") != "Begin":
                    error_msg = data.get("error", f"Handshake failed - unexpected response: {data}")
                    raise RuntimeError(error_msg)
                
                # ✅ handshake ok – store and mark active
                self.websockets[session_id] = websocket
                self.connections[session_id] = {
                    "websocket": websocket,
                    "callback": on_message_callback,
                    "error_callback": on_error_callback,
                    "active": True
                }
                
                # Start message handler task
                asyncio.create_task(self._handle_messages(session_id))
                
                session_ai_id = data.get('id', 'unknown')
                logger.info(f"AssemblyAI v3 ready for session {session_id} (AI session: {session_ai_id})")
                return True
                
            except asyncio.TimeoutError:
                await websocket.close()
                error_msg = "Timeout waiting for AssemblyAI Begin response"
                logger.error(f"{error_msg} for session {session_id}")
                if on_error_callback:
                    on_error_callback(error_msg)
                return False
                
            except Exception as exc:
                await websocket.close()
                error_msg = str(exc)
                logger.error(f"AssemblyAI handshake failed for session {session_id}: {error_msg}")
                if on_error_callback:
                    on_error_callback(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"Failed to start AssemblyAI transcription for session {session_id}: {e}")
            # Cleanup on any failure
            if session_id in self.websockets:
                try:
                    await self.websockets[session_id].close()
                except:
                    pass
                del self.websockets[session_id]
            if session_id in self.connections:
                del self.connections[session_id]
            
            if on_error_callback:
                on_error_callback(f"Failed to start transcription: {str(e)}")
            return False
    
    async def _handle_messages(self, session_id: UUID):
        """Handle incoming messages from AssemblyAI WebSocket."""
        if session_id not in self.connections:
            return
        
        connection_info = self.connections[session_id]
        websocket = connection_info["websocket"]
        callback = connection_info["callback"]
        error_callback = connection_info["error_callback"]
        
        try:
            async for message in websocket:
                if not connection_info.get("active", False):
                    break
                
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == "Begin":
                        session_ai_id = data.get('id')
                        expires_at = data.get('expires_at')
                        logger.info(f"AssemblyAI session began: ID={session_ai_id} for session {session_id}")
                        
                    elif msg_type == "Turn":
                        # Handle v3 Turn messages (both partial and final)
                        transcript = data.get('transcript', '')
                        formatted = data.get('turn_is_formatted', False)
                        confidence = data.get('confidence', 0.8)  # AssemblyAI doesn't always provide confidence
                        
                        if transcript and callback:
                            transcript_data = {
                                "text": transcript,
                                "is_final": formatted,  # Formatted turns are final
                                "confidence": confidence,
                                "start": 0.0,  # AssemblyAI v3 doesn't provide timing in real-time
                                "duration": 0.0,
                                "session_id": str(session_id),
                                "timestamp": data.get('created'),
                                "turn_formatted": formatted
                            }
                            
                            # Call the callback
                            await self._safe_callback(callback, transcript_data)
                    
                    elif msg_type in ("PartialTranscript", "FinalTranscript"):
                        # Handle both partial and final transcripts with correct field names
                        is_final = msg_type == "FinalTranscript"
                        transcript = data.get("text") if is_final else data.get("partial_transcript", "")
                        confidence = data.get("confidence", 0.0)
                        
                        if transcript and callback:
                            transcript_data = {
                                "text": transcript,
                                "is_final": is_final,
                                "confidence": confidence,
                                "start": data.get("start", 0.0),
                                "duration": data.get("end", 0.0) - data.get("start", 0.0),
                                "session_id": str(session_id),
                                "timestamp": data.get("created"),
                                "turn_formatted": is_final
                            }
                            
                            await self._safe_callback(callback, transcript_data)
                    
                    elif msg_type == "Termination" or msg_type == "SessionTerminated":
                        # Handle session termination (v3 uses "Termination", v2 uses "SessionTerminated")
                        audio_duration = data.get('audio_duration_seconds', 0)
                        session_duration = data.get('session_duration_seconds', 0)
                        logger.info(f"AssemblyAI session terminated for {session_id}: "
                                  f"Audio={audio_duration}s, Session={session_duration}s")
                        break
                    
                    elif "error" in data:
                        # Handle any error messages from AssemblyAI
                        error_msg = data.get("error", "Unknown error")
                        logger.error(f"AssemblyAI error for session {session_id}: {error_msg}")
                        if error_callback:
                            error_callback(f"AssemblyAI error: {error_msg}")
                        break
                    
                    # Log any unhandled message types for debugging
                    elif msg_type not in ["Begin", "Turn", "PartialTranscript", "FinalTranscript", "Termination", "SessionTerminated"]:
                        logger.debug(f"Unhandled AssemblyAI message type for session {session_id}: {msg_type}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding AssemblyAI message for session {session_id}: {e}")
                except Exception as e:
                    logger.error(f"Error processing AssemblyAI message for session {session_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"AssemblyAI WebSocket connection closed for session {session_id}")
        except Exception as e:
            logger.error(f"Error in AssemblyAI message handler for session {session_id}: {e}")
            if error_callback:
                error_callback(str(e))
        finally:
            # Mark connection as inactive and cleanup
            if session_id in self.connections:
                self.connections[session_id]["active"] = False
            logger.info(f"AssemblyAI WebSocket closed for session {session_id}")
    
    async def _safe_callback(self, callback, data):
        """Safely call callback function."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.error(f"Error in transcript callback: {e}")
    
    async def send_audio(self, session_id: UUID, audio_data: bytes) -> bool:
        """Send audio data to AssemblyAI for transcription."""
        
        if session_id not in self.websockets:
            logger.error(f"No AssemblyAI connection found for session {session_id}")
            return False
        
        try:
            websocket = self.websockets[session_id]
            if websocket.closed:
                logger.error(f"AssemblyAI WebSocket closed for session {session_id}")
                return False
            
            # Send audio data as binary
            await websocket.send(audio_data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio to AssemblyAI for session {session_id}: {e}")
            return False
    
    async def stop_transcription(self, session_id: UUID):
        """Stop transcription for a session."""
        if session_id in self.connections:
            try:
                # Mark as inactive
                self.connections[session_id]["active"] = False
                
                # Send termination message
                if session_id in self.websockets:
                    websocket = self.websockets[session_id]
                    if not websocket.closed:
                        terminate_message = {"type": "Terminate"}
                        await websocket.send(json.dumps(terminate_message))
                        await asyncio.sleep(0.1)  # Give time for message to send
                        await websocket.close()
                    
                    del self.websockets[session_id]
                
                del self.connections[session_id]
                logger.info(f"Stopped AssemblyAI transcription for session {session_id}")
                
            except Exception as e:
                logger.error(f"Error stopping AssemblyAI transcription for session {session_id}: {e}")
    
    async def transcribe_file(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe an audio file using AssemblyAI (for file uploads)."""
        
        if not self.is_available():
            return {"error": "AssemblyAI service not available"}
        
        try:
            # Upload file to AssemblyAI - Use self.api_key
            headers = {"authorization": self.api_key}
            
            # Upload audio file
            async with httpx.AsyncClient() as client:
                with open(audio_file_path, "rb") as audio_file:
                    upload_response = await client.post(
                        "https://api.assemblyai.com/v2/upload",
                        headers=headers,
                        files={"file": audio_file}
                    )
                
                if upload_response.status_code != 200:
                    return {"error": f"File upload failed: {upload_response.text}"}
                
                upload_url = upload_response.json()["upload_url"]
                
                # Request transcription
                transcript_request = {
                    "audio_url": upload_url,
                    "punctuate": True,
                    "format_text": True
                }
                
                transcript_response = await client.post(
                    "https://api.assemblyai.com/v2/transcript",
                    headers=headers,
                    json=transcript_request
                )
                
                if transcript_response.status_code != 200:
                    return {"error": f"Transcription request failed: {transcript_response.text}"}
                
                transcript_id = transcript_response.json()["id"]
                
                # Poll for completion
                max_retries = 60  # 5 minutes max
                for _ in range(max_retries):
                    status_response = await client.get(
                        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                        headers=headers
                    )
                    
                    if status_response.status_code != 200:
                        return {"error": f"Status check failed: {status_response.text}"}
                    
                    result = status_response.json()
                    status = result["status"]
                    
                    if status == "completed":
                        transcript = result.get("text", "")
                        confidence = result.get("confidence", 0.0)
                        
                        return {
                            "text": transcript,
                            "confidence": confidence,
                            "has_speech": bool(transcript.strip()),
                            "word_count": len(transcript.split()) if transcript else 0,
                            "duration": result.get("audio_duration", 0.0),
                            "start_time": 0.0,
                            "end_time": result.get("audio_duration", 0.0),
                            "language": "en"
                        }
                    
                    elif status == "error":
                        return {"error": f"Transcription failed: {result.get('error')}"}
                    
                    # Wait before next check
                    await asyncio.sleep(5)
                
                return {"error": "Transcription timeout"}
            
        except Exception as e:
            logger.error(f"AssemblyAI file transcription failed: {e}")
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
_assemblyai_service: Optional[AssemblyAISTTService] = None


def get_assemblyai_service() -> AssemblyAISTTService:
    """Get global AssemblyAI STT service instance."""
    global _assemblyai_service
    if _assemblyai_service is None:
        _assemblyai_service = AssemblyAISTTService()
    return _assemblyai_service