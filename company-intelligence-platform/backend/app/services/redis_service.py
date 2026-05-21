# app/services/redis_service.py
"""
Centralized Resilient Redis Service Layer
========================================
Provides distributed lock management, Circuit Breakers, safe key serialization,
latency telemetries, and operation timeouts. Serves as a single entry point for
all Redis communications.
"""

import json
import time
import logging
import asyncio
from typing import Optional, Any, Dict, List, Callable

import redis
import redis.asyncio as aioredis
from app.core.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger("company_intel.services.redis_service")


class CircuitBreakerOpenException(Exception):
    """Raised when the Circuit Breaker is OPEN and blocks Redis operations."""
    pass


class CircuitBreaker:
    """
    Stateful Circuit Breaker for Redis connection management.
    Handles temporary Redis outages safely, preventing blocking/hanging the API.
    Transitions: CLOSED <-> OPEN -> HALF_OPEN -> CLOSED
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 10.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_state_change = time.time()

    def record_success(self):
        """Records a successful connection; resets failure count and closes circuit if open."""
        if self.state != "CLOSED":
            logger.info(f"🟢 [Circuit Breaker] Redis connectivity restored! Transitioning from {self.state} to CLOSED.")
            self.state = "CLOSED"
        self.failure_count = 0
        self.last_state_change = time.time()

    def record_failure(self):
        """Records a connection failure; trips circuit to OPEN if failure threshold exceeded."""
        self.failure_count += 1
        logger.warning(f"⚠️ [Circuit Breaker] Redis operation failure recorded ({self.failure_count}/{self.failure_threshold}).")
        if self.failure_count >= self.failure_threshold and self.state != "OPEN":
            logger.critical(
                f"🚨 [Circuit Breaker] Redis failure threshold exceeded! "
                f"Tripping circuit breaker to OPEN for {self.recovery_timeout}s."
            )
            self.state = "OPEN"
            self.last_state_change = time.time()

    def allow_request(self) -> bool:
        """Determines if requests are allowed under current state."""
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            # Check if recovery timeout has elapsed to allow probe request
            if time.time() - self.last_state_change > self.recovery_timeout:
                logger.info("🟡 [Circuit Breaker] Recovery cooldown elapsed. Transitioning to HALF_OPEN to probe connection.")
                self.state = "HALF_OPEN"
                self.last_state_change = time.time()
                return True
            return False
        # HALF_OPEN allows a single probe request
        return True


class RedisService:
    """
    Centralized Redis Service Layer.
    Wraps resilient connection pools, managing safe CRUD, distributed locks,
    telemetry logging, and automated degradation.
    """
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.latency_warning_threshold_ms = 100.0  # Alert if operations exceed 100ms

    async def initialize(self):
        """Initializes async and sync client connection pools."""
        await redis_client.initialize()
        logger.info(f"[Redis Service] Initialized successfully. Fallback mode active: {self.is_fallback}")

    @property
    def client(self) -> aioredis.Redis:
        """Returns the dynamic active async Redis client instance (real or FakeRedis)."""
        return redis_client.client

    @property
    def sync_client(self) -> redis.Redis:
        """Returns the dynamic active synchronous Redis client instance (real or FakeRedis)."""
        return redis_client.sync_client

    @property
    def is_fallback(self) -> bool:
        """Returns True if the backend is currently executing via in-memory FakeRedis."""
        return redis_client.is_fallback

    async def _execute_async(self, func: Any, *args, **kwargs) -> Any:
        """
        Executes an async Redis function wrapped with circuit breaking,
        strict operation timeouts, and latency telemetries.
        """
        if not self.circuit_breaker.allow_request():
            raise CircuitBreakerOpenException("Circuit breaker is OPEN. Redis requests are temporarily blocked.")

        # Dynamically resolve client to always get the latest validated instance
        client = self.client
        if not client:
            await self.initialize()
            client = self.client

        if not client:
            raise redis.exceptions.ConnectionError("Redis client is not initialized or None.")

        # Resolve function dynamically against client to avoid stale bound-method references
        resolved_func = func
        if isinstance(func, str):
            resolved_func = getattr(client, func)
        else:
            method_name = getattr(func, "__name__", None)
            if method_name and hasattr(client, method_name):
                resolved_func = getattr(client, method_name)

        # Assert socket/connection health for real Redis to catch transient drops fast
        if not self.is_fallback:
            try:
                await asyncio.wait_for(client.ping(), timeout=1.0)
            except Exception as ping_exc:
                logger.warning(f"[-] [Redis Ping Failure] Active ping check failed: {ping_exc}. Attempting connection recovery...")
                await redis_client.initialize()
                client = self.client
                if not client:
                    raise redis.exceptions.ConnectionError("Failed to reinitialize Redis client after ping failure.") from ping_exc
                # Re-resolve function after re-initialization
                if isinstance(func, str):
                    resolved_func = getattr(client, func)
                elif method_name:
                    resolved_func = getattr(client, method_name)

        start_time = time.time()
        try:
            # Enforce strict timeout
            result = await asyncio.wait_for(resolved_func(*args, **kwargs), timeout=3.0)
            
            # Successful run - update breaker state
            self.circuit_breaker.record_success()
            
            # Latency profiling
            latency_ms = (time.time() - start_time) * 1000
            if latency_ms > self.latency_warning_threshold_ms:
                logger.warning(
                    f"⚠️ [Redis Latency Warning] Slow operation took {latency_ms:.2f}ms "
                    f"(Threshold: {self.latency_warning_threshold_ms}ms)"
                )
            return result
        except asyncio.TimeoutError as exc:
            self.circuit_breaker.record_failure()
            logger.error("❌ [Redis Operation Timeout] Operation timed out.")
            raise exc
        except Exception as exc:
            self.circuit_breaker.record_failure()
            logger.error(f"❌ [Redis Operation Failure] Operation failed: {exc}")
            raise exc

    # ==========================================
    # VALUE OPERATIONS (JSON)
    # ==========================================
    async def get_json(self, key: str) -> Optional[Any]:
        """
        Retrieves and deserializes a JSON cached value.
        Downgrades non-JSON parsing warnings to debug to avoid log spam,
        safely returning the raw string value as fallback.
        """
        try:
            val = await self._execute_async("get", key)
            if not val:
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError) as je:
                logger.debug(
                    f"[Redis Service] Non-JSON or malformed value detected in get_json "
                    f"for key '{key}', returning raw string as fallback. Error: {je}"
                )
                return val
        except Exception as e:
            logger.error(f"[Redis Service] get_json failed for '{key}': {e}. Returning fallback None.")
            return None

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Serializes and caches a JSON value with an optional TTL expiration."""
        try:
            serialized = json.dumps(value)
            await self._execute_async("set", key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"[Redis Service] set_json failed for '{key}': {e}.")
            return False

    # Backwards compatibility wrappers
    async def get(self, key: str) -> Optional[Any]:
        """Retrieves a cached value, safely returning deserialized JSON or raw string fallback."""
        return await self.get_json(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Serializes and caches a value with an optional TTL expiration."""
        return await self.set_json(key, value, ttl)

    # ==========================================
    # VALUE OPERATIONS (RAW STRINGS)
    # ==========================================
    async def get_raw(self, key: str) -> Optional[str]:
        """Retrieves a raw, undecorated string from Redis without any JSON processing."""
        try:
            val = await self._execute_async("get", key)
            return val if val else None
        except Exception as e:
            logger.error(f"[Redis Service] get_raw failed for '{key}': {e}. Returning None.")
            return None

    async def set_raw(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Saves a raw string directly to Redis without JSON encoding."""
        try:
            await self._execute_async("set", key, value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"[Redis Service] set_raw failed for '{key}': {e}.")
            return False

    async def delete(self, key: str) -> bool:
        """Deletes a key from the cache store."""
        try:
            await self._execute_async("delete", key)
            return True
        except Exception as e:
            logger.error(f"[Redis Service] DELETE failed for '{key}': {e}.")
            return False

    async def exists(self, key: str) -> bool:
        """Checks whether a key exists in Redis."""
        try:
            return bool(await self._execute_async("exists", key))
        except Exception as e:
            logger.error(f"[Redis Service] EXISTS failed for '{key}': {e}.")
            return False

    # ==========================================
    # DISTRIBUTED MUTEX LOCKS
    # ==========================================
    async def set_lock(self, lock_key: str, identifier: str, ttl_seconds: int = 1800) -> bool:
        """
        Acquires a non-blocking distributed lock using SET NX EX.
        Guarantees atomicity and distributed safety for concurrent workers.
        """
        try:
            acquired = await self._execute_async("set", lock_key, identifier, nx=True, ex=ttl_seconds)
            if acquired:
                logger.info(f"🔑 [Redis Lock] Lock acquired for '{lock_key}' (ID: {identifier}, TTL: {ttl_seconds}s)")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ [Redis Lock] Failed to acquire lock for '{lock_key}': {e}")
            return False

    async def has_lock(self, lock_key: str) -> bool:
        """
        Checks whether a lock is active using EXISTS.
        Bypasses JSON deserialization completely.
        """
        try:
            return await self.exists(lock_key)
        except Exception as e:
            logger.error(f"❌ [Redis Lock] has_lock check failed for '{lock_key}': {e}")
            return False

    async def get_lock_holder(self, lock_key: str) -> Optional[str]:
        """Retrieves the active lock identifier without any JSON parsing."""
        return await self.get_raw(lock_key)

    async def release_lock(self, lock_key: str, identifier: str) -> bool:
        """
        Releases a distributed lock atomically using Lua scripting.
        Only deletes the lock if the identifier matches the active lock holder.
        """
        lua_release = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        async def _direct_release() -> bool:
            try:
                current_holder = await self.get_lock_holder(lock_key)
                if current_holder == identifier or not current_holder:
                    await self.delete(lock_key)
                    logger.warning(f"🔓 [Redis Lock] Direct delete fallback succeeded for '{lock_key}' (ID: {identifier})")
                    return True
                return False
            except Exception as fallback_exc:
                logger.critical(f"❌ [Redis Lock] Direct delete fallback failed for '{lock_key}': {fallback_exc}")
                return False

        try:
            client = self.client
            if not hasattr(client, "eval"):
                logger.warning(
                    f"⚠️ [Redis Lock] Redis client does not support EVAL; using direct delete fallback for '{lock_key}'."
                )
                return await _direct_release()

            result = await self._execute_async("eval", lua_release, 1, lock_key, identifier)
            if result:
                logger.info(f"🔓 [Redis Lock] Lock released for '{lock_key}' (ID: {identifier})")
                return True
            return False
        except Exception as e:
            message = str(e).lower()
            if "unknown command" in message or "unsupported" in message or "no such command" in message:
                logger.warning(
                    f"⚠️ [Redis Lock] EVAL unsupported for '{lock_key}': {e}. Falling back to direct delete."
                )
                return await _direct_release()

            logger.error(f"❌ [Redis Lock] Failed to release lock atomically for '{lock_key}': {e}")
            return await _direct_release()

    async def force_release_lock(self, lock_key: str) -> bool:
        """Forcibly releases a lock key. Used for auto-cleanup and deadlock recovery."""
        try:
            await self.delete(lock_key)
            logger.warning(f"🧹 [Redis Lock] Forcibly cleared lock key: '{lock_key}'")
            return True
        except Exception as e:
            logger.error(f"❌ [Redis Lock] Force release failed for '{lock_key}': {e}")
            return False

    # Backwards compatibility lock wrapper
    async def acquire_lock(self, lock_key: str, identifier: str, ttl_seconds: int = 1800) -> bool:
        """Acquires lock. Backwards compatible wrapper around set_lock."""
        return await self.set_lock(lock_key, identifier, ttl_seconds)

    # ==========================================
    # COUNTERS & NUMERIC OPERATIONS
    # ==========================================
    async def incr_counter(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        """Increments a counter and optionally sets a TTL expiration."""
        try:
            res = await self._execute_async("incrby", key, amount)
            if ttl is not None and res == amount:
                # Set TTL on first increment
                await self._execute_async("expire", key, ttl)
            return res
        except Exception as e:
            logger.error(f"[Redis Service] INCR failed for '{key}': {e}")
            return None

    async def get_counter(self, key: str) -> Optional[int]:
        """Retrieves a counter value as an integer, safe from JSON serialization warnings."""
        try:
            val = await self.get_raw(key)
            return int(val) if val else None
        except Exception as e:
            logger.error(f"[Redis Service] get_counter failed for '{key}': {e}")
            return None

    # ==========================================
    # WORKFLOW STATE & TASK COORDINATION
    # ==========================================
    async def get_workflow_state(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves workflow status payload using safe JSON retrieval."""
        company_id = company_name.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "")
        return await self.get_json(f"orchestration:{company_id}:status")

    async def set_workflow_state(self, company_name: str, state: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Saves workflow status payload using safe JSON serialization."""
        company_id = company_name.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "")
        return await self.set_json(f"orchestration:{company_id}:status", state, ttl)

    async def enqueue_task(self, queue_name: str, payload: Any) -> bool:
        """Pushes a task payload to a Redis list queue."""
        try:
            serialized = json.dumps(payload)
            await self._execute_async("rpush", queue_name, serialized)
            return True
        except Exception as e:
            logger.error(f"[Redis Service] enqueue_task failed on '{queue_name}': {e}")
            return False

    async def dequeue_task(self, queue_name: str) -> Optional[Any]:
        """Pulls and parses a task payload from a Redis list queue."""
        try:
            val = await self._execute_async("lpop", queue_name)
            return json.loads(val) if val else None
        except Exception as e:
            logger.error(f"[Redis Service] dequeue_task failed on '{queue_name}': {e}")
            return None

    # ==========================================
    # AUTO-HEALING & CORRUPTED DATA SWEEPER
    # ==========================================
    async def cleanup_corrupted_locks(self) -> Dict[str, int]:
        """
        Scans for orchestration locks, detects stale/orphaned locks,
        and auto-heals by clearing them safely to prevent pipeline deadlock.
        """
        logger.info("🧹 [Redis Cleanup] Starting orchestration lock validation and auto-healing...")
        stats = {"scanned": 0, "deleted_malformed": 0, "deleted_orphaned": 0, "deleted_stale": 0}
        try:
            lock_keys = await self.scan_keys("orchestration:*:lock")
            stats["scanned"] = len(lock_keys)
            for lock_key in lock_keys:
                try:
                    val = await self.get_raw(lock_key)
                    if not val:
                        await self.force_release_lock(lock_key)
                        stats["deleted_malformed"] += 1
                        continue

                    # Key format: orchestration:<company_id>:lock -> status key is orchestration:<company_id>:status
                    status_key = lock_key.replace(":lock", ":status")
                    status_exists = await self.exists(status_key)
                    if not status_exists:
                        logger.warning(f"🧹 [Redis Cleanup] Auto-healing orphaned lock '{lock_key}': status key '{status_key}' does not exist.")
                        await self.force_release_lock(lock_key)
                        stats["deleted_orphaned"] += 1
                        continue

                    status_payload = await self.get_json(status_key)
                    if not status_payload or not isinstance(status_payload, dict):
                        logger.warning(f"🧹 [Redis Cleanup] Auto-healing malformed status/lock for '{lock_key}'")
                        await self.force_release_lock(lock_key)
                        stats["deleted_malformed"] += 1
                        continue

                    status_state = status_payload.get("status")
                    if status_state in ("completed", "failed", "duplicate"):
                        logger.info(f"🧹 [Redis Cleanup] Auto-healing stale lock '{lock_key}': status is terminal '{status_state}'.")
                        await self.force_release_lock(lock_key)
                        stats["deleted_stale"] += 1
                except Exception as key_err:
                    logger.error(f"❌ [Redis Cleanup] Error validating key '{lock_key}': {key_err}")
                    try:
                        await self.force_release_lock(lock_key)
                        stats["deleted_malformed"] += 1
                    except Exception:
                        pass
            logger.info(
                f"✨ [Redis Cleanup Completed] Scanned: {stats['scanned']}, "
                f"Cleared Malformed: {stats['deleted_malformed']}, "
                f"Cleared Orphaned: {stats['deleted_orphaned']}, "
                f"Cleared Stale: {stats['deleted_stale']}"
            )
            return stats
        except Exception as e:
            logger.error(f"❌ [Redis Cleanup] Lock validation failed to complete: {e}")
            return stats

    # ==========================================
    # KEY SCANNING & TELEMETRY
    # ==========================================
    async def scan_keys(self, pattern: str) -> List[str]:
        """Scans and retrieves keys matching a glob pattern safely in production via SCAN."""
        if not self.circuit_breaker.allow_request():
            logger.warning("[Redis Service] Circuit Breaker is OPEN. SCAN request skipped.")
            return []

        client = self.client
        if not client:
            try:
                await self.initialize()
                client = self.client
            except Exception:
                return []

        if not client:
            return []

        keys = []
        try:
            # We can use the scan_iter safely
            async for key in client.scan_iter(match=pattern, count=100):
                keys.append(key)
            self.circuit_breaker.record_success()
            return keys
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"❌ [Redis Service] SCAN failed for pattern '{pattern}': {e}")
            # Try a reconnect if it represents a connection failure
            if isinstance(e, (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError)) and not self.is_fallback:
                logger.warning("[Redis Service] Reconnection triggered during SCAN failure.")
                try:
                    await redis_client.initialize()
                    client = self.client
                    if client:
                        keys = []
                        async for key in client.scan_iter(match=pattern, count=100):
                            keys.append(key)
                        return keys
                except Exception as retry_err:
                    logger.critical(f"[Redis Service] SCAN recovery failed: {retry_err}")
            return []


# Central Application Singleton instance
redis_service = RedisService()
