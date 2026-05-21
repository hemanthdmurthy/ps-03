import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

logger = logging.getLogger("company_intel.middleware.cors")

def setup_cors(app: FastAPI):
    """
    Configures robust CORS middleware on the FastAPI app.
    Supports local, staging, and production frontends securely.
    Rejects unknown origins and prints highly-detailed warnings in logs.
    """
    # 1. Parse allowed origins from environment (comma-separated)
    origins_str = settings.CORS_ALLOWED_ORIGINS or ""
    allowed_origins = [orig.strip() for orig in origins_str.split(",") if orig.strip()]
    
    # Ensure settings.FRONTEND_URL is explicitly included if configured
    if settings.FRONTEND_URL:
        frontend_url = settings.FRONTEND_URL.strip()
        if frontend_url and frontend_url not in allowed_origins:
            allowed_origins.append(frontend_url)
            
    # Include default safe fallbacks if none are loaded
    if not allowed_origins:
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173"
        ]

    # 2. Determine environment and enforce safety policies
    is_prod = settings.NODE_ENV == "production" or settings.ENVIRONMENT == "production"
    
    # Wildcard '*' is NOT allowed in production with credentials
    if is_prod and "*" in allowed_origins:
        logger.warning("[CORS Security] Wildcard '*' detected in allowed origins for production with credentials enabled. Stripping wildcard for safety!")
        allowed_origins = [o for o in allowed_origins if o != "*"]

    logger.info(f"[CORS Initialization] Configured Allowed Origins: {allowed_origins}")

    # 3. Add Custom CORS Security Interceptor Middleware
    # Intercepts requests, logs blocked origins in detail, and returns a safe HTTP 400 response.
    @app.middleware("http")
    async def cors_security_interceptor(request: Request, call_next):
        origin = request.headers.get("origin")
        
        # If there is no Origin header, it's not a browser CORS request; let it pass safely.
        if not origin:
            return await call_next(request)
            
        # Check if origin is allowed
        # (In dev/staging only, if wildcard '*' exists, we allow all origins)
        allow_all = "*" in allowed_origins and not is_prod
        
        if allow_all or origin in allowed_origins:
            return await call_next(request)
        else:
            # Blocked origin - Log detailed system telemetry
            logger.warning(
                f"🚨 [CORS BLOCKED] Unauthorized cross-origin request detected! "
                f"Origin: '{origin}', "
                f"Path: '{request.url.path}', "
                f"Method: '{request.method}', "
                f"Client IP: '{request.client.host if request.client else 'unknown'}'"
            )
            return Response(
                content=f"CORS request blocked: Origin '{origin}' is not authorized.",
                status_code=400,
                media_type="text/plain"
            )

    # 4. Mount standard CORSMiddleware with credentials support
    # Standardize HTTP methods & headers allowed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins if not ("*" in allowed_origins) else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
            "Cookie",
            "token"
        ],
        expose_headers=["Content-Length", "X-Request-ID"],
        max_age=600,  # 10 minutes cache for preflight OPTIONS requests
    )

