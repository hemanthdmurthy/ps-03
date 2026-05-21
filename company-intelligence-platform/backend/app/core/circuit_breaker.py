import logging
import time
from typing import Callable, Any
from functools import wraps
from app.core.redis_client import redis_client

logger = logging.getLogger("company_intel.core.circuit_breaker")

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """
    Distributed Circuit Breaker backed by Redis.
    Prevents cascading failures by short-circuiting calls to a failing external service.
    """
    def __init__(self, service_name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_key = f"cb:failures:{self.service_name}"
        self.state_key = f"cb:state:{self.service_name}"
        
    def _get_state(self):
        # Default state is closed
        try:
            state = redis_client.safe_execute_sync(redis_client.sync_client.get, self.state_key)
            return state or "closed"
        except Exception:
            return "closed"
            
    def _record_failure(self):
        try:
            fails = redis_client.safe_execute_sync(redis_client.sync_client.incr, self.failure_key)
            redis_client.safe_execute_sync(redis_client.sync_client.expire, self.failure_key, self.recovery_timeout * 2)
            if fails >= self.failure_threshold:
                self._open_circuit()
        except Exception as e:
            logger.error(f"Failed to record circuit breaker failure: {e}")

    def _open_circuit(self):
        logger.critical(f"[Circuit Breaker] OPENED for {self.service_name}! Short-circuiting traffic.")
        try:
            redis_client.safe_execute_sync(redis_client.sync_client.setex, self.state_key, self.recovery_timeout, "open")
        except Exception:
            pass

    def _reset(self):
        logger.info(f"[Circuit Breaker] CLOSED for {self.service_name}. Traffic flowing normally.")
        try:
            redis_client.safe_execute_sync(redis_client.sync_client.delete, self.state_key)
            redis_client.safe_execute_sync(redis_client.sync_client.delete, self.failure_key)
        except Exception:
            pass

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            state = self._get_state()
            if state == "open":
                raise CircuitBreakerOpenException(f"Circuit Breaker for {self.service_name} is OPEN.")
                
            try:
                result = func(*args, **kwargs)
                self._reset()
                return result
            except Exception as e:
                self._record_failure()
                raise e
        return wrapper

    async def async_call(self, func: Callable, *args, **kwargs) -> Any:
        state = self._get_state()
        if state == "open":
            raise CircuitBreakerOpenException(f"Circuit Breaker for {self.service_name} is OPEN.")
            
        try:
            result = await func(*args, **kwargs)
            self._reset()
            return result
        except Exception as e:
            self._record_failure()
            raise e
