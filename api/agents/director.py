"""
Message Director
Routes incoming messages to appropriate agents
"""

import logging
from typing import Dict, Any, List, Optional

from llm.manager import LLMManager
from vector_store import VectorStoreClient
from .base_agent import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class MessageDirector:
    """
    Routes messages to appropriate agents based on intent and context
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        couchdb: Any,
        vector_store: VectorStoreClient
    ):
        self.llm = llm_manager
        self.couchdb = couchdb
        self.vector_store = vector_store
        self._agents: List[BaseAgent] = []
        self._agent_map: Dict[str, BaseAgent] = {}
        
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the director"""
        self._agents.append(agent)
        self._agent_map[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name"""
        return self._agent_map.get(name)
    
    async def route_message(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """
        Route message to most appropriate agent
        
        Args:
            message: User message
            context: Context dict containing:
                - user_id: Telegram user ID
                - username: Telegram username
                - awaiting_research: bool (if Research mode active)
                - last_agent: str (name of last used agent)
                
        Returns:
            AgentResponse from selected agent
        """
        
        # Check if Research mode is explicitly active
        if context.get('awaiting_research', False):
            research_agent = self.get_agent('research')
            if research_agent:
                logger.info("Routing to Research Agent (explicit mode)")
                return await research_agent.process(message, context)
        
        # Analyze intent with LLM
        intent = await self._analyze_intent(message)
        
        logger.info(f"Message intent: {intent}")
        
        # Route based on intent
        if intent == 'question':
            # Route to Q&A Agent
            qa_agent = self.get_agent('qa')
            if qa_agent:
                logger.info("Routing to Q&A Agent")
                return await qa_agent.process(message, context)
        
        # Default: always save as note via Note Taker
        note_taker = self.get_agent('note_taker')
        if note_taker:
            logger.info("Routing to Note Taker Agent")
            return await note_taker.process(message, context)
        
        # Fallback
        return AgentResponse(
            text="No agents available to handle this message.",
            success=False
        )
    
    async def _analyze_intent(self, message: str) -> str:
        """
        Analyze message intent using LLM
        
        Returns:
            Intent string: 'question', 'note', 'command'
        """
        # Quick heuristic checks first
        if message.strip().startswith('/'):
            return 'command'
        
        if '?' in message or any(
            message.lower().startswith(q) 
            for q in ['что', 'где', 'когда', 'как', 'почему', 'кто', 
                     'what', 'where', 'when', 'how', 'why', 'who']
        ):
            return 'question'
        
        # For short messages, default to note
        if len(message.split()) < 15:
            return 'note'
        
        # Use LLM for ambiguous cases
        try:
            system_prompt = """You are an intent classifier. 
Classify the user message as one of:
- "question" - if user is asking something
- "note" - if user is saving information/thoughts
- "command" - if user is giving a command

Respond with just one word: question, note, or command."""

            response = await self.llm.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Message: {message}"}
                ],
                temperature=0.1
            )
            
            intent = response.strip().lower()
            if intent in ['question', 'note', 'command']:
                return intent
            
        except Exception as e:
            logger.warning(f"Intent analysis failed: {e}")
        
        # Default to note
        return 'note'
    
    async def select_best_agent(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Optional[BaseAgent]:
        """
        Select best agent based on confidence scores
        
        Returns:
            Best matching agent or None
        """
        if not self._agents:
            return None
        
        # Get confidence scores from all agents
        scores = []
        for agent in self._agents:
            try:
                score = await agent.can_handle(message, context)
                scores.append((agent, score))
            except Exception as e:
                logger.error(f"Error checking agent {agent.name}: {e}")
                scores.append((agent, 0.0))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return best agent if score is above threshold
        best_agent, best_score = scores[0]
        if best_score > 0.3:
            logger.info(f"Selected agent: {best_agent.name} (score: {best_score:.2f})")
            return best_agent
        
        logger.warning(f"No confident agent found (best score: {best_score:.2f})")
        return None
    
    def list_agents(self) -> List[str]:
        """Get list of registered agent names"""
        return [agent.name for agent in self._agents]
