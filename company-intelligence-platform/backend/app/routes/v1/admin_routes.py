import os
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.dependencies.auth_deps import get_current_user, RoleChecker
from app.models.user import User
from app.models.student import Student
from app.models.staging_company import StagingCompany
from app.models.validation_run import ValidationRun, ValidationResultsDetail, ValidationCorrectionSuggestion
# Defensive imports of Research session tables
try:
    from app.models.research import ResearchSession
except ImportError:
    ResearchSession = None

from app.schemas.admin_schemas import (
    ValidationRunResponse, ValidationResultsDetailResponse, ValidationRunDetailResponse,
    CorrectionSuggestionResponse, SystemMonitoringResponse
)

router = APIRouter(prefix="/admin", tags=["Administrative & HITL Workflows"])
admin_only = RoleChecker(["admin"])


@router.get("/validation/runs", response_model=List[ValidationRunResponse], dependencies=[Depends(admin_only)])
async def list_validation_runs(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(ValidationRun).order_by(ValidationRun.executed_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/validation/runs/{run_id}", response_model=ValidationRunDetailResponse, dependencies=[Depends(admin_only)])
async def get_validation_run_details(run_id: str, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(ValidationRun).filter(ValidationRun.id == run_id))
    run = r.scalars().first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Validation run with ID '{run_id}' not found.")
    dr = await db.execute(select(ValidationResultsDetail).filter(ValidationResultsDetail.run_id == run_id))
    details = dr.scalars().all()
    return ValidationRunDetailResponse(run=run, details=details)


@router.get("/validation/suggestions", response_model=List[CorrectionSuggestionResponse], dependencies=[Depends(admin_only)])
async def list_correction_suggestions(status_filter: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1), db: AsyncSession = Depends(get_async_db)):
    stmt = select(ValidationCorrectionSuggestion)
    if status_filter:
        stmt = stmt.filter(ValidationCorrectionSuggestion.status == status_filter)
    result = await db.execute(stmt.order_by(ValidationCorrectionSuggestion.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/validation/suggestions/{suggestion_id}/approve", response_model=CorrectionSuggestionResponse)
async def approve_correction_suggestion(suggestion_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation restricted to administrators.")
    r = await db.execute(select(ValidationCorrectionSuggestion).filter(ValidationCorrectionSuggestion.id == suggestion_id))
    suggestion = r.scalars().first()
    if not suggestion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Correction suggestion with ID '{suggestion_id}' not found.")
    if suggestion.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot approve suggestion that is already '{suggestion.status}'.")
    cr = await db.execute(select(StagingCompany).filter(StagingCompany.company_id == suggestion.company_id))
    company = cr.scalars().first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staging Company profile with ID '{suggestion.company_id}' not found.")
    if not hasattr(company, suggestion.field_name):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Field '{suggestion.field_name}' does not exist on StagingCompany profile schema.")
    setattr(company, suggestion.field_name, suggestion.suggested_value)
    company.updated_at = datetime.utcnow()
    suggestion.status = "applied"
    suggestion.reviewed_by = current_user.username
    suggestion.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


@router.post("/validation/suggestions/{suggestion_id}/reject", response_model=CorrectionSuggestionResponse)
async def reject_correction_suggestion(suggestion_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation restricted to administrators.")
    r = await db.execute(select(ValidationCorrectionSuggestion).filter(ValidationCorrectionSuggestion.id == suggestion_id))
    suggestion = r.scalars().first()
    if not suggestion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Correction suggestion with ID '{suggestion_id}' not found.")
    if suggestion.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot reject suggestion that is already '{suggestion.status}'.")
    suggestion.status = "rejected"
    suggestion.reviewed_by = current_user.username
    suggestion.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


@router.get("/monitoring/stats", response_model=SystemMonitoringResponse, dependencies=[Depends(admin_only)])
async def get_system_monitoring_stats(db: AsyncSession = Depends(get_async_db)):
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_students = (await db.execute(select(func.count(Student.id)))).scalar() or 0
    total_companies = (await db.execute(select(func.count(StagingCompany.company_id)))).scalar() or 0
    total_runs = (await db.execute(select(func.count(ValidationRun.id)))).scalar() or 0
    total_details = (await db.execute(select(func.count(ValidationResultsDetail.id)))).scalar() or 0
    total_suggestions = (await db.execute(select(func.count(ValidationCorrectionSuggestion.id)))).scalar() or 0
    total_sessions = 0
    if ResearchSession is not None:
        try: total_sessions = (await db.execute(select(func.count(ResearchSession.id)))).scalar() or 0
        except Exception: pass
    db_size = 0
    for path in ["company_intel.db", "app.db", "backend.db", "database.db"]:
        if os.path.exists(path):
            db_size = os.path.getsize(path)
            break
    if db_size == 0:
        db_url = os.getenv("DATABASE_URL", "")
        if "sqlite:///" in db_url:
            clean_path = db_url.replace("sqlite:///", "")
            if os.path.exists(clean_path): db_size = os.path.getsize(clean_path)
    return SystemMonitoringResponse(total_users=total_users, total_students=total_students, total_companies=total_companies, total_validation_runs=total_runs, total_validation_details=total_details, total_correction_suggestions=total_suggestions, total_research_sessions=total_sessions, database_file_size_bytes=db_size, system_status="healthy")
