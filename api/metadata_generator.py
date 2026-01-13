"""
Metadata Generator
Extracts rich metadata from notes using LLM
"""

import re
import yaml
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from llm.manager import LLMManager

logger = logging.getLogger(__name__)


class MetadataGenerator:
    """
    Generates rich metadata for notes using LLM analysis
    """
    
    def __init__(self, llm_manager: LLMManager):
        self.llm = llm_manager
        
    async def extract_metadata(
        self,
        content: str,
        existing_folders: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured metadata from note content
        
        Args:
            content: Note content (may include existing frontmatter)
            existing_folders: List of existing folders for categorization
            
        Returns:
            Dict with extracted metadata
        """
        # Remove existing frontmatter for analysis
        clean_content = self._remove_frontmatter(content)
        
        if not clean_content or len(clean_content.strip()) < 10:
            return self._get_default_metadata()
        
        # Build prompt with folder context
        folders_context = ""
        if existing_folders:
            folders_list = "\n".join([f"- {folder}" for folder in existing_folders[:20]])
            folders_context = f"""
Existing folder structure (suggest one of these or create new):
{folders_list}
"""
        
        system_prompt = """You are an expert at analyzing notes and extracting structured metadata.
Your task is to analyze the note content and provide rich metadata in JSON format.
Be concise but accurate. Extract entities, topics, and suggest appropriate categorization."""

        user_prompt = f"""{folders_context}

Analyze this note and extract metadata:

Note content:
{clean_content[:2000]}  

Provide metadata in this JSON structure:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "category": "suggested/folder/path",
  "summary": "Brief 1-2 sentence summary",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "entities": {{
    "people": ["Person Name"],
    "companies": ["Company Name"],
    "locations": ["Location"]
  }},
  "sentiment": "positive|negative|neutral",
  "priority": "low|medium|high",
  "has_tasks": true|false
}}

Rules:
- Tags: 3-5 relevant tags (lowercase, no spaces)
- Category: Choose from existing folders or suggest new logical path
- Summary: 1-2 sentences capturing main idea
- Keywords: 3-7 important terms from the content
- Entities: Extract mentioned people, companies, locations
- Sentiment: Overall tone of the note
- Priority: Urgency/importance indicator
- has_tasks: Whether note contains action items/todos
"""

        try:
            # Get structured response from LLM
            metadata = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            # Validate and normalize
            metadata = self._validate_metadata(metadata)
            
            logger.info(f"Extracted metadata: {len(metadata.get('tags', []))} tags, "
                       f"category: {metadata.get('category', 'N/A')}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return self._get_default_metadata()
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize extracted metadata"""
        validated = {}
        
        # Tags (ensure list of strings)
        validated['tags'] = []
        if 'tags' in metadata and isinstance(metadata['tags'], list):
            validated['tags'] = [
                str(tag).lower().strip()
                for tag in metadata['tags']
                if tag and len(str(tag)) < 30
            ][:10]  # Max 10 tags
        
        # Category
        validated['category'] = str(metadata.get('category', 'Inbox')).strip()
        if not validated['category']:
            validated['category'] = 'Inbox'
        
        # Summary
        validated['summary'] = str(metadata.get('summary', '')).strip()[:500]
        
        # Keywords
        validated['keywords'] = []
        if 'keywords' in metadata and isinstance(metadata['keywords'], list):
            validated['keywords'] = [
                str(kw).lower().strip()
                for kw in metadata['keywords']
                if kw and len(str(kw)) < 50
            ][:15]  # Max 15 keywords
        
        # Entities
        entities = metadata.get('entities', {})
        if isinstance(entities, dict):
            validated['entities'] = {
                'people': [str(p) for p in entities.get('people', []) if p][:10],
                'companies': [str(c) for c in entities.get('companies', []) if c][:10],
                'locations': [str(l) for l in entities.get('locations', []) if l][:10]
            }
        else:
            validated['entities'] = {'people': [], 'companies': [], 'locations': []}
        
        # Sentiment
        sentiment = str(metadata.get('sentiment', 'neutral')).lower()
        if sentiment not in ['positive', 'negative', 'neutral']:
            sentiment = 'neutral'
        validated['sentiment'] = sentiment
        
        # Priority
        priority = str(metadata.get('priority', 'medium')).lower()
        if priority not in ['low', 'medium', 'high']:
            priority = 'medium'
        validated['priority'] = priority
        
        # Has tasks
        validated['has_tasks'] = bool(metadata.get('has_tasks', False))
        
        return validated
    
    def _get_default_metadata(self) -> Dict[str, Any]:
        """Return default metadata structure"""
        return {
            'tags': [],
            'category': 'Inbox',
            'summary': '',
            'keywords': [],
            'entities': {
                'people': [],
                'companies': [],
                'locations': []
            },
            'sentiment': 'neutral',
            'priority': 'medium',
            'has_tasks': False
        }
    
    def enrich_frontmatter(
        self,
        content: str,
        metadata: Dict[str, Any],
        source: str = "telegram",
        username: str = ""
    ) -> str:
        """
        Add or update YAML frontmatter in note content
        
        Args:
            content: Original note content
            metadata: Extracted metadata dict
            source: Source of the note (telegram, api, etc.)
            username: Username who created the note
            
        Returns:
            Content with enriched frontmatter
        """
        # Extract existing frontmatter
        existing_fm, body = self._parse_frontmatter(content)
        
        # Build new frontmatter
        now = datetime.now()
        
        frontmatter = {
            # Preserve or set creation info
            'created': existing_fm.get('created', now.isoformat()),
            'source': existing_fm.get('source', source),
            'from': existing_fm.get('from', username),
            
            # AI-generated metadata with ai_ prefix
            'ai_tags': metadata.get('tags', []),
            'ai_category': metadata.get('category', 'Inbox'),
            'ai_summary': metadata.get('summary', ''),
            'ai_keywords': metadata.get('keywords', []),
            'ai_entities': metadata.get('entities', {}),
            'ai_sentiment': metadata.get('sentiment', 'neutral'),
            'ai_priority': metadata.get('priority', 'medium'),
            'ai_has_tasks': metadata.get('has_tasks', False),
            'ai_indexed': now.isoformat()
        }
        
        # Convert to YAML
        yaml_str = yaml.dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )
        
        # Build final content
        final_content = f"---\n{yaml_str}---\n\n{body.strip()}\n"
        
        return final_content
    
    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """
        Parse YAML frontmatter from content
        
        Returns:
            Tuple of (frontmatter_dict, body_content)
        """
        # Match YAML frontmatter
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)
        
        if match:
            yaml_str = match.group(1)
            body = match.group(2)
            
            try:
                frontmatter = yaml.safe_load(yaml_str) or {}
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse existing frontmatter: {e}")
                frontmatter = {}
            
            return frontmatter, body
        else:
            return {}, content
    
    def _remove_frontmatter(self, content: str) -> str:
        """Remove frontmatter and return clean content"""
        _, body = self._parse_frontmatter(content)
        return body
    
    def extract_existing_folders(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Extract unique folder paths from documents
        
        Args:
            documents: List of CouchDB documents with 'path' field
            
        Returns:
            Sorted list of unique folder paths
        """
        folders = set()
        
        for doc in documents:
            path = doc.get('path', '')
            if '/' in path:
                # Extract folder path (everything before last /)
                folder = '/'.join(path.split('/')[:-1])
                if folder:
                    folders.add(folder)
        
        # Sort by frequency (most common first) and name
        sorted_folders = sorted(folders)
        
        return sorted_folders[:30]  # Return top 30 folders
