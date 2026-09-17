from _contextvars import ContextVar
from typing import Optional
from langchain_core.caches import BaseCache

# This variable is private to each async task (request)
tenant_cache_var: ContextVar[Optional[BaseCache]] = ContextVar(
    "tenant_cache", default=None
)

tenant_id_context: ContextVar[str] = ContextVar("tenant_id", default="default")

session_id_context: ContextVar[Optional[str]] = ContextVar("session_id", default=None)

request_id_context: ContextVar[str] = ContextVar("request_id", default="default")
