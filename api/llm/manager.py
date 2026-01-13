"""
LLM Manager - Factory and unified interface for LLM providers
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings

from .base import LLMProvider
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class LLMSettings(BaseSettings):
    """Settings for LLM providers"""
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    default_llm_provider: str = "claude"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    
    class Config:
        env_file = ".env"


class LLMManager:
    """
    Manages multiple LLM providers and provides unified interface
    """
    
    def __init__(self, settings: Optional[LLMSettings] = None):
        self.settings = settings or LLMSettings()
        self._providers: Dict[str, LLMProvider] = {}
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize available LLM providers"""
        # Claude provider
        if self.settings.anthropic_api_key:
            try:
                self._providers['claude'] = ClaudeProvider(
                    api_key=self.settings.anthropic_api_key
                )
                logger.info("Claude provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude provider: {e}")
        
        # OpenAI provider
        if self.settings.openai_api_key:
            try:
                self._providers['openai'] = OpenAIProvider(
                    api_key=self.settings.openai_api_key,
                    embedding_model=self.settings.openai_embedding_model
                )
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        if not self._providers:
            raise ValueError(
                "No LLM providers initialized. Please provide API keys in .env file."
            )
    
    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        """
        Get LLM provider by name
        
        Args:
            name: Provider name ('claude' or 'openai'). 
                  If None, uses default from settings.
                  
        Returns:
            LLM provider instance
        """
        provider_name = name or self.settings.default_llm_provider
        
        if provider_name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' not available. "
                f"Available providers: {available}"
            )
        
        return self._providers[provider_name]
    
    async def complete(
        self, 
        messages: List[Dict[str, str]], 
        provider: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text completion using specified or default provider
        
        Args:
            messages: List of message dicts
            provider: Provider name (optional, uses default)
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated text
        """
        llm = self.get_provider(provider)
        return await llm.complete(messages, **kwargs)
    
    async def complete_json(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response
        
        Args:
            messages: List of message dicts
            provider: Provider name (optional, uses default)
            **kwargs: Provider-specific parameters
            
        Returns:
            Parsed JSON response
        """
        llm = self.get_provider(provider)
        return await llm.complete_json(messages, **kwargs)
    
    async def embed_text(
        self, 
        text: str,
        dimensions: Optional[int] = None
    ) -> List[float]:
        """
        Generate embeddings for text using OpenAI
        (Claude doesn't support embeddings)
        
        Args:
            text: Input text to embed
            dimensions: Embedding dimensions (optional)
            
        Returns:
            Embedding vector
        """
        if 'openai' not in self._providers:
            raise ValueError(
                "OpenAI provider required for embeddings. "
                "Please set OPENAI_API_KEY in .env"
            )
        
        dims = dimensions or self.settings.embedding_dimensions
        return await self._providers['openai'].embed(text, dimensions=dims)
    
    def list_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self._providers.keys())
    
    def is_available(self, provider: str) -> bool:
        """Check if provider is available"""
        return provider in self._providers
