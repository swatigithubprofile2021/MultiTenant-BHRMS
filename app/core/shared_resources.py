import torch

from sqlalchemy.ext.asyncio import AsyncEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from sentence_transformers import CrossEncoder
from app.services.document_service import DocumentProcessor

# from app.ai.retrieval.chroma_manager import ChromaManager
from app.db.session import async_engine, engine as sync_engine
from app.ai.retrieval.pgvector_manager import PgvectorManager
from app.ai.embeddings.embedding_manager import (
    EmbeddingManager,
    LangChainEmbeddingsAdapter,
)
from app.ai.llm.llm_manager import LLMManager
from app.ai.reranker import Reranker

from app.core.config import settings


class SharedResources:
    _instance = None

    def __init__(self):
        # --- 1. Create the CORE embedding object ONCE ---
        self.shared_embed_model = HuggingFaceEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"local_files_only": True},
            max_length=512,
            embed_batch_size=32,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
        # 1. Load Embedding Model (Shared by Processor and Chroma)
        print("📥 Loading Embedding Model...")
        self.embed_service = EmbeddingManager(embed_model=self.shared_embed_model)

        # Re-rank model
        print("📥 Loading Reranker Model...")
        self.reranker = Reranker(
            model=CrossEncoder(
                model_name_or_path=settings.RERANK_MODEL,
                device="cuda" if torch.cuda.is_available() else "cpu",
            )
        )

        # 2. Load LLM (Qwen2.5:0.5b / Qwen3:0.6b)
        print("📥 Loading LLM (Ollama)...")
        self.llm_service = LLMManager()

        # 4. Load PgVector Manager
        self.pgvector_manager = PgvectorManager()
        self.pgvector_manager.init(
            async_engine, sync_engine, embed_dim=settings.EMBEDDDING_DIMEN
        )  # initalize the vectordb

        # # 3. Load Document Processor (Uses the same embed model)
        self.doc_processor = DocumentProcessor(
            embed_model=self.shared_embed_model,
            vector_store=self.pgvector_manager.vector_store,
        )

        self.langchain_embed_adapter = LangChainEmbeddingsAdapter(
            self.shared_embed_model
        )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def shutdown(self):
        print("🛑 Shutting down Shared Resources...")
        try:
            # 1. Close ChromaDB connections (Crucial to prevent data corruption)
            # if hasattr(self, "chroma_manager"):
            # # If your ChromaManager has a persistent client, close it
            # self.chroma_manager._client.clear_system_cache()
            # self.chroma_manager.close()

            # 2. Clear GPU/RAM references
            self.shared_embed_model = None
            self.llm_service = None
            self.embed_service = None
            self.doc_processor = None
            self.langchain_embed_adapter = None
            self.reranker = None
            self.pgvector_manager = None

            # 3. Force garbage collection
            import gc

            gc.collect()

            # 4. If using CUDA (unlikely on i5-U but good practice)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            print("✅ Cleanup complete.")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")


# Helper function to use in both FastAPI and Celery
def get_shared_models():
    res = SharedResources.get_instance()
    return {
        "llm": res.llm_service,
        "embed": res.embed_service,
        "reranker": res.reranker,
        "vectordb": res.pgvector_manager,
        "doc_processor": res.doc_processor,
    }
