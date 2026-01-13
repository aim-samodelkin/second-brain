"""
Claude API Provider implementation
"""

import json
import logging
from typing import List, Dict, Any
from anthropic import AsyncAnthropic

from .base import LLMProvider

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Claude API provider"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", **kwargs):
        super().__init__(api_key, **kwargs)
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key)
        
    async def complete(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """Generate text completion using Claude API"""
        self._validate_messages(messages)
        
        # Extract system message if present
        system_message = None
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                user_messages.append(msg)
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_message if system_message else None,
                messages=user_messages,
                **kwargs
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    async def complete_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate structured JSON response"""
        
        # Append JSON instruction to last message
        if messages:
            last_msg = messages[-1]
            if last_msg['role'] == 'user':
                last_msg['content'] += "\n\nRespond with valid JSON only, no markdown formatting."
        
        response_text = await self.complete(
            messages, 
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Parse JSON from response
        try:
            # Try to extract JSON from markdown code blocks
            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            elif '```' in response_text:
                start = response_text.find('```') + 3
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            raise ValueError(f"Invalid JSON response from Claude: {e}")
    
    async def embed(self, text: str) -> List[float]:
        """
        Claude doesn't provide embeddings API.
        This will raise NotImplementedError.
        Use OpenAI provider for embeddings.
        """
        raise NotImplementedError(
            "Claude does not provide embeddings API. "
            "Use OpenAI provider for embeddings."
        )
