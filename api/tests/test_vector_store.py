"""
Tests for Vector Store Client
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from vector_store import VectorStoreClient, VectorStoreSettings


class TestVectorStoreClient:
    """Tests for VectorStoreClient"""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Fixture for mocked Qdrant client"""
        with patch('vector_store.AsyncQdrantClient') as mock:
            mock_instance = Mock()
            mock_instance.get_collections = AsyncMock(return_value=Mock(collections=[]))
            mock_instance.create_collection = AsyncMock()
            mock_instance.upsert = AsyncMock()
            mock_instance.search = AsyncMock(return_value=[])
            mock_instance.get_collection = AsyncMock(return_value=Mock(
                points_count=100,
                config=Mock(params=Mock(vectors=Mock(size=1536))),
                indexed_vectors_count=100
            ))
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_qdrant_client):
        """Test vector store initialization"""
        settings = VectorStoreSettings(
            qdrant_url="http://localhost:6333",
            qdrant_collection="test_collection"
        )
        
        client = VectorStoreClient(settings)
        await client.initialize()
        
        assert client._initialized is True
        mock_qdrant_client.get_collections.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upsert_note(self, mock_qdrant_client):
        """Test upserting note with vector"""
        settings = VectorStoreSettings()
        client = VectorStoreClient(settings)
        await client.initialize()
        
        embedding = [0.1] * 1536
        metadata = {
            'category': 'Projects',
            'tags': ['ai', 'ml'],
            'keywords': ['test'],
            'mtime': 1234567890,
            'ctime': 1234567890,
            'summary': 'Test note'
        }
        
        result = await client.upsert_note(
            note_id="test/note.md",
            embedding=embedding,
            metadata=metadata
        )
        
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_similar(self, mock_qdrant_client):
        """Test similarity search"""
        # Setup mock search results
        mock_result = Mock()
        mock_result.score = 0.95
        mock_result.payload = {
            'note_id': 'test/note.md',
            'category': 'Projects',
            'tags': ['ai'],
            'keywords': ['test'],
            'summary': 'Test note',
            'mtime': 1234567890
        }
        mock_qdrant_client.search = AsyncMock(return_value=[mock_result])
        
        settings = VectorStoreSettings()
        client = VectorStoreClient(settings)
        await client.initialize()
        
        query_embedding = [0.1] * 1536
        results = await client.search_similar(
            query_embedding=query_embedding,
            limit=10
        )
        
        assert len(results) == 1
        assert results[0]['note_id'] == 'test/note.md'
        assert results[0]['score'] == 0.95
        mock_qdrant_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_qdrant_client):
        """Test search with metadata filters"""
        settings = VectorStoreSettings()
        client = VectorStoreClient(settings)
        await client.initialize()
        
        query_embedding = [0.1] * 1536
        filters = {
            'categories': ['Projects'],
            'tags': ['ai'],
            'after_date': 1234567890
        }
        
        await client.search_similar(
            query_embedding=query_embedding,
            filters=filters,
            limit=10
        )
        
        # Verify search was called with filters
        call_args = mock_qdrant_client.search.call_args
        assert call_args is not None
        assert 'query_filter' in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_get_stats(self, mock_qdrant_client):
        """Test getting collection statistics"""
        settings = VectorStoreSettings()
        client = VectorStoreClient(settings)
        await client.initialize()
        
        stats = await client.get_stats()
        
        assert 'total_vectors' in stats
        assert 'vector_dimensions' in stats
        assert stats['total_vectors'] == 100
        assert stats['vector_dimensions'] == 1536
    
    @pytest.mark.asyncio
    async def test_delete_note(self, mock_qdrant_client):
        """Test deleting note vector"""
        mock_qdrant_client.delete = AsyncMock()
        
        settings = VectorStoreSettings()
        client = VectorStoreClient(settings)
        await client.initialize()
        
        result = await client.delete_note("test/note.md")
        
        assert result is True
        mock_qdrant_client.delete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
