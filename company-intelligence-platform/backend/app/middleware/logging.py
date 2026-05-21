import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from loguru import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles centralized structured logging for all HTTP requests.
    Tracks endpoints, execution time, and response status codes with Loguru.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Bind context to keep structured logging uniform
        log_context = logger.bind(
            category="access",
            request_id=request_id,
            client_host=client_host,
            method=method,
            path=path
        )

        log_context.info(f"HTTP {method} {path} - Initiated from {client_host}")

        try:
            response = await call_next(request)
            start_time = getattr(request.state, "start_time", None)
            duration = (time.time() - start_time) if start_time else 0.0

            # Enrich context with response metrics
            response_log_context = log_context.bind(
                status_code=response.status_code,
                duration=round(duration, 4)
            )

            log_msg = f"HTTP {method} {path} - {response.status_code} in {duration:.4f}s"
            if response.status_code >= 500:
                response_log_context.error(log_msg)
            elif response.status_code >= 400:
                response_log_context.warning(log_msg)
            else:
                response_log_context.info(log_msg)

            return response

        except Exception as exc:
            start_time = getattr(request.state, "start_time", None)
            duration = (time.time() - start_time) if start_time else 0.0
            
            log_context.bind(
                duration=round(duration, 4)
            ).opt(exception=exc).error(
                f"HTTP {method} {path} - Exception encountered after {duration:.4f}s: {exc}"
            )
            raise exc
