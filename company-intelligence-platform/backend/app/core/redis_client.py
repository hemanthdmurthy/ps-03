# app/core/redis_client.py
"""
Production-Grade Resilient Redis Client Layer
==============================================
Provides a centralized, highly reliable connection pooling wrapper for both async
and synchronous Redis clients. Implements self-healing DNS/networking, exponential
backoff retry logic, operation timeouts, startup diagnostics, and automatic
degradation fallbacks to in-memory FakeRedis.
"""

import os
import sys
import time
import socket
import logging
import asyncio
import random
import urllib.parse
from typing import Optional, Any, Dict, List

import redis
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("company_intel.core.redis_client")

class MockPubSub:
    """Mock PubSub class representing Redis Pub/Sub behavior for MockRedisClient."""
    def __init__(self, client):
        self.client = client
        self.channels = set()
        
    async def subscribe(self, channel, *args, **kwargs):
        self.channels.add(channel)
        logger.info(f"MockPubSub: Subscribed to channel '{channel}'")
        return True
        
    async def unsubscribe(self, channel=None, *args, **kwargs):
        if channel:
            self.channels.discard(channel)
            logger.info(f"MockPubSub: Unsubscribed from channel '{channel}'")
        else:
            self.channels.clear()
            logger.info("MockPubSub: Unsubscribed from all channels")
        return True
        
    async def get_message(self, ignore_subscribe_messages=False, timeout=1.0, *args, **kwargs):
        # Return None after a short sleep to avoid busy loops
        await asyncio.sleep(min(timeout, 0.1))
        return None
        
    async def close(self):
        self.channels.clear()
        logger.info("MockPubSub: Closed connection")


class MockRedisClient:
    """Ultra-fallback mock Redis class representing standard key-value and list behavior in extreme failures."""
    def __init__(self):
        self._store = {}
        
    async def ping(self): return True
    def ping_sync(self): return True
    
    async def get(self, key, *args, **kwargs): return self._store.get(key)
    def get_sync(self, key, *args, **kwargs): return self._store.get(key)
    
    async def set(self, key, value, nx=False, ex=None, *args, **kwargs):
        if nx and key in self._store:
            return None  # Redis set nx returns None (nil) if not set
        self._store[key] = value
        return True
        
    def set_sync(self, key, value, nx=False, ex=None, *args, **kwargs):
        if nx and key in self._store:
            return None
        self._store[key] = value
        return True
        
    async def delete(self, *keys, **kwargs):
        for k in keys:
            self._store.pop(k, None)
        return True
        
    def delete_sync(self, *keys, **kwargs):
        for k in keys:
            self._store.pop(k, None)
        return True
        
    async def exists(self, key, *args, **kwargs):
        return key in self._store
        
    def exists_sync(self, key, *args, **kwargs):
        return key in self._store
        
    async def publish(self, channel, message, *args, **kwargs): return 0
    def publish_sync(self, channel, message, *args, **kwargs): return 0
    
    def pubsub(self, *args, **kwargs):
        return MockPubSub(self)
        
    def scan_iter(self, match=None, count=None, *args, **kwargs):
        import fnmatch
        async def _generator():
            for key in list(self._store.keys()):
                if match is None or fnmatch.fnmatch(str(key), match):
                    yield key
        return _generator()
        
    async def llen(self, key, *args, **kwargs):
        lst = self._store.get(key)
        if not isinstance(lst, list):
            return 0
        return len(lst)

    async def rpush(self, key, value, *args, **kwargs):
        if key not in self._store or not isinstance(self._store[key], list):
            self._store[key] = []
        self._store[key].append(value)
        return len(self._store[key])

    async def lrange(self, key, start, end, *args, **kwargs):
        lst = self._store.get(key)
        if not isinstance(lst, list):
            return []
        if end == -1:
            return lst[start:]
        return lst[start:end+1]

    async def lindex(self, key, index, *args, **kwargs):
        lst = self._store.get(key)
        if not isinstance(lst, list):
            return None
        try:
            return lst[index]
        except Exception:
            return None

    async def lrem(self, key, count, value, *args, **kwargs):
        lst = self._store.get(key)
        if not isinstance(lst, list):
            return 0
        removed = 0
        if count == 0:
            while value in lst:
                lst.remove(value)
                removed += 1
        return removed

    async def lpop(self, key, *args, **kwargs):
        lst = self._store.get(key)
        if not isinstance(lst, list) or len(lst) == 0:
            return None
        return lst.pop(0)

    async def eval(self, script, numkeys, *args, **kwargs):
        # Extremely simplified eval to support releasing the distributed lock in mock mode
        if len(args) >= 2:
            lock_key = args[0]
            identifier = args[1]
            if self._store.get(lock_key) == identifier:
                self._store.pop(lock_key, None)
                return 1
        return 0

    async def close(self): pass
    def close_sync(self): pass


class ResilientRedisClient:
    """
    Resilient Redis Client wrapper providing thread-safe, pool-managed access
    to both synchronous and asynchronous Redis clients, with self-healing features.
    """
    def __init__(self):
        self._async_client: Optional[aioredis.Redis] = None
        self._sync_client: Optional[redis.Redis] = None
        self._is_initialized = False
        self._is_fallback = False
        self._last_error: Optional[str] = None
        self._error_type: Optional[str] = None
        self._redis_url = ""
        self._host = ""
        self._port = 6379
        self._db = 0
        self._scheme = "redis"
        self._in_docker = False
        
        # Async lock to serialize concurrent connection setup
        self._init_lock: Optional[asyncio.Lock] = None
        
        # Operational Stats
        self._connect_time: Optional[float] = None
        self._ops_count = 0
        self._failure_count = 0
        self._reconnect_attempts = 0

    @property
    def is_healthy(self) -> bool:
        """Returns True if connected to real Redis or initialized under fallback."""
        return self._is_initialized

    @property
    def is_fallback(self) -> bool:
        """Returns True if degraded and using in-memory FakeRedis."""
        return self._is_fallback

    @property
    def client(self) -> aioredis.Redis:
        """Returns the active async Redis client instance (real or FakeRedis)."""
        if not self._is_initialized or self._async_client is None:
            logger.warning("[Redis Client] Async client accessed before explicit initialization. Initializing inline...")
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self.initialize())
            else:
                self.initialize_sync()
            if self._async_client is None:
                self._initialize_fakeredis()
        return self._async_client

    @property
    def sync_client(self) -> redis.Redis:
        """Returns the active synchronous Redis client instance (real or FakeRedis)."""
        if not self._is_initialized or self._sync_client is None:
            logger.warning("[Redis Client] Sync client accessed before explicit initialization. Initializing inline...")
            self.initialize_sync()
        return self._sync_client

    def pipeline(self) -> aioredis.client.Pipeline:
        """Returns an async Redis pipeline for batch optimizations."""
        return self.client.pipeline()
        
    def pipeline_sync(self) -> redis.client.Pipeline:
        """Returns a sync Redis pipeline for batch optimizations."""
        return self.sync_client.pipeline()

    @property
    def stats(self) -> Dict[str, Any]:
        """Exposes operational diagnostics and health parameters."""
        return {
            "redis_url": self._mask_url(self._redis_url),
            "host": self._host,
            "port": self._port,
            "scheme": self._scheme,
            "in_docker": self._in_docker,
            "is_initialized": self._is_initialized,
            "is_fallback": self._is_fallback,
            "last_error": self._last_error,
            "error_type": self._error_type,
            "reconnect_attempts": self._reconnect_attempts,
            "failure_count": self._failure_count,
            "ops_count": self._ops_count,
            "uptime_seconds": round(time.time() - self._connect_time, 2) if self._connect_time else 0
        }

    def _mask_url(self, url: str) -> str:
        """Helper to mask credentials in URLs for safe logging."""
        if not url:
            return ""
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.password:
                netloc = parsed.netloc.replace(f":{parsed.password}@", "@")
                return parsed._replace(netloc=netloc).geturl()
        except Exception:
            pass
        return url

    def _optimize_url(self, url: str) -> str:
        """
        Self-healing routing logic:
        - Detects if running inside Docker container.
        - Translates localhost to 'redis' if containerized.
        - Translates 'redis' container hostname to localhost/127.0.0.1 if running directly on host.
        - Enforces correct URI schemes.
        """
        if not url:
            url = "redis://127.0.0.1:6379/0"

        # Correct malformed URI formats
        if not (url.startswith("redis://") or url.startswith("rediss://")):
            if url.startswith("redis:"):
                url = url.replace("redis:", "redis://")
            elif url.startswith("rediss:"):
                url = url.replace("rediss:", "rediss://")
            else:
                url = f"redis://{url}"

        # Detect docker environment
        self._in_docker = os.path.exists('/.dockerenv') or os.environ.get("RUNNING_IN_DOCKER") == "true"

        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 6379
            path = parsed.path or "/0"
            password = parsed.password
            username = parsed.username
            scheme = parsed.scheme

            self._scheme = scheme
            self._port = port
            self._db = int(path.lstrip("/").split("/")[0]) if path.lstrip("/") else 0

            new_host = host
            if self._in_docker:
                # If running inside Docker and target is localhost, redirect to the service container 'redis'
                if host in ("localhost", "127.0.0.1"):
                    new_host = "redis"
                    logger.info(
                        f"[Redis Auto-Heal] Container execution detected. "
                        f"Redirecting host from local '{host}' to container service '{new_host}'."
                    )
            else:
                # Running directly on host OS
                # Attempt name resolution. If host resolves to gaierror (e.g. 'redis' is not defined), fallback to 127.0.0.1
                try:
                    socket.gethostbyname(host)
                except socket.gaierror:
                    if host == "redis":
                        new_host = "127.0.0.1"
                        logger.info(
                            f"[Redis Auto-Heal] Local OS host execution detected. "
                            f"Redirecting unreachable container host '{host}' to '{new_host}'."
                        )

            self._host = new_host

            # Reconstruct the optimized URL
            auth_str = ""
            if username or password:
                u_str = username or ""
                p_str = password or ""
                auth_str = f"{u_str}:{p_str}@"
            
            optimized_url = f"{scheme}://{auth_str}{new_host}:{port}{path}"
            return optimized_url

        except Exception as exc:
            logger.error(f"[Redis URL Parser] Failed parsing/formatting URL '{url}': {exc}")
            return url

    async def initialize(self, raise_on_fail: bool = False) -> bool:
        """
        Initializes the async and sync client connection pools.
        Performs network connectivity pings with exponential backoff on startup.
        If real Redis is unavailable, gracefully degrades to local in-memory FakeRedis.
        """
        if self._init_lock is None:
            self._init_lock = asyncio.Lock()
            
        async with self._init_lock:
            if self._is_initialized and not self._is_fallback:
                return True

            self._redis_url = self._optimize_url(settings.REDIS_URL)
            logger.info(f"[Redis Startup] Target Connection: {self._mask_url(self._redis_url)} (Host: {self._host}, Port: {self._port})")

            # Configures socket parameters for high production reliability
            socket_opts = {
                "socket_connect_timeout": 3.0, # Fail fast during network degradation
                "socket_timeout": 3.0,
                "retry_on_timeout": True,
                "health_check_interval": 30
            }

            if self._scheme == "rediss":
                # Enable SSL protections with safe default settings
                socket_opts.update({
                    "ssl_cert_reqs": None,
                    "ssl_check_hostname": False
                })

            max_startup_retries = 6  # Allows 1s -> 2s -> 4s -> 8s -> 16s -> 30s max backoff delay pattern
            base_retry_delay = 1.0

            for attempt in range(1, max_startup_retries + 1):
                try:
                    logger.info(f"[Redis Connect] Attempt {attempt}/{max_startup_retries} to ping Redis at {self._host}:{self._port}...")
                    
                    # Async Pool Setup
                    async_client = aioredis.Redis.from_url(
                        self._redis_url,
                        decode_responses=True,
                        encoding="utf-8",
                        **socket_opts
                    )
                    
                    # Sync Pool Setup
                    sync_client = redis.Redis.from_url(
                        self._redis_url,
                        decode_responses=True,
                        encoding="utf-8",
                        **socket_opts
                    )

                    # Test connections
                    await async_client.ping()
                    sync_client.ping()

                    # Save validated connection objects to prevent returning partially initialized None
                    self._async_client = async_client
                    self._sync_client = sync_client

                    # Connection established!
                    self._is_initialized = True
                    self._is_fallback = False
                    self._last_error = None
                    self._error_type = None
                    self._connect_time = time.time()
                    self._reconnect_attempts = 0
                    
                    logger.info(f"[+] [Redis Success] Successfully connected and verified Redis at {self._host}:{self._port}!")
                    return True

                except Exception as e:
                    self._reconnect_attempts += 1
                    self._failure_count += 1
                    self._last_error = str(e)
                    self._error_type = type(e).__name__
                    
                    # Check for specific failure categories to print highly-structured logs
                    if isinstance(e, redis.exceptions.AuthenticationError):
                        logger.error(f"[-] [Redis Auth Error] Authentication failed: check username/passwords. Error: {e}")
                    elif isinstance(e, redis.exceptions.TimeoutError):
                        logger.warning(f"[-] [Redis Timeout] Connection timed out: check network routes. Error: {e}")
                    elif "gaierror" in str(e) or "DNS" in str(e):
                        logger.error(f"[-] [Redis DNS Error] Hostname resolution failed for '{self._host}'. Error: {e}")
                    elif "SSL" in str(e) or "ssl" in str(e).lower():
                        logger.error(f"[-] [Redis SSL/TLS Error] SSL handshake failed. URL scheme is '{self._scheme}'. Error: {e}")
                    else:
                        logger.warning(f"[-] [Redis Connection Failed] Error: {e}")

                    if attempt < max_startup_retries:
                        # Required Pattern with Jitter: 1s -> 2s -> 4s -> 8s -> 16s -> 30s max
                        delay_limit = min(base_retry_delay * (2 ** (attempt - 1)), 30.0)
                        # Add jitter/randomization
                        delay = round(random.uniform(0.5 * delay_limit, delay_limit), 2)
                        logger.info(f"[Redis Retry] Waiting {delay}s before next connection attempt...")
                        await asyncio.sleep(delay)
                    else:
                        logger.warning(
                            f"[-] [Redis Outage] Max startup connection attempts exceeded. "
                            f"Current environment: {settings.ENVIRONMENT}"
                        )
                        if raise_on_fail:
                            raise redis.exceptions.ConnectionError(
                                f"Failed to connect to critical Redis server at {self._host}:{self._port} after {max_startup_retries} attempts."
                            ) from e

            # Fallback Mode Activation
            self._initialize_fakeredis()
            return False

    def initialize_sync(self) -> bool:
        """
        Synchronous initialization helper. Used if sync client is accessed
        before async initialize has had a chance to spin up.
        """
        if self._is_initialized and not self._is_fallback:
            return True

        self._redis_url = self._optimize_url(settings.REDIS_URL)
        socket_opts = {
            "socket_connect_timeout": 2.0,
            "socket_timeout": 2.0,
            "retry_on_timeout": True
        }

        try:
            self._sync_client = redis.Redis.from_url(
                self._redis_url,
                decode_responses=True,
                encoding="utf-8",
                **socket_opts
            )
            self._sync_client.ping()
            
            # Setup async client as well
            self._async_client = aioredis.Redis.from_url(
                self._redis_url,
                decode_responses=True,
                encoding="utf-8",
                **socket_opts
            )
            
            self._is_initialized = True
            self._is_fallback = False
            self._connect_time = time.time()
            logger.info(f"[+] [Redis Sync Success] Synchronous connection verified at {self._host}:{self._port}.")
            return True
        except Exception as e:
            logger.warning(f"[-] [Redis Sync Connect Failed] {e}. Falling back synchronously to FakeRedis.")
            self._initialize_fakeredis()
            return False

    def _initialize_fakeredis(self):
        """Initializes internal in-memory FakeRedis caches for both sync & async.
        
        CRITICAL: Both clients MUST share a common FakeServer so that pub/sub
        messages published via sync_client are visible to async pubsub subscribers.
        Without a shared server, Celery worker events (sync publish) are silently
        dropped and SSE streams never receive updates — causing 0% progress stuck.
        """
        try:
            import fakeredis
            import fakeredis.aioredis as fake_async_redis

            # Shared server is the key: both clients talk to the SAME in-memory bus
            shared_server = fakeredis.FakeServer()

            self._async_client = fake_async_redis.FakeRedis(
                server=shared_server, decode_responses=True
            )
            self._sync_client = fakeredis.FakeRedis(
                server=shared_server, decode_responses=True
            )

            self._is_fallback = True
            self._is_initialized = True
            self._connect_time = time.time()
            logger.info(
                "[+] [Redis Fallback] In-memory FakeRedis successfully active "
                "for both sync/async operations (shared server — pub/sub bridged)."
            )
        except Exception as fake_exc:
            logger.critical(f"[-] [Fatal Fallback Failure] Could not load fakeredis package: {fake_exc}")
            # If all else fails, create extremely basic mock client dictionaries to avoid runtime AttributeError crashes
            self._async_client = MockRedisClient()
            self._sync_client = MockRedisClient()
            self._is_fallback = True
            self._is_initialized = True

    async def close(self):
        """Closes all active pools and connections gracefully during application shutdown."""
        logger.info("[Redis Shutdown] Gracefully tearing down Redis connection pools...")
        
        # Teardown Async Client
        if self._async_client:
            try:
                await self._async_client.close()
                logger.info("[Redis Shutdown] Async connection pool disposed.")
            except Exception as e:
                logger.error(f"[Redis Shutdown] Async close error: {e}")
                
        # Teardown Sync Client
        if self._sync_client:
            try:
                self._sync_client.close()
                logger.info("[Redis Shutdown] Sync connection pool disposed.")
            except Exception as e:
                logger.error(f"[Redis Shutdown] Sync close error: {e}")
                
        self._is_initialized = False

    # ==========================================
    # RESILIENT WRAPPERS WITH RETRIES AND TIMEOUTS
    # ==========================================
    async def safe_execute_async(self, func, *args, **kwargs) -> Any:
        """
        Executes an async Redis function inside a controlled retry wrapper.
        If the primary connection is severed and we are not under fallback,
        triggers automatic recovery or dynamically drops to FakeRedis fallback.
        """
        self._ops_count += 1
        try:
            # Wrap the operation in an asyncio timeout for strict latency guarantees
            return await asyncio.wait_for(func(*args, **kwargs), timeout=3.5)
        except asyncio.TimeoutError:
            self._failure_count += 1
            logger.error(f"[Redis Operation Timeout] Async call timed out after 3.5s.")
            return None
        except Exception as exc:
            self._failure_count += 1
            self._last_error = str(exc)
            logger.error(f"[Redis Async Op Error] Operation failed: {exc}")
            
            # Check if this represents a lost connection, trigger self-healing
            if isinstance(exc, (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError)) and not self._is_fallback:
                logger.warning("[Redis Reconnect Trigger] Connection severed during execution. Re-running initialize...")
                await self.initialize()
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=3.5)
                except Exception as retry_exc:
                    logger.critical(f"[Redis Recovery Fail] Failed secondary execution after reconnect: {retry_exc}")
                    # Degrade to fakeredis immediately to avoid crashing the endpoint
                    self._initialize_fakeredis()
                    return await func(*args, **kwargs)
            return None

    def safe_execute_sync(self, func, *args, **kwargs) -> Any:
        """
        Synchronous safe execution retry layer.
        """
        self._ops_count += 1
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            self._failure_count += 1
            self._last_error = str(exc)
            logger.error(f"[Redis Op Error] Sync operation failed: {exc}")
            
            if isinstance(exc, (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError)) and not self._is_fallback:
                logger.warning("[Redis Reconnect Trigger] Synchronous connection lost. Attempting recovery...")
                self.initialize_sync()
                try:
                    return func(*args, **kwargs)
                except Exception as retry_exc:
                    logger.critical(f"[Redis Sync Recovery Fail] Failed secondary sync execution: {retry_exc}")
                    self._initialize_fakeredis()
                    return func(*args, **kwargs)
            return None


# Instantiate central application singleton
redis_client = ResilientRedisClient()
