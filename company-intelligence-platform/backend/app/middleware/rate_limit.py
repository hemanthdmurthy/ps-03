import time
import logging
import uuid
from collections import defaultdict
from threading import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("company_intel.middleware.rate_limit")

class RateLimiter:
    def __init__(self, requests_per_minute: int = 120):
        self.requests_per_minute = requests_per_minute
        self.history = defaultdict(list)
        self.lock = Lock()

    def check_rate_limit(self, key: str) -> tuple[bool, int]:
        """
        Checks if the request is permitted for the given key under sliding window rules.
        Returns:
            (is_allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        cutoff = now - 60.0

        with self.lock:
            # Purge requests older than 1 minute
            self.history[key] = [t for t in self.history[key] if t > cutoff]

            if len(self.history[key]) < self.requests_per_minute:
                self.history[key].append(now)
                return True, 0
            else:
                # Determine seconds remaining until a slot frees up
                oldest_timestamp = self.history[key][0]
                retry_after = int(60.0 - (now - oldest_timestamp))
                return False, max(1, retry_after)

# Instantiate a global rate limiter
global_rate_limiter = RateLimiter(requests_per_minute=120)

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Thread-safe sliding window rate limiting middleware.
    Keyed by authenticated username (if logged in) or client IP address.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        # Bypass rate limiting for health checks and documentation static assets
        if path in {"/", "/health", "/api/health", "/api/v1/health", "/docs", "/redoc", "/openapi.json"} or path.startswith("/docs/") or path.startswith("/redoc/"):
            return await call_next(request)

        # Determine the unique rate limiting key
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "username"):
            key = f"user:{user.username}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"ip:{client_ip}"

        allowed, retry_after = global_rate_limiter.check_rate_limit(key)

        if not allowed:
            logger.warning(f"Rate limit exceeded for key: {key} (Retry after: {retry_after}s)")

            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            from datetime import datetime

            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down and try again later.",
                        "details": {
                            "retry_after_seconds": retry_after,
                            "limit_per_minute": global_rate_limiter.requests_per_minute
                        }
                    },
                    "meta": {
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
            response.headers["Retry-After"] = str(retry_after)
            return response

        return await call_next(request)
