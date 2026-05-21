import asyncio
import logging
import contextlib
from typing import Optional, Coroutine, Any

logger = logging.getLogger(__name__)

class AsyncRuntimeManager:
    _concurrency_semaphore: Optional[asyncio.Semaphore] = None
    _max_concurrency = 100

    @classmethod
    def set_max_concurrency(cls, limit: int):
        cls._max_concurrency = limit
        if cls._concurrency_semaphore:
            cls._concurrency_semaphore = asyncio.Semaphore(limit)

    @classmethod
    def get_semaphore(cls) -> asyncio.Semaphore:
        if not cls._concurrency_semaphore:
            cls._concurrency_semaphore = asyncio.Semaphore(cls._max_concurrency)
        return cls._concurrency_semaphore

    @staticmethod
    def get_safe_loop() -> asyncio.AbstractEventLoop:
        """Retrieves or creates an event loop safely, handling RuntimeError."""
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            pass

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
            return loop
        except RuntimeError:
            logger.warning("No running event loop or closed loop detected. Creating a new event loop.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    @staticmethod
    async def run_with_backpressure(coro: Coroutine, timeout: Optional[float] = None) -> Any:
        """Runs a coroutine with backpressure using semaphore and adaptive timeout."""
        sem = AsyncRuntimeManager.get_semaphore()
        try:
            # Queue load shedding - fail fast if saturated
            if sem.locked():
                logger.warning("Concurrency saturated, applying backpressure.")
            async with sem:
                if timeout:
                    return await asyncio.wait_for(coro, timeout=timeout)
                return await coro
        except asyncio.TimeoutError:
            logger.error("Adaptive timeout triggered for coroutine.")
            raise

    @staticmethod
    def run_coroutine(coro: Coroutine, timeout: Optional[float] = None) -> Any:
        """Runs a coroutine safely, managing the loop and optional timeouts."""
        wrapped_coro = AsyncRuntimeManager.run_with_backpressure(coro, timeout)
        try:
            loop = asyncio.get_running_loop()
            return asyncio.create_task(wrapped_coro)
        except RuntimeError:
            pass

        loop = AsyncRuntimeManager.get_safe_loop()
        try:
            return loop.run_until_complete(wrapped_coro)
        except Exception as e:
            logger.error(f"Error running coroutine: {e}")
            raise

    @staticmethod
    def cleanup_orphaned_tasks(loop: asyncio.AbstractEventLoop):
        """Cancels all pending tasks in the given loop."""
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                loop.run_until_complete(task)

def get_safe_loop() -> asyncio.AbstractEventLoop:
    return AsyncRuntimeManager.get_safe_loop()
