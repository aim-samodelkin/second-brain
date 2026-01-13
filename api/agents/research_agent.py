"""
Research Agent
Deep analysis and synthesis of knowledge on specific topics
"""

import logging
from typing import Dict, Any, List

from .qa_agent import QAAgent
from .base_agent import AgentResponse
from llm.manager import LLMManager
from vector_store import VectorStoreClient

logger = logging.getLogger(__name__)


class ResearchAgent(QAAgent):
    """
    Agent for deep research and analysis of topics
    Extends QAAgent with multi-pass analysis and synthesis
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        couchdb: Any,
        vector_store: VectorStoreClient
    ):
        super().__init__(llm_manager, couchdb, vector_store)
        self.name = "research"
        
    async def can_handle(self, message: str, context: Dict[str, Any]) -> float:
        """Research is activated explicitly via menu"""
        if context.get('awaiting_research', False):
            return 1.0
        return 0.0
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """
        Deep research process:
        1. Broad search (top 100 candidates)
        2. Rerank to top 20-30
        3. Multi-pass analysis:
           - Overview and key themes
           - Detailed connections analysis
           - Synthesis and conclusions
        4. Structured report
        """
        try:
            self.logger.info(f"Starting research on: {message[:100]}...")
            
            # Stage 1 & 2: Search and filter
            keywords = self._extract_keywords(message)
            filters = await self._stage1_metadata_filter(keywords)
            
            candidates = await self._stage2_hybrid_search(
                query=message,
                filters=filters,
                limit=100  # More candidates for research
            )
            
            if not candidates:
                return AgentResponse(
                    text="🔍 Не нашел достаточно материала для исследования этой темы.",
                    success=True,
                    metadata={'found_count': 0}
                )
            
            # Stage 3: Rerank to top 30
            top_docs = await self._rerank_and_load(
                query=message,
                candidates=candidates,
                top_k=30
            )
            
            if not top_docs:
                return AgentResponse(
                    text="🔍 Нашел заметки, но не смог их обработать.",
                    success=True,
                    metadata={'found_count': len(candidates)}
                )
            
            # Multi-pass analysis
            research_result = await self._multi_pass_analysis(message, top_docs)
            
            return research_result
            
        except Exception as e:
            self.logger.error(f"Research failed: {e}", exc_info=True)
            return AgentResponse(
                text=f"❌ Ошибка при исследовании: {str(e)}",
                success=False
            )
    
    async def _rerank_and_load(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 30
    ) -> List[Dict[str, Any]]:
        """Rerank and load full content for top documents"""
        
        # Prepare for reranking
        docs_for_rerank = []
        for cand in candidates:
            text = cand.get('summary', cand['note_id'])
            docs_for_rerank.append(text)
        
        # Rerank
        reranked_indices = list(range(len(candidates)))
        
        if self.cohere_client and docs_for_rerank:
            try:
                rerank_response = self.cohere_client.rerank(
                    query=query,
                    documents=docs_for_rerank,
                    top_n=min(top_k, len(docs_for_rerank)),
                    model="rerank-english-v3.0"
                )
                reranked_indices = [r.index for r in rerank_response.results]
                self.logger.info(f"Reranked to top {len(reranked_indices)}")
            except Exception as e:
                self.logger.warning(f"Reranking failed: {e}")
                reranked_indices = list(range(min(top_k, len(candidates))))
        
        # Load full content
        docs = []
        for idx in reranked_indices[:top_k]:
            try:
                cand = candidates[idx]
                doc = await self.couchdb.get_document(cand['note_id'])
                docs.append({
                    'path': cand['note_id'],
                    'content': doc.get('data', ''),
                    'category': cand.get('category', ''),
                    'tags': cand.get('tags', [])
                })
            except Exception as e:
                self.logger.warning(f"Failed to load doc: {e}")
        
        return docs
    
    async def _multi_pass_analysis(
        self,
        topic: str,
        documents: List[Dict[str, Any]]
    ) -> AgentResponse:
        """
        Multi-pass analysis of research topic
        """
        
        # Pass 1: Overview and themes
        self.logger.info("Pass 1: Overview...")
        overview = await self._pass1_overview(topic, documents)
        
        # Pass 2: Connections
        self.logger.info("Pass 2: Connections...")
        connections = await self._pass2_connections(topic, documents)
        
        # Pass 3: Synthesis
        self.logger.info("Pass 3: Synthesis...")
        synthesis = await self._pass3_synthesis(topic, overview, connections)
        
        # Format final report
        report = self._format_research_report(
            topic=topic,
            overview=overview,
            connections=connections,
            synthesis=synthesis,
            sources=documents[:10]
        )
        
        return AgentResponse(
            text=report,
            success=True,
            metadata={
                'documents_analyzed': len(documents),
                'sources': [doc['path'] for doc in documents[:10]]
            }
        )
    
    async def _pass1_overview(
        self,
        topic: str,
        documents: List[Dict[str, Any]]
    ) -> str:
        """First pass: General overview and key themes"""
        
        # Build context (limit to avoid token overflow)
        context = ""
        for i, doc in enumerate(documents[:15], 1):
            context += f"\n--- Doc {i}: {doc['path']} ---\n"
            context += doc['content'][:1500]  # Limit per doc
            context += "\n"
        
        prompt = f"""Analyze these documents about "{topic}" and provide:

1. A brief overview (3-4 sentences)
2. Key themes and topics (bullet points)
3. Main concepts mentioned

Documents:
{context[:8000]}

Respond in Russian with clear structure."""

        try:
            response = await self.llm.complete(
                messages=[
                    {"role": "system", "content": "You are a research analyst. Provide clear, structured analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1500
            )
            return response.strip()
        except Exception as e:
            self.logger.error(f"Pass 1 failed: {e}")
            return "Не удалось создать обзор."
    
    async def _pass2_connections(
        self,
        topic: str,
        documents: List[Dict[str, Any]]
    ) -> str:
        """Second pass: Analyze connections and relationships"""
        
        # Focus on relationships
        context = ""
        for i, doc in enumerate(documents[:15], 1):
            context += f"\n{i}. {doc['path']}\n"
            context += doc['content'][:1000]
            context += "\n"
        
        prompt = f"""Analyze connections and relationships in these documents about "{topic}":

{context[:8000]}

Identify:
1. How documents relate to each other
2. Common patterns or recurring ideas
3. Contradictions or different perspectives
4. Knowledge gaps (what's missing)

Respond in Russian."""

        try:
            response = await self.llm.complete(
                messages=[
                    {"role": "system", "content": "You are a research analyst focusing on connections and patterns."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1500
            )
            return response.strip()
        except Exception as e:
            self.logger.error(f"Pass 2 failed: {e}")
            return "Не удалось проанализировать связи."
    
    async def _pass3_synthesis(
        self,
        topic: str,
        overview: str,
        connections: str
    ) -> str:
        """Third pass: Synthesize findings"""
        
        prompt = f"""Based on the research about "{topic}", synthesize the findings:

Overview:
{overview}

Connections:
{connections}

Provide:
1. Key insights (3-5 main points)
2. Actionable conclusions
3. Suggested next steps or areas for further exploration

Respond in Russian with clear structure."""

        try:
            response = await self.llm.complete(
                messages=[
                    {"role": "system", "content": "You are a research analyst synthesizing findings."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1500
            )
            return response.strip()
        except Exception as e:
            self.logger.error(f"Pass 3 failed: {e}")
            return "Не удалось синтезировать выводы."
    
    def _format_research_report(
        self,
        topic: str,
        overview: str,
        connections: str,
        synthesis: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """Format final research report"""
        
        report = f"""🔍 **Исследование:** {topic}

📊 **ОБЗОР**
{overview}

🔗 **СВЯЗИ И ПАТТЕРНЫ**
{connections}

💡 **ВЫВОДЫ И ИНСАЙТЫ**
{synthesis}

📚 **ИСТОЧНИКИ** ({len(sources)} документов)
"""
        
        for i, doc in enumerate(sources[:10], 1):
            report += f"\n{i}. `{doc['path']}`"
            if doc.get('tags'):
                tags_str = ", ".join(doc['tags'][:3])
                report += f" [{tags_str}]"
        
        return report
