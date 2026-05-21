# app/core/resilience.py
"""
Enterprise-Grade Resilience & Fault Containment Framework
==========================================================
Provides production-hardened abstractions for:
- Retry isolation with exponential backoff + jitter
- Timeout containment wrappers (sync & async)
- Fallback execution chains
- Service degradation policies
- Bulkhead isolation (semaphore-based)
- Stuck task detection & quarantine
- Runtime fault boundaries
"""

import asyncio
import logging
import time
import random
import json
import functools
from typing import Callable, Any, Optional, List, TypeVar, Coroutine
from datetime import datetime

logger = logging.getLogger("company_intel.core.resilience")

T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════════════════
# 1. RETRY ISOLATION WITH EXPONENTIAL BACKOFF + JITTER
# ═══════════════════════════════════════════════════════════════════════════

class RetryConfig:
    """Configuration for controlled retry behavior."""
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,),
        non_retryable_exceptions: tuple = (),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.non_retryable_exceptions = non_retryable_exceptions


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for synchronous functions with exponential backoff + jitter.
    Prevents retry storms by capping delay and adding randomization.
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.non_retryable_exceptions as e:
                    logger.error(f"[Retry] Non-retryable exception in {func.__name__}: {e}")
                    raise
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = min(
                            config.base_delay * (config.exponential_base ** attempt),
                            config.max_delay
                        )
                        if config.jitter:
                            delay = random.uniform(0.5 * delay, delay)
                        logger.warning(
                            f"[Retry] {func.__name__} attempt {attempt + 1}/{config.max_retries + 1} "
                            f"failed: {e}. Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[Retry] {func.__name__} exhausted all {config.max_retries + 1} attempts. "
                            f"Last error: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


async def async_retry_with_backoff(
    func: Callable[..., Coroutine],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Async retry wrapper with exponential backoff + jitter.
    Designed for isolated async operations.
    """
    if config is None:
        config = RetryConfig()

    last_exception = None
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except config.non_retryable_exceptions as e:
            logger.error(f"[AsyncRetry] Non-retryable exception: {e}")
            raise
        except config.retryable_exceptions as e:
            last_exception = e
            if attempt < config.max_retries:
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )
                if config.jitter:
                    delay = random.uniform(0.5 * delay, delay)
                logger.warning(
                    f"[AsyncRetry] Attempt {attempt + 1}/{config.max_retries + 1} "
                    f"failed: {e}. Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"[AsyncRetry] Exhausted all {config.max_retries + 1} attempts.")
    raise last_exception


# ═══════════════════════════════════════════════════════════════════════════
# 2. TIMEOUT CONTAINMENT WRAPPERS
# ═══════════════════════════════════════════════════════════════════════════

class TimeoutContainmentError(Exception):
    """Raised when an operation exceeds its allotted timeout budget."""
    pass


def sync_timeout(seconds: float):
    """
    Decorator to enforce a strict wall-clock timeout on synchronous functions.
    Uses a background thread to enforce the deadline.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=seconds)
                except concurrent.futures.TimeoutError:
                    logger.error(
                        f"[Timeout] {func.__name__} exceeded {seconds}s deadline. Contained."
                    )
                    raise TimeoutContainmentError(
                        f"{func.__name__} timed out after {seconds} seconds"
                    )
        return wrapper
    return decorator


async def async_timeout(coro: Coroutine, seconds: float, operation_name: str = "operation") -> Any:
    """
    Wraps an async coroutine with a strict timeout boundary.
    Raises TimeoutContainmentError instead of raw TimeoutError for clarity.
    """
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        logger.error(f"[Timeout] {operation_name} exceeded {seconds}s deadline. Contained.")
        raise TimeoutContainmentError(
            f"{operation_name} timed out after {seconds} seconds"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. FALLBACK EXECUTION CHAINS
# ═══════════════════════════════════════════════════════════════════════════

class FallbackChain:
    """
    Executes a chain of fallback strategies in order.
    Each strategy is attempted until one succeeds.
    Prevents total system failure by gracefully degrading through alternatives.
    """
    def __init__(self, name: str):
        self.name = name
        self._strategies: List[tuple] = []  # List of (name, callable)

    def add_strategy(self, name: str, func: Callable):
        """Register a fallback strategy."""
        self._strategies.append((name, func))
        return self

    def execute(self, *args, **kwargs) -> Any:
        """Execute strategies in order until one succeeds."""
        errors = []
        for strategy_name, func in self._strategies:
            try:
                logger.info(f"[Fallback:{self.name}] Attempting strategy: {strategy_name}")
                result = func(*args, **kwargs)
                logger.info(f"[Fallback:{self.name}] Strategy '{strategy_name}' succeeded.")
                return result
            except Exception as e:
                logger.warning(
                    f"[Fallback:{self.name}] Strategy '{strategy_name}' failed: {e}"
                )
                errors.append((strategy_name, e))

        logger.error(
            f"[Fallback:{self.name}] All {len(self._strategies)} strategies exhausted. "
            f"Errors: {[(n, str(e)) for n, e in errors]}"
        )
        raise RuntimeError(
            f"All fallback strategies exhausted for '{self.name}'. "
            f"Last error: {errors[-1][1] if errors else 'unknown'}"
        )

    async def async_execute(self, *args, **kwargs) -> Any:
        """Execute async strategies in order until one succeeds."""
        errors = []
        for strategy_name, func in self._strategies:
            try:
                logger.info(f"[Fallback:{self.name}] Attempting async strategy: {strategy_name}")
                result = await func(*args, **kwargs)
                logger.info(f"[Fallback:{self.name}] Async strategy '{strategy_name}' succeeded.")
                return result
            except Exception as e:
                logger.warning(
                    f"[Fallback:{self.name}] Async strategy '{strategy_name}' failed: {e}"
                )
                errors.append((strategy_name, e))

        logger.error(
            f"[Fallback:{self.name}] All {len(self._strategies)} async strategies exhausted."
        )
        raise RuntimeError(
            f"All async fallback strategies exhausted for '{self.name}'."
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. SERVICE DEGRADATION POLICIES
# ═══════════════════════════════════════════════════════════════════════════

class DegradationLevel:
    FULL = "full"          # All services operational
    PARTIAL = "partial"    # Non-critical services disabled
    MINIMAL = "minimal"    # Only health and critical paths operational
    EMERGENCY = "emergency"  # Read-only, no writes


class ServiceDegradationManager:
    """
    Centralized degradation state machine.
    Tracks which services are degraded and what level the system is operating at.
    """
    def __init__(self):
        self._level = DegradationLevel.FULL
        self._degraded_services: dict = {}
        self._change_log: List[dict] = []

    @property
    def level(self) -> str:
        return self._level

    @property
    def degraded_services(self) -> dict:
        return self._degraded_services.copy()

    def degrade_service(self, service_name: str, reason: str):
        """Mark a service as degraded."""
        self._degraded_services[service_name] = {
            "reason": reason,
            "degraded_at": datetime.utcnow().isoformat(),
        }
        self._recalculate_level()
        self._change_log.append({
            "action": "degraded",
            "service": service_name,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.warning(f"[Degradation] Service '{service_name}' degraded: {reason}. System level: {self._level}")

    def restore_service(self, service_name: str):
        """Restore a previously degraded service."""
        if service_name in self._degraded_services:
            del self._degraded_services[service_name]
            self._recalculate_level()
            self._change_log.append({
                "action": "restored",
                "service": service_name,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.info(f"[Degradation] Service '{service_name}' restored. System level: {self._level}")

    def is_service_degraded(self, service_name: str) -> bool:
        return service_name in self._degraded_services

    def _recalculate_level(self):
        """Recalculate system degradation level based on active degradations."""
        count = len(self._degraded_services)
        critical_services = {"database", "redis", "celery"}
        degraded_critical = critical_services & set(self._degraded_services.keys())

        if count == 0:
            self._level = DegradationLevel.FULL
        elif len(degraded_critical) >= 2:
            self._level = DegradationLevel.EMERGENCY
        elif len(degraded_critical) >= 1:
            self._level = DegradationLevel.MINIMAL
        else:
            self._level = DegradationLevel.PARTIAL

    def get_status(self) -> dict:
        return {
            "level": self._level,
            "degraded_services": self._degraded_services,
            "change_log_recent": self._change_log[-10:] if self._change_log else [],
        }


# Global singleton
degradation_manager = ServiceDegradationManager()


# ═══════════════════════════════════════════════════════════════════════════
# 5. BULKHEAD ISOLATION (SEMAPHORE-BASED)
# ═══════════════════════════════════════════════════════════════════════════

class BulkheadFull(Exception):
    """Raised when a bulkhead has no available capacity."""
    pass


class Bulkhead:
    """
    Limits concurrent access to a resource/service to prevent cascading overload.
    Uses an asyncio.Semaphore under the hood.
    """
    def __init__(self, name: str, max_concurrent: int = 10):
        self.name = name
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._active_count = 0
        self._rejected_count = 0

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def execute(self, coro: Coroutine, timeout: Optional[float] = None) -> Any:
        """
        Execute a coroutine within the bulkhead.
        Rejects with BulkheadFull if capacity is exhausted.
        """
        sem = self._get_semaphore()
        if sem.locked():
            self._rejected_count += 1
            logger.warning(
                f"[Bulkhead:{self.name}] Capacity exhausted ({self.max_concurrent} slots). "
                f"Rejecting request. Total rejections: {self._rejected_count}"
            )
            raise BulkheadFull(f"Bulkhead '{self.name}' is full.")

        async with sem:
            self._active_count += 1
            try:
                if timeout:
                    return await asyncio.wait_for(coro, timeout=timeout)
                return await coro
            finally:
                self._active_count -= 1

    @property
    def stats(self) -> dict:
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active": self._active_count,
            "rejected_total": self._rejected_count,
        }


# Pre-configured bulkheads for failure domain segmentation
research_bulkhead = Bulkhead("research_workflow", max_concurrent=5)
notification_bulkhead = Bulkhead("notifications", max_concurrent=20)
db_bulkhead = Bulkhead("database_operations", max_concurrent=50)
external_api_bulkhead = Bulkhead("external_api_calls", max_concurrent=10)


# ═══════════════════════════════════════════════════════════════════════════
# 6. STUCK TASK DETECTION & QUARANTINE
# ═══════════════════════════════════════════════════════════════════════════

class TaskQuarantine:
    """
    Tracks and quarantines stuck or repeatedly failing tasks.
    Prevents them from poisoning the queue through infinite retry loops.
    """
    def __init__(self):
        self._quarantined: dict = {}
        self._failure_counts: dict = {}
        self._quarantine_threshold = 5

    def record_failure(self, task_id: str, task_name: str, error: str) -> bool:
        """
        Record a task failure. Returns True if the task should be quarantined.
        """
        key = f"{task_name}:{task_id}"
        self._failure_counts[key] = self._failure_counts.get(key, 0) + 1

        if self._failure_counts[key] >= self._quarantine_threshold:
            self._quarantined[key] = {
                "task_id": task_id,
                "task_name": task_name,
                "error": error,
                "failure_count": self._failure_counts[key],
                "quarantined_at": datetime.utcnow().isoformat(),
            }
            logger.critical(
                f"[Quarantine] Task {task_name}:{task_id} quarantined after "
                f"{self._failure_counts[key]} failures."
            )
            return True
        return False

    def is_quarantined(self, task_id: str, task_name: str) -> bool:
        key = f"{task_name}:{task_id}"
        return key in self._quarantined

    def release(self, task_id: str, task_name: str):
        key = f"{task_name}:{task_id}"
        self._quarantined.pop(key, None)
        self._failure_counts.pop(key, None)
        logger.info(f"[Quarantine] Task {task_name}:{task_id} released from quarantine.")

    @property
    def quarantined_tasks(self) -> dict:
        return self._quarantined.copy()


# Global singleton
task_quarantine = TaskQuarantine()


# ═══════════════════════════════════════════════════════════════════════════
# 7. RUNTIME FAULT BOUNDARY DECORATOR
# ═══════════════════════════════════════════════════════════════════════════

def fault_boundary(
    operation_name: str = "operation",
    fallback_value: Any = None,
    log_level: str = "error",
    suppress: bool = True,
):
    """
    Decorator that wraps a function in a fault boundary.
    Catches all exceptions and optionally returns a fallback value.
    Prevents exceptions from propagating into calling code and crashing parent systems.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_func = getattr(logger, log_level, logger.error)
                log_func(
                    f"[FaultBoundary:{operation_name}] Contained exception in "
                    f"{func.__name__}: {e}"
                )
                if suppress:
                    return fallback_value
                raise
        return wrapper
    return decorator


def async_fault_boundary(
    operation_name: str = "operation",
    fallback_value: Any = None,
    log_level: str = "error",
    suppress: bool = True,
):
    """Async version of the fault boundary decorator."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log_func = getattr(logger, log_level, logger.error)
                log_func(
                    f"[FaultBoundary:{operation_name}] Contained async exception in "
                    f"{func.__name__}: {e}"
                )
                if suppress:
                    return fallback_value
                raise
        return wrapper
    return decorator
