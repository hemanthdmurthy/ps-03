# app/middleware/prometheus.py
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from app.core.metrics import track_api_request

logger = logging.getLogger("company_intel.middleware.prometheus")

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records core Prometheus metrics for every FastAPI endpoint.
    Tracks:
    - Request total count categorized by method, path, and status code.
    - Request duration histogram categorized by method and path.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        
        # Bypass recording endpoints related to scrape/health metrics to avoid self-referencing loops
        if (
            path in {"/metrics", "/health", "/api/health", "/docs", "/redoc", "/openapi.json"}
            or path.startswith("/docs/")
            or path.startswith("/redoc/")
        ):
            return await call_next(request)

        method = request.method
        start_time = time.time()
        
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            # Re-raise exceptions while ensuring they are categorized as server error (500)
            status_code = 500
            raise e
        finally:
            duration = time.time() - start_time
            track_api_request(
                method=method,
                endpoint=path,
                status_code=status_code,
                duration=duration
            )
