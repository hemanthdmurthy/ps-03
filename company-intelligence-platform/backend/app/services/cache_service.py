import logging
import json
import asyncio
import time
from typing import Optional, Any
from functools import wraps
import redis.asyncio as aioredis
from fastapi import Request
from fastapi.encoders import jsonable_encoder

from app.core.config import settings
from app.core.redis_client import redis_client

logger = logging.getLogger("company_intel.services.cache")

class CacheService:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.is_fallback = False
        self.enabled = settings.CACHE_ENABLED

    async def initialize(self, raise_on_fail: bool = False):
        """
        Initializes the Redis connection pool using the central resilient client.
        If the connection fails, it falls back gracefully to in-memory FakeRedis.
        """
        if not self.enabled:
            logger.info("Redis Caching is explicitly disabled via configuration.")
            return

        # Initialize the global resilient client
        await redis_client.initialize(raise_on_fail=raise_on_fail)
        self.redis = redis_client.client
        self.is_fallback = redis_client.is_fallback

    async def close(self):
        """Closes the Redis connection pool gracefully on shutdown."""
        # The central client manages the active connection pooling teardown
        await redis_client.close()
        logger.info("Redis cache service closed.")

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieves and deserializes the JSON cached value.
        Degrades gracefully to return None if Redis fails.
        """
        if not self.enabled or not self.redis:
            return None

        from app.core.metrics import track_redis_op
        start_time = time.time()
        status = "miss"
        try:
            value = await self.redis.get(key)
            if value:
                status = "hit"
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET exception for key '{key}': {e}", exc_info=True)
            status = "failure"
            return None
        finally:
            duration = time.time() - start_time
            track_redis_op(operation="get", status=status, duration=duration)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Serializes and sets a value in cache with a TTL (Time-To-Live).
        Degrades gracefully and returns False if Redis fails.
        """
        if not self.enabled or not self.redis:
            return False

        if ttl is None:
            ttl = settings.CACHE_DEFAULT_TTL

        from app.core.metrics import track_redis_op
        start_time = time.time()
        status = "success"
        try:
            serialized_value = json.dumps(jsonable_encoder(value))
            await self.redis.set(key, serialized_value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Redis SET exception for key '{key}': {e}", exc_info=True)
            status = "failure"
            return False
        finally:
            duration = time.time() - start_time
            track_redis_op(operation="set", status=status, duration=duration)

    async def delete(self, key: str) -> bool:
        """
        Deletes a single key from cache.
        Degrades gracefully if Redis fails.
        """
        if not self.enabled or not self.redis:
            return False

        from app.core.metrics import track_redis_op
        start_time = time.time()
        status = "success"
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE exception for key '{key}': {e}", exc_info=True)
            status = "failure"
            return False
        finally:
            duration = time.time() - start_time
            track_redis_op(operation="delete", status=status, duration=duration)


    async def clear_pattern(self, pattern: str) -> bool:
        """
        Scans and deletes all keys matching a glob pattern (e.g. 'analytics:*').
        Uses SCAN iterators rather than KEYS for maximum production safety.
        """
        if not self.enabled or not self.redis:
            return False

        try:
            keys_to_delete = []
            async for key in self.redis.scan_iter(match=pattern):
                keys_to_delete.append(key)

            if keys_to_delete:
                await self.redis.delete(*keys_to_delete)
                logger.info(f"[+] Cleared {len(keys_to_delete)} keys matching pattern: '{pattern}'")
            return True
        except Exception as e:
            logger.error(f"Redis clear_pattern exception for '{pattern}': {e}", exc_info=True)
            return False

# Instantiate global cache service singleton
cache_service = CacheService()

def cache_response(ttl: Optional[int] = None, key_prefix: str = "response", user_dependent: bool = False):
    """
    Decorator to cache FastAPI endpoint responses.
    Automatically serializes the output of the decorated endpoint.
    Handles route path, sorted query parameters, and user scope.
    
    If Redis fails, the decorator degrades gracefully by executing the original endpoint handler.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not cache_service.enabled or not cache_service.redis:
                # Cache disabled or down; execute endpoint directly
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            # Try to find FastAPI's Request object in endpoint arguments/keyword arguments
            request: Optional[Request] = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for v in kwargs.values():
                    if isinstance(v, Request):
                        request = v
                        break

            if not request:
                # Fallback cache key generation based on function name & sorted arguments
                param_str = str(sorted(kwargs.items()))
                cache_key = f"{key_prefix}:{func.__name__}:{param_str}"
            else:
                # Robust cache key incorporating URL path & sorted query params
                path = request.url.path
                sorted_query = sorted(request.query_params.items())
                query_str = "&".join(f"{k}={v}" for k, v in sorted_query)
                
                user_suffix = ""
                if user_dependent:
                    user = getattr(request.state, "user", None)
                    if user and hasattr(user, "username"):
                        user_suffix = f":user:{user.username}"
                    else:
                        user_suffix = ":user:anonymous"

                cache_key = f"{key_prefix}:{path}"
                if query_str:
                    cache_key += f"?{query_str}"
                if user_suffix:
                    cache_key += user_suffix

            # 1. Attempt Cache Lookup
            try:
                cached_data = await cache_service.get(cache_key)
                if cached_data is not None:
                    logger.debug(f"[*] Cache HIT for key: '{cache_key}'")
                    return cached_data
            except Exception as e:
                logger.warning(f"Cache hit lookup failed, bypassing cache: {e}")

            logger.debug(f"[*] Cache MISS for key: '{cache_key}'")

            # 2. Cache Miss: Execute actual route handler
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # 3. Store result in Cache
            try:
                await cache_service.set(cache_key, result, ttl=ttl)
            except Exception as e:
                logger.warning(f"Failed to write results to cache: {e}")

            return result
        return wrapper
    return decorator
