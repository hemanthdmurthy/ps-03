import uuid
from datetime import datetime
from fastapi import Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

def format_error_response(status_code: int, code: str, message: str, details: any, request_id: str) -> JSONResponse:
    """Helper to return standardized error JSON bodies."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handles Pydantic validation errors.
    Returns standard error codes with specific structural validation details.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # Structure Pydantic errors neatly
    error_details = []
    for err in exc.errors():
        field_path = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        error_details.append({
            "field": field_path or "request_body",
            "issue": err.get("type"),
            "message": err.get("msg")
        })

    logger.bind(
        category="access",
        request_id=request_id,
        path=request.url.path,
        error_details=error_details
    ).warning(f"Validation failed for request to {request.url.path}: {exc}")

    return format_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request parameters or body failed structural validation audits.",
        details=error_details,
        request_id=request_id
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handles standard HTTP exceptions raised manually within the routes.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    # Map code depending on status code
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "TOO_MANY_REQUESTS"
    }
    code = code_map.get(exc.status_code, "HTTP_EXCEPTION")

    # If the exception is auth related, categorize as auth
    category = "access"
    if exc.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN) or "auth" in request.url.path:
        category = "auth"

    logger.bind(
        category=category,
        request_id=request_id,
        status_code=exc.status_code,
        path=request.url.path
    ).warning(f"HTTP exception {exc.status_code} raised on {request.url.path}: {exc.detail}")

    return format_error_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail),
        details=None,
        request_id=request_id
    )

async def db_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Catches all SQLAlchemy database errors to protect sensitive connection or structural tracebacks.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.bind(
        category="system",
        request_id=request_id,
        path=request.url.path
    ).opt(exception=exc).error(f"Database Exception on {request.url.path}: {exc}")

    return format_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="DATABASE_ERROR",
        message="A database persistence or retrieval transaction failed. Please contact administrators.",
        details=None,
        request_id=request_id
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global catch-all for any unhandled thread exceptions or internal logical crashes.
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.bind(
        category="system",
        request_id=request_id,
        path=request.url.path
    ).opt(exception=exc).error(f"Unhandled crash on {request.url.path}: {exc}")

    return format_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected system anomaly was intercepted. Reference the Request ID for debugging.",
        details=None,
        request_id=request_id
    )

def setup_exception_handlers(app):
    """
    Utility function to register exception handlers to the FastAPI app.
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, db_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
