"""
Tests for Metadata Generator
"""

import pytest
from unittest.mock import Mock, AsyncMock

from metadata_generator import MetadataGenerator


class TestMetadataGenerator:
    """Tests for MetadataGenerator"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Fixture for mocked LLM manager"""
        manager = Mock()
        manager.complete_json = AsyncMock(return_value={
            'tags': ['test', 'ai', 'ml'],
            'category': 'Projects/AI',
            'summary': 'Test note about AI',
            'keywords': ['artificial', 'intelligence', 'test'],
            'entities': {
                'people': ['John Doe'],
                'companies': ['OpenAI'],
                'locations': []
            },
            'sentiment': 'positive',
            'priority': 'high',
            'has_tasks': False
        })
        return manager
    
    @pytest.mark.asyncio
    async def test_extract_metadata(self, mock_llm_manager):
        """Test metadata extraction"""
        generator = MetadataGenerator(mock_llm_manager)
        
        content = "This is a test note about machine learning and AI."
        metadata = await generator.extract_metadata(content)
        
        assert 'tags' in metadata
        assert 'category' in metadata
        assert 'summary' in metadata
        assert len(metadata['tags']) > 0
        mock_llm_manager.complete_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_metadata_with_folders(self, mock_llm_manager):
        """Test metadata extraction with existing folders context"""
        generator = MetadataGenerator(mock_llm_manager)
        
        existing_folders = ['Projects', 'Knowledge', 'Ideas']
        content = "Test content"
        
        metadata = await generator.extract_metadata(
            content,
            existing_folders=existing_folders
        )
        
        assert metadata is not None
        # Verify folders were passed in prompt
        call_args = mock_llm_manager.complete_json.call_args
        assert call_args is not None
    
    def test_validate_metadata(self, mock_llm_manager):
        """Test metadata validation"""
        generator = MetadataGenerator(mock_llm_manager)
        
        raw_metadata = {
            'tags': ['valid', 'another', '', 'x' * 50],  # One empty, one too long
            'category': 'Valid/Category',
            'summary': 'Valid summary',
            'keywords': ['word1', 'word2'],
            'entities': {
                'people': ['Person 1'],
                'companies': [],
                'locations': ['Location']
            },
            'sentiment': 'positive',
            'priority': 'high',
            'has_tasks': True
        }
        
        validated = generator._validate_metadata(raw_metadata)
        
        assert len(validated['tags']) == 2  # Empty and too-long filtered out
        assert validated['category'] == 'Valid/Category'
        assert validated['sentiment'] in ['positive', 'negative', 'neutral']
        assert validated['priority'] in ['low', 'medium', 'high']
    
    def test_validate_metadata_invalid_sentiment(self, mock_llm_manager):
        """Test metadata validation with invalid sentiment"""
        generator = MetadataGenerator(mock_llm_manager)
        
        raw_metadata = {
            'tags': [],
            'category': 'Test',
            'summary': '',
            'keywords': [],
            'entities': {},
            'sentiment': 'invalid_value',  # Invalid
            'priority': 'invalid_priority',  # Invalid
            'has_tasks': 'not_a_bool'  # Will be converted to bool
        }
        
        validated = generator._validate_metadata(raw_metadata)
        
        # Should default to valid values
        assert validated['sentiment'] == 'neutral'
        assert validated['priority'] == 'medium'
        assert isinstance(validated['has_tasks'], bool)
    
    def test_enrich_frontmatter(self, mock_llm_manager):
        """Test enriching content with frontmatter"""
        generator = MetadataGenerator(mock_llm_manager)
        
        content = "Simple note content"
        metadata = {
            'tags': ['test', 'example'],
            'category': 'Projects',
            'summary': 'Test summary',
            'keywords': ['test'],
            'entities': {'people': [], 'companies': [], 'locations': []},
            'sentiment': 'neutral',
            'priority': 'medium',
            'has_tasks': False
        }
        
        enriched = generator.enrich_frontmatter(
            content=content,
            metadata=metadata,
            source='telegram',
            username='testuser'
        )
        
        # Verify frontmatter was added
        assert '---' in enriched
        assert 'ai_tags:' in enriched
        assert 'ai_category:' in enriched
        assert 'ai_summary:' in enriched
        assert 'source: telegram' in enriched
        assert 'from: testuser' in enriched
        assert content in enriched
    
    def test_parse_existing_frontmatter(self, mock_llm_manager):
        """Test parsing existing frontmatter"""
        generator = MetadataGenerator(mock_llm_manager)
        
        content_with_frontmatter = """---
created: 2024-01-01
source: test
---

Body content here"""
        
        frontmatter, body = generator._parse_frontmatter(content_with_frontmatter)
        
        assert 'created' in frontmatter
        assert frontmatter['created'] == '2024-01-01'
        assert 'Body content here' in body
    
    def test_remove_frontmatter(self, mock_llm_manager):
        """Test removing frontmatter"""
        generator = MetadataGenerator(mock_llm_manager)
        
        content_with_frontmatter = """---
created: 2024-01-01
---

Body content"""
        
        clean_content = generator._remove_frontmatter(content_with_frontmatter)
        
        assert '---' not in clean_content
        assert 'created:' not in clean_content
        assert 'Body content' in clean_content
    
    def test_extract_existing_folders(self, mock_llm_manager):
        """Test extracting folder structure from documents"""
        generator = MetadataGenerator(mock_llm_manager)
        
        documents = [
            {'path': 'Projects/AI/note1.md'},
            {'path': 'Projects/AI/note2.md'},
            {'path': 'Knowledge/Tech/note3.md'},
            {'path': 'Ideas/note4.md'},
            {'path': 'Inbox/note5.md'}
        ]
        
        folders = generator.extract_existing_folders(documents)
        
        assert 'Projects/AI' in folders
        assert 'Knowledge/Tech' in folders
        assert 'Ideas' in folders
        assert 'Inbox' in folders
        assert len(folders) <= 30
    
    @pytest.mark.asyncio
    async def test_default_metadata_on_error(self, mock_llm_manager):
        """Test that default metadata is returned on LLM error"""
        # Make LLM throw an error
        mock_llm_manager.complete_json = AsyncMock(side_effect=Exception("LLM error"))
        
        generator = MetadataGenerator(mock_llm_manager)
        
        metadata = await generator.extract_metadata("Test content")
        
        # Should return default metadata structure
        assert metadata['category'] == 'Inbox'
        assert metadata['tags'] == []
        assert metadata['sentiment'] == 'neutral'
        assert metadata['priority'] == 'medium'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
