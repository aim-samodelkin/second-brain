"""
Tests for Second Brain REST API
"""
import pytest
from datetime import datetime


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns OK status"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
    
    def test_health_endpoint_healthy(self, client, mock_couchdb):
        """Test health endpoint when CouchDB is healthy"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["couchdb"]["connected"] is True
        assert data["couchdb"]["doc_count"] == 42


class TestAuthentication:
    """Tests for API authentication"""
    
    def test_valid_token(self, client, auth_headers):
        """Test request with valid API token"""
        response = client.get("/api/notes/recent", headers=auth_headers)
        assert response.status_code == 200
    
    def test_invalid_token(self, client, invalid_auth_headers):
        """Test request with invalid API token"""
        response = client.get("/api/notes/recent", headers=invalid_auth_headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API token"
    
    def test_missing_token(self, client):
        """Test request without API token"""
        response = client.get("/api/notes/recent")
        assert response.status_code == 422  # Validation error


class TestNotesAPI:
    """Tests for notes endpoints"""
    
    def test_create_quick_note(self, client, auth_headers, mock_couchdb):
        """Test creating a quick note"""
        note_data = {
            "content": "Test note content",
            "tags": ["test", "api"],
            "source": "api"
        }
        response = client.post(
            "/api/notes/quick",
            json=note_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "test_doc_id" in data["id"]
        assert "Note created" in data["message"]
        
        # Verify CouchDB was called
        mock_couchdb.create_document.assert_called_once()
    
    def test_create_quick_note_empty_content(self, client, auth_headers):
        """Test creating note with empty content fails"""
        note_data = {"content": "", "tags": []}
        response = client.post(
            "/api/notes/quick",
            json=note_data,
            headers=auth_headers
        )
        assert response.status_code == 422  # Validation error
    
    def test_search_notes(self, client, auth_headers, mock_couchdb):
        """Test searching notes"""
        response = client.get(
            "/api/notes/search?q=test&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["count"] == 2
        assert len(data["results"]) == 2
        assert "snippet" in data["results"][0]
        
        mock_couchdb.search_documents.assert_called_once_with("test", 5)
    
    def test_get_recent_notes(self, client, auth_headers, mock_couchdb):
        """Test getting recent notes"""
        response = client.get(
            "/api/notes/recent?limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "notes" in data
        assert len(data["notes"]) == 1
        
        mock_couchdb.get_recent_documents.assert_called_once_with(10)
    
    def test_get_note_by_id(self, client, auth_headers, mock_couchdb):
        """Test getting a specific note by ID"""
        response = client.get(
            "/api/notes/Inbox/Test.md",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_doc"
        assert "content" in data
        assert data["path"] == "Inbox/Test.md"
    
    def test_get_daily_summary(self, client, auth_headers, mock_couchdb):
        """Test getting daily summary"""
        response = client.get(
            "/api/notes/summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "total_notes" in data
        assert data["total_notes"] == 42
        assert "new_notes_today" in data
        assert "recent_notes" in data


class TestWebViewer:
    """Tests for web viewer"""
    
    def test_web_viewer_returns_html(self, client):
        """Test web viewer returns HTML page"""
        response = client.get("/view")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Second Brain" in response.text
        assert "apiToken" in response.text  # Login form


class TestInputValidation:
    """Tests for input validation"""
    
    def test_note_content_too_long(self, client, auth_headers):
        """Test note content exceeding max length"""
        note_data = {
            "content": "x" * 50001,  # Max is 50000
            "tags": []
        }
        response = client.post(
            "/api/notes/quick",
            json=note_data,
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_search_with_special_characters(self, client, auth_headers, mock_couchdb):
        """Test search handles special characters"""
        response = client.get(
            "/api/notes/search?q=test%20query%20with%20spaces",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_recent_notes_limit_bounds(self, client, auth_headers, mock_couchdb):
        """Test recent notes with various limit values"""
        # Default limit
        response = client.get("/api/notes/recent", headers=auth_headers)
        assert response.status_code == 200
        
        # Custom limit
        response = client.get("/api/notes/recent?limit=5", headers=auth_headers)
        assert response.status_code == 200
