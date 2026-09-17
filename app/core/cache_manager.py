from typing import Dict
from langchain_redis import RedisSemanticCache
from app.core.logger import logger
from app.core.config import settings


class CacheManager:
    _instance = None
    _caches: Dict[str, RedisSemanticCache] = {}

    def get_cache_for_tenant(self, tenant_id, embed_adapter):
        if tenant_id not in self._caches:
            # Only runs the FIRST time a company employee asks a question
            logger.info(f"🔌 Initializing persistent cache for {tenant_id}")
            self._caches[tenant_id] = RedisSemanticCache(
                redis_url=settings.REDIS_URL,
                embeddings=embed_adapter,
                prefix=f"ai_cache:{tenant_id}:",
                distance_threshold=settings.REDIS_SEMANTIC_DISTANCE_THRES,
                name=f"semantic_cache_{tenant_id}_v1",
                ttl=settings.REDIS_SEMANTIC_CACHE_TTL,
            )
        return self._caches[tenant_id]


cache_manager = CacheManager()
