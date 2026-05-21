import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

logger = logging.getLogger("company_intel.middleware.request_tracking")

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique Request ID to each incoming request.
    This facilitates end-to-end request tracing, logging, and error tracking.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        # Check if the client or proxy passed an existing request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Attach tracking metadata to request state
        request.state.request_id = request_id
        request.state.start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Compute total process duration
        process_time = time.time() - request.state.start_time

        # Expose tracing headers in the HTTP response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.6f}s"

        return response
