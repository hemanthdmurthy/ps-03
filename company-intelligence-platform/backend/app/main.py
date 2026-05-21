import logging
from fastapi import FastAPI

from app.core.config import settings
from app.utils.logging_util import configure_logging
from app.middleware import (
    setup_cors,
    RequestTrackingMiddleware,
    RequestLoggingMiddleware,
    AuthenticationMiddleware,
    RateLimitingMiddleware,
    StandardResponseMiddleware,
    setup_exception_handlers,
    PrometheusMiddleware,
    RequestValidationMiddleware
)
from app.routes import api_router

# Setup Logging
configure_logging()
logger = logging.getLogger("company_intel.main")

# Run Self-Healing Port Validation
from app.utils.port_validator import execute_pre_startup_check
execute_pre_startup_check()

# Initialize FastAPI App
app = FastAPI(
    title="Placement Intel Portal API",
    version="1.0.0",
    description="Modular, production-grade, stateful Multi-Agent Orchestrator backend pipeline."
)

# Setup CORS Middleware
setup_cors(app)

# Register custom production middlewares in execution order:
# Prometheus -> RequestTracking -> RequestValidation -> RequestLogging -> Authentication -> RateLimiting -> StandardResponse
app.add_middleware(StandardResponseMiddleware)
app.add_middleware(RateLimitingMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RequestTrackingMiddleware)
app.add_middleware(PrometheusMiddleware)


# Setup Centralized Exception Handling
setup_exception_handlers(app)

# Include Modular API Routers
app.include_router(api_router)
from app.routes.v1.websocket_routes import router as websocket_router
app.include_router(websocket_router)

# Explicitly mount the Enterprise AI Router to ensure prefix /api/v1 routing consistency
from app.routes.ai_routes import router as ai_router
app.include_router(ai_router, prefix="/api/v1")

# Mount LangGraph Workflow using LangServe
logger.info("[Startup] Initiating LangGraph import and compilation checks...")
try:
    # Check for circular imports or graph import failures
    from app.graphs.placement_graph import graph
    logger.info("[Startup] LangGraph import and compile verification: Success.")
    
    # Verify schema generation
    input_schema = graph.input_schema
    output_schema = graph.output_schema
    config_schema = graph.config_schema
    logger.info("[Startup] LangGraph schema verification: Success.")
except Exception as e:
    logger.exception("[Startup] LangGraph import/compilation check failed (potential circular import or initialization issue)")
    raise e

try:
    from langserve import add_routes
    logger.info("[Startup] LangServe module successfully imported.")
    
    # Mount LangServe routes
    add_routes(
        app,
        graph,
        path="/placement-agent"
    )
    logger.info("[LangServe] LangServe mounted successfully at /placement-agent")
except Exception as e:
    logger.exception("[LangServe] LangServe mount failed")
    raise e



# Globally keep a reference to the Redis Pub/Sub notification manager
from app.core.redis_pubsub import pubsub_manager
from app.services.websocket_event_handlers import register_all_handlers
from app.utils.websocket_manager import manager as ws_manager

@app.on_event("startup")
async def startup_services():
    """Initializes standard cache services, launches cross-instance Redis Pub/Sub, and manages active connection stale sweepers."""
    # 0. Run automated database schema reconciliation
    # Moved to prestart.sh and CI/CD pipelines to prevent Uvicorn blocking.
    pass

    from app.services.cache_service import cache_service
    from app.core.redis_client import redis_client

    
    # 1. Initialize Resilient Redis connection & Cache
    # Fail-fast check: refuse startup in non-testing environments if critical Redis connection fails
    # Only hard-fail on Redis in production. In development/testing, degrade to FakeRedis.
    raise_on_fail = settings.ENVIRONMENT == "production"
    await cache_service.initialize(raise_on_fail=raise_on_fail)
    
    # Execute startup lock validation and auto-healing sweeper
    try:
        from app.services.redis_service import redis_service
        await redis_service.cleanup_corrupted_locks()
    except Exception as cleanup_err:
        logger.error(f"[Startup Cleanup] Failed to run lock auto-healing sweeper: {cleanup_err}")
    
    # Print startup diagnostics
    stats = redis_client.stats
    logger.info("=" * 60)
    logger.info("📡 [REDIS STARTUP DIAGNOSTICS]")
    logger.info(f"   Host:             {stats.get('host')}")
    logger.info(f"   Active Port:      {stats.get('port')}")
    logger.info(f"   In Docker:        {stats.get('in_docker')}")
    logger.info(f"   Fallback Mode:    {stats.get('is_fallback')} (FakeRedis)")
    logger.info(f"   Initialization:   {'SUCCESS' if stats.get('is_initialized') else 'FAILED'}")
    logger.info(f"   Retry attempts:   {stats.get('reconnect_attempts')}")
    if stats.get('last_error'):
        logger.info(f"   Last Error:       {stats.get('last_error')}")
    logger.info("=" * 60)
    
    # 2. Initialize and spin up scalable Redis Pub/Sub WS Listener
    if cache_service.enabled:
        pubsub_initialized = await pubsub_manager.initialize()
        if pubsub_initialized:
            await register_all_handlers(pubsub_manager)
            await pubsub_manager.start_listener()
            if redis_client.is_fallback:
                logger.info("[Redis WS Sync] Local FakeRedis Pub/Sub event bus active and running.")
            else:
                logger.info("[Redis WS Sync] Scalable Redis Pub/Sub event bus active and running.")
        else:
            logger.warning("[Redis WS Sync] Pub/Sub initialization failed. Falling back to single-instance WebSocket mode.")
            
    # 3. Start active WebSocket connections stale connections cleanup sweeper
    await ws_manager.start_cleanup_task()
    logger.info("[WebSocket Manager] Stale connection cleaner task successfully registered.")

@app.on_event("shutdown")
async def shutdown_services():
    """Shuts down connection pools, closes active Pub/Sub loops, cancels stale sweepers, and disposes database engines."""
    # 1. Stop active WebSocket connections sweeper
    await ws_manager.stop_cleanup_task()
    logger.info("[WebSocket Manager] Stale connection cleaner task terminated.")

    # 2. Shutdown Redis Pub/Sub Listener
    await pubsub_manager.shutdown()
    logger.info("[Redis WS Sync] Scalable Pub/Sub event bus shutdown successfully.")
            
    # 3. Shutdown standard cache connections
    from app.services.cache_service import cache_service
    await cache_service.close()
    
    # 4. Dispose async database engine for clean connection pool teardown
    from app.core.database import async_engine
    await async_engine.dispose()
    logger.info("Async database engine disposed successfully.")

    # 5. Flush and shutdown OpenTelemetry TracerProvider
    try:
        from app.core.telemetry import shutdown_telemetry
        shutdown_telemetry()
    except Exception as tel_err:
        logger.warning("[Shutdown] Telemetry shutdown error: %s", tel_err)


@app.on_event("startup")
async def seed_users():
    """
    On application startup, checks if the users database table is empty.
    If so, seeds default 'admin', 'researcher', and 'viewer' accounts for local dev onboarding.
    Uses async database session for non-blocking I/O.
    """
    if settings.ENVIRONMENT == "testing":
        logger.info("[Startup] Skipping user seeding in testing environment.")
        return
        
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal
    from app.models.user import User
    from app.utils.security import hash_password

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(func.count(User.id)))
            count = result.scalar() or 0
            if count == 0:
                logger.info("Database users table is empty. Seeding default accounts...")

                # 1. Seed Admin
                admin_user = User(
                    id="seed-admin-uuid-111",
                    username="admin",
                    email="admin@placementintel.com",
                    hashed_password=hash_password("admin123"),
                    role="admin",
                    is_active=True
                )

                # 2. Seed Researcher
                researcher_user = User(
                    id="seed-researcher-uuid-222",
                    username="researcher",
                    email="researcher@placementintel.com",
                    hashed_password=hash_password("researcher123"),
                    role="researcher",
                    is_active=True
                )

                # 3. Seed Viewer
                viewer_user = User(
                    id="seed-viewer-uuid-333",
                    username="viewer",
                    email="viewer@placementintel.com",
                    hashed_password=hash_password("viewer123"),
                    role="viewer",
                    is_active=True
                )

                db.add_all([admin_user, researcher_user, viewer_user])
                await db.commit()
                logger.info("[+] Default accounts ('admin', 'researcher', 'viewer') successfully seeded!")
            else:
                logger.info("Database users table already seeded.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to seed default accounts: {e}", exc_info=True)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title="Placement Intelligence Platform API",
        version="1.0.0",
        description="""# 🚀 Placement Intelligence Platform API

Welcome to the **Placement Intelligence Platform API** — a modular, enterprise-grade, stateful Multi-Agent Orchestrator backend system powering target market identification, continuous extraction audits, and automated verification loops.

---

## 🔒 Security & Authentication
This API enforces role-based access control (RBAC) and state-of-the-art **JWT (JSON Web Token) Bearer Authentication** with token rotation.

* **Authentication Endpoint**: `POST /api/v1/auth/login` yields an access token (JWT) and refresh token.
* **Accessing Protected Routes**: Provide the access token in the standard HTTP header:
  `Authorization: Bearer <your_jwt_access_token>`
* **Token Lifetime**: Access tokens are stateless, ephemeral keys. Refresh tokens support secure sliding-session rotation via `POST /api/v1/auth/refresh`.

---

## 📦 Standard Response Envelope
To guarantee robust client integration and structured payload tracking, all successful JSON API endpoints are standardized by the `StandardResponseMiddleware`:

```json
{
  "success": true,
  "data": { ... core response body ... },
  "meta": {
    "request_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "timestamp": "2026-05-18T05:56:32.123456Z"
  }
}
```

*Note: Health check, raw metrics, SSE streams, and static assets bypass the enveloping layer for low-latency compatibility.*

---

## 🛡️ Centrally Standardized Errors
All system failures, validation exceptions, database transaction aborts, or unauthorized requests are processed through centralized exception handlers to yield normalized error envelopes:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request parameters or body failed structural validation audits.",
    "details": [
      {
        "field": "email",
        "issue": "value_error.email",
        "message": "value is not a valid email address"
      }
    ]
  },
  "meta": {
    "request_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "timestamp": "2026-05-18T05:56:32.123456Z"
  }
}
```

---

## 👥 Role-Based Permission Matrix
| Role | Access Level | Responsibilities |
| :--- | :--- | :--- |
| **`admin`** | Full Authority | System-wide admin, HITL workflow overrides, user administration. |
| **`researcher`** | High Authority | Enriches companies, triggers background agents, reviews staging data. |
| **`viewer`** | Read Authority | Default role. Can view drives, student listings, analytics, and status dashboard. |""",
        routes=app.routes,
    )
    
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
        
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your JWT Access token (without 'Bearer ' prefix) to authorize requests."
    }
    
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
        
    openapi_schema["components"]["schemas"]["StandardResponseMeta"] = {
        "type": "object",
        "properties": {
            "request_id": {"type": "string", "example": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6", "description": "Unique request identifier for backend tracing"},
            "timestamp": {"type": "string", "format": "date-time", "example": "2026-05-18T05:56:32.123456Z", "description": "UTC timestamp when the response was processed"}
        },
        "required": ["request_id", "timestamp"]
    }
    
    openapi_schema["components"]["schemas"]["StandardErrorDetail"] = {
        "type": "object",
        "properties": {
            "field": {"type": "string", "example": "email", "description": "The specific request field that failed validation"},
            "issue": {"type": "string", "example": "value_error.email", "description": "The Pydantic issue type code"},
            "message": {"type": "string", "example": "value is not a valid email address", "description": "Human-friendly explanation of validation error"}
        },
        "required": ["field", "issue", "message"]
    }
    
    openapi_schema["components"]["schemas"]["StandardErrorBody"] = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "example": "VALIDATION_ERROR", "description": "Enterprise machine-readable error classification code"},
            "message": {"type": "string", "example": "Request parameters or body failed structural validation audits.", "description": "General description of the failure"},
            "details": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/StandardErrorDetail"},
                "description": "Granular, structured validation failures list if applicable"
            }
        },
        "required": ["code", "message"]
    }
    
    openapi_schema["components"]["schemas"]["StandardErrorResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": False, "description": "Always false for error outcomes"},
            "error": {"$ref": "#/components/schemas/StandardErrorBody"},
            "meta": {"$ref": "#/components/schemas/StandardResponseMeta"}
        },
        "required": ["success", "error", "meta"]
    }

    def is_bypassed_path(p: str) -> bool:
        if p in {
            "/",
            "/health", "/api/health", "/api/v1/health",
            "/info", "/api/info", "/api/v1/info",
            "/docs", "/redoc", "/openapi.json",
            "/api/v1", "/api/v1/", "/api", "/api/"
        }:
            return True
        if p == "/placement-agent" or p.startswith("/placement-agent/"):
            return True
        if p.endswith("/metrics") or "/metrics" in p:
            return True
        for prefix in [
            "/api/research", "/api/v1/research",
            "/api/session", "/api/v1/session",
            "/api/tokens", "/api/v1/tokens",
            "/api/remediation", "/api/v1/remediation"
        ]:
            if p.startswith(prefix):
                return True
        return False

    for path, path_item in openapi_schema.get("paths", {}).items():
        is_secured = True
        
        if path in {"/", "/health", "/api/health", "/api/v1/health", "/metrics", "/api/metrics", "/api/v1/metrics"}:
            is_secured = False
        elif path == "/placement-agent" or path.startswith("/placement-agent/"):
            is_secured = False
        elif "/auth/login" in path or "/auth/register" in path or "/auth/refresh" in path:
            is_secured = False
            
        for method, operation in path_item.items():
            if is_secured:
                if "security" not in operation:
                    operation["security"] = []
                if not any("BearerAuth" in scheme for scheme in operation["security"]):
                    operation["security"].append({"BearerAuth": []})
            
            for status_code in ["400", "401", "403", "404", "422", "500"]:
                if not is_secured and status_code in ["401", "403"]:
                    continue
                operation["responses"][status_code] = {
                    "description": f"Standard {status_code} Error response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/StandardErrorResponse"}
                        }
                    }
                }

            if not is_bypassed_path(path):
                for success_code in ["200", "201", "202"]:
                    if success_code in operation["responses"]:
                        response_obj = operation["responses"][success_code]
                        if "content" in response_obj and "application/json" in response_obj["content"]:
                            original_schema = response_obj["content"]["application/json"].get("schema")
                            if original_schema:
                                schema_name = None
                                if "$ref" in original_schema:
                                    schema_name = original_schema["$ref"].split("/")[-1]
                                
                                if schema_name:
                                    wrapped_name = f"StandardResponse_{schema_name}"
                                    if wrapped_name not in openapi_schema["components"]["schemas"]:
                                        openapi_schema["components"]["schemas"][wrapped_name] = {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean", "example": True, "description": "Always true for successful outcomes"},
                                                "data": {"$ref": f"#/components/schemas/{schema_name}"},
                                                "meta": {"$ref": "#/components/schemas/StandardResponseMeta"}
                                            },
                                            "required": ["success", "data", "meta"]
                                        }
                                    response_obj["content"]["application/json"]["schema"] = {
                                        "$ref": f"#/components/schemas/{wrapped_name}"
                                    }
                                else:
                                    if original_schema.get("type") == "array" and "items" in original_schema:
                                        items = original_schema["items"]
                                        if "$ref" in items:
                                            item_name = items["$ref"].split("/")[-1]
                                            wrapped_name = f"StandardResponse_List_{item_name}"
                                            if wrapped_name not in openapi_schema["components"]["schemas"]:
                                                openapi_schema["components"]["schemas"][wrapped_name] = {
                                                    "type": "object",
                                                    "properties": {
                                                        "success": {"type": "boolean", "example": True, "description": "Always true for successful outcomes"},
                                                        "data": {
                                                            "type": "array",
                                                            "items": {"$ref": f"#/components/schemas/{item_name}"}
                                                        },
                                                        "meta": {"$ref": "#/components/schemas/StandardResponseMeta"}
                                                    },
                                                    "required": ["success", "data", "meta"]
                                                }
                                            response_obj["content"]["application/json"]["schema"] = {
                                                "$ref": f"#/components/schemas/{wrapped_name}"
                                            }
                                            continue
                                            
                                    wrapped_inline = {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean", "example": True, "description": "Always true for successful outcomes"},
                                            "data": original_schema,
                                            "meta": {"$ref": "#/components/schemas/StandardResponseMeta"}
                                        },
                                        "required": ["success", "data", "meta"]
                                    }
                                    response_obj["content"]["application/json"]["schema"] = wrapped_inline

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ═══════════════════════════════════════════════════════════════════════════
# TELEMETRY INITIALIZATION (fault-tolerant — never crashes startup)
# ═══════════════════════════════════════════════════════════════════════════
try:
    from app.core.database import async_engine
    from app.core.telemetry import (
        setup_telemetry, shutdown_telemetry,
        TELEMETRY_AVAILABLE, get_telemetry_status,
    )

    # ── Startup validation: log telemetry config snapshot ──
    logger.info("=" * 60)
    logger.info("[Telemetry] Startup validation")
    logger.info("  OTEL_ENABLED:                 %s", settings.OTEL_ENABLED)
    logger.info("  OTEL_EXPORTER_OTLP_ENDPOINT:  %s", settings.OTEL_EXPORTER_OTLP_ENDPOINT or "(empty/disabled)")
    logger.info("  OTEL_JAEGER_ENDPOINT:          %s", settings.OTEL_JAEGER_ENDPOINT or "(empty/disabled)")
    logger.info("  OTEL_SERVICE_NAME:             %s", settings.OTEL_SERVICE_NAME)
    logger.info("  OTEL_EXPORT_CONSOLE:           %s", settings.OTEL_EXPORT_CONSOLE)
    logger.info("  TELEMETRY_AVAILABLE:           %s", TELEMETRY_AVAILABLE)
    logger.info("=" * 60)

    if TELEMETRY_AVAILABLE:
        setup_telemetry(app=app, engine=async_engine.sync_engine)
        # Emit post-init diagnostics
        tel_status = get_telemetry_status()
        if tel_status.get("initialized"):
            exporter_info = tel_status.get("exporter")
            if exporter_info:
                logger.info("[Telemetry] Exporter active: %s", exporter_info.get("exporter", "unknown"))
            else:
                logger.info("[Telemetry] Running in silent degradation mode (no exporter).")
    else:
        logger.warning(
            "[Telemetry] OpenTelemetry dependencies not installed. "
            "Distributed tracing disabled."
        )
except Exception as telemetry_err:
    logger.warning(
        "[Telemetry] Initialization failed: %s. "
        "Backend continuing without distributed tracing.",
        telemetry_err
    )

logger.info("FastAPI backend application successfully initialized.")

if __name__ == "__main__":
    import uvicorn
    # Start uvicorn server mapping to settings port
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
