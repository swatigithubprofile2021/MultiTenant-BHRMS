from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import torch
from sentence_transformers import CrossEncoder
import os

base_path = "./ai_models/embeddings/"
rerank_base_path = "./ai_models/rerank/"
os.makedirs(base_path, exist_ok=True)
os.makedirs(rerank_base_path, exist_ok=True)

## embedding model cache
HuggingFaceEmbedding(
    # model_name="sentence-transformers/all-MiniLM-L6-v2",
    # model_name="BAAI/bge-small-en-v1.5",
    model_name="BAAI/bge-base-en-v1.5",
    cache_folder=base_path,
    max_length=512,
    embed_batch_size=32,
    device="cuda" if torch.cuda.is_available() else "cpu",
)

# embeding_path = f"{base_path}models--BAAI--bge-small-en-v1.5/snapshots"
embeding_path = f"{base_path}models--BAAI--bge-base-en-v1.5/snapshots"
model_id = list(os.listdir(embeding_path))[-1]
print("embedding model path: \n", f"{embeding_path}/{model_id}")


## rerank model cache
reranker = CrossEncoder(
    model_name_or_path="BAAI/bge-reranker-base",
    cache_folder=rerank_base_path,
    device="cuda" if torch.cuda.is_available() else "cpu",
)


rerank_embeding_path = f"{rerank_base_path}models--BAAI--bge-reranker-base/snapshots"
rerank_model_id = list(os.listdir(rerank_embeding_path))[-1]
print("rerank embedding model path: \n", f"{rerank_embeding_path}/{rerank_model_id}")
