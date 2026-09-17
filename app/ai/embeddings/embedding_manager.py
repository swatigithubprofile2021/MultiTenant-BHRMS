from typing import List
import hashlib
from langchain_core.embeddings import Embeddings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.core.config import settings


class EmbeddingManager:
    """
    Manages open-source embeddings with caching and batching
    """

    def __init__(self, embed_model: HuggingFaceEmbedding):
        self.model = embed_model
        self.cache = {}  # In-memory cache; replace with Redis in production

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings with caching"""
        # Check cache
        uncached_texts = []
        results = {}

        for text in texts:
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self.cache:
                results[text] = self.cache[cache_key]
            else:
                uncached_texts.append(text)

        # Batch process uncached
        if uncached_texts:
            embeddings = self.model.get_text_embedding_batch(uncached_texts)
            for text, emb in zip(uncached_texts, embeddings):
                cache_key = hashlib.md5(text.encode()).hexdigest()
                self.cache[cache_key] = emb
                results[text] = emb

        return [results[text] for text in texts]


class LangChainEmbeddingsAdapter(Embeddings):
    """
    A bridge that makes LlamaIndex models work inside LangChain caches.
    """

    def __init__(self, llamaindex_model):
        self._model = llamaindex_model

    def embed_query(self, text: str) -> List[float]:
        # Maps LangChain's 'embed_query' to LlamaIndex's 'get_query_embedding'
        return self._model.get_query_embedding(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # Maps LangChain's 'embed_documents' to LlamaIndex's 'get_text_embeddings'
        return self._model.get_text_embeddings(texts)
