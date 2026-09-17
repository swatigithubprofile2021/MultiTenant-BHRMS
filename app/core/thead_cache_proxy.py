import re
from langchain_core.caches import BaseCache

from app.core.context import tenant_cache_var, request_id_context


class ThreadSafeCacheProxy(BaseCache):
    """A proxy that directs LangChain to the cache stored in the current ContextVar."""

    def __init__(self, redis_client):
        self.redis_client = redis_client

    def _get_clean_query(self, prompt: str) -> str:
        # Find the VERY LAST "Human:" tag and take only that text
        # This ignores the System instructions, PDF Context, and History
        parts = re.split(r"Human:\s*", prompt, flags=re.IGNORECASE)
        if len(parts) > 1:
            return parts[-1].strip()
        return prompt.strip()

    def lookup(self, prompt, llm_string):
        query = self._get_clean_query(prompt)
        print(
            f"🔍 CACHE LOOKUP FOR: {query} {llm_string}"
        )  # Verify this in your console

        current_cache = tenant_cache_var.get()
        if current_cache:
            result = current_cache.lookup(query, llm_string)
            if result:
                # Mark as a hit for this request
                # Add this print to see the actual content being returned
                print(
                    f"✅ CACHE HIT! Query: [{query}] -> Result: [{result[0].text[:50]}...]"
                )
                req_id = request_id_context.get()

                self.redis_client.setex(f"hit:{req_id}", 60, "true")
                return result
            print(f"❌ CACHE MISS for: [{query}]")
        return None

    def update(self, prompt, llm_string, return_val):
        # If we are updating, it was a miss
        query = self._get_clean_query(prompt)
        print(
            f"🔍 Update CACHE LOOKUP FOR: {query} {llm_string}"
        )  # Verify this in your console

        # This is what the LLM just generated
        llm_output = return_val[0].text

        print(f"🤖 LLM GENERATED: [{llm_output}] for Query: [{query}]")

        if llm_output.strip().lower() == query.strip().lower():
            print("⚠️ WARNING: LLM is parroting the question! Not updating cache.")
            return  # Don't save bad parrot answers to Redis!

        cache = tenant_cache_var.get()
        if cache:
            cache.update(query, llm_string, return_val)

    def clear(self, **kwargs):
        cache = tenant_cache_var.get()
        if cache:
            cache.clear(**kwargs)
