# app/routes/v1/__init__.py
from fastapi import APIRouter

# Import versioned route modules
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

# Unified APIRouter for API version 1
v1_router = APIRouter()

# Grouping and mounting V1 routes with their respective tags/prefixes
v1_router.include_router(health_router)
v1_router.include_router(research_router)
v1_router.include_router(metrics_router)
v1_router.include_router(auth_router)
v1_router.include_router(user_router)
v1_router.include_router(student_router)
v1_router.include_router(skill_router)
v1_router.include_router(company_router)
v1_router.include_router(placement_router)
v1_router.include_router(analytics_router)
v1_router.include_router(admin_router)
v1_router.include_router(notification_router)
v1_router.include_router(remediation_router)
v1_router.include_router(websocket_router)

