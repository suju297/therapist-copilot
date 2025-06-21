"""Enhanced WebSocket route for real-time audio streaming with Deepgram integration."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import get_settings
from services.audio_buffer import get_audio_buffer, remove_audio_buffer
from services.stt_adapter import transcribe_audio_file, get_stt_service
from services.risk_classifier import assess_risk_level

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class ConnectionManager:
    """Enhanced WebSocket connection manager with Deepgram real-time support."""
    
    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.session_states: Dict[UUID, Dict[str, Any]] = {}
        self.session_transcripts: Dict[UUID, list] = {}
        self.deepgram_clients: Dict[UUID, Any] = {}  # Store Deepgram real-time clients
    
    async def connect(self, websocket: WebSocket, session_id: UUID):
        """Accept WebSocket connection and initialize session with real-time STT."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_states[session_id] = {
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "chunks_received": 0,
            "transcripts_generated": 0,
            "is_locked": False,
            "risk_level": "low",
            "highest_risk_score": 0.0,
            "stt_provider": get_stt_service().get_active_provider(),
            "realtime_enabled": False
        }
        self.session_transcripts[session_id] = []
        
        # Initialize real-time STT if Deepgram is available
        await self._initialize_realtime_stt(session_id)
        
        logger.info(f"WebSocket connected for session {session_id}")
    
    async def _initialize_realtime_stt(self, session_id: UUID):
        """Initialize real-time STT client if available."""
        try:
            stt_service = get_stt_service()
            
            if stt_service.get_active_provider() == "deepgram":
                from services.deepgram_service import DeepgramRealtimeClient
                
                # Create transcript handler
                def on_transcript(transcript_data: Dict[str, Any]):
                    # Schedule the transcript processing
                    asyncio.create_task(self._handle_realtime_transcript(session_id, transcript_data))
                
                # Create and connect Deepgram client
                deepgram_client = DeepgramRealtimeClient(session_id, on_transcript)
                deepgram_client.connect()
                
                self.deepgram_clients[session_id] = deepgram_client
                self.session_states[session_id]["realtime_enabled"] = True
                
                logger.info(f"Real-time STT initialized for session {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to initialize real-time STT for session {session_id}: {e}")
            self.session_states[session_id]["realtime_enabled"] = False
    
    async def _handle_realtime_transcript(self, session_id: UUID, transcript_data: Dict[str, Any]):
        """Handle real-time transcript from Deepgram."""
        try:
            if session_id not in self.active_connections:
                return
            
            # Store transcript if it's final
            if transcript_data.get("is_final", False):
                transcript_entry = {
                    "text": transcript_data["text"],
                    "confidence": transcript_data.get("confidence", 0.0),
                    "timestamp": datetime.utcnow().isoformat(),
                    "duration": transcript_data.get("duration", 0.0),
                    "word_count": transcript_data.get("word_count", 0),
                    "provider": "deepgram",
                    "realtime": True
                }
                
                if session_id not in self.session_transcripts:
                    self.session_transcripts[session_id] = []
                self.session_transcripts[session_id].append(transcript_entry)
                
                # Update session state
                if session_id in self.session_states:
                    self.session_states[session_id]["transcripts_generated"] += 1
                
                # Run risk assessment in background
                asyncio.create_task(self._check_transcript_risks(session_id, transcript_data["text"]))
            
            # Send transcript to client (both interim and final)
            await self.broadcast_to_session(
                session_id,
                "transcription",
                {
                    "text": transcript_data["text"],
                    "confidence": transcript_data.get("confidence", 0.0),
                    "is_final": transcript_data.get("is_final", False),
                    "word_count": transcript_data.get("word_count", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                    "provider": "deepgram",
                    "realtime": True
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling real-time transcript for session {session_id}: {e}")
    
    async def _check_transcript_risks(self, session_id: UUID, transcript_text: str):
        """Check transcript for risks and apply guardrails."""
        try:
            # Perform risk assessment
            risk_result = await assess_risk_level(transcript_text)
            
            risk_score = risk_result["risk_score"]
            risk_level = risk_result["risk_level"]
            
            # Update session state with risk info
            if session_id in self.session_states:
                current_highest = self.session_states[session_id]["highest_risk_score"]
                if risk_score > current_highest:
                    self.session_states[session_id]["highest_risk_score"] = risk_score
                    self.session_states[session_id]["risk_level"] = risk_level
            
            # Send risk assessment to client
            await self.broadcast_to_session(
                session_id,
                "risk_assessment",
                {
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "explanation": risk_result["explanation"],
                    "recommendations": risk_result.get("recommendations", []),
                    "transcript_analyzed": transcript_text[:100] + "..." if len(transcript_text) > 100 else transcript_text
                }
            )
            
            # Check if immediate action is required
            if risk_score >= settings.risk_threshold:
                # Lock session for high risk
                if session_id in self.session_states:
                    self.session_states[session_id]["is_locked"] = True
                
                # Send crisis alert
                await self.broadcast_to_session(
                    session_id,
                    "crisis_detected",
                    {
                        "risk_score": risk_score,
                        "risk_level": risk_level,
                        "explanation": risk_result["explanation"],
                        "immediate_action_required": True,
                        "session_locked": True,
                        "emergency_contacts": "Contact emergency services if needed"
                    }
                )
                
                logger.warning(f"CRISIS DETECTED - Session {session_id}: Risk score {risk_score}")
            
            elif risk_level in ["medium", "moderate"]:
                # Send warning for medium risk
                await self.broadcast_to_session(
                    session_id,
                    "risk_warning",
                    {
                        "risk_score": risk_score,
                        "risk_level": risk_level,
                        "explanation": risk_result["explanation"],
                        "recommendations": risk_result.get("recommendations", [])
                    }
                )
        
        except Exception as e:
            logger.error(f"Risk assessment failed for session {session_id}: {e}")
            await self.broadcast_to_session(
                session_id,
                "risk_error",
                {"message": "Risk assessment failed"}
            )
    
    def disconnect(self, session_id: UUID):
        """Remove WebSocket connection and cleanup."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_states:
            del self.session_states[session_id]
        if session_id in self.session_transcripts:
            del self.session_transcripts[session_id]
        
        # Cleanup Deepgram client
        if session_id in self.deepgram_clients:
            try:
                self.deepgram_clients[session_id].close()
            except Exception as e:
                logger.error(f"Error closing Deepgram client for session {session_id}: {e}")
            del self.deepgram_clients[session_id]
        
        # Cleanup audio buffer
        remove_audio_buffer(session_id)
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_message(self, session_id: UUID, message: Dict[str, Any]):
        """Send message to specific session."""
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {e}")
                self.disconnect(session_id)
    
    async def broadcast_to_session(self, session_id: UUID, event_type: str, data: Any):
        """Broadcast event to session."""
        message = {
            "type": event_type,
            "session_id": str(session_id),
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_message(session_id, message)
    
    async def send_audio_to_realtime_stt(self, session_id: UUID, audio_data: bytes):
        """Send audio data to real-time STT service."""
        if session_id in self.deepgram_clients:
            try:
                deepgram_client = self.deepgram_clients[session_id]
                deepgram_client.send_audio(audio_data)
            except Exception as e:
                logger.error(f"Failed to send audio to Deepgram for session {session_id}: {e}")
    
    def get_session_summary(self, session_id: UUID) -> Dict[str, Any]:
        """Get session summary for risk assessment."""
        if session_id not in self.session_transcripts:
            return {}
        
        transcripts = self.session_transcripts[session_id]
        full_text = " ".join([t["text"] for t in transcripts])
        
        return {
            "session_id": str(session_id),
            "transcript_count": len(transcripts),
            "full_transcript": full_text,
            "session_state": self.session_states.get(session_id, {}),
            "realtime_enabled": self.session_states.get(session_id, {}).get("realtime_enabled", False)
        }


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/audio/{session_id}")
async def websocket_audio_stream(websocket: WebSocket, session_id: UUID):
    """Enhanced WebSocket endpoint with real-time STT and risk assessment."""
    
    try:
        # Connect WebSocket
        await manager.connect(websocket, session_id)
        
        # Initialize audio buffer (still needed for fallback processing)
        audio_buffer = get_audio_buffer(session_id)
        
        # Get STT service info
        stt_service = get_stt_service()
        service_info = stt_service.get_service_info()
        
        # Send initial connection message
        await manager.broadcast_to_session(
            session_id,
            "connection_established",
            {
                "session_id": str(session_id),
                "audio_config": {
                    "sample_rate": settings.audio_sample_rate,
                    "chunk_ms": settings.ws_chunk_ms,
                    "chunk_samples": settings.ws_chunk_samples
                },
                "stt_config": {
                    "provider": service_info["active_provider"],
                    "realtime_enabled": manager.session_states[session_id]["realtime_enabled"]
                },
                "risk_threshold": settings.risk_threshold
            }
        )
        
        # Main message loop
        while True:
            try:
                # Check if session is locked
                if manager.session_states.get(session_id, {}).get("is_locked", False):
                    await manager.broadcast_to_session(
                        session_id,
                        "session_locked",
                        {"reason": "Crisis intervention required"}
                    )
                    logger.warning(f"Session {session_id} is locked, closing WebSocket")
                    break
                
                # Receive message
                message = await websocket.receive()
                
                if message["type"] == "websocket.disconnect":
                    break
                
                # Handle different message types
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Audio data received
                        await handle_audio_chunk(session_id, message["bytes"], audio_buffer)
                    elif "text" in message:
                        # Control message received
                        await handle_control_message(session_id, message["text"])
                
                # Update activity
                if session_id in manager.session_states:
                    manager.session_states[session_id]["last_activity"] = datetime.utcnow()
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop for session {session_id}: {e}")
                await manager.broadcast_to_session(
                    session_id,
                    "error",
                    {"message": "Processing error occurred"}
                )
                break
    
    except Exception as e:
        logger.error(f"WebSocket connection failed for session {session_id}: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        # Cleanup
        manager.disconnect(session_id)


async def handle_audio_chunk(session_id: UUID, audio_data: bytes, audio_buffer):
    """Handle incoming audio chunk with both real-time and batch processing."""
    try:
        # Add to audio buffer (for fallback processing)
        buffer_stats = audio_buffer.add_chunk(audio_data)
        
        # Update session state
        if session_id in manager.session_states:
            manager.session_states[session_id]["chunks_received"] += 1
        
        # Send to real-time STT if available
        await manager.send_audio_to_realtime_stt(session_id, audio_data)
        
        # Send buffer status update
        await manager.broadcast_to_session(
            session_id,
            "audio_received",
            {
                "chunk_number": buffer_stats["chunk_number"],
                "duration_seconds": buffer_stats["duration_seconds"],
                "total_samples": buffer_stats["total_samples"],
                "realtime_processing": manager.session_states[session_id]["realtime_enabled"]
            }
        )
        
        # Fallback batch processing (for non-real-time providers or backup)
        if not manager.session_states[session_id]["realtime_enabled"]:
            # Process transcription for recent chunks (every 3rd chunk to avoid overload)
            if buffer_stats["chunk_number"] % 3 == 0:
                await process_transcription_batch(session_id, audio_buffer)
    
    except Exception as e:
        logger.error(f"Failed to handle audio chunk for session {session_id}: {e}")
        await manager.broadcast_to_session(
            session_id,
            "error",
            {"message": "Failed to process audio chunk"}
        )


async def process_transcription_batch(session_id: UUID, audio_buffer):
    """Process transcription and risk assessment for recent audio chunks (fallback method)."""
    try:
        # Get combined audio file for recent chunks
        audio_file = audio_buffer.get_combined_audio_file(last_n_chunks=3)
        
        if not audio_file:
            return
        
        # Transcribe audio using batch API
        transcription_result = await transcribe_audio_file(audio_file)
        
        if not transcription_result.get("has_speech", False):
            # No speech detected, skip
            return
        
        transcript_text = transcription_result["text"]
        
        # Store transcript in memory
        transcript_data = {
            "text": transcript_text,
            "confidence": transcription_result.get("confidence"),
            "timestamp": datetime.utcnow().isoformat(),
            "chunk_index": audio_buffer.chunk_counter,
            "duration": transcription_result.get("duration"),
            "provider": transcription_result.get("provider", "unknown"),
            "realtime": False
        }
        
        if session_id not in manager.session_transcripts:
            manager.session_transcripts[session_id] = []
        manager.session_transcripts[session_id].append(transcript_data)
        
        # Update session state
        if session_id in manager.session_states:
            manager.session_states[session_id]["transcripts_generated"] += 1
        
        # Send transcription to client
        await manager.broadcast_to_session(
            session_id,
            "transcription",
            {
                "text": transcript_text,
                "confidence": transcription_result.get("confidence"),
                "chunk_index": audio_buffer.chunk_counter,
                "word_count": transcription_result.get("word_count", 0),
                "timestamp": transcript_data["timestamp"],
                "provider": transcription_result.get("provider", "unknown"),
                "realtime": False
            }
        )
        
        # Run risk assessment in background
        asyncio.create_task(manager._check_transcript_risks(session_id, transcript_text))
        
        # Clean up temporary audio file
        import os
        try:
            os.remove(audio_file)
        except:
            pass
    
    except Exception as e:
        logger.error(f"Transcription batch processing failed for session {session_id}: {e}")
        await manager.broadcast_to_session(
            session_id,
            "transcription_error",
            {"message": "Transcription processing failed"}
        )


async def handle_control_message(session_id: UUID, message_text: str):
    """Handle control messages from client."""
    try:
        control_data = json.loads(message_text)
        command = control_data.get("command")
        
        if command == "get_session_summary":
            summary = manager.get_session_summary(session_id)
            await manager.broadcast_to_session(
                session_id,
                "session_summary",
                summary
            )
        
        elif command == "reset_session":
            # Clear transcripts and reset state
            if session_id in manager.session_transcripts:
                manager.session_transcripts[session_id] = []
            if session_id in manager.session_states:
                manager.session_states[session_id].update({
                    "transcripts_generated": 0,
                    "is_locked": False,
                    "risk_level": "low",
                    "highest_risk_score": 0.0
                })
            
            await manager.broadcast_to_session(
                session_id,
                "session_reset",
                {"message": "Session reset successfully"}
            )
        
        elif command == "get_stt_status":
            stt_service = get_stt_service()
            service_info = stt_service.get_service_info()
            
            await manager.broadcast_to_session(
                session_id,
                "stt_status",
                service_info
            )
        
    except json.JSONDecodeError:
        await manager.broadcast_to_session(
            session_id,
            "error",
            {"message": "Invalid control message format"}
        )
    except Exception as e:
        logger.error(f"Control message handling failed for session {session_id}: {e}")


@router.get("/ws/sessions")
async def get_active_sessions():
    """Get information about active WebSocket sessions."""
    return {
        "active_sessions": len(manager.active_connections),
        "sessions": {
            str(session_id): {
                **state,
                "connected_at": state["connected_at"].isoformat(),
                "last_activity": state["last_activity"].isoformat(),
                "transcript_count": len(manager.session_transcripts.get(session_id, [])),
                "realtime_enabled": state.get("realtime_enabled", False),
                "stt_provider": state.get("stt_provider", "unknown")
            }
            for session_id, state in manager.session_states.items()
        }
    }