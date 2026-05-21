import json
import logging
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

logger = logging.getLogger("company_intel.middleware.response_formatter")

class StandardResponseMiddleware(BaseHTTPMiddleware):
    """
    Middleware that standardizes successful JSON responses by wrapping them
    in a uniform success envelope with tracking metadata.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Bypass for health checks, documentation, non-JSON formats, and active SSE streams
        path = request.url.path
        content_type = response.headers.get("content-type", "")

        is_bypass = (
            path in {
                "/",
                "/health", "/api/health", "/api/v1/health",
                "/info", "/api/info", "/api/v1/info",
                "/docs", "/redoc", "/openapi.json",
                "/api/v1", "/api/v1/", "/api", "/api/"
            }
            or path.startswith("/docs/")
            or path.startswith("/redoc/")
            or path == "/placement-agent"
            or path.startswith("/placement-agent/")
            or "text/event-stream" in content_type
            or "application/json" not in content_type
        )

        if not is_bypass:
            for prefix in [
                "/api/research", "/api/v1/research",
                "/api/session", "/api/v1/session",
                "/api/tokens", "/api/v1/tokens",
                "/api/remediation", "/api/v1/remediation"
            ]:
                if path.startswith(prefix):
                    is_bypass = True
                    break

        if is_bypass:
            return response

        # Standardize successful outcomes (errors are handled by exception handlers)
        if response.status_code < 400:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            try:
                data = json.loads(body.decode("utf-8"))

                # Assert if already enveloped in standardized response format
                if isinstance(data, dict) and "success" in data and ("data" in data or "error" in data):
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type="application/json"
                    )

                # Standard wrapper
                request_id = getattr(request.state, "request_id", None)

                formatted_body = {
                    "success": True,
                    "data": data,
                    "meta": {
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }

                new_body = json.dumps(formatted_body).encode("utf-8")

                # Construct headers
                headers = dict(response.headers)
                headers["content-length"] = str(len(new_body))

                return Response(
                    content=new_body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type="application/json"
                )

            except Exception as e:
                logger.warning(f"Could not wrap JSON response, returning raw content: {e}")
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json"
                )

        return response
