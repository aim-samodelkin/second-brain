"""
Q&A Agent
Answers questions using 3-stage search: Metadata Filter → Hybrid Search → Rerank + Analysis
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import cohere
from pydantic_settings import BaseSettings

from .base_agent import BaseAgent, AgentResponse
from llm.manager import LLMManager
from vector_store import VectorStoreClient

logger = logging.getLogger(__name__)


class CohereSettings(BaseSettings):
    """Settings for Cohere API"""
    cohere_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"


class QAAgent(BaseAgent):
    """
    Agent that answers questions using knowledge base search
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        couchdb: Any,
        vector_store: VectorStoreClient
    ):
        super().__init__("qa", llm_manager, couchdb, vector_store)
        
        # Initialize Cohere client for reranking
        settings = CohereSettings()
        self.cohere_client = None
        if settings.cohere_api_key:
            try:
                self.cohere_client = cohere.Client(settings.cohere_api_key)
                logger.info("Cohere client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Cohere: {e}")
        
    async def can_handle(self, message: str, context: Dict[str, Any]) -> float:
        """Q&A handles questions"""
        if self._is_question(message):
            return 0.9  # High confidence for questions
        return 0.1
    
    async def process(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """
        Process question using 3-stage search pipeline
        
        Stages:
        1. Metadata filtering - quick prefilter
        2. Hybrid search - vector + full-text (top 50)
        3. Rerank + LLM analysis - final answer
        """
        try:
            self.logger.info(f"Processing question: {message[:100]}...")
            
            # Stage 1: Metadata filtering
            keywords = self._extract_keywords(message)
            metadata_filters = await self._stage1_metadata_filter(keywords)
            
            # Stage 2: Hybrid search
            candidates = await self._stage2_hybrid_search(
                query=message,
                filters=metadata_filters,
                limit=50
            )
            
            if not candidates:
                return AgentResponse(
                    text="🤷 Не нашел релевантных заметок по вашему вопросу.",
                    success=True,
                    metadata={'found_count': 0}
                )
            
            # Stage 3: Rerank and analyze
            answer = await self._stage3_rerank_and_analyze(
                question=message,
                candidates=candidates,
                top_k=10
            )
            
            return answer
            
        except Exception as e:
            self.logger.error(f"Q&A processing failed: {e}", exc_info=True)
            return AgentResponse(
                text=f"❌ Ошибка при поиске ответа: {str(e)}",
                success=False
            )
    
    async def _stage1_metadata_filter(
        self,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Stage 1: Create metadata filters based on keywords
        
        Returns:
            Filter dict for vector search
        """
        # For now, return minimal filters
        # Can be extended to filter by tags, categories, date ranges
        filters = {}
        
        # Could add logic to identify category hints in keywords
        # e.g., if "project" in keywords, filter by Projects/* category
        
        self.logger.info(f"Stage 1: Metadata filters created")
        return filters
    
    async def _stage2_hybrid_search(
        self,
        query: str,
        filters: Dict[str, Any],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: Hybrid search combining vector and full-text search
        
        Returns:
            List of candidate documents with scores
        """
        candidates = []
        
        # Vector search via Qdrant
        try:
            query_embedding = await self.llm.embed_text(query)
            vector_results = await self.vector_store.search_similar(
                query_embedding=query_embedding,
                limit=30,
                filters=filters,
                score_threshold=0.3
            )
            
            # Add source tag
            for result in vector_results:
                result['search_source'] = 'vector'
                result['search_score'] = result['score']
            
            candidates.extend(vector_results)
            self.logger.info(f"Vector search: {len(vector_results)} results")
            
        except Exception as e:
            self.logger.warning(f"Vector search failed: {e}")
        
        # Full-text search via CouchDB
        try:
            text_results = await self.couchdb.search_documents(query, limit=30)
            
            # Convert to consistent format and avoid duplicates
            existing_ids = {c['note_id'] for c in candidates}
            
            for doc in text_results:
                note_id = doc.get('_id') or doc.get('path', '')
                if note_id not in existing_ids:
                    candidates.append({
                        'note_id': note_id,
                        'search_source': 'fulltext',
                        'search_score': 0.7,  # Default score for text search
                        'summary': doc.get('data', '')[:200],
                        'category': doc.get('path', '').rsplit('/', 1)[0] if '/' in doc.get('path', '') else 'Inbox'
                    })
            
            self.logger.info(f"Full-text search: {len(text_results)} results")
            
        except Exception as e:
            self.logger.warning(f"Full-text search failed: {e}")
        
        # Limit to top 50
        candidates = candidates[:limit]
        self.logger.info(f"Stage 2: {len(candidates)} candidates")
        
        return candidates
    
    async def _stage3_rerank_and_analyze(
        self,
        question: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10
    ) -> AgentResponse:
        """
        Stage 3: Rerank with Cohere and generate answer with LLM
        
        Returns:
            AgentResponse with answer
        """
        # Prepare documents for reranking
        docs_for_rerank = []
        for cand in candidates:
            text = cand.get('summary', '')
            if not text:
                # If no summary, try to get from CouchDB
                try:
                    doc = await self.couchdb.get_document(cand['note_id'])
                    text = doc.get('data', '')[:500]
                except:
                    text = cand['note_id']
            docs_for_rerank.append(text)
        
        # Rerank with Cohere if available
        reranked_indices = list(range(len(candidates)))
        
        if self.cohere_client and docs_for_rerank:
            try:
                self.logger.info("Reranking with Cohere...")
                rerank_response = self.cohere_client.rerank(
                    query=question,
                    documents=docs_for_rerank,
                    top_n=min(top_k, len(docs_for_rerank)),
                    model="rerank-english-v3.0"
                )
                
                reranked_indices = [result.index for result in rerank_response.results]
                self.logger.info(f"Reranked to top {len(reranked_indices)}")
                
            except Exception as e:
                self.logger.warning(f"Cohere reranking failed: {e}")
                # Fall back to original order
                reranked_indices = list(range(min(top_k, len(candidates))))
        else:
            reranked_indices = list(range(min(top_k, len(candidates))))
        
        # Get top documents
        top_candidates = [candidates[i] for i in reranked_indices[:top_k]]
        
        # Load full content for top candidates
        context_docs = []
        for cand in top_candidates:
            try:
                doc = await self.couchdb.get_document(cand['note_id'])
                context_docs.append({
                    'path': cand['note_id'],
                    'content': doc.get('data', '')[:2000],  # Limit to 2K chars per doc
                    'category': cand.get('category', '')
                })
            except Exception as e:
                self.logger.warning(f"Failed to load doc {cand['note_id']}: {e}")
        
        if not context_docs:
            return AgentResponse(
                text="🤷 Нашел заметки, но не смог их загрузить.",
                success=True,
                metadata={'found_count': len(candidates)}
            )
        
        # Generate answer with LLM
        answer_text = await self._generate_answer(question, context_docs)
        
        # Format response with sources
        sources_text = "\n\n📚 **Источники:**\n"
        for i, doc in enumerate(context_docs[:5], 1):
            sources_text += f"{i}. `{doc['path']}`\n"
        
        final_text = answer_text + sources_text
        
        return AgentResponse(
            text=final_text,
            success=True,
            metadata={
                'found_count': len(candidates),
                'reranked_count': len(top_candidates),
                'sources': [doc['path'] for doc in context_docs]
            }
        )
    
    async def _generate_answer(
        self,
        question: str,
        context_docs: List[Dict[str, Any]]
    ) -> str:
        """Generate answer using LLM with context"""
        
        # Build context from documents
        context_text = ""
        for i, doc in enumerate(context_docs, 1):
            context_text += f"\n--- Document {i}: {doc['path']} ---\n"
            context_text += doc['content']
            context_text += "\n"
        
        system_prompt = """Ты помощник, который отвечает на вопросы на основе базы знаний пользователя.

Правила:
- Отвечай на русском языке (если вопрос на русском)
- Используй только информацию из предоставленных документов
- Если информации недостаточно, так и скажи
- Будь кратким и по делу
- Ссылайся на конкретные документы при необходимости"""

        user_prompt = f"""Вопрос: {question}

Контекст из базы знаний:
{context_text[:6000]}

Ответь на вопрос, используя информацию из контекста."""

        try:
            answer = await self.llm.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            
            return answer.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to generate answer: {e}")
            return "❌ Не удалось сгенерировать ответ."
