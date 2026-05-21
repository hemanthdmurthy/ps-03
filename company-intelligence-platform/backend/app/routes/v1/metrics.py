import logging
import uuid
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from app.services.db import db_service

logger = logging.getLogger("company_intel.routes.metrics")

router = APIRouter(prefix="/tokens")

@router.get("/metrics", tags=["Metrics"])
async def get_token_metrics():
    """Returns high-level token and cost metrics for the dashboard."""
    try:
        metrics = await db_service.aget_token_dashboard_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error fetching token metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs", tags=["Metrics"])
async def get_token_logs(limit: int = 50):
    """Returns the most recent token usage logs, falling back to mock data when DB is empty."""
    import datetime
    try:
        # ── Primary: query directly from SQLAlchemy async session ─────────
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models import TokenUsageLog
        from app.services.db import to_dict

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(TokenUsageLog)
                .order_by(TokenUsageLog.created_at.desc())
                .limit(limit)
            )
            logs = result.scalars().all()

            if logs:
                return [to_dict(log) for log in logs]

        # ── Fallback: return mock data when table is empty ─────────────────
        now = datetime.datetime.now()
        return [
            {
                "id": str(uuid.uuid4()),
                "company_name": "NVIDIA Corporation",
                "domain_name": "Market Intelligence",
                "model_name": "gpt-4o",
                "total_tokens": 12450,
                "estimated_cost": 0.1245,
                "execution_time_ms": 1450,
                "status": "success",
                "created_at": (now - datetime.timedelta(minutes=5)).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "company_name": "OpenAI Inc",
                "domain_name": "Tech Stack Audit",
                "model_name": "claude-3-opus",
                "total_tokens": 8200,
                "estimated_cost": 0.2460,
                "execution_time_ms": 3200,
                "status": "success",
                "created_at": (now - datetime.timedelta(minutes=15)).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "company_name": "Stripe",
                "domain_name": "Executive Mapping",
                "model_name": "gemini-1.5-pro",
                "total_tokens": 5400,
                "estimated_cost": 0.0540,
                "execution_time_ms": 1100,
                "status": "success",
                "created_at": (now - datetime.timedelta(minutes=45)).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "company_name": "Ather Energy",
                "domain_name": "Risk Assessment",
                "model_name": "gpt-4o",
                "total_tokens": 15600,
                "estimated_cost": 0.1560,
                "execution_time_ms": 2100,
                "status": "warning",
                "created_at": (now - datetime.timedelta(hours=2)).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "company_name": "Razorpay",
                "domain_name": "Funding & Financials",
                "model_name": "mistral-large",
                "total_tokens": 3200,
                "estimated_cost": 0.0120,
                "execution_time_ms": 850,
                "status": "success",
                "created_at": (now - datetime.timedelta(hours=4)).isoformat()
            }
        ]
    except Exception as e:
        logger.error(f"Error fetching token logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
