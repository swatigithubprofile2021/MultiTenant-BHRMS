import time
from app.schemas.request_response import QueryRequest

from langchain_core.prompts import ChatPromptTemplate

from app.services.agent.agent_service import AgentService
from app.core.evaluator import get_product_grade
from app.core.logger import logger
from app.ai.llm.llm_manager import LLMManager
from app.ai.llm.prompts.system_prompt import build_system_prompt


class GenerativeAgentService(AgentService):
    """
    LangChain for orchestration Generative agent service
    """

    def __init__(
        self,
        llm: LLMManager,
        tenant_id: str = "default",
        agent_prompt: str = "",
        tenant_prompt: str = "",
        tone: str = "",
    ):
        super().__init__(llm, tenant_id, agent_prompt, tenant_prompt, tone)

        self._init()

    def _init(
        self,
        # tone: str = "Friendly, helpful, professional, concise."
    ):
        """Setup Modern LCEL Generative Chain for content generation"""

        # Prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    build_system_prompt(
                        self.tenant_prompt,
                        self.agent_prompt,
                        self.tone,
                        is_context=False,
                    ),
                ),
                ("human", "{input}"),
            ]
        )

        # Final gen Chain
        self.gen_chain = prompt | self.llm

    async def stream_response(
        self,
        request: QueryRequest,
    ):
        """
        Asynchronous Generator for Streaming gnerate content based on query using astream_events
        """
        start_time = time.time()

        full_answer = ""

        try:
            # 4. Use astream_events for true token-by-token output
            usage_metadata = {}
            async for event in self.gen_chain.astream_events(
                {"input": request.question, "chat_history": []},
                version="v2",
                config={"cache": False},
            ):
                kind = event["event"]
                # print(event)

                if kind == "on_chat_model_stream":
                    # Get the tags for this specific event
                    tags = event.get("tags", [])

                    # PROCESS if it's the final answer
                    token = event["data"]["chunk"].content
                    if token:
                        full_answer += token
                        yield {"type": "token", "content": token}

                elif kind == "on_chain_end":
                    usage = event["data"]["output"].usage_metadata
                    usage_metadata.update(usage)

            # 5. Calculate Metrics
            grade_data = get_product_grade(request.question, full_answer, [])
            processing_time = (time.time() - start_time) * 1000

            yield {
                "type": "final_metrics",
                "confidence_score": grade_data["score"],
                "status": grade_data["status"],
                "metrics": grade_data["metrics"],
                "processing_time_ms": processing_time,
                "usage_metadata": usage_metadata,
            }

        except Exception as e:
            logger.exception(f"Error in streaming RAG: {e}")
            yield {
                "type": "error",
                "content": "I encountered an error processing your request.",
            }
