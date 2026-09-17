import time
from typing import Dict, List
from langchain_redis import RedisChatMessageHistory
from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterCondition,
    FilterOperator,
    VectorStoreQuery,
)
from llama_index.core import Settings as llamaSettings, VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor

from app.schemas.request_response import QueryRequest, QueryResponse
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory

from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.history_aware_retriever import (
    create_history_aware_retriever,
)
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.output_parsers import JsonOutputParser

from app.services.agent.agent_service import AgentService
from app.core.config import settings
from app.core.evaluator import get_product_grade
from app.core.logger import logger
from app.ai.embeddings.embedding_manager import EmbeddingManager
from app.ai.llm.llm_manager import LLMManager
from app.ai.reranker import Reranker
from app.ai.llm.prompts.system_prompt import build_system_prompt
from app.ai.llm.prompts.query_re_write_prompt import contextualize_system_prompt_v2

llamaSettings.llm = None


class ChatRAGAgentService(AgentService):
    """
    Hybrid retrieval using LlamaIndex for semantic search and LangChain for orchestration
    """

    def __init__(
        self,
        llm: LLMManager,
        embed_service: EmbeddingManager,
        vector_store: PGVectorStore,
        reranker: Reranker,
        allowed_sources: List[str],
        tenant_id: str = "default",
        agent_prompt: str = "",
        tenant_prompt: str = "",
        tone: str = "",
    ):
        super().__init__(llm, tenant_id, agent_prompt, tenant_prompt, tone)

        self.embed_service = embed_service
        self.vector_store = vector_store
        self.reranker = reranker
        self.allowed_sources = allowed_sources
        self.chat_history = None
        self.allowed_sources.append("Unknown")

        # Initialize components
        self._init_query_engine()

        # Conversation memory per session
        self.memories: Dict[str, ChatMessageHistory] = {}

    def _init_query_engine(self):
        """Initialize LlamaIndex query engine with advanced retrieval"""
        # if self.index is None:
        #     return
        index = VectorStoreIndex.from_vector_store(
            self.vector_store, self.embed_service.model
        )

        # Configure retriever
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=settings.TOP_K_RETRIEVAL,
            vector_store_query_mode="hybrid",  # Can use "hybrid" with sparse vectors
            # alpha=0.5,  # Balance between semantic and keyword (if hybrid)
        )

        # Post-processors for relevance
        postprocessors = [
            SimilarityPostprocessor(similarity_cutoff=settings.SIMILARITY_CUTOFF)
        ]

        # Create query engine
        self.query_engine = RetrieverQueryEngine(
            retriever=retriever, node_postprocessors=postprocessors
        )

        # Wrap with LangChain for orchestration
        self._setup_langchain_orchestration()

    async def _query_router(self, query: str) -> str:
        """
        _query_router: helper for determine the context/intent of search or route.
        based on that apply category filter within tenant docs.
        """
        print(f"🔍 CHECK REWRITTEN QUERY for route: '{query}'")

        # categories = ["Travel_Policy", "Leave_Policy", "Medical_Policy", "Unknown"]

        filters = [
            MetadataFilter(
                key="tenant_id", operator=FilterOperator.EQ, value=self.tenant_id
            ),
        ]

        if len(self.allowed_sources) > 1:
            router_prompt = PromptTemplate.from_template(
                "Classify the following query into one or more of the following categories: "
                f"{','.join(self.allowed_sources)}. "
                "Query: {query}. Output only a JSON with the key 'query_type', "
                "where the value is a list of applicable categories"
            )

            routing_chain = router_prompt | self.llm | JsonOutputParser()

            result = await routing_chain.ainvoke({"query": query})

            filter_cateories = result.get("query_type")
            if isinstance(filter_cateories, list):
                if len(filter_cateories) and "Unknown" not in filter_cateories:
                    filters.append(
                        MetadataFilter(
                            key="category",
                            operator=FilterOperator.IN,
                            value=filter_cateories,
                        )
                    )

        self.query_engine.retriever._filters = MetadataFilters(
            filters=filters, condition=FilterCondition.AND
        )

    def _check_for_policy_conflict(self, docs):
        """
        'docs' is a List[Document] coming directly from the retriever
        """
        print("!!!!!!!!!!!!!!", docs, "!!!!!!!!!!!!!!!1")
        # 1. Safety check if docs is empty
        if not isinstance(docs, list):
            return docs

        # 2. Extract unique categories from the metadata
        categories = list(
            set(
                doc.metadata.get("category")
                for doc in docs
                if doc.metadata.get("category")
            )
        )

        # 3. Check for conflict (more than 1 category found)
        if len(categories) > 1:
            pass
            # We raise a custom exception to "break" the chain and catch it in the stream
            # This is the cleanest way to stop the LLM from starting
            # raise ValueError(f"POLICY_CONFLICT:{','.join(categories)}")

        # 4. If no conflict, return the docs exactly as they arrived
        return docs

    def _setup_langchain_orchestration(
        self
    ):
        """Setup Modern LCEL RAG Chain for complex HR reasoning with given tone"""

        contextualize_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_system_prompt_v2),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        async def custom_retrieval(query: str):
            print(f"DEBUG: Internal Retriever Search Query: '{query}'")
            # 1. Initial retrieval (LlamaIndex nodes)
            nodes = self.query_engine.retrieve(query)

            # 2. Rerank the nodes directly
            reranked_results = await self.reranker.rerank(query, nodes, top_k=5)

            # 3. Create LangChain Documents with merged metadata and rerank scores
            docs = [
                Document(
                    page_content=node_obj.node.get_content(),
                    metadata={
                        **node_obj.node.metadata,
                        "rerank_score": float(score),
                        "original_score": node_obj.score,
                    },
                )
                for node_obj, score in reranked_results
            ]

            return docs

        async def debug_input(query):
            print(f"🛠️ REWRITTEN QUERY SENT TO RETRIEVER: '{query}'")
            await self._query_router(query)
            return await custom_retrieval(query)

        # 2. History-Aware Retriever
        self.history_aware_retriever = create_history_aware_retriever(
            self.llm, RunnableLambda(debug_input), contextualize_prompt
        ).with_config(tags=["rewriter"])

        # 3. Answer Generation
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    build_system_prompt(
                        self.tenant_prompt, self.agent_prompt, self.tone
                    ),
                ),
                ("human", "{input}"),
                # This nudge prevents parrotting
                # (
                #     "ai",
                #     "I will look into the HR records for you. Based on the context provided:",
                # ),
            ]
        )

        # 4. Final Chain Assembly
        # create_stuff_documents_chain handles the 'context' variable automatically
        question_answer_chain = create_stuff_documents_chain(
            self.llm, qa_prompt
        ).with_config(tags=["qna_chain"])

        # 5. Final Retrieval Chain
        self.rag_chain = create_retrieval_chain(
            self.history_aware_retriever,
            question_answer_chain,
        )

    async def detect_conflict(self, question: str, existing_category: str = None):
        # If the user already made a choice, there is no conflict to detect
        if existing_category:
            return "clear", [existing_category]

        # 1. Get Embeddings for the question
        embeddings_list = await self.embed_service.get_embeddings([question])
        query_embedding = embeddings_list[0]

        # 2. Query the LlamaIndex Chroma Store directly
        # Retrieve more documents than usual (e.g., k=5) without filters
        # Note: Use similarity_search_with_score to get the raw distance/score
        query_obj = VectorStoreQuery(
            query_embedding=query_embedding, similarity_top_k=5
        )

        # query() is the standard method for LlamaIndex VectorStores
        results = self.vector_store.query(query_obj)

        if not results.nodes:
            return None, []

        # 3. Extract Categories and Scores
        # LlamaIndex stores scores in results.similarities
        category_scores = {}
        for node, similarity in zip(results.nodes, results.similarities):
            cat = node.metadata.get("category", "general")
            # Keep the highest similarity score for each category
            if cat not in category_scores or similarity > category_scores[cat]:
                category_scores[cat] = similarity

        # 4. Conflict Logic (Same as before)
        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_cats) > 1:
            (cat1, score1), (cat2, score2) = sorted_cats[:2]
            # Similarity in LlamaIndex/Chroma is usually 0 to 1 (Cosine)
            if abs(score1 - score2) < 0.05:
                return "conflict", [cat1, cat2]

        return "clear", [sorted_cats[0][0]] if sorted_cats else [None]

    def with_redis_chat_history(self, chat_history: RedisChatMessageHistory):
        self.chat_history = chat_history

    async def stream_response(self, request: QueryRequest):
        """
        Asynchronous Generator for Streaming RAG responses using astream_events
        """
        if self.chat_history is None:
            yield {"type": "error", "msg": "chat history not initialize."}
            return

        start_time = time.time()
        session_id = request.session_id

        full_answer = ""
        source_docs = []
        sources_sent = False

        # 1. Memory Setup
        memory = (
            self.chat_history
            if self.chat_history
            else self.memories.get(session_id, ChatMessageHistory())
        )

        # Check if this is a "Refined" query
        use_cache = True
        if request.filters and request.filters.category:
            use_cache = False

        try:
            usage_metadata = {}
            # Use astream_events for true token-by-token output
            async for event in self.rag_chain.astream_events(
                {"input": request.question, "chat_history": memory.messages},
                version="v2",
                config={"cache": use_cache},
            ):
                kind = event["event"]

                # 1. Capture Sources
                if kind == "on_chain_end" and not sources_sent:
                    output = event["data"].get("output")
                    if (
                        isinstance(output, list)
                        and len(output) > 0
                        and hasattr(output[0], "page_content")
                    ):
                        source_docs = output
                        yield {
                            "type": "sources",
                            "content": [
                                {
                                    "content": doc.page_content[:300],
                                    "metadata": doc.metadata,
                                }
                                for doc in source_docs
                            ],
                        }
                        sources_sent = True

                elif kind == "on_chat_model_stream":
                    # Get the tags for this specific event
                    tags = event.get("tags", [])

                    # SKIP if the event comes from the rewriter
                    if "rewriter" in tags:
                        continue

                    # PROCESS if it's the final answer
                    token = event["data"]["chunk"].content
                    if token:
                        full_answer += token
                        yield {"type": "token", "content": token}

                elif kind == "on_parser_end":
                    # Get the tags for this specific event
                    tags = event.get("tags", [])

                    # SKIP if the event comes not from qna_chain
                    if "qna_chain" not in tags:
                        continue

                    usage_metadata.update(event["data"]["input"].usage_metadata)

            # Calculate Metrics
            grade_data = get_product_grade(request.question, full_answer, source_docs)
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

    def clear_memory(self, session_id: str):
        """Clear conversation memory for a session"""
        if session_id in self.memories:
            del self.memories[session_id]
