"""Performance and load tests for the Therapist Copilot system."""

import asyncio
import concurrent.futures
import time
import pytest
from unittest.mock import patch, Mock
from uuid import uuid4

import numpy as np
from fastapi.testclient import TestClient


class TestAPIPerformance:
    """Test API endpoint performance."""
    
    @pytest.mark.slow
    def test_health_check_response_time(self, test_client):
        """Test health check endpoint response time."""
        # Warm up
        test_client.get("/api/v1/health/quick")
        
        # Measure response time
        start_time = time.time()
        response = test_client.get("/api/v1/health/quick")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 0.1  # Should respond within 100ms
    
    @pytest.mark.slow
    def test_session_list_performance(self, test_client, auth_headers):
        """Test session list endpoint performance with large datasets."""
        # Mock large dataset
        with patch('routes.draft.select') as mock_select:
            # Create mock sessions
            mock_sessions = []
            for i in range(1000):
                mock_session = Mock()
                mock_session.id = uuid4()
                mock_session.created_at = time.time()
                mock_session.updated_at = time.time()
                mock_session.status = "active"
                mock_session.therapist_id = f"therapist_{i}"
                mock_session.client_name = f"Client {i}"
                mock_session.session_type = "individual"
                mock_session.locked_flag = False
                mock_session.risk_level = "low"
                mock_session.draft_blob = None
                mock_session.word_count = 100
                mock_session.duration_minutes = 50
                mock_sessions.append(mock_session)
            
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_sessions[:50]  # First 50
            mock_select.return_value.offset.return_value.limit.return_value.order_by.return_value = mock_result
            
            start_time = time.time()
            response = test_client.get("/api/v1/sessions", headers=auth_headers)
            end_time = time.time()
            
            assert response.status_code == 200
            response_time = end_time - start_time
            assert response_time < 1.0  # Should respond within 1 second
    
    @pytest.mark.slow
    def test_concurrent_api_requests(self, test_client, auth_headers):
        """Test handling of concurrent API requests."""
        def make_request():
            return test_client.get("/api/v1/health/quick").status_code == 200
        
        # Test with multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(results)
        assert len(results) == 50


class TestDatabasePerformance:
    """Test database operation performance."""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_transcript_storage(self, async_session, sample_session):
        """Test storing large numbers of transcripts."""
        from services.transcript_store import TranscriptStore
        from models.transcript import TranscriptCreate
        
        store = TranscriptStore(async_session)
        
        # Create many transcripts
        transcripts = []
        for i in range(100):
            transcript_create = TranscriptCreate(
                session_id=sample_session.id,
                text=f"This is transcript number {i} with some sample content for testing.",
                speaker="client" if i % 2 else "therapist",
                confidence=0.9,
                chunk_index=i
            )
            transcripts.append(transcript_create)
        
        # Measure batch insertion time
        start_time = time.time()
        
        stored_transcripts = []
        for transcript_create in transcripts:
            transcript = await store.add_transcript(transcript_create, process_deidentification=False)
            stored_transcripts.append(transcript)
        
        end_time = time.time()
        
        # Verify all transcripts were stored
        assert len(stored_transcripts) == 100
        
        # Should complete within reasonable time (10ms per transcript)
        total_time = end_time - start_time
        assert total_time < 10.0  # 10 seconds max for 100 transcripts
        
        # Test retrieval performance
        start_time = time.time()
        retrieved_transcripts = await store.get_session_transcripts(sample_session.id)
        end_time = time.time()
        
        retrieval_time = end_time - start_time
        assert retrieval_time < 1.0  # Should retrieve within 1 second
        assert len(retrieved_transcripts) == 100
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, async_session):
        """Test concurrent database operations."""
        from models.session import Session
        
        async def create_session(session_id):
            session = Session(
                id=session_id,
                therapist_id="test_therapist",
                status="active"
            )
            async_session.add(session)
            await async_session.commit()
            return session.id
        
        # Create sessions concurrently
        session_ids = [uuid4() for _ in range(20)]
        tasks = [create_session(sid) for sid in session_ids]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Check that most operations succeeded
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 15  # At least 75% success rate
        
        # Should complete within reasonable time
        total_time = end_time - start_time
        assert total_time < 5.0  # 5 seconds max
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_text_search_performance(self, async_session, sample_session):
        """Test text search performance with large datasets."""
        from services.transcript_store import TranscriptStore
        from models.transcript import TranscriptCreate
        
        store = TranscriptStore(async_session)
        
        # Create transcripts with various content
        test_phrases = [
            "I feel anxious about work",
            "Sleep has been difficult lately",
            "Family relationships are stressful",
            "I'm worried about my health",
            "Money concerns keep me up at night",
            "I feel overwhelmed by everything",
            "Social situations make me nervous",
            "I have trouble concentrating",
            "My mood has been very low",
            "I feel disconnected from others"
        ]
        
        # Create many transcripts with repeated phrases
        for i in range(200):
            phrase = test_phrases[i % len(test_phrases)]
            transcript_create = TranscriptCreate(
                session_id=sample_session.id,
                text=f"{phrase} - transcript {i}",
                chunk_index=i
            )
            await store.add_transcript(transcript_create)
        
        # Test search performance
        search_terms = ["anxious", "sleep", "family", "overwhelmed"]
        
        for term in search_terms:
            start_time = time.time()
            results = await store.search_transcripts(sample_session.id, term)
            end_time = time.time()
            
            search_time = end_time - start_time
            assert search_time < 0.5  # Should search within 500ms
            assert len(results) > 0  # Should find matches


class TestWebSocketPerformance:
    """Test WebSocket performance under load."""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self, test_client, sample_audio_data):
        """Test WebSocket message throughput."""
        session_id = uuid4()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            # Skip connection message
            websocket.receive_json()
            
            # Send many audio chunks and measure throughput
            chunk_count = 100
            start_time = time.time()
            
            for i in range(chunk_count):
                websocket.send_bytes(sample_audio_data)
                response = websocket.receive_json()
                assert response["type"] == "audio_received"
            
            end_time = time.time()
            
            total_time = end_time - start_time
            throughput = chunk_count / total_time
            
            # Should handle at least 10 chunks per second
            assert throughput >= 10.0
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multiple_websocket_connections(self, test_client, sample_audio_data):
        """Test performance with multiple WebSocket connections."""
        session_ids = [uuid4() for _ in range(5)]
        
        async def test_connection(session_id):
            with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                # Skip connection message
                websocket.receive_json()
                
                # Send several audio chunks
                for _ in range(10):
                    websocket.send_bytes(sample_audio_data)
                    response = websocket.receive_json()
                    assert response["type"] == "audio_received"
                
                return True
        
        # Test concurrent connections
        start_time = time.time()
        tasks = [test_connection(sid) for sid in session_ids]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # All connections should succeed
        assert all(results)
        
        # Should complete within reasonable time
        total_time = end_time - start_time
        assert total_time < 10.0  # 10 seconds max
    
    @pytest.mark.slow
    def test_websocket_memory_usage(self, test_client, sample_audio_data):
        """Test WebSocket memory usage with continuous streaming."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        session_id = uuid4()
        
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            websocket.receive_json()  # connection message
            
            # Send many audio chunks
            for i in range(500):
                websocket.send_bytes(sample_audio_data)
                websocket.receive_json()  # audio_received
                
                # Check memory usage periodically
                if i % 100 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_increase = current_memory - initial_memory
                    
                    # Memory increase should be reasonable (< 100MB)
                    assert memory_increase < 100
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        assert total_memory_increase < 150  # 150MB max


class TestAudioProcessingPerformance:
    """Test audio processing performance."""
    
    @pytest.mark.slow
    def test_audio_buffer_performance(self, sample_audio_data):
        """Test audio buffer performance with high-frequency data."""
        from services.audio_buffer import AudioBuffer
        
        session_id = uuid4()
        buffer = AudioBuffer(session_id)
        
        # Test adding many chunks
        chunk_count = 1000
        start_time = time.time()
        
        for i in range(chunk_count):
            result = buffer.add_chunk(sample_audio_data)
            assert result["chunk_number"] == i + 1
        
        end_time = time.time()
        
        total_time = end_time - start_time
        throughput = chunk_count / total_time
        
        # Should handle at least 100 chunks per second
        assert throughput >= 100.0
        
        # Test buffer stats performance
        start_time = time.time()
        stats = buffer.get_buffer_stats()
        end_time = time.time()
        
        stats_time = end_time - start_time
        assert stats_time < 0.01  # Should be very fast
        assert stats["total_chunks"] == chunk_count
    
    @pytest.mark.slow
    def test_large_audio_chunk_processing(self):
        """Test processing of large audio chunks."""
        from services.audio_buffer import AudioBuffer
        
        session_id = uuid4()
        buffer = AudioBuffer(session_id)
        
        # Create large audio chunk (10 seconds worth)
        large_audio = np.random.randint(-32768, 32767, size=160000, dtype=np.int16)
        large_audio_bytes = large_audio.tobytes()
        
        start_time = time.time()
        result = buffer.add_chunk(large_audio_bytes)
        end_time = time.time()
        
        processing_time = end_time - start_time
        assert processing_time < 0.1  # Should process within 100ms
        assert result["total_samples"] == 160000
    
    @pytest.mark.slow
    def test_concurrent_audio_processing(self, sample_audio_data):
        """Test concurrent audio processing across multiple sessions."""
        from services.audio_buffer import AudioBufferManager
        
        manager = AudioBufferManager()
        session_ids = [uuid4() for _ in range(10)]
        
        def process_audio_for_session(session_id):
            buffer = manager.get_buffer(session_id)
            for _ in range(50):
                buffer.add_chunk(sample_audio_data)
            return buffer.get_buffer_stats()["total_chunks"]
        
        # Process audio concurrently
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_audio_for_session, sid) for sid in session_ids]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        # All should succeed
        assert all(result == 50 for result in results)
        
        # Should complete within reasonable time
        total_time = end_time - start_time
        assert total_time < 5.0  # 5 seconds max


class TestServicePerformance:
    """Test service layer performance."""
    
    @pytest.mark.slow
    def test_deidentification_performance(self):
        """Test deidentification performance with large text."""
        from services.deidentify import deidentify_text
        
        # Create large text with various PII
        large_text = " ".join([
            f"Patient John Smith {i} called 555-{i:04d} and emailed john{i}@example.com on 01/01/2023."
            for i in range(1000)
        ])
        
        start_time = time.time()
        result = deidentify_text(large_text)
        end_time = time.time()
        
        processing_time = end_time - start_time
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert "[NAME]" in result
        assert "[PHONE]" in result
        assert "[EMAIL]" in result
    
    @pytest.mark.slow
    def test_risk_assessment_performance(self):
        """Test risk assessment performance."""
        from services.risk_classifier import assess_risk_sync
        
        test_texts = [
            "I feel anxious about work and can't sleep.",
            "Everything seems hopeless and I don't know what to do.",
            "I'm having trouble concentrating on daily tasks.",
            "My mood has been very low lately.",
            "I feel overwhelmed by all my responsibilities."
        ]
        
        # Test batch risk assessment
        start_time = time.time()
        
        results = []
        for text in test_texts * 100:  # 500 assessments
            result = assess_risk_sync(text, use_llm=False)
            results.append(result)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        throughput = len(results) / total_time
        
        # Should process at least 10 assessments per second
        assert throughput >= 10.0
        assert all("overall_risk_score" in result for result in results)
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_embedding_generation_performance(self):
        """Test embedding generation performance."""
        test_texts = [
            "I feel anxious about my upcoming presentation.",
            "Sleep has been difficult for me recently.",
            "I'm worried about my job security.",
            "Family relationships are causing me stress.",
            "I have trouble managing my emotions."
        ]
        
        # Mock embedding generation to test without actual model
        with patch('services.embeddings._embeddings_service.generate_embedding') as mock_embed:
            mock_embed.return_value = [0.1] * 384  # Mock 384-dim embedding
            
            from services.embeddings import generate_embeddings_batch
            
            # Test batch generation
            start_time = time.time()
            embeddings = await generate_embeddings_batch(test_texts * 20, batch_size=10)  # 100 texts
            end_time = time.time()
            
            total_time = end_time - start_time
            assert total_time < 5.0  # Should complete within 5 seconds
            assert len(embeddings) == 100
            assert all(len(emb) == 384 for emb in embeddings)


class TestSystemResourceUsage:
    """Test system resource usage under load."""
    
    @pytest.mark.slow
    def test_cpu_usage_under_load(self, test_client, auth_headers):
        """Test CPU usage under sustained load."""
        import psutil
        import threading
        
        # Monitor CPU usage
        cpu_percentages = []
        
        def monitor_cpu():
            for _ in range(20):  # Monitor for 20 seconds
                cpu_percentages.append(psutil.cpu_percent(interval=1))
        
        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # Generate load
        def make_requests():
            for _ in range(100):
                response = test_client.get("/api/v1/health", headers=auth_headers)
                assert response.status_code in [200, 503]  # 503 for degraded health
        
        # Multiple concurrent request threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_requests)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        # Check that CPU usage was reasonable
        avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
        max_cpu = max(cpu_percentages)
        
        # Should not exceed 80% average CPU usage
        assert avg_cpu < 80.0
        # Should not exceed 95% peak CPU usage
        assert max_cpu < 95.0
    
    @pytest.mark.slow
    def test_memory_usage_stability(self, test_client, sample_audio_data):
        """Test memory usage stability over time."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        session_id = uuid4()
        
        # Simulate extended usage
        with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
            websocket.receive_json()  # connection message
            
            memory_samples = []
            
            for i in range(200):
                # Send audio data
                websocket.send_bytes(sample_audio_data)
                websocket.receive_json()  # audio_received
                
                # Sample memory usage periodically
                if i % 20 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_samples.append(current_memory)
        
        # Check memory growth
        if len(memory_samples) > 1:
            memory_growth = memory_samples[-1] - memory_samples[0]
            # Memory growth should be minimal (< 50MB)
            assert memory_growth < 50
        
        # Check for memory leaks (memory should not continuously grow)
        if len(memory_samples) >= 5:
            # Check if memory is continuously increasing
            increases = 0
            for i in range(1, len(memory_samples)):
                if memory_samples[i] > memory_samples[i-1]:
                    increases += 1
            
            # Not all samples should show increase (would indicate leak)
            leak_ratio = increases / (len(memory_samples) - 1)
            assert leak_ratio < 0.8  # Less than 80% of samples showing increase


@pytest.mark.slow
class TestStressTests:
    """Stress tests for system limits."""
    
    def test_maximum_concurrent_sessions(self, test_client):
        """Test maximum number of concurrent sessions."""
        session_count = 20
        session_ids = [uuid4() for _ in range(session_count)]
        
        def create_session(session_id):
            try:
                with test_client.websocket_connect(f"/api/v1/ws/audio/{session_id}") as websocket:
                    websocket.receive_json()  # connection message
                    return True
            except Exception:
                return False
        
        # Test concurrent session creation
        with concurrent.futures.ThreadPoolExecutor(max_workers=session_count) as executor:
            futures = [executor.submit(create_session, sid) for sid in session_ids]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Most sessions should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8  # At least 80% success rate
    
    @pytest.mark.asyncio
    async def test_database_connection_limits(self, async_session):
        """Test database connection handling under load."""
        from models.session import Session
        
        async def create_many_sessions():
            sessions = []
            for i in range(50):
                session = Session(
                    therapist_id=f"therapist_{i}",
                    status="active"
                )
                sessions.append(session)
            
            # Add all sessions
            for session in sessions:
                async_session.add(session)
            
            await async_session.commit()
            return len(sessions)
        
        # Test multiple concurrent database operations
        tasks = [create_many_sessions() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Most operations should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 3  # At least 60% success rate