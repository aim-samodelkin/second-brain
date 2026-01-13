"""
Base Agent class for all intelligent agents
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import logging

from llm.manager import LLMManager
from vector_store import VectorStoreClient

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from an agent"""
    text: str  # Main response text
    success: bool = True
    metadata: Optional[Dict[str, Any]] = None  # Additional data
    suggested_actions: Optional[List[str]] = None  # Follow-up actions


class BaseAgent(ABC):
    """
    Abstract base class for all agents
    """
    
    def __init__(
        self,
        name: str,
        llm_manager: LLMManager,
        couchdb: Any,  # CouchDBClient from main.py
        vector_store: VectorStoreClient
    ):
        self.name = name
        self.llm = llm_manager
        self.couchdb = couchdb
        self.vector_store = vector_store
        self.logger = logging.getLogger(f"agents.{name}")
    
    @abstractmethod
    async def can_handle(self, message: str, context: Dict[str, Any]) -> float:
        """
        Determine if this agent can handle the message
        
        Args:
            message: User message text
            context: Context dict with user info, history, etc.
            
        Returns:
            Confidence score 0.0-1.0 (higher = more confident)
        """
        pass
    
    @abstractmethod
    async def process(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """
        Process the message and return response
        
        Args:
            message: User message text
            context: Context dict
            
        Returns:
            AgentResponse with result
        """
        pass
    
    def _is_question(self, message: str) -> bool:
        """Check if message is a question"""
        question_words = [
            'что', 'где', 'когда', 'как', 'почему', 'зачем', 'кто', 'чем',
            'what', 'where', 'when', 'how', 'why', 'who', 'which'
        ]
        
        message_lower = message.lower()
        
        # Check for question mark
        if '?' in message:
            return True
        
        # Check for question words at start
        for word in question_words:
            if message_lower.startswith(word + ' '):
                return True
        
        return False
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract simple keywords from text"""
        # Simple keyword extraction (can be improved with NLP)
        words = text.lower().split()
        # Filter out common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were',
            'и', 'в', 'на', 'с', 'по', 'для', 'из', 'к', 'от', 'о', 'это', 'как'
        }
        
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        return keywords[:10]
