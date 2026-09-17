from typing import Any, AsyncGenerator, Dict, List
from redis import Redis
from langchain_core.runnables import Runnable
from langchain_core.messages import AIMessage
from langchain_core.language_models import LanguageModelInput
from fastapi import Depends, Request
from app.ai.retrieval.pgvector_manager import PgvectorManager
from app.db.models.user import User
from app.services.agent.agent_service import AgentService
from app.services.document_service import DocumentProcessor
from app.ai.embeddings.embedding_manager import EmbeddingManager
from app.ai.llm.llm_manager import LLMManager
from app.ai.reranker import Reranker
from app.core.shared_resources import SharedResources
from app.core.cache_manager import cache_manager
from app.services.tenant_service import tenant_manager
from app.api.deps.auth_dep import get_current_user

from app.core.context import (
    tenant_cache_var,
    session_id_context,
    tenant_id_context,
)


def get_llm(
    request: Request, temperature: float, model: str
) -> Runnable[LanguageModelInput, AIMessage]:
    llm_manager: LLMManager = request.app.state.models.get("llm")
    llm = llm_manager.get(model=model)
    if llm:
        llm = llm.bind(options={"temperature": temperature})
    return llm


def get_llm_manager(request: Request) -> LLMManager:
    return request.app.state.models.get("llm")


def get_doc_processor(request: Request) -> DocumentProcessor:
    return request.app.state.models.get("doc_processor")


def get_vectordb(request: Request) -> PgvectorManager:
    return request.app.state.models.get("vectordb")


def get_embed(request: Request) -> EmbeddingManager:
    return request.app.state.models.get("embed")


def get_rerank(request: Request) -> Reranker:
    return request.app.state.models.get("reranker")


async def get_agent_service(
    request: Request,
    is_chat_service: bool,
    user: User | Dict[str, Any] = Depends(get_current_user),
    llm: LLMManager = Depends(get_llm),
    embed: EmbeddingManager = Depends(get_embed),
    vectordb: PgvectorManager = Depends(get_vectordb),
    reranker: Reranker = Depends(get_rerank),
    agent_prompt: str = "",
    session_id: str | None = None,
    allowed_sources: List[str] = [],
    tone:str=""
) -> AsyncGenerator[AgentService]:
    # Extract IDs from JWT. tenant_id for track the company, session_id for track the user
    if not isinstance(user, dict):
        tenant_id = f"tenant_{user.tenant_id}"
        session_id = f"session_{user.id}" if session_id is None else session_id
    else:
        tenant_id = f"tenant_{user['tenant_id']}"
        session_id = (
            f"session_{user['session_id']}" if session_id is None else session_id
        )

    # 2. Set the Identifiers (For Logging/History/RAG isolation)
    t_id_token = tenant_id_context.set(tenant_id)
    s_id_token = session_id_context.set(session_id)

    shared = SharedResources.get_instance()
    print("allowed_sources in dep", allowed_sources)
    # 1. Use the Manager to get the service (LRU logic happens inside)
    service = tenant_manager.get_service(
        tenant_id,
        llm,
        agent_prompt,
        is_chat_service,
        allowed_sources,
        embed,
        vectordb.vector_store,
        reranker,
        tone
    )

    # 2. Setup the Thread-Safe Semantic Cache (Redis)
    tenant_cache = cache_manager.get_cache_for_tenant(
        tenant_id=tenant_id, embed_adapter=shared.langchain_embed_adapter
    )

    # 3. Set the ContextVar for the current async task
    token = tenant_cache_var.set(tenant_cache)
    try:
        yield service
    finally:
        # clear all contextvars
        tenant_cache_var.reset(token)
        tenant_id_context.reset(t_id_token)
        session_id_context.reset(s_id_token)
