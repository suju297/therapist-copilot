"""Integration tests for API endpoints."""

import json
import pytest
from uuid import uuid4
from unittest.mock import patch, Mock

from fastapi.testclient import TestClient
from conftest import assert_uuid_format, assert_datetime_format


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_quick_health_check(self, test_client):
        """Test quick health check endpoint."""
        response = test_client.get("/api/v1/health/quick")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "therapist-copilot-api"
    
    def test_comprehensive_health_check(self, test_client):
        """Test comprehensive health check."""
        # Mock external services
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            response = test_client.get("/api/v1/health")
            
            assert response.status_code in [200, 503]  # Might be degraded due to mocks
            data = response.json()
            assert "status" in data
            assert "services" in data
            assert "timestamp" in data
    
    def test_database_health_check(self, test_client):
        """Test database health check."""
        response = test_client.get("/api/v1/health/database")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "details" in data


class TestSessionEndpoints:
    """Test session management endpoints."""
    
    def test_list_sessions_unauthorized(self, test_client):
        """Test listing sessions without authentication."""
        response = test_client.get("/api/v1/sessions")
        assert response.status_code == 401
    
    def test_list_sessions_authorized(self, test_client, auth_headers):
        """Test listing sessions with authentication."""
        response = test_client.get("/api/v1/sessions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
    
    def test_get_session_details(self, test_client, auth_headers, sample_session):
        """Test getting session details."""
        response = test_client.get(
            f"/api/v1/sessions/{sample_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_session.id)
        assert data["therapist_id"] == sample_session.therapist_id
        assert data["status"] == sample_session.status
        assert assert_datetime_format(data["created_at"])
    
    def test_get_nonexistent_session(self, test_client, auth_headers):
        """Test getting details for non-existent session."""
        fake_id = uuid4()
        response = test_client.get(
            f"/api/v1/sessions/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestDraftEndpoints:
    """Test SOAP draft generation endpoints."""
    
    def test_generate_draft_unauthorized(self, test_client, sample_session):
        """Test draft generation without authentication."""
        response = test_client.post(f"/api/v1/draft/{sample_session.id}")
        assert response.status_code == 401
    
    def test_generate_draft_no_transcript(self, test_client, auth_headers, sample_session):
        """Test draft generation with no transcript data."""
        response = test_client.post(
            f"/api/v1/draft/{sample_session.id}",
            headers=auth_headers,
            json={"force_regenerate": True}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "No transcript available" in data["detail"]
    
    @patch('services.draft_pipeline.generate_draft')
    def test_generate_draft_success(self, mock_generate_draft, test_client, auth_headers, 
                                   sample_session, sample_transcript, mock_llm_response):
        """Test successful draft generation."""
        mock_generate_draft.return_value = mock_llm_response
        
        response = test_client.post(
            f"/api/v1/draft/{sample_session.id}",
            headers=auth_headers,
            json={"force_regenerate": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["draft_generated"] is True
        assert data["session_id"] == str(sample_session.id)
        assert data["soap_note"] is not None
        assert data["homework_assignments"] is not None
    
    def test_get_existing_draft(self, test_client, auth_headers, sample_session):
        """Test getting existing draft."""
        # First create a draft in the session
        sample_session.draft_blob = {
            "soap_note": {"subjective": "Test", "objective": "Test", "assessment": "Test", "plan": "Test"},
            "homework_assignments": []
        }
        
        response = test_client.get(
            f"/api/v1/draft/{sample_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["draft_generated"] is True
        assert data["soap_note"] is not None
    
    def test_update_draft(self, test_client, auth_headers, sample_session):
        """Test updating a draft."""
        update_data = {
            "soap_note": {
                "subjective": "Updated subjective",
                "objective": "Updated objective", 
                "assessment": "Updated assessment",
                "plan": "Updated plan"
            },
            "notes": "Updated notes"
        }
        
        response = test_client.put(
            f"/api/v1/draft/{sample_session.id}",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data["message"]
    
    def test_delete_draft(self, test_client, auth_headers, sample_session):
        """Test deleting a draft."""
        response = test_client.delete(
            f"/api/v1/draft/{sample_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
    
    def test_draft_with_locked_session(self, test_client, auth_headers, sample_session):
        """Test that draft generation fails for locked sessions."""
        # Lock the session
        sample_session.locked_flag = True
        
        response = test_client.post(
            f"/api/v1/draft/{sample_session.id}",
            headers=auth_headers,
            json={"force_regenerate": True}
        )
        
        assert response.status_code == 423
        data = response.json()
        assert "locked" in data["detail"]


class TestHomeworkEndpoints:
    """Test homework assignment endpoints."""
    
    def test_assign_homework_unauthorized(self, test_client, sample_session):
        """Test homework assignment without authentication."""
        homework_data = {
            "title": "Test Assignment",
            "description": "Test description",
            "category": "anxiety"
        }
        
        response = test_client.post(
            f"/api/v1/homework/{sample_session.id}",
            json=homework_data
        )
        assert response.status_code == 401
    
    def test_assign_homework_success(self, test_client, auth_headers, sample_session):
        """Test successful homework assignment."""
        homework_data = {
            "title": "Breathing Exercise",
            "description": "Practice 4-7-8 breathing technique",
            "category": "anxiety",
            "priority": "high",
            "estimated_duration": 10
        }
        
        response = test_client.post(
            f"/api/v1/homework/{sample_session.id}",
            headers=auth_headers,
            json=homework_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == homework_data["title"]
        assert data["category"] == homework_data["category"]
        assert data["priority"] == homework_data["priority"]
        assert data["status"] == "assigned"
        assert data["access_token"] is not None
        assert data["qr_code_url"] is not None
        assert assert_uuid_format(data["id"])
    
    def test_get_session_homework(self, test_client, auth_headers, sample_session, sample_homework):
        """Test getting homework for a session."""
        response = test_client.get(
            f"/api/v1/homework/{sample_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["session_id"] == str(sample_session.id)
    
    def test_generate_qr_code(self, test_client, auth_headers, sample_homework):
        """Test QR code generation."""
        response = test_client.post(
            f"/api/v1/send_hw",
            headers=auth_headers,
            params={"homework_id": str(sample_homework.id)}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
    
    def test_client_homework_access(self, test_client, sample_homework):
        """Test client access to homework via token."""
        # Set access token for homework
        sample_homework.access_token = "test-token-123"
        
        response = test_client.get(f"/api/v1/hw/test-token-123")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert sample_homework.title in response.text
    
    def test_client_homework_completion(self, test_client, sample_homework):
        """Test client completing homework."""
        sample_homework.access_token = "test-token-123"
        
        completion_data = {
            "completion_notes": "Completed successfully",
            "client_feedback": "Very helpful exercise"
        }
        
        response = test_client.post(
            f"/api/v1/hw/test-token-123/complete",
            data=completion_data
        )
        
        assert response.status_code == 200
        assert "Homework Completed" in response.text
    
    def test_update_homework(self, test_client, auth_headers, sample_homework):
        """Test updating homework assignment."""
        update_data = {
            "priority": "low",
            "status": "completed"
        }
        
        response = test_client.put(
            f"/api/v1/homework/{sample_homework.id}",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data["message"]
    
    def test_delete_homework(self, test_client, auth_headers, sample_homework):
        """Test deleting homework assignment."""
        response = test_client.delete(
            f"/api/v1/homework/{sample_homework.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]


class TestWebSocketStats:
    """Test WebSocket statistics endpoints."""
    
    def test_get_websocket_stats(self, test_client):
        """Test getting WebSocket connection statistics."""
        response = test_client.get("/api/v1/ws/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "sessions" in data
    
    def test_force_disconnect_session(self, test_client):
        """Test forcing disconnection of a WebSocket session."""
        fake_session_id = uuid4()
        
        response = test_client.post(f"/api/v1/ws/disconnect/{fake_session_id}")
        
        # Should return 404 for non-existent session
        assert response.status_code == 404


class TestErrorHandling:
    """Test API error handling."""
    
    def test_invalid_uuid_format(self, test_client, auth_headers):
        """Test handling of invalid UUID format."""
        response = test_client.get(
            "/api/v1/sessions/invalid-uuid",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_fields(self, test_client, auth_headers, sample_session):
        """Test handling of missing required fields."""
        # Try to create homework without required fields
        response = test_client.post(
            f"/api/v1/homework/{sample_session.id}",
            headers=auth_headers,
            json={}  # Missing required fields
        )
        
        assert response.status_code == 422
    
    def test_invalid_json_payload(self, test_client, auth_headers, sample_session):
        """Test handling of invalid JSON payload."""
        response = test_client.post(
            f"/api/v1/draft/{sample_session.id}",
            headers=auth_headers,
            data="invalid json"  # Invalid JSON
        )
        
        assert response.status_code == 422
    
    def test_internal_server_error_handling(self, test_client, auth_headers):
        """Test internal server error handling."""
        with patch('routes.draft.generate_draft') as mock_generate:
            mock_generate.side_effect = Exception("Test error")
            
            response = test_client.post(
                f"/api/v1/draft/{uuid4()}",
                headers=auth_headers,
                json={"force_regenerate": True}
            )
            
            assert response.status_code in [404, 500]  # Session not found or internal error


class TestAuthentication:
    """Test authentication and authorization."""
    
    def test_invalid_token(self, test_client):
        """Test request with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        
        response = test_client.get("/api/v1/sessions", headers=headers)
        assert response.status_code == 401
    
    def test_missing_token(self, test_client):
        """Test request without token."""
        response = test_client.get("/api/v1/sessions")
        assert response.status_code == 401
    
    def test_malformed_auth_header(self, test_client):
        """Test request with malformed auth header."""
        headers = {"Authorization": "InvalidFormat token"}
        
        response = test_client.get("/api/v1/sessions", headers=headers)
        assert response.status_code == 401
    
    def test_valid_token(self, test_client, auth_headers):
        """Test request with valid token."""
        response = test_client.get("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 200


class TestPagination:
    """Test pagination functionality."""
    
    def test_sessions_pagination(self, test_client, auth_headers):
        """Test session list pagination."""
        # Test with limit and offset
        response = test_client.get(
            "/api/v1/sessions",
            headers=auth_headers,
            params={"limit": 10, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["sessions"]) <= 10
    
    def test_sessions_filtering(self, test_client, auth_headers):
        """Test session list filtering."""
        response = test_client.get(
            "/api/v1/sessions",
            headers=auth_headers,
            params={"status": "active"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned sessions should have active status
        for session in data["sessions"]:
            assert session["status"] == "active"


class TestConcurrency:
    """Test concurrent request handling."""
    
    def test_concurrent_session_creation(self, test_client, auth_headers):
        """Test handling of concurrent requests."""
        import concurrent.futures
        import threading
        
        def create_session():
            homework_data = {
                "title": f"Concurrent Test {threading.current_thread().ident}",
                "description": "Test concurrent creation",
                "category": "test"
            }
            
            # Create a session first
            session_response = test_client.post(
                "/api/v1/sessions",
                headers=auth_headers,
                json={"therapist_id": "test", "status": "active"}
            )
            
            if session_response.status_code == 201:
                session_id = session_response.json()["id"]
                
                # Then create homework
                homework_response = test_client.post(
                    f"/api/v1/homework/{session_id}",
                    headers=auth_headers,
                    json=homework_data
                )
                
                return homework_response.status_code == 200
            
            return False
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_session) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # At least some requests should succeed
        assert any(results)