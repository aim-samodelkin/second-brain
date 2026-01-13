"""
OpenAI API Provider implementation
"""

import json
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI

from .base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-4-turbo-preview",
        embedding_model: str = "text-embedding-3-small",
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        self.model = model
        self.embedding_model = embedding_model
        self.client = AsyncOpenAI(api_key=api_key)
        
    async def complete(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """Generate text completion using OpenAI API"""
        self._validate_messages(messages)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def complete_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON response using JSON mode"""
        self._validate_messages(messages)
        
        # Ensure system message requests JSON
        has_system = any(msg['role'] == 'system' for msg in messages)
        if not has_system:
            messages.insert(0, {
                'role': 'system',
                'content': 'You are a helpful assistant that responds in JSON format.'
            })
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                **kwargs
            )
            
            response_text = response.choices[0].message.content
            return json.loads(response_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def embed(self, text: str, dimensions: int = 1536) -> List[float]:
        """Generate embeddings using OpenAI API"""
        if not text or not text.strip():
            raise ValueError("Text for embedding cannot be empty")
        
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
                dimensions=dimensions if self.embedding_model.startswith("text-embedding-3") else None
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI Embeddings API error: {e}")
            raise
