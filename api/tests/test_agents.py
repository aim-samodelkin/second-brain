"""
Tests for intelligent agents
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from agents.base_agent import BaseAgent, AgentResponse
from agents.director import MessageDirector


class TestBaseAgent:
    """Tests for BaseAgent functionality"""
    
    def test_is_question_with_question_mark(self):
        """Test question detection with question mark"""
        
        class DummyAgent(BaseAgent):
            async def can_handle(self, message, context):
                return 0.5
            
            async def process(self, message, context):
                return AgentResponse(text="test", success=True)
        
        agent = DummyAgent(
            name="dummy",
            llm_manager=Mock(),
            couchdb=Mock(),
            vector_store=Mock()
        )
        
        assert agent._is_question("What is this?") is True
        assert agent._is_question("Это вопрос?") is True
        assert agent._is_question("This is statement") is False
    
    def test_extract_keywords(self):
        """Test keyword extraction"""
        
        class DummyAgent(BaseAgent):
            async def can_handle(self, message, context):
                return 0.5
            
            async def process(self, message, context):
                return AgentResponse(text="test", success=True)
        
        agent = DummyAgent(
            name="dummy",
            llm_manager=Mock(),
            couchdb=Mock(),
            vector_store=Mock()
        )
        
        keywords = agent._extract_keywords("machine learning deployment strategies")
        assert "machine" in keywords
        assert "learning" in keywords
        assert "deployment" in keywords
        assert len(keywords) <= 10


class TestMessageDirector:
    """Tests for MessageDirector"""
    
    @pytest.mark.asyncio
    async def test_director_initialization(self):
        """Test director initialization"""
        llm_manager = Mock()
        couchdb = Mock()
        vector_store = Mock()
        
        director = MessageDirector(llm_manager, couchdb, vector_store)
        
        assert director is not None
        assert len(director.list_agents()) == 0
    
    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test agent registration"""
        llm_manager = Mock()
        couchdb = Mock()
        vector_store = Mock()
        
        director = MessageDirector(llm_manager, couchdb, vector_store)
        
        # Create mock agent
        mock_agent = Mock(spec=BaseAgent)
        mock_agent.name = "test_agent"
        
        director.register_agent(mock_agent)
        
        assert "test_agent" in director.list_agents()
        assert director.get_agent("test_agent") is mock_agent
    
    @pytest.mark.asyncio
    async def test_analyze_intent_question(self):
        """Test intent analysis for questions"""
        llm_manager = Mock()
        couchdb = Mock()
        vector_store = Mock()
        
        director = MessageDirector(llm_manager, couchdb, vector_store)
        
        # Question should be detected
        intent = await director._analyze_intent("What is machine learning?")
        assert intent == "question"
        
        # Command should be detected
        intent = await director._analyze_intent("/start")
        assert intent == "command"
    
    @pytest.mark.asyncio
    async def test_route_to_research_mode(self):
        """Test routing with research mode active"""
        llm_manager = Mock()
        couchdb = Mock()
        vector_store = Mock()
        
        director = MessageDirector(llm_manager, couchdb, vector_store)
        
        # Register mock research agent
        research_agent = Mock(spec=BaseAgent)
        research_agent.name = "research"
        research_agent.process = AsyncMock(return_value=AgentResponse(
            text="Research results",
            success=True
        ))
        
        director.register_agent(research_agent)
        
        # Route with research mode
        context = {'awaiting_research': True}
        response = await director.route_message("Test topic", context)
        
        # Verify research agent was called
        research_agent.process.assert_called_once()
        assert response.text == "Research results"


class TestAgentResponse:
    """Tests for AgentResponse dataclass"""
    
    def test_agent_response_creation(self):
        """Test AgentResponse creation"""
        response = AgentResponse(
            text="Test response",
            success=True,
            metadata={'key': 'value'}
        )
        
        assert response.text == "Test response"
        assert response.success is True
        assert response.metadata == {'key': 'value'}
        assert response.suggested_actions is None
    
    def test_agent_response_with_actions(self):
        """Test AgentResponse with suggested actions"""
        response = AgentResponse(
            text="Test",
            success=True,
            suggested_actions=["action1", "action2"]
        )
        
        assert len(response.suggested_actions) == 2
        assert "action1" in response.suggested_actions


@pytest.mark.asyncio
async def test_integration_director_with_agents():
    """Integration test: Director routing to multiple agents"""
    
    # Setup
    llm_manager = Mock()
    llm_manager.complete = AsyncMock(return_value="note")
    
    couchdb = Mock()
    vector_store = Mock()
    
    director = MessageDirector(llm_manager, couchdb, vector_store)
    
    # Create mock note taker
    note_taker = Mock(spec=BaseAgent)
    note_taker.name = "note_taker"
    note_taker.can_handle = AsyncMock(return_value=0.5)
    note_taker.process = AsyncMock(return_value=AgentResponse(
        text="Note saved",
        success=True
    ))
    
    # Create mock QA agent
    qa_agent = Mock(spec=BaseAgent)
    qa_agent.name = "qa"
    qa_agent.can_handle = AsyncMock(return_value=0.9)
    qa_agent.process = AsyncMock(return_value=AgentResponse(
        text="Answer to question",
        success=True
    ))
    
    director.register_agent(note_taker)
    director.register_agent(qa_agent)
    
    # Test routing to note taker (statement)
    response = await director.route_message(
        "This is a note",
        {'user_id': 123}
    )
    
    assert response.success is True
    # Either note_taker or qa could be called depending on intent analysis
    assert response.text in ["Note saved", "Answer to question"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
