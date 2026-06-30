import hashlib
import logging
from typing import Optional

from langchain_core.caches import BaseCache, RETURN_VAL_TYPE
from langchain_core.globals import set_llm_cache
from langchain_core.load import dumps, loads
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None


class AsyncRedisCache(BaseCache):
    """Async Redis cache with MD5-based cache key generation."""

    def __init__(self, redis_client: Redis, ttl_seconds: Optional[int] = None) -> None:
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds

    def _key(self, prompt: str, llm_string: str) -> str:
        """Create a deterministic Redis key from the prompt and LLM config."""
        key_payload = f"{prompt}:{llm_string}"
        key_hash = hashlib.md5(key_payload.encode("utf-8")).hexdigest()
        return f"langchain:llm_cache:{key_hash}"

    def lookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        """Synchronous lookup is intentionally unsupported for async Redis."""
        raise NotImplementedError("AsyncRedisCache only supports async lookup")

    def update(
        self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE
    ) -> None:
        """Synchronous update is intentionally unsupported for async Redis."""
        raise NotImplementedError("AsyncRedisCache only supports async update")

    def clear(self, **kwargs: object) -> None:
        """Synchronous clear is intentionally unsupported for async Redis."""
        raise NotImplementedError("AsyncRedisCache only supports async clear")

    async def alookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        """Look up cached generations from Redis."""
        cached_value = await self.redis_client.get(self._key(prompt, llm_string))
        if cached_value is None:
            return None

        return loads(cached_value)

    async def aupdate(
        self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE
    ) -> None:
        """Write generations to Redis."""
        key = self._key(prompt, llm_string)
        value = dumps(return_val)

        if self.ttl_seconds is None:
            await self.redis_client.set(key, value)
            return

        await self.redis_client.set(key, value, ex=self.ttl_seconds)

    async def aclear(self, **kwargs: object) -> None:
        """Clear LangChain LLM cache keys from Redis."""
        cursor = 0

        while True:
            cursor, keys = await self.redis_client.scan(
                cursor=cursor,
                match="langchain:llm_cache:*",
                count=100,
            )
            if keys:
                await self.redis_client.delete(*keys)

            if cursor == 0:
                break


async def init_redis_cache(redis_url: Optional[str]) -> bool:
    """Initialize LangChain's global LLM cache using Redis.

    The app continues to run when Redis is not configured or unavailable.
    Returns True when Redis cache is enabled, otherwise False.
    """
    global _redis_client

    if not redis_url:
        logger.warning("REDIS_URL is not configured; running without Redis LLM cache")
        return False

    try:
        _redis_client = Redis.from_url(redis_url, decode_responses=True)
        await _redis_client.ping()

        set_llm_cache(AsyncRedisCache(_redis_client))
        logger.info("Redis LLM cache enabled")
        return True
    except Exception as exc:
        if _redis_client is not None:
            await _redis_client.aclose()

        _redis_client = None
        logger.warning("Redis LLM cache disabled: %s", exc)
        return False


async def cleanup_redis_cache() -> None:
    """Close Redis connection if it was initialized."""
    global _redis_client

    if _redis_client is None:
        return

    await _redis_client.aclose()
    _redis_client = None