import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.models.user import User
from app.models.staging_company import StagingCompany
from app.models.validation_run import ValidationCorrectionSuggestion

logger = logging.getLogger("company_intel.routes.remediation")

router = APIRouter(prefix="/remediation", tags=["AI Remediation & HITL Workflows (Frontend Compatible)"])

@router.get("/suggestions")
async def list_remediation_suggestions(db: AsyncSession = Depends(get_async_db)):
    """List AI self-healing correction suggestions formatted for frontend integration."""
    try:
        result = await db.execute(select(ValidationCorrectionSuggestion))
        suggestions = result.scalars().all()
        out = []
        for sugg in suggestions:
            company_name = "Unknown Company"
            # Load company name via explicit query (async-safe)
            if sugg.company_id:
                cr = await db.execute(select(StagingCompany.name).filter(StagingCompany.company_id == sugg.company_id))
                cname = cr.scalar()
                if cname:
                    company_name = cname
            out.append({
                "id": sugg.id, "company_id": sugg.company_id, "company_name": company_name,
                "field_name": sugg.field_name, "original_value": sugg.original_value,
                "suggested_value": sugg.suggested_value, "rationale": sugg.rationale,
                "confidence": sugg.confidence, "status": sugg.status, "source": sugg.source,
                "reviewed_by": sugg.reviewed_by,
                "reviewed_at": sugg.reviewed_at.isoformat() if sugg.reviewed_at else None,
                "created_at": sugg.created_at.isoformat() if sugg.created_at else None
            })
        return out
    except Exception as e:
        logger.error(f"Error fetching remediation suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve correction suggestions.")


@router.post("/suggestion/{suggestion_id}/{action}")
async def process_remediation_action(suggestion_id: str, action: str, db: AsyncSession = Depends(get_async_db)):
    """Approve or reject an AI-generated correction suggestion."""
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid action '{action}'. Action must be 'approve' or 'reject'.")
    r = await db.execute(select(ValidationCorrectionSuggestion).filter(ValidationCorrectionSuggestion.id == suggestion_id))
    suggestion = r.scalars().first()
    if not suggestion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Correction suggestion with ID '{suggestion_id}' not found.")
    if suggestion.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot process suggestion that is already '{suggestion.status}'.")
    try:
        if action == "approve":
            cr = await db.execute(select(StagingCompany).filter(StagingCompany.company_id == suggestion.company_id))
            company = cr.scalars().first()
            if not company:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staging Company profile with ID '{suggestion.company_id}' not found.")
            if not hasattr(company, suggestion.field_name):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Field '{suggestion.field_name}' does not exist on StagingCompany profile schema.")
            setattr(company, suggestion.field_name, suggestion.suggested_value)
            company.processed_at = datetime.utcnow()
            suggestion.status = "applied"
            suggestion.reviewed_by = "system_hitl"
            suggestion.reviewed_at = datetime.utcnow()
            logger.info(f"Successfully approved & applied suggestion {suggestion_id} to StagingCompany {suggestion.company_id}")
        else:
            suggestion.status = "rejected"
            suggestion.reviewed_by = "system_hitl"
            suggestion.reviewed_at = datetime.utcnow()
            logger.info(f"Successfully rejected suggestion {suggestion_id}")
        await db.commit()
        await db.refresh(suggestion)
        return {"success": True, "message": f"Suggestion successfully {suggestion.status}.", "suggestion_id": suggestion.id, "status": suggestion.status}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing remediation action '{action}' on suggestion {suggestion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to perform action '{action}' on correction suggestion.")
