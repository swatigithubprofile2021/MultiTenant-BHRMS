from collections import OrderedDict
from app.services.agent.agent_service import AgentService
from app.services.agent.chat_rag_agent_service import ChatRAGAgentService
from app.services.agent.generative_agent_service import GenerativeAgentService
from app.ai.embeddings.embedding_manager import EmbeddingManager
from app.ai.llm.llm_manager import LLMManager
from app.ai.reranker import Reranker
from llama_index.vector_stores.postgres import PGVectorStore
from typing import List


class TenantManager:
    def __init__(self, capacity: int = 10):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get_service(
        self,
        tenant_id: str,
        llm: LLMManager,
        agent_prompt: str,
        is_chat_service: bool,
        allowed_sources: List[str] = [],
        embed: EmbeddingManager | None = None,
        vector_store: PGVectorStore | None = None,
        reranker: Reranker | None = None,
        tone: str = ""
    ) -> AgentService:
        cached_tenant_id = (
            f"{tenant_id}_chat" if is_chat_service else f"{tenant_id}_gen"
        )

        if cached_tenant_id in self.cache:
            # Move to end to mark as "Recently Used"
            self.cache.move_to_end(cached_tenant_id)
            return self.cache[cached_tenant_id]

        # If not in cache, initialize new engine
        engine = self._initialize_agent_service(
            tenant_id,
            is_chat_service,
            llm,
            embed,
            vector_store,
            reranker,
            agent_prompt,
            allowed_sources,
            tone
        )

        if len(self.cache) >= self.capacity:
            # Remove the first item (Least Recently Used)
            self.cache.popitem(last=False)

        self.cache[cached_tenant_id] = engine
        return engine

    def _initialize_agent_service(
        self,
        tenant_id: str,
        is_chat_service: bool,
        llm: LLMManager,
        embed: EmbeddingManager,
        vector_store: PGVectorStore,
        reranker: Reranker,
        agent_prompt: str,
        allowed_sources: List[str] = [],
        tone: str = ""
    ) -> AgentService:
        # Your logic to load and tenant data
        if is_chat_service:
            return ChatRAGAgentService(
                llm,
                embed,
                vector_store,
                reranker,
                tenant_id=tenant_id,
                agent_prompt=agent_prompt,
                allowed_sources=allowed_sources,
                tone=tone
            )
        else:
            return GenerativeAgentService(
                llm, tenant_id=tenant_id, agent_prompt=agent_prompt,tone=tone
            )


# Initialize as a global singleton for the app
tenant_manager = TenantManager(capacity=50)
