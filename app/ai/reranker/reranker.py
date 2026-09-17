from langchain_core.documents import Document
from llama_index.core.schema import NodeWithScore
from sentence_transformers import CrossEncoder


class Reranker:

    def __init__(self, model: CrossEncoder):
        self.model = model

    async def rerank(self, query: str, items: Document | NodeWithScore, top_k: int = 3):
        # items can be LlamaIndex Nodes or LangChain Documents
        # Extract text content for the reranker model
        texts = [
            item.node.get_content() if hasattr(item, "node") else item.page_content
            for item in items
        ]

        pairs = [(query, txt) for txt in texts]
        scores = self.model.predict(pairs)

        # Zip the original objects with their new scores
        scored_items = list(zip(items, scores))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # Return top_k original objects (which still contain metadata)
        return scored_items[:top_k]
