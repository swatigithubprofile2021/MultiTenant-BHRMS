from fastapi import FastAPI
from contextlib import asynccontextmanager
import redis
import redis.asyncio as async_redis

from langchain_core.globals import set_llm_cache

from app.core.thead_cache_proxy import (
    ThreadSafeCacheProxy,
)
from app.core.config import settings
from app.core.thead_cache_proxy import ThreadSafeCacheProxy
from app.core.shared_resources import SharedResources, get_shared_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    async_pool = async_redis.ConnectionPool.from_url(
        settings.REDIS_URL, decode_responses=True
    )
    r_client = async_redis.Redis(connection_pool=async_pool)
    app.state.redis_client = r_client

    sync_redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.sync_redis = sync_redis

    resources = SharedResources.get_instance()
    app.state.models = get_shared_models()

    # Agent system: Global thread-safe cache proxy initialized."
    set_llm_cache(ThreadSafeCacheProxy(redis_client=sync_redis))

    yield
    print("🛑 Shutting down Agent system...")
    resources.shutdown()
    set_llm_cache(None)
    await app.state.redis_client.close()
    await async_pool.disconnect()
    sync_redis.close()

    app.state.models.clear()
