"""
Vector Store Client for Qdrant
Handles semantic search and vector storage
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range,
    SearchParams
)
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class VectorStoreSettings(BaseSettings):
    """Settings for vector store"""
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "second_brain_notes"
    embedding_dimensions: int = 1536
    
    class Config:
        env_file = ".env"


class VectorStoreClient:
    """
    Client for Qdrant vector database operations
    """
    
    def __init__(self, settings: Optional[VectorStoreSettings] = None):
        self.settings = settings or VectorStoreSettings()
        self.client = AsyncQdrantClient(url=self.settings.qdrant_url)
        self.collection_name = self.settings.qdrant_collection
        self._initialized = False
        
    async def initialize(self):
        """Initialize collection if it doesn't exist"""
        if self._initialized:
            return
        
        try:
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.settings.embedding_dimensions,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection created: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise
    
    async def upsert_note(
        self,
        note_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Insert or update note vector and metadata
        
        Args:
            note_id: Unique note identifier (path in CouchDB)
            embedding: Vector embedding of note content
            metadata: Metadata dict containing:
                - category: str (folder path)
                - tags: List[str]
                - keywords: List[str]
                - mtime: int (timestamp)
                - ctime: int (timestamp)
                - summary: str (optional)
                
        Returns:
            True if successful
        """
        await self.initialize()
        
        try:
            # Create point with vector and payload
            point = PointStruct(
                id=abs(hash(note_id)) % (10 ** 8),  # Convert note_id to numeric ID
                vector=embedding,
                payload={
                    "note_id": note_id,
                    "category": metadata.get("category", ""),
                    "tags": metadata.get("tags", []),
                    "keywords": metadata.get("keywords", []),
                    "mtime": metadata.get("mtime", 0),
                    "ctime": metadata.get("ctime", 0),
                    "summary": metadata.get("summary", ""),
                    "indexed_at": datetime.now().isoformat()
                }
            )
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Upserted vector for note: {note_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert note vector: {e}")
            raise
    
    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 30,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar notes by vector similarity
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            filters: Optional filters dict:
                - categories: List[str] - filter by categories
                - tags: List[str] - filter by tags
                - after_date: int - filter notes after timestamp
            score_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of dicts with 'note_id', 'score', and metadata
        """
        await self.initialize()
        
        try:
            # Build filter conditions
            filter_conditions = []
            
            if filters:
                # Category filter
                if 'categories' in filters and filters['categories']:
                    filter_conditions.append(
                        FieldCondition(
                            key="category",
                            match=MatchValue(any=filters['categories'])
                        )
                    )
                
                # Tags filter
                if 'tags' in filters and filters['tags']:
                    filter_conditions.append(
                        FieldCondition(
                            key="tags",
                            match=MatchValue(any=filters['tags'])
                        )
                    )
                
                # Date range filter
                if 'after_date' in filters:
                    filter_conditions.append(
                        FieldCondition(
                            key="mtime",
                            range=Range(gte=filters['after_date'])
                        )
                    )
            
            # Perform search
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter,
                with_payload=True
            )
            
            # Format results
            formatted_results = []
            for hit in results:
                result = {
                    "note_id": hit.payload.get("note_id"),
                    "score": hit.score,
                    "category": hit.payload.get("category"),
                    "tags": hit.payload.get("tags", []),
                    "keywords": hit.payload.get("keywords", []),
                    "summary": hit.payload.get("summary", ""),
                    "mtime": hit.payload.get("mtime", 0)
                }
                formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} similar notes")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise
    
    async def delete_note(self, note_id: str) -> bool:
        """
        Delete note vector from collection
        
        Args:
            note_id: Note identifier
            
        Returns:
            True if successful
        """
        await self.initialize()
        
        try:
            point_id = abs(hash(note_id)) % (10 ** 8)
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
            
            logger.info(f"Deleted vector for note: {note_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete note vector: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics
        
        Returns:
            Dict with stats about the collection
        """
        await self.initialize()
        
        try:
            info = await self.client.get_collection(self.collection_name)
            
            return {
                "total_vectors": info.points_count,
                "vector_dimensions": info.config.params.vectors.size,
                "indexed_count": info.indexed_vectors_count if hasattr(info, 'indexed_vectors_count') else info.points_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_vectors": 0,
                "vector_dimensions": self.settings.embedding_dimensions,
                "indexed_count": 0
            }
    
    async def clear_collection(self):
        """Clear all vectors from collection (use with caution!)"""
        await self.initialize()
        
        try:
            await self.client.delete_collection(self.collection_name)
            await self.initialize()  # Recreate empty collection
            logger.warning(f"Collection {self.collection_name} cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise
