"""
Second Brain API Server
Provides REST API for notes and integrates with Telegram bot
"""

import logging
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# ============================================
# CONFIGURATION
# ============================================

class Settings(BaseSettings):
    """Application settings from environment variables"""
    couchdb_url: str = "http://couchdb:5984"
    couchdb_user: str
    couchdb_password: str
    couchdb_database: str = "obsidian_notes"
    api_secret_key: str
    notes_api_token: str
    telegram_bot_token: str
    telegram_admin_id: int

    class Config:
        env_file = ".env"


settings = Settings()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================
# PYDANTIC MODELS
# ============================================

class QuickNote(BaseModel):
    """Quick note from Telegram or API"""
    content: str = Field(..., min_length=1, max_length=50000)
    tags: Optional[List[str]] = []
    source: str = "api"


class NoteResponse(BaseModel):
    """Response after creating a note"""
    id: str
    success: bool
    message: str


class DailySummary(BaseModel):
    """Daily summary of notes"""
    date: str
    total_notes: int
    new_notes_today: int
    recent_notes: List[dict]


# ============================================
# COUCHDB CLIENT
# ============================================

class CouchDBClient:
    """Async client for CouchDB operations"""

    def __init__(self):
        self.base_url = f"{settings.couchdb_url}/{settings.couchdb_database}"
        self.auth = (settings.couchdb_user, settings.couchdb_password)

    async def create_document(self, doc: dict) -> dict:
        """Create a new document in CouchDB"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json=doc,
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def get_document(self, doc_id: str) -> dict:
        """Get document by ID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/{doc_id}",
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def search_documents(self, query: str, limit: int = 10) -> List[dict]:
        """Search documents using Mango query"""
        selector = {
            "$or": [
                {"data": {"$regex": f"(?i){query}"}},
                {"path": {"$regex": f"(?i){query}"}}
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/_find",
                json={
                    "selector": selector,
                    "limit": limit,
                    "fields": ["_id", "path", "data", "mtime"]
                },
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json().get("docs", [])

    async def get_recent_documents(self, limit: int = 10) -> List[dict]:
        """Get recently modified documents"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/_find",
                json={
                    "selector": {
                        "type": "leaf",
                        "mtime": {"$gt": 0}
                    },
                    "sort": [{"mtime": "desc"}],
                    "limit": limit,
                    "fields": ["_id", "path", "data", "mtime"]
                },
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json().get("docs", [])

    async def get_all_documents(self, limit: int = 200) -> List[dict]:
        """Get all documents (for folder structure analysis)"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/_find",
                json={
                    "selector": {
                        "type": "leaf"
                    },
                    "limit": limit,
                    "fields": ["_id", "path", "mtime"]
                },
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json().get("docs", [])

    async def get_stats(self) -> dict:
        """Get database statistics"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                auth=self.auth,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()


couchdb = CouchDBClient()


# ============================================
# AUTHENTICATION
# ============================================

async def verify_api_token(x_api_token: str = Header(...)):
    """Verify API token from header"""
    if x_api_token != settings.notes_api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return x_api_token


# ============================================
# FASTAPI APPLICATION
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting Second Brain API...")
    # Start Telegram bot in background
    from bot import start_bot
    await start_bot()
    yield
    logger.info("Shutting down Second Brain API...")
    from bot import stop_bot
    await stop_bot()


app = FastAPI(
    title="Second Brain API",
    description="API for managing Obsidian notes via CouchDB",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "Second Brain API"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        stats = await couchdb.get_stats()
        return {
            "status": "healthy",
            "couchdb": {
                "connected": True,
                "doc_count": stats.get("doc_count", 0)
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.post("/api/notes/quick", response_model=NoteResponse)
async def create_quick_note(
    note: QuickNote,
    token: str = Depends(verify_api_token)
):
    """
    Create a quick note from Telegram or other sources.
    The note will be saved as a markdown file in the Inbox folder.
    """
    try:
        # Generate filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Inbox/Quick_{timestamp}.md"

        # Format content with frontmatter
        tags_str = ", ".join(note.tags) if note.tags else ""
        content = f"""---
created: {datetime.now().isoformat()}
source: {note.source}
tags: [{tags_str}]
---

{note.content}
"""

        # Create document in Livesync format
        doc = {
            "_id": filename,
            "path": filename,
            "data": content,
            "type": "leaf",
            "mtime": int(datetime.now().timestamp() * 1000),
            "ctime": int(datetime.now().timestamp() * 1000),
            "size": len(content)
        }

        result = await couchdb.create_document(doc)

        return NoteResponse(
            id=result["id"],
            success=True,
            message=f"Note created: {filename}"
        )

    except Exception as e:
        logger.error(f"Error creating quick note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/search")
async def search_notes(
    q: str,
    limit: int = 10,
    token: str = Depends(verify_api_token)
):
    """Search notes by content or title"""
    try:
        results = await couchdb.search_documents(q, limit)

        return {
            "query": q,
            "count": len(results),
            "results": [
                {
                    "id": doc["_id"],
                    "path": doc.get("path", ""),
                    "snippet": doc.get("data", "")[:200] + "..." if len(doc.get("data", "")) > 200 else doc.get("data", ""),
                    "modified": doc.get("mtime", 0)
                }
                for doc in results
            ]
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/recent")
async def get_recent_notes(
    limit: int = 10,
    token: str = Depends(verify_api_token)
):
    """Get recently modified notes"""
    try:
        docs = await couchdb.get_recent_documents(limit)

        return {
            "count": len(docs),
            "notes": [
                {
                    "id": doc["_id"],
                    "path": doc.get("path", ""),
                    "modified": datetime.fromtimestamp(
                        doc.get("mtime", 0) / 1000
                    ).isoformat() if doc.get("mtime") else None
                }
                for doc in docs
            ]
        }
    except Exception as e:
        logger.error(f"Error getting recent notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/summary", response_model=DailySummary)
async def get_daily_summary(token: str = Depends(verify_api_token)):
    """Get daily summary of notes activity"""
    try:
        stats = await couchdb.get_stats()
        recent = await couchdb.get_recent_documents(20)

        today = datetime.now().date()
        new_today = sum(
            1 for doc in recent
            if doc.get("mtime") and
            datetime.fromtimestamp(doc["mtime"] / 1000).date() == today
        )

        return DailySummary(
            date=today.isoformat(),
            total_notes=stats.get("doc_count", 0),
            new_notes_today=new_today,
            recent_notes=[
                {
                    "id": doc["_id"],
                    "path": doc.get("path", ""),
                    "modified": doc.get("mtime", 0)
                }
                for doc in recent[:5]
            ]
        )
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_system_stats(token: str = Depends(verify_api_token)):
    """Get system statistics including AI agents and indexing status"""
    try:
        from bot import director, vector_store
        
        # CouchDB stats
        couchdb_stats = await couchdb.get_stats()
        
        # Vector store stats
        vector_stats = {}
        if vector_store:
            try:
                vector_stats = await vector_store.get_stats()
            except Exception as e:
                logger.warning(f"Failed to get vector stats: {e}")
        
        # Agent stats (if available)
        agents_info = {}
        if director:
            agents_info = {
                "registered_agents": director.list_agents(),
                "total_agents": len(director.list_agents())
            }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "couchdb": {
                "total_documents": couchdb_stats.get("doc_count", 0),
                "db_name": couchdb_stats.get("db_name", ""),
                "data_size": couchdb_stats.get("data_size", 0)
            },
            "vector_store": {
                "total_vectors": vector_stats.get("total_vectors", 0),
                "vector_dimensions": vector_stats.get("vector_dimensions", 1536),
                "indexed_count": vector_stats.get("indexed_count", 0)
            },
            "agents": agents_info,
            "indexing": {
                "pending_notes": max(0, couchdb_stats.get("doc_count", 0) - vector_stats.get("total_vectors", 0))
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reindex")
async def trigger_reindex(token: str = Depends(verify_api_token)):
    """Manually trigger reindexing of all notes"""
    try:
        from bot import metadata_generator, vector_store, llm_manager
        from indexer import BackgroundIndexer
        
        if not all([metadata_generator, vector_store, llm_manager]):
            raise HTTPException(
                status_code=503,
                detail="Indexing services not available"
            )
        
        indexer = BackgroundIndexer(
            couchdb=couchdb,
            llm_manager=llm_manager,
            vector_store=vector_store,
            metadata_generator=metadata_generator
        )
        
        # This will be async, return immediately
        asyncio.create_task(indexer.reindex_all())
        
        return {
            "status": "started",
            "message": "Reindexing started in background"
        }
        
    except Exception as e:
        logger.error(f"Error starting reindex: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/{note_id:path}")
async def get_note(note_id: str, token: str = Depends(verify_api_token)):
    """Get a specific note by ID"""
    try:
        doc = await couchdb.get_document(note_id)
        return {
            "id": doc["_id"],
            "path": doc.get("path", ""),
            "content": doc.get("data", ""),
            "modified": doc.get("mtime", 0),
            "created": doc.get("ctime", 0)
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Note not found")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WEB VIEWER
# ============================================

@app.get("/view", response_class=HTMLResponse)
async def notes_viewer():
    """Simple web viewer for notes (read-only)"""
    html = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <title>Second Brain - Notes Viewer</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f23;
            color: #cccccc;
            min-height: 100vh;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 {
            color: #00cc00;
            margin-bottom: 30px;
            font-size: 24px;
        }
        .search {
            width: 100%;
            padding: 15px 20px;
            font-size: 16px;
            background: #1a1a2e;
            border: 2px solid #333;
            color: #fff;
            border-radius: 10px;
            margin-bottom: 20px;
            transition: border-color 0.3s;
        }
        .search:focus {
            outline: none;
            border-color: #00cc00;
        }
        .note {
            background: #1a1a2e;
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            border-left: 4px solid #00cc00;
            transition: transform 0.2s;
        }
        .note:hover {
            transform: translateX(5px);
        }
        .note-title {
            color: #00cc00;
            font-weight: 600;
            font-size: 14px;
            word-break: break-all;
        }
        .note-date {
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        }
        .note-content {
            margin-top: 12px;
            color: #999;
            font-size: 14px;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        .login-form {
            background: #1a1a2e;
            padding: 40px;
            border-radius: 15px;
            max-width: 400px;
            margin: 100px auto;
        }
        .login-form h2 {
            color: #00cc00;
            margin-bottom: 20px;
            text-align: center;
        }
        .login-form input {
            display: block;
            width: 100%;
            padding: 15px;
            margin: 15px 0;
            border-radius: 8px;
            border: 2px solid #333;
            background: #0f0f23;
            color: #fff;
            font-size: 16px;
        }
        .login-form input:focus {
            outline: none;
            border-color: #00cc00;
        }
        .login-form button {
            width: 100%;
            background: #00cc00;
            color: #0f0f23;
            padding: 15px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            margin-top: 10px;
            transition: background 0.3s;
        }
        .login-form button:hover {
            background: #00ff00;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #1a1a2e;
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            color: #00cc00;
            font-size: 24px;
            font-weight: bold;
        }
        .stat-label {
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        }
        .error {
            background: #2e1a1a;
            border-left-color: #cc0000;
            color: #cc0000;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="login-form" id="loginForm">
            <h2>Second Brain</h2>
            <input type="password" id="apiToken" placeholder="API Token">
            <button onclick="login()">Enter</button>
        </div>

        <div id="notesArea" style="display: none;">
            <h1>Second Brain</h1>

            <div class="stats" id="stats"></div>

            <input type="text" class="search" id="searchInput"
                   placeholder="Search notes..." onkeyup="debounceSearch(this.value)">

            <div id="notesList">
                <div class="loading">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        let token = '';
        let searchTimeout = null;

        function login() {
            token = document.getElementById('apiToken').value;
            if (!token) return;

            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('notesArea').style.display = 'block';
            loadStats();
            loadRecentNotes();
        }

        async function loadStats() {
            try {
                const res = await fetch('/api/notes/summary', {
                    headers: {'X-API-Token': token}
                });
                if (!res.ok) throw new Error('Failed to load stats');
                const data = await res.json();

                document.getElementById('stats').innerHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${data.total_notes}</div>
                        <div class="stat-label">Total Notes</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.new_notes_today}</div>
                        <div class="stat-label">Today</div>
                    </div>
                `;
            } catch (e) {
                console.error(e);
            }
        }

        async function loadRecentNotes() {
            try {
                const res = await fetch('/api/notes/recent?limit=20', {
                    headers: {'X-API-Token': token}
                });
                if (!res.ok) throw new Error('Unauthorized');
                const data = await res.json();
                displayNotes(data.notes);
            } catch (e) {
                document.getElementById('notesList').innerHTML =
                    '<div class="note error">Error loading notes. Check your token.</div>';
            }
        }

        function debounceSearch(query) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => searchNotes(query), 300);
        }

        async function searchNotes(query) {
            if (query.length < 2) {
                loadRecentNotes();
                return;
            }

            try {
                const res = await fetch('/api/notes/search?q=' + encodeURIComponent(query) + '&limit=20', {
                    headers: {'X-API-Token': token}
                });
                if (!res.ok) throw new Error('Search failed');
                const data = await res.json();
                displaySearchResults(data.results);
            } catch (e) {
                console.error(e);
            }
        }

        function displayNotes(notes) {
            const list = document.getElementById('notesList');
            if (!notes || notes.length === 0) {
                list.innerHTML = '<div class="note">No notes yet.</div>';
                return;
            }

            list.innerHTML = notes.map(n => `
                <div class="note">
                    <div class="note-title">${escapeHtml(n.path || n.id)}</div>
                    <div class="note-date">${n.modified ? new Date(n.modified).toLocaleString('ru-RU') : ''}</div>
                </div>
            `).join('');
        }

        function displaySearchResults(results) {
            const list = document.getElementById('notesList');
            if (!results || results.length === 0) {
                list.innerHTML = '<div class="note">No results found.</div>';
                return;
            }

            list.innerHTML = results.map(n => `
                <div class="note">
                    <div class="note-title">${escapeHtml(n.path || n.id)}</div>
                    <div class="note-date">${n.modified ? new Date(n.modified).toLocaleString('ru-RU') : ''}</div>
                    ${n.snippet ? '<div class="note-content">' + escapeHtml(n.snippet) + '</div>' : ''}
                </div>
            `).join('');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Check for stored token
        document.addEventListener('DOMContentLoaded', () => {
            const savedToken = sessionStorage.getItem('sb_token');
            if (savedToken) {
                document.getElementById('apiToken').value = savedToken;
            }
        });

        // Save token on login
        const originalLogin = login;
        login = function() {
            sessionStorage.setItem('sb_token', document.getElementById('apiToken').value);
            originalLogin();
        };
    </script>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
