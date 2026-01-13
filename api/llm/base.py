"""
Base abstract class for LLM providers
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.config = kwargs
        
    @abstractmethod
    async def complete(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> str:
        """
        Generate text completion from messages
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    async def complete_json(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response
        
        Args:
            messages: List of message dicts
            **kwargs: Provider-specific parameters
            
        Returns:
            Parsed JSON response
        """
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Generate embeddings for text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        pass
    
    def _validate_messages(self, messages: List[Dict[str, str]]) -> None:
        """Validate messages format"""
        if not messages:
            raise ValueError("Messages list cannot be empty")
            
        for msg in messages:
            if 'role' not in msg or 'content' not in msg:
                raise ValueError("Each message must have 'role' and 'content'")
            if msg['role'] not in ['system', 'user', 'assistant']:
                raise ValueError(f"Invalid role: {msg['role']}")
