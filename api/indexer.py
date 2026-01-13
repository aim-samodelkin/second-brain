"""
Background Indexer
Processes existing notes to generate metadata and embeddings
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from llm.manager import LLMManager
from vector_store import VectorStoreClient
from metadata_generator import MetadataGenerator

logger = logging.getLogger(__name__)


class BackgroundIndexer:
    """
    Background task for indexing existing notes
    """
    
    def __init__(
        self,
        couchdb: Any,
        llm_manager: LLMManager,
        vector_store: VectorStoreClient,
        metadata_generator: MetadataGenerator,
        batch_size: int = 5,
        delay_seconds: int = 12  # 5 notes per minute
    ):
        self.couchdb = couchdb
        self.llm = llm_manager
        self.vector_store = vector_store
        self.metadata_gen = metadata_generator
        self.batch_size = batch_size
        self.delay_seconds = delay_seconds
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._stats = {
            'total_notes': 0,
            'indexed_notes': 0,
            'pending_notes': 0,
            'failed_notes': 0,
            'last_run': None
        }
    
    async def start(self):
        """Start background indexing task"""
        if self._running:
            logger.warning("Indexer already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._indexing_loop())
        logger.info("Background indexer started")
    
    async def stop(self):
        """Stop background indexing task"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background indexer stopped")
    
    async def _indexing_loop(self):
        """Main indexing loop"""
        logger.info("Starting indexing loop...")
        
        # Initial delay to let system stabilize
        await asyncio.sleep(30)
        
        while self._running:
            try:
                # Find notes that need indexing
                pending_notes = await self._find_pending_notes()
                
                if pending_notes:
                    logger.info(f"Found {len(pending_notes)} notes to index")
                    
                    # Process in batches
                    for i in range(0, len(pending_notes), self.batch_size):
                        if not self._running:
                            break
                        
                        batch = pending_notes[i:i + self.batch_size]
                        await self._process_batch(batch)
                        
                        # Rate limiting
                        await asyncio.sleep(self.delay_seconds)
                    
                    self._stats['last_run'] = datetime.now().isoformat()
                else:
                    logger.debug("No pending notes to index")
                
                # Wait before next scan (check every 10 minutes)
                await asyncio.sleep(600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in indexing loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait a minute on error
    
    async def _find_pending_notes(self) -> List[Dict[str, Any]]:
        """
        Find notes that need indexing
        (notes without ai_indexed field in frontmatter)
        """
        try:
            # Get all documents
            all_docs = await self.couchdb.get_all_documents(limit=500)
            self._stats['total_notes'] = len(all_docs)
            
            # Get vector store stats to see what's already indexed
            vector_stats = await self.vector_store.get_stats()
            indexed_count = vector_stats.get('total_vectors', 0)
            self._stats['indexed_notes'] = indexed_count
            
            # Simple heuristic: if note count > vector count, we have pending notes
            # In real implementation, would check frontmatter for ai_indexed field
            pending = []
            
            for doc in all_docs:
                # Check if note has ai_indexed marker
                content = doc.get('data', '')
                if 'ai_indexed:' not in content:
                    pending.append(doc)
            
            self._stats['pending_notes'] = len(pending)
            
            # Return oldest notes first (by ctime)
            pending.sort(key=lambda x: x.get('ctime', 0))
            
            return pending[:50]  # Limit to 50 per scan
            
        except Exception as e:
            logger.error(f"Failed to find pending notes: {e}")
            return []
    
    async def _process_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of notes"""
        logger.info(f"Processing batch of {len(batch)} notes...")
        
        for doc in batch:
            try:
                await self._index_note(doc)
            except Exception as e:
                logger.error(f"Failed to index note {doc.get('_id')}: {e}")
                self._stats['failed_notes'] += 1
    
    async def _index_note(self, doc: Dict[str, Any]):
        """Index a single note"""
        note_id = doc.get('_id') or doc.get('path', '')
        content = doc.get('data', '')
        
        if not content or len(content.strip()) < 10:
            logger.debug(f"Skipping empty note: {note_id}")
            return
        
        logger.info(f"Indexing note: {note_id}")
        
        # Extract metadata
        metadata = await self.metadata_gen.extract_metadata(content)
        
        # Enrich content with frontmatter
        enriched_content = self.metadata_gen.enrich_frontmatter(
            content=content,
            metadata=metadata,
            source='indexer',
            username='system'
        )
        
        # Update document in CouchDB
        try:
            # Get current revision
            current_doc = await self.couchdb.get_document(note_id)
            rev = current_doc.get('_rev')
            
            # Update document
            updated_doc = {
                **current_doc,
                'data': enriched_content,
                'size': len(enriched_content)
            }
            
            # CouchDB update would go here
            # For now, skip to avoid conflicts
            logger.debug(f"Would update {note_id} with metadata")
            
        except Exception as e:
            logger.warning(f"Failed to update document {note_id}: {e}")
        
        # Generate embedding and save to vector store
        try:
            # Create text for embedding
            embed_text = f"{metadata.get('summary', '')} {content}"
            embedding = await self.llm.embed_text(embed_text[:8000])
            
            # Save to Qdrant
            await self.vector_store.upsert_note(
                note_id=note_id,
                embedding=embedding,
                metadata={
                    'category': metadata.get('category', 'Inbox'),
                    'tags': metadata.get('tags', []),
                    'keywords': metadata.get('keywords', []),
                    'mtime': doc.get('mtime', 0),
                    'ctime': doc.get('ctime', 0),
                    'summary': metadata.get('summary', '')
                }
            )
            
            self._stats['indexed_notes'] += 1
            logger.info(f"Successfully indexed: {note_id}")
            
        except Exception as e:
            logger.error(f"Failed to create embedding for {note_id}: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        return {
            **self._stats,
            'is_running': self._running
        }
    
    async def reindex_all(self):
        """Manually trigger full reindex"""
        logger.info("Starting manual full reindex...")
        
        try:
            pending_notes = await self._find_pending_notes()
            
            for note in pending_notes:
                await self._index_note(note)
            
            logger.info(f"Reindex completed: {len(pending_notes)} notes processed")
            return {'success': True, 'notes_processed': len(pending_notes)}
            
        except Exception as e:
            logger.error(f"Reindex failed: {e}")
            return {'success': False, 'error': str(e)}
