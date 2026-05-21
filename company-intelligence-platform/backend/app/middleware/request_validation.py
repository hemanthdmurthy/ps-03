# app/middleware/request_validation.py
"""
Request Validation & Payload Audit Middleware
==============================================
Intercepts incoming HTTP requests to validate structure, content types, and payload size.
Protects the API against memory spikes, oversized JSON inputs, and bad encodings.
"""

import logging
import uuid
from datetime import datetime
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("company_intel.middleware.validation")


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware that performs early structural and security validation
    on incoming API payloads before route execution.
    """
    def __init__(self, app, max_content_length: int = 5 * 1024 * 1024):  # Default: 5MB
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        # 1. Skip validation checks for local file/SSE streams, health probes, or metrics
        path = request.url.path
        if path.endswith("/stream") or "/health" in path or "/metrics" in path or path == "/":
            return await call_next(request)

        # 2. Enforce Strict Content-Length Validation
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length_bytes = int(content_length)
                if length_bytes > self.max_content_length:
                    logger.warning(
                        f"🚨 [Request Denied] Payload size {length_bytes} bytes exceeds the maximum "
                        f"limit of {self.max_content_length} bytes! "
                        f"Path: '{path}', IP: '{request.client.host if request.client else 'unknown'}'"
                    )
                    return Response(
                        content=f"Payload Too Large: Maximum allowed size is {self.max_content_length} bytes.",
                        status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
                        media_type="text/plain"
                    )
            except ValueError:
                return Response(
                    content="Invalid Content-Length header format.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    media_type="text/plain"
                )

        # 3. Enforce Strict Content-Type check on mutations (POST/PUT/PATCH)
        method = request.method
        if method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type") or ""
            # Only validate if there is a payload
            if content_length and int(content_length) > 0:
                if "application/json" not in content_type and "multipart/form-data" not in content_type:
                    logger.warning(
                        f"🚨 [Request Denied] Invalid content-type '{content_type}' for mutation request! "
                        f"Path: '{path}', Method: '{method}', IP: '{request.client.host if request.client else 'unknown'}'"
                    )
                    return Response(
                        content="Unsupported Media Type: Request must be 'application/json' or 'multipart/form-data'.",
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        media_type="text/plain"
                    )

        # 4. Check for encoding security
        try:
            # Touch query parameters to trigger early parsing and encoding verification
            _ = request.query_params
        except Exception as query_exc:
            logger.warning(f"🚨 [Request Denied] Malformed or invalid query parameter encoding. Error: {query_exc}")
            return Response(
                content="Bad Request: Query parameters contain invalid character encoding.",
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="text/plain"
            )

        # Allow execution to proceed to downstream route handlers
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Let general exception handlers do the mapping, but log it early
            logger.error(f"❌ [Request Validation Middleware] Downstream execution crash on {path}: {exc}", exc_info=True)
            raise exc
