"""
Smart Note Taker Agent
Intelligently categorizes and enriches notes with metadata
"""

import logging
from datetime import datetime
from typing import Dict, Any

from .base_agent import BaseAgent, AgentResponse
from llm.manager import LLMManager
from vector_store import VectorStoreClient
from metadata_generator import MetadataGenerator

logger = logging.getLogger(__name__)


class SmartNoteTaker(BaseAgent):
    """
    Agent that saves notes with intelligent categorization and metadata
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        couchdb: Any,
        vector_store: VectorStoreClient,
        metadata_generator: MetadataGenerator
    ):
        super().__init__("note_taker", llm_manager, couchdb, vector_store)
        self.metadata_gen = metadata_generator
        
    async def can_handle(self, message: str, context: Dict[str, Any]) -> float:
        """Note Taker handles all non-command messages"""
        # Skip commands
        if message.strip().startswith('/'):
            return 0.0
        
        # Handle everything else with medium confidence
        # (specific agents can override with higher confidence)
        return 0.5
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """
        Process message and save as smart note
        
        Steps:
        1. Get existing folders for context
        2. Extract metadata using LLM
        3. Enrich content with frontmatter
        4. Save to CouchDB in suggested category
        5. Generate and save embedding to Qdrant
        6. Return confirmation
        """
        try:
            # Get existing folder structure
            existing_folders = await self._get_existing_folders()
            
            # Extract metadata
            self.logger.info("Extracting metadata...")
            metadata = await self.metadata_gen.extract_metadata(
                content=message,
                existing_folders=existing_folders
            )
            
            # Determine filename and path
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            category = metadata.get('category', 'Inbox')
            filename = f"{category}/Telegram_{timestamp}.md"
            
            # Enrich content with frontmatter
            username = context.get('username', 'unknown')
            enriched_content = self.metadata_gen.enrich_frontmatter(
                content=message,
                metadata=metadata,
                source='telegram',
                username=username
            )
            
            # Create document for CouchDB (Obsidian LiveSync format)
            doc = {
                "_id": filename,
                "path": filename,
                "data": enriched_content,
                "type": "leaf",
                "mtime": int(datetime.now().timestamp() * 1000),
                "ctime": int(datetime.now().timestamp() * 1000),
                "size": len(enriched_content)
            }
            
            # Save to CouchDB
            self.logger.info(f"Saving note to CouchDB: {filename}")
            result = await self.couchdb.create_document(doc)
            
            # Generate embedding and save to vector store
            try:
                self.logger.info("Generating embedding...")
                # Create text for embedding (summary + content)
                embed_text = f"{metadata.get('summary', '')} {message}"
                embedding = await self.llm.embed_text(embed_text[:8000])  # Limit to 8K chars
                
                # Save to Qdrant
                await self.vector_store.upsert_note(
                    note_id=filename,
                    embedding=embedding,
                    metadata={
                        'category': category,
                        'tags': metadata.get('tags', []),
                        'keywords': metadata.get('keywords', []),
                        'mtime': doc['mtime'],
                        'ctime': doc['ctime'],
                        'summary': metadata.get('summary', '')
                    }
                )
                self.logger.info("Embedding saved to Qdrant")
                
            except Exception as e:
                self.logger.warning(f"Failed to save embedding: {e}")
                # Continue even if embedding fails
            
            # Build response
            tags_str = ", ".join(metadata.get('tags', [])[:5])
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(metadata.get('priority', 'medium'), '🟡')
            
            response_text = f"""✅ Note saved!

📁 Category: `{category}`
🏷 Tags: {tags_str}
{priority_emoji} Priority: {metadata.get('priority', 'medium')}

💡 Summary: {metadata.get('summary', 'N/A')[:200]}

📄 File: `{filename}`
"""
            
            return AgentResponse(
                text=response_text,
                success=True,
                metadata={
                    'note_id': filename,
                    'category': category,
                    'tags': metadata.get('tags', []),
                    'has_tasks': metadata.get('has_tasks', False)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save note: {e}", exc_info=True)
            return AgentResponse(
                text=f"❌ Failed to save note: {str(e)}",
                success=False
            )
    
    async def _get_existing_folders(self) -> list:
        """Get list of existing folders from CouchDB"""
        try:
            # Get recent documents to analyze folder structure
            docs = await self.couchdb.get_all_documents(limit=200)
            folders = self.metadata_gen.extract_existing_folders(docs)
            self.logger.info(f"Found {len(folders)} existing folders")
            return folders
            
        except Exception as e:
            self.logger.warning(f"Failed to get existing folders: {e}")
            return ['Inbox', 'Projects', 'Knowledge', 'Tasks', 'Ideas']
