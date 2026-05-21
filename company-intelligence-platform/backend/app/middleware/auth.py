import logging
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.database import SessionLocal
from app.models.user import User
from app.utils.jwt_helper import decode_token

logger = logging.getLogger("company_intel.middleware.auth")

PUBLIC_PATHS = {
    "/",
    "/health",
    "/api/health",
    "/api/v1/health",
    "/info",
    "/api/info",
    "/api/v1/info",
    "/api/auth/login",
    "/api/v1/auth/login",
    "/api/auth/register",
    "/api/v1/auth/register",
    "/api/auth/refresh",
    "/api/v1/auth/refresh",
    "/api/research",
    "/api/v1/research",
    "/api/session",
    "/api/v1/session",
    "/api/tokens",
    "/api/v1/tokens",
    "/api/remediation",
    "/api/v1/remediation",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1",
    "/api/v1/",
    "/api",
    "/api/",
    "/placement-agent",
    "/api/v1/placement-agent",
    "/api/placement-agent"
}

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Global authentication middleware.
    Validates JWT access tokens for protected routes and attaches the user to the request state.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        # Preflight requests (OPTIONS) bypass authentication checks
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        # Determine if the route is public
        is_public = False
        if path in PUBLIC_PATHS:
            is_public = True
        else:
            for public_path in PUBLIC_PATHS:
                if public_path in {"/api/v1", "/api/v1/", "/api", "/api/"}:
                    continue
                if path.startswith(public_path + "/"):
                    is_public = True
                    break

        auth_header = request.headers.get("Authorization")
        token = None

        if auth_header:
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            else:
                # If a token is provided but format is invalid on a protected route
                if not is_public:
                    return self._error_response(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token format. Use 'Bearer <token>'"
                    )

        # Enforce authentication for protected routes if token is missing
        if not is_public and not token:
            return self._error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials are required"
            )

        request.state.user = None

        if token:
            try:
                # Decode the access token
                payload = decode_token(token, is_refresh=False)
                username = payload.get("sub")
                token_type = payload.get("type")

                if not username or token_type != "access":
                    if not is_public:
                        return self._error_response(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token claims"
                        )
                else:
                    # Optimize by checking Redis session cache first
                    from app.services.cache_service import cache_service
                    from datetime import datetime
                    
                    user = None
                    try:
                        user_data = await cache_service.get(f"session:{username}")
                        if user_data:
                            # Rehydrate cached dictionary into detached User model instance
                            user = User(
                                id=user_data["id"],
                                username=user_data["username"],
                                email=user_data["email"],
                                role=user_data["role"],
                                is_active=user_data["is_active"]
                            )
                            if user_data.get("created_at"):
                                user.created_at = datetime.fromisoformat(user_data["created_at"])
                            if user_data.get("updated_at"):
                                user.updated_at = datetime.fromisoformat(user_data["updated_at"])
                    except Exception as e:
                        logger.warning(f"Error reading user session cache: {e}")

                    if not user:
                        # Fallback to Database query
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter(User.username == username).first()
                            if user:
                                try:
                                    # Cache the user record for 10 minutes (600 seconds)
                                    await cache_service.set(f"session:{username}", user.to_dict(), ttl=600)
                                except Exception as e:
                                    logger.warning(f"Failed to cache user session: {e}")
                        finally:
                            db.close()

                    if user:
                        if not user.is_active:
                            if not is_public:
                                return self._error_response(
                                    status_code=status.HTTP_403_FORBIDDEN,
                                    detail="User account is inactive"
                                )
                        else:
                            # Successfully authenticated, attach to state
                            request.state.user = user
                    else:
                        if not is_public:
                            return self._error_response(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="User associated with token not found"
                            )

            except JWTError as e:
                logger.warning(f"JWT verification failed: {e}")
                if not is_public:
                    return self._error_response(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token is invalid or has expired"
                    )
            except Exception as e:
                logger.error(f"Error resolving user: {e}", exc_info=True)
                if not is_public:
                    return self._error_response(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Internal server error verifying credentials"
                    )

        # Move to next handler
        return await call_next(request)

    def _error_response(self, status_code: int, detail: str) -> JSONResponse:
        """Helper to return standardized error JSON directly from middleware."""
        from datetime import datetime
        import uuid

        # Standardized shape matching exception handlers
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": "AUTHENTICATION_ERROR" if status_code == 401 else "AUTHORIZATION_ERROR" if status_code == 403 else "INTERNAL_SERVER_ERROR",
                    "message": detail,
                    "details": None
                },
                "meta": {
                    "request_id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
