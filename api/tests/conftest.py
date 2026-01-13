"""
Pytest fixtures for Second Brain API tests
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set test environment variables before importing app
os.environ.update({
    "COUCHDB_URL": "http://localhost:5984",
    "COUCHDB_USER": "test_user",
    "COUCHDB_PASSWORD": "test_password",
    "COUCHDB_DATABASE": "test_db",
    "API_SECRET_KEY": "test_secret_key_12345",
    "NOTES_API_TOKEN": "test_api_token",
    "TELEGRAM_BOT_TOKEN": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "TELEGRAM_ADMIN_ID": "12345678"
})

from fastapi.testclient import TestClient


@pytest.fixture
def mock_couchdb():
    """Mock CouchDB client for tests"""
    with patch("main.couchdb") as mock:
        # Mock methods
        mock.create_document = AsyncMock(return_value={
            "ok": True,
            "id": "test_doc_id",
            "rev": "1-abc123"
        })
        mock.get_document = AsyncMock(return_value={
            "_id": "test_doc",
            "path": "Inbox/Test.md",
            "data": "# Test Note\n\nContent here",
            "mtime": 1704067200000,
            "ctime": 1704067200000
        })
        mock.search_documents = AsyncMock(return_value=[
            {
                "_id": "note1",
                "path": "Inbox/Note1.md",
                "data": "First note content",
                "mtime": 1704067200000
            },
            {
                "_id": "note2",
                "path": "Inbox/Note2.md",
                "data": "Second note content",
                "mtime": 1704067100000
            }
        ])
        mock.get_recent_documents = AsyncMock(return_value=[
            {
                "_id": "recent1",
                "path": "Inbox/Recent1.md",
                "data": "Recent note",
                "mtime": 1704067200000
            }
        ])
        mock.get_stats = AsyncMock(return_value={
            "db_name": "test_db",
            "doc_count": 42,
            "update_seq": "100-abc"
        })
        yield mock


@pytest.fixture
def mock_bot():
    """Mock Telegram bot for tests"""
    with patch("main.start_bot", new_callable=AsyncMock), \
         patch("main.stop_bot", new_callable=AsyncMock):
        yield


@pytest.fixture
def client(mock_couchdb, mock_bot):
    """Test client with mocked dependencies"""
    # Import after mocking
    from main import app
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Headers with valid API token"""
    return {"X-API-Token": "test_api_token"}


@pytest.fixture
def invalid_auth_headers():
    """Headers with invalid API token"""
    return {"X-API-Token": "wrong_token"}
