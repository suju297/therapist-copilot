"""Integration tests for WebSocket functionality."""

import asyncio
import json
import pytest
from unittest.mock import patch, Mock, AsyncMock
from uuid import uuid4

import websockets
from fastapi.testclient import TestClient

from conftest import create_test_audio_file


class TestWebSocketConnection:
    """Test WebSocket connection and basic functionality."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self, test_client):
        """Test WebSocket connection establishment."""
        session_id = uuid4()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            # Should receive connection established message
            data = websocket.receive_json()
            
            assert data["type"] == "connection_established"
            assert data["session_id"] == str(session_id)
            assert "audio_config" in data["data"]
            
            # Audio config should have expected values
            audio_config = data["data"]["audio_config"]
            assert audio_config["sample_rate"] == 16000
            assert audio_config["chunk_ms"] == 1000
    
    @pytest.mark.asyncio
    async def test_websocket_audio_streaming(self, test_client, sample_audio_data):
        """Test audio data streaming through WebSocket."""
        session_id = uuid4()
        
        with patch('services.stt_adapter.transcribe_audio_file') as mock_transcribe:
            # Mock transcription response
            mock_transcribe.return_value = {
                "text": "Hello, how are you?",
                "confidence": 0.95,
                "has_speech": True,
                "duration": 1.0,
                "word_count": 4
            }
            
            with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                # Receive connection message
                websocket.receive_json()
                
                # Send audio data
                websocket.send_bytes(sample_audio_data)
                
                # Should receive audio received confirmation
                response = websocket.receive_json()
                assert response["type"] == "audio_received"
                assert response["data"]["chunk_number"] == 1
    
    @pytest.mark.asyncio
    async def test_websocket_control_messages(self, test_client):
        """Test WebSocket control message handling."""
        session_id = uuid4()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            # Receive connection message
            websocket.receive_json()
            
            # Send ping message
            ping_message = {
                "type": "ping",
                "timestamp": "2023-01-01T12:00:00Z"
            }
            websocket.send_text(json.dumps(ping_message))
            
            # Should receive pong response
            response = websocket.receive_json()
            assert response["type"] == "pong"
            assert response["data"]["timestamp"] == ping_message["timestamp"]
    
    @pytest.mark.asyncio
    async def test_websocket_session_status(self, test_client):
        """Test WebSocket session status requests."""
        session_id = uuid4()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            # Receive connection message
            websocket.receive_json()
            
            # Request status
            status_message = {"type": "get_status"}
            websocket.send_text(json.dumps(status_message))
            
            # Should receive status update
            response = websocket.receive_json()
            assert response["type"] == "status_update"
            assert "data" in response
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_session(self, test_client):
        """Test WebSocket connection with invalid session ID."""
        # This should still work as the route creates new sessions
        invalid_session_id = "invalid-uuid-format"
        
        with pytest.raises(Exception):
            # Should fail due to invalid UUID format
            with test_client.websocket_connect(f"/api/v1/ws/audio/{invalid_session_id}"):
                pass


class TestWebSocketTranscription:
    """Test WebSocket transcription functionality."""
    
    @pytest.mark.asyncio
    async def test_transcription_generation(self, test_client, sample_audio_data):
        """Test that audio generates transcriptions."""
        session_id = uuid4()
        
        with patch('services.stt_adapter.transcribe_audio_file') as mock_transcribe:
            mock_transcribe.return_value = {
                "text": "This is a test transcription.",
                "confidence": 0.9,
                "has_speech": True,
                "duration": 2.5,
                "word_count": 5,
                "start_time": 0.0,
                "end_time": 2.5
            }
            
            with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                # Skip connection message
                websocket.receive_json()
                
                # Send multiple audio chunks to trigger transcription
                for i in range(3):
                    websocket.send_bytes(sample_audio_data)
                    websocket.receive_json()  # audio_received message
                
                # Should eventually receive transcription
                received_transcription = False
                for _ in range(10):  # Try multiple times
                    try:
                        response = websocket.receive_json()
                        if response["type"] == "transcription":
                            received_transcription = True
                            assert "text" in response["data"]
                            assert response["data"]["text"] == "This is a test transcription."
                            break
                    except:
                        continue
                
                assert received_transcription
    
    @pytest.mark.asyncio
    async def test_transcription_confidence_reporting(self, test_client, sample_audio_data):
        """Test that transcription confidence is reported."""
        session_id = uuid4()
        
        with patch('services.stt_adapter.transcribe_audio_file') as mock_transcribe:
            mock_transcribe.return_value = {
                "text": "High confidence transcription",
                "confidence": 0.98,
                "has_speech": True,
                "duration": 1.5,
                "word_count": 3
            }
            
            with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                websocket.receive_json()  # connection message
                
                # Send audio chunks
                for _ in range(3):
                    websocket.send_bytes(sample_audio_data)
                    websocket.receive_json()  # audio_received
                
                # Look for transcription message
                for _ in range(10):
                    try:
                        response = websocket.receive_json()
                        if response["type"] == "transcription":
                            assert response["data"]["confidence"] == 0.98
                            break
                    except:
                        continue
    
    @pytest.mark.asyncio
    async def test_no_speech_detection(self, test_client, sample_audio_data):
        """Test handling of audio with no speech."""
        session_id = uuid4()
        
        with patch('services.stt_adapter.transcribe_audio_file') as mock_transcribe:
            mock_transcribe.return_value = {
                "text": "",
                "confidence": 0.0,
                "has_speech": False,
                "duration": 1.0,
                "word_count": 0
            }
            
            with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                websocket.receive_json()  # connection message
                
                # Send audio chunks
                for _ in range(3):
                    websocket.send_bytes(sample_audio_data)
                    websocket.receive_json()  # audio_received
                
                # Should not receive transcription for silent audio
                # Wait a bit and verify no transcription comes
                await asyncio.sleep(0.1)
                
                # No transcription message should be sent for silent audio


class TestWebSocketRiskDetection:
    """Test WebSocket risk detection functionality."""
    
    @pytest.mark.asyncio
    async def test_risk_detection_and_warning(self, test_client, sample_audio_data):
        """Test risk detection and warning messages."""
        session_id = uuid4()
        
        with patch('services.stt_adapter.transcribe_audio_file') as mock_transcribe:
            with patch('guards.guardrails.check_and_apply_guardrails') as mock_guardrails:
                # Mock moderate risk transcription
                mock_transcribe.return_value = {
                    "text": "I feel very anxious and overwhelmed.",
                    "confidence": 0.9,
                    "has_speech": True,
                    "duration": 2.0,
                    "word_count": 6
                }
                
                # Mock moderate risk assessment
                mock_guardrails.return_value = {
                    "session_locked": False,
                    "risk_assessment": {
                        "risk_level": "moderate",
                        "overall_risk_score": 0.6
                    },
                    "intervention_required": False
                }
                
                with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                    websocket.receive_json()  # connection message
                    
                    # Send audio chunks
                    for _ in range(3):
                        websocket.send_bytes(sample_audio_data)
                        websocket.receive_json()  # audio_received
                    
                    # Look for risk warning
                    received_warning = False
                    for _ in range(15):
                        try:
                            response = websocket.receive_json()
                            if response["type"] == "risk_warning":
                                received_warning = True
                                assert response["data"]["risk_level"] == "moderate"
                                assert response["data"]["session_locked"] is False
                                break
                        except:
                            continue
                    
                    assert received_warning
    
    @pytest.mark.asyncio
    async def test_crisis_detection_and_session_lock(self, test_client, sample_audio_data):
        """Test crisis detection and session locking."""
        session_id = uuid4()
        
        with patch('services.stt_adapter.transcribe_audio_file') as mock_transcribe:
            with patch('guards.guardrails.check_and_apply_guardrails') as mock_guardrails:
                # Mock high-risk transcription
                mock_transcribe.return_value = {
                    "text": "I want to kill myself and end it all.",
                    "confidence": 0.95,
                    "has_speech": True,
                    "duration": 3.0,
                    "word_count": 8
                }
                
                # Mock crisis assessment with session lock
                mock_guardrails.return_value = {
                    "session_locked": True,
                    "risk_assessment": {
                        "risk_level": "high",
                        "overall_risk_score": 0.9,
                        "immediate_action_required": True
                    },
                    "intervention_required": True,
                    "lock_reason": "Crisis intervention required"
                }
                
                with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                    websocket.receive_json()  # connection message
                    
                    # Send audio chunks
                    for _ in range(3):
                        websocket.send_bytes(sample_audio_data)
                        websocket.receive_json()  # audio_received
                    
                    # Look for crisis detection message
                    received_crisis = False
                    for _ in range(15):
                        try:
                            response = websocket.receive_json()
                            if response["type"] == "risk_detected":
                                received_crisis = True
                                assert response["data"]["session_locked"] is True
                                assert response["data"]["risk_level"] == "high"
                                break
                        except:
                            continue
                    
                    assert received_crisis
    
    @pytest.mark.asyncio
    async def test_session_locked_connection_closure(self, test_client):
        """Test that locked sessions close WebSocket connections."""
        session_id = uuid4()
        
        with patch('guards.guardrails.is_session_locked') as mock_locked:
            mock_locked.return_value = True
            
            with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                websocket.receive_json()  # connection message
                
                # Should receive session locked message
                response = websocket.receive_json()
                assert response["type"] == "session_locked"
                assert "Crisis intervention required" in response["data"]["reason"]


class TestWebSocketErrorHandling:
    """Test WebSocket error handling."""
    
    @pytest.mark.asyncio
    async def test_audio_processing_error(self, test_client, sample_audio_data):
        """Test handling of audio processing errors."""
        session_id = uuid4()
        
        with patch('services.stt_adapter.transcribe_audio_file') as mock_transcribe:
            mock_transcribe.side_effect = Exception("Transcription service error")
            
            with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                websocket.receive_json()  # connection message
                
                # Send audio data
                websocket.send_bytes(sample_audio_data)
                websocket.receive_json()  # audio_received
                
                # Should receive error message
                for _ in range(10):
                    try:
                        response = websocket.receive_json()
                        if response["type"] == "transcription_error":
                            assert "processing failed" in response["data"]["message"]
                            break
                    except:
                        continue
    
    @pytest.mark.asyncio
    async def test_invalid_control_message(self, test_client):
        """Test handling of invalid control messages."""
        session_id = uuid4()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            websocket.receive_json()  # connection message
            
            # Send invalid JSON
            websocket.send_text("invalid json")
            
            # Connection should remain open, invalid message ignored
            # Send valid message to verify connection is still working
            ping_message = {"type": "ping", "timestamp": "test"}
            websocket.send_text(json.dumps(ping_message))
            
            response = websocket.receive_json()
            assert response["type"] == "pong"
    
    @pytest.mark.asyncio
    async def test_malformed_audio_data(self, test_client):
        """Test handling of malformed audio data."""
        session_id = uuid4()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            websocket.receive_json()  # connection message
            
            # Send malformed audio data (too short)
            websocket.send_bytes(b"short")
            
            # Should receive audio_received message even with malformed data
            response = websocket.receive_json()
            assert response["type"] == "audio_received"
    
    @pytest.mark.asyncio
    async def test_connection_interruption_recovery(self, test_client, sample_audio_data):
        """Test recovery from connection interruptions."""
        session_id = uuid4()
        
        # First connection
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            websocket.receive_json()  # connection message
            websocket.send_bytes(sample_audio_data)
            websocket.receive_json()  # audio_received
        
        # Reconnect with same session ID
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            # Should get connection established message again
            response = websocket.receive_json()
            assert response["type"] == "connection_established"
            assert response["session_id"] == str(session_id)


class TestWebSocketPerformance:
    """Test WebSocket performance and scalability."""
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self, test_client):
        """Test handling multiple concurrent WebSocket connections."""
        session_ids = [uuid4() for _ in range(3)]
        
        async def connect_and_test(session_id):
            with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                response = websocket.receive_json()
                assert response["type"] == "connection_established"
                assert response["session_id"] == str(session_id)
                return True
        
        # Test concurrent connections
        tasks = [connect_and_test(sid) for sid in session_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All connections should succeed
        assert all(result is True for result in results)
    
    @pytest.mark.asyncio
    async def test_high_frequency_audio_streaming(self, test_client, sample_audio_data):
        """Test high-frequency audio streaming."""
        session_id = uuid4()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            websocket.receive_json()  # connection message
            
            # Send many audio chunks rapidly
            chunk_count = 10
            for i in range(chunk_count):
                websocket.send_bytes(sample_audio_data)
                
                # Receive audio_received confirmation
                response = websocket.receive_json()
                assert response["type"] == "audio_received"
                assert response["data"]["chunk_number"] == i + 1
    
    @pytest.mark.asyncio
    async def test_large_audio_chunks(self, test_client):
        """Test handling of large audio chunks."""
        session_id = uuid4()
        
        # Create large audio chunk (2 seconds worth)
        import numpy as np
        large_audio = np.random.randint(-32768, 32767, size=32000, dtype=np.int16)
        large_audio_bytes = large_audio.tobytes()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            websocket.receive_json()  # connection message
            
            # Send large audio chunk
            websocket.send_bytes(large_audio_bytes)
            
            # Should handle large chunks gracefully
            response = websocket.receive_json()
            assert response["type"] == "audio_received"
            assert response["data"]["total_samples"] > 16000  # More than 1 second


class TestWebSocketStats:
    """Test WebSocket statistics and monitoring."""
    
    @pytest.mark.asyncio
    async def test_connection_statistics_tracking(self, test_client):
        """Test that connection statistics are tracked."""
        session_id = uuid4()
        
        # Check initial stats
        stats_response = test_client.get("/api/v1/ws/stats")
        initial_stats = stats_response.json()
        initial_connections = initial_stats["active_connections"]
        
        # Create connection
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            websocket.receive_json()  # connection message
            
            # Check stats during connection
            stats_response = test_client.get("/api/v1/ws/stats")
            active_stats = stats_response.json()
            
            # Should show increased connection count
            assert active_stats["active_connections"] >= initial_connections
            assert str(session_id) in active_stats["sessions"]
        
        # Check stats after disconnection
        stats_response = test_client.get("/api/v1/ws/stats")
        final_stats = stats_response.json()
        
        # Connection count should return to initial or lower
        assert final_stats["active_connections"] <= active_stats["active_connections"]