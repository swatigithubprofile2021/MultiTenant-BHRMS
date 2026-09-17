from typing import Dict
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import Engine
from app.core.logger import logger
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator,
    FilterCondition,
)


class PgvectorManager:
    """
    Manages pgvector-based document storage with tenant isolation
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PgvectorManager, cls).__new__(cls)
        return cls._instance

    def init(
        self,
        async_engine: AsyncEngine,
        sync_engine: Engine,
        embed_dim: int = 384,
        hnsw_kwargs: Dict[str, int] | None = None,
    ):

        if hnsw_kwargs is None:
            hnsw_kwargs = {
                "hnsw_m": 16,
                "hnsw_ef_construction": 200,
                "hnsw_ef_search": 150,
                "hnsw_dist_method": "vector_cosine_ops",
            }

        self.vector_store = PGVectorStore(
            async_engine=async_engine,
            engine=sync_engine,
            table_name="tenants_docs",
            schema_name="public",
            hybrid_search=True,
            embed_dim=embed_dim,  # match your embeddings
            use_jsonb=True,
            perform_setup=True,  # auto create table if not exists
            hnsw_kwargs=hnsw_kwargs,  # optional IVFFlat/HNSW tuning
            indexed_metadata_keys={
                ("tenant_id", "text"),
                ("file_hash", "text"),
            },  # optional
        )

    async def delete_collection(self, tenant_id: int, file_hash: str):
        """Delete all documents for a tenant"""
        safe_tenant = f"tenant_{tenant_id}"

        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="tenant_id",
                    operator=FilterOperator.EQ,
                    value=safe_tenant,
                ),
                MetadataFilter(
                    key="file_hash",
                    operator=FilterOperator.EQ,
                    value=file_hash,
                ),
            ],
            condition=FilterCondition.AND,
        )

        try:
            await self.vector_store.adelete_nodes(filters=filters)
            logger.info(f"Deleted all documents for tenant {safe_tenant}")
        except Exception as e:
            logger.exception(
                f"Error deleting tenant collection: {e}", stack_info=True, exc_info=True
            )
