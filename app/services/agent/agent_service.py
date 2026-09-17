from abc import ABC, abstractmethod

from langchain_redis import RedisChatMessageHistory
from llama_index.core import Settings as llamaSettings
from app.ai.llm.llm_manager import LLMManager
from app.schemas.request_response import QueryRequest

llamaSettings.llm = None


class AgentService(ABC):
    def __init__(
        self,
        llm: LLMManager,
        tenant_id: str = "default",
        agent_prompt: str = "",
        tenant_prompt: str = "",
        tone: str = "",
    ):
        self.tenant_id = tenant_id
        self.llm = llm
        self.agent_prompt = agent_prompt
        self.tenant_prompt = tenant_prompt
        self.tone = tone

    def with_redis_chat_history(self, chat_history: RedisChatMessageHistory):
        pass

    @abstractmethod
    async def stream_response(self, request: QueryRequest):
        """
        Asynchronous Generator for Streaming RAG responses using astream_events
        """
        raise NotImplementedError()
