# app/routes/__init__.py
from fastapi import APIRouter

# Import the unified V1 router
from app.routes.v1 import v1_router

# Import individual V1 sub-routers for prefix mounting (avoids duplication and maintains precise control)
from app.routes.v1.health import router as health_router
from app.routes.v1.research import router as research_router
from app.routes.v1.metrics import router as metrics_router
from app.routes.v1.auth_routes import router as auth_router
from app.routes.v1.user_routes import router as user_router
from app.routes.v1.student_routes import router as student_router
from app.routes.v1.skill_routes import router as skill_router
from app.routes.v1.company_routes import router as company_router
from app.routes.v1.placement_routes import router as placement_router
from app.routes.v1.analytics_routes import router as analytics_router
from app.routes.v1.admin_routes import router as admin_router
from app.routes.v1.notification_routes import router as notification_router
from app.routes.v1.remediation_routes import router as remediation_router
from app.routes.v1.websocket_routes import router as websocket_router
from app.routes.ai_routes import router as ai_router

# Root router for the application
api_router = APIRouter()

# 1. Health checks at root level (e.g. /, /health, /metrics)
api_router.include_router(health_router)

# 2. Versioned API routes prefixed with /api/v1/
api_router.include_router(health_router, prefix="/api/v1")
api_router.include_router(research_router, prefix="/api/v1")
api_router.include_router(metrics_router, prefix="/api/v1")
api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(user_router, prefix="/api/v1")
api_router.include_router(student_router, prefix="/api/v1")
api_router.include_router(skill_router, prefix="/api/v1")
api_router.include_router(company_router, prefix="/api/v1")
api_router.include_router(placement_router, prefix="/api/v1")
api_router.include_router(analytics_router, prefix="/api/v1")
api_router.include_router(admin_router, prefix="/api/v1")
api_router.include_router(notification_router, prefix="/api/v1")
api_router.include_router(remediation_router, prefix="/api/v1")
api_router.include_router(websocket_router, prefix="/api/v1")
api_router.include_router(ai_router, prefix="/api/v1")

# 3. Backward Compatibility: Mount exact same routers directly under /api/ prefix
# This prevents breaking existing frontend requests and external integrations
api_router.include_router(health_router, prefix="/api")
api_router.include_router(research_router, prefix="/api")
api_router.include_router(metrics_router, prefix="/api")
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(user_router, prefix="/api")
api_router.include_router(student_router, prefix="/api")
api_router.include_router(skill_router, prefix="/api")
api_router.include_router(company_router, prefix="/api")
api_router.include_router(placement_router, prefix="/api")
api_router.include_router(analytics_router, prefix="/api")
api_router.include_router(admin_router, prefix="/api")
api_router.include_router(notification_router, prefix="/api")
api_router.include_router(remediation_router, prefix="/api")
api_router.include_router(websocket_router, prefix="/api")
api_router.include_router(ai_router, prefix="/api")
