"""WebSocket route for real-time audio streaming with multiple STT providers."""

import asyncio
import json
import logging
import os
from typing import Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import get_settings
from services.audio_buffer import get_audio_buffer, remove_audio_buffer
from services.risk_classifier import assess_risk_level

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for audio streaming."""
    
    def __init__(self):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.session_states: Dict[UUID, Dict[str, Any]] = {}
        self.session_transcripts: Dict[UUID, list] = {}  # In-memory transcript storage
        self._ws_lock: Dict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)  # Serialize WebSocket writes
        self.stt_service = None
        self._initialize_stt_service()
    
    def _initialize_stt_service(self):
        """Initialize STT service based on provider."""
        try:
            # Always use AssemblyAI
            from services.assemblyai_service import get_assemblyai_service
            self.stt_service = get_assemblyai_service()
            logger.info(f"Initialized AssemblyAI STT service for WebSocket manager")
                
        except Exception as e:
            logger.error(f"Failed to initialize AssemblyAI service: {e}")
            self.stt_service = None
    
    async def connect(self, websocket: WebSocket, session_id: UUID):
        """Accept WebSocket connection and initialize session."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_states[session_id] = {
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "chunks_received": 0,
            "transcripts_generated": 0,
            "is_locked": False,
            "risk_level": "low",
            "highest_risk_score": 0.0
        }
        self.session_transcripts[session_id] = []
        
        logger.info(f"WebSocket connected for session {session_id}")
    
    def disconnect(self, session_id: UUID):
        """Remove WebSocket connection and cleanup."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_states:
            del self.session_states[session_id]
        if session_id in self.session_transcripts:
            del self.session_transcripts[session_id]
        
        # Cleanup audio buffer
        remove_audio_buffer(session_id)
        
        # Stop STT transcription
        if self.stt_service:
            asyncio.create_task(self.stt_service.stop_transcription(session_id))
        
        logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_message(self, session_id: UUID, message: Dict[str, Any]):
        """Send message to specific session with write serialization."""
        if session_id not in self.active_connections:
            return
            
        try:
            # Serialize all writes to prevent WebSocket race conditions
            async with self._ws_lock[session_id]:
                await self.active_connections[session_id].send_text(json.dumps(message))
        except Exception as e:
            # Use logger.exception to see the actual error details
            logger.exception(f"Failed to send message to session {session_id}: {e}")
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
            "session_state": self.session_states.get(session_id, {})
        }


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/audio/{session_id}")
async def websocket_audio_stream(websocket: WebSocket, session_id: UUID):
    """WebSocket endpoint for real-time audio streaming with STT transcription."""
    
    # Get fresh settings for this connection
    settings = get_settings()
    
    try:
        # Connect WebSocket
        await manager.connect(websocket, session_id)
        
        # Initialize audio buffer
        audio_buffer = get_audio_buffer(session_id)
        
        # Initialize STT service
        stt_service = manager.stt_service
        
        if not stt_service or not stt_service.is_available():
            await manager.broadcast_to_session(
                session_id,
                "error",
                {"message": f"{settings.stt_provider.upper()} STT service not available. Check API key configuration."}
            )
            logger.error(f"STT service not available for session {session_id}")
            return
        
        # Check concurrent session limits for free tier
        MAX_CONCURRENT_ASSEMBLYAI = 1  # Free plan allows exactly one live stream
        if stt_service.get_connection_count() >= MAX_CONCURRENT_ASSEMBLYAI:
            await manager.broadcast_to_session(
                session_id,
                "error",
                {"message": "Only one concurrent realtime session allowed on free tier. Close other tabs or wait 15 seconds."}
            )
            logger.warning(f"Rejected session {session_id} - too many concurrent AssemblyAI connections")
            return
        
        # Set up STT callbacks
        async def on_transcript_message(transcript_data: Dict[str, Any]):
            """Handle transcript messages from STT service."""
            try:
                if transcript_data.get("text"):
                    # Store transcript
                    transcript_entry = {
                        "text": transcript_data["text"],
                        "confidence": transcript_data.get("confidence", 0.0),
                        "is_final": transcript_data.get("is_final", False),
                        "timestamp": datetime.utcnow().isoformat(),
                        "start": transcript_data.get("start", 0.0),
                        "duration": transcript_data.get("duration", 0.0)
                    }
                    
                    # Only store final transcripts
                    if transcript_data.get("is_final", False):
                        if session_id not in manager.session_transcripts:
                            manager.session_transcripts[session_id] = []
                        manager.session_transcripts[session_id].append(transcript_entry)
                        
                        # Update session state
                        if session_id in manager.session_states:
                            manager.session_states[session_id]["transcripts_generated"] += 1
                        
                        # Run risk assessment for final transcripts
                        asyncio.create_task(check_transcript_risks(session_id, transcript_data["text"]))
                    
                    # Send transcription to client
                    await manager.broadcast_to_session(
                        session_id,
                        "transcription",
                        {
                            "text": transcript_data["text"],
                            "confidence": transcript_data.get("confidence", 0.0),
                            "is_final": transcript_data.get("is_final", False),
                            "timestamp": transcript_entry["timestamp"]
                        }
                    )
                    
                    logger.debug(f"Sent transcription to session {session_id}: '{transcript_data['text'][:50]}...' (final: {transcript_data.get('is_final', False)})")
                    
            except Exception as e:
                logger.error(f"Error processing transcript for session {session_id}: {e}")
        
        def on_stt_error(error_message: str):
            """Handle STT errors."""
            logger.error(f"STT error for session {session_id}: {error_message}")
            asyncio.create_task(manager.broadcast_to_session(
                session_id,
                "transcription_error",
                {"message": f"Transcription error: {error_message}"}
            ))
        
        # Start real-time transcription
        transcription_started = await stt_service.start_real_time_transcription(
            session_id=session_id,
            on_message_callback=on_transcript_message,
            on_error_callback=on_stt_error
        )
        
        if not transcription_started:
            await manager.broadcast_to_session(
                session_id,
                "error",
                {"message": "Failed to start real-time transcription"}
            )
            logger.error(f"Failed to start STT transcription for session {session_id}")
            return

        # Send initial connection message ONLY after STT service confirms it's ready
        # (AssemblyAI v3 now waits for "Begin" frame before returning True)
        await manager.broadcast_to_session(
            session_id,
            "connection_established",
            {
                "session_id": str(session_id),
                "audio_config": {
                    "sample_rate": settings.audio_sample_rate,
                    "chunk_ms": settings.ws_chunk_ms,
                    "chunk_samples": settings.ws_chunk_samples,
                    "encoding": "linear16"
                },
                "risk_threshold": settings.risk_threshold,
                "stt_provider": settings.stt_provider,
                "stt_state": "ready"  # ← ADD THIS LINE!
            }
        )
        logger.info(f"connection_established sent to session {session_id} after STT confirmation")
        
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
                        await handle_audio_chunk(session_id, message["bytes"], audio_buffer, stt_service)
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


async def handle_audio_chunk(session_id: UUID, audio_data: bytes, audio_buffer, stt_service):
    """Handle incoming audio chunk."""
    try:
        # Add to audio buffer
        buffer_stats = audio_buffer.add_chunk(audio_data)
        
        # Update session state
        if session_id in manager.session_states:
            manager.session_states[session_id]["chunks_received"] += 1
        
        # Send audio data to STT service
        await stt_service.send_audio(session_id, audio_data)
        
        # Send buffer status update
        await manager.broadcast_to_session(
            session_id,
            "audio_received",
            {
                "chunk_number": buffer_stats["chunk_number"],
                "duration_seconds": buffer_stats["duration_seconds"],
                "total_samples": buffer_stats["total_samples"]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to handle audio chunk for session {session_id}: {e}")
        await manager.broadcast_to_session(
            session_id,
            "error",
            {"message": "Failed to process audio chunk"}
        )


async def check_transcript_risks(session_id: UUID, transcript_text: str):
    """Check transcript for risks and apply guardrails."""
    try:
        # Get fresh settings for risk threshold
        settings = get_settings()
        
        # Perform risk assessment
        risk_result = await assess_risk_level(transcript_text)
        
        risk_score = risk_result["risk_score"]
        risk_level = risk_result["risk_level"]
        
        # Update session state with risk info
        if session_id in manager.session_states:
            current_highest = manager.session_states[session_id]["highest_risk_score"]
            if risk_score > current_highest:
                manager.session_states[session_id]["highest_risk_score"] = risk_score
                manager.session_states[session_id]["risk_level"] = risk_level
        
        # Send risk assessment to client
        await manager.broadcast_to_session(
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
            if session_id in manager.session_states:
                manager.session_states[session_id]["is_locked"] = True
            
            # Send crisis alert
            await manager.broadcast_to_session(
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
            await manager.broadcast_to_session(
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
        await manager.broadcast_to_session(
            session_id,
            "risk_error",
            {"message": "Risk assessment failed"}
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
        
        elif command == "ping":
            # Handle ping/pong for connection testing
            await manager.broadcast_to_session(
                session_id,
                "pong",
                {"timestamp": control_data.get("timestamp", datetime.utcnow().isoformat())}
            )
        
        elif command == "get_status":
            # Send current session status
            session_state = manager.session_states.get(session_id, {})
            await manager.broadcast_to_session(
                session_id,
                "status_update",
                {
                    "session_state": {
                        **session_state,
                        "connected_at": session_state.get("connected_at", datetime.utcnow()).isoformat(),
                        "last_activity": session_state.get("last_activity", datetime.utcnow()).isoformat()
                    },
                    "transcript_count": len(manager.session_transcripts.get(session_id, []))
                }
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
    settings = get_settings()  # Get fresh settings
    
    stt_connections = 0
    if manager.stt_service:
        stt_connections = manager.stt_service.get_connection_count()
    
    return {
        "active_sessions": len(manager.active_connections),
        "stt_connections": stt_connections,
        "stt_provider": settings.stt_provider,
        "sessions": {
            str(session_id): {
                **state,
                "connected_at": state["connected_at"].isoformat(),
                "last_activity": state["last_activity"].isoformat(),
                "transcript_count": len(manager.session_transcripts.get(session_id, []))
            }
            for session_id, state in manager.session_states.items()
        }
    }


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    settings = get_settings()
    
    stt_connections = 0
    if manager.stt_service:
        stt_connections = manager.stt_service.get_connection_count()
    
    return {
        "active_connections": len(manager.active_connections),
        "active_sessions": len(manager.session_states),
        "stt_connections": stt_connections,
        "stt_provider": settings.stt_provider,
        "total_transcripts": sum(len(transcripts) for transcripts in manager.session_transcripts.values()),
        "sessions": {
            str(session_id): {
                "chunks_received": state["chunks_received"],
                "transcripts_generated": state["transcripts_generated"],
                "risk_level": state["risk_level"],
                "is_locked": state["is_locked"],
                "connected_duration_seconds": (datetime.utcnow() - state["connected_at"]).total_seconds()
            }
            for session_id, state in manager.session_states.items()
        }
    }


@router.post("/ws/test-message/{session_id}")
async def test_message_to_session(session_id: UUID, message: str = "Test message"):
    """Test endpoint to send a message to a specific session (for debugging)."""
    if session_id in manager.active_connections:
        await manager.broadcast_to_session(
            session_id,
            "test_message",
            {"message": message, "sent_at": datetime.utcnow().isoformat()}
        )
        return {"success": True, "message": f"Test message sent to session {session_id}"}
    else:
        return {"success": False, "error": "Session not found"}, 404


@router.post("/ws/disconnect/{session_id}")
async def force_disconnect_session(session_id: UUID):
    """Force disconnect a WebSocket session (admin endpoint)."""
    if session_id in manager.active_connections:
        await manager.broadcast_to_session(
            session_id,
            "force_disconnect",
            {"reason": "Session terminated by administrator"}
        )
        manager.disconnect(session_id)
        return {"message": f"Session {session_id} disconnected"}
    else:
        return {"error": "Session not found"}, 404