import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies.db_deps import get_async_db
from app.models.staging_company import StagingCompany
from app.models.student import Student, Resume
from app.models.placement import PlacementDrive, PlacementApplication, InterviewSchedule, PlacementResult
from app.schemas.placement_schemas import (
    PlacementDriveCreate, PlacementDriveUpdate, PlacementDriveResponse, DriveDetailedResponse,
    PlacementApplicationCreate, PlacementApplicationUpdate, PlacementApplicationResponse,
    InterviewScheduleCreate, InterviewScheduleUpdate, InterviewScheduleResponse,
    PlacementResultCreate, PlacementResultUpdate, PlacementResultResponse
)
from app.dependencies.auth_deps import RoleChecker
from app.services.cache_service import cache_service

router = APIRouter(prefix="/placements", tags=["Placements"])
admin_or_researcher = RoleChecker(["admin", "researcher"])
viewer_or_higher = RoleChecker(["admin", "researcher", "viewer"])


@router.get("/drives", response_model=List[DriveDetailedResponse], dependencies=[Depends(viewer_or_higher)])
async def list_drives(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1), status_filter: Optional[str] = None, min_package: Optional[float] = None, db: AsyncSession = Depends(get_async_db)):
    stmt = select(PlacementDrive).options(selectinload(PlacementDrive.company))
    if status_filter: stmt = stmt.filter(PlacementDrive.status == status_filter)
    if min_package is not None: stmt = stmt.filter(PlacementDrive.package_lpa >= min_package)
    result = await db.execute(stmt.offset(skip).limit(limit))
    drives = result.scalars().all()
    results = []
    for d in drives:
        resp = DriveDetailedResponse.model_validate(d)
        count_r = await db.execute(select(func.count(PlacementApplication.id)).filter(PlacementApplication.drive_id == d.id))
        resp.applications_count = count_r.scalar() or 0
        results.append(resp)
    return results


@router.get("/drives/{drive_id}", response_model=DriveDetailedResponse, dependencies=[Depends(viewer_or_higher)])
async def get_drive(drive_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PlacementDrive).options(selectinload(PlacementDrive.company)).filter(PlacementDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Placement recruitment drive with ID '{drive_id}' not found.")
    resp = DriveDetailedResponse.model_validate(drive)
    count_r = await db.execute(select(func.count(PlacementApplication.id)).filter(PlacementApplication.drive_id == drive.id))
    resp.applications_count = count_r.scalar() or 0
    return resp


@router.post("/drives", response_model=PlacementDriveResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_drive(payload: PlacementDriveCreate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(StagingCompany).filter(StagingCompany.company_id == payload.company_id))
    if not r.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"StagingCompany with ID '{payload.company_id}' does not exist.")
    new_drive = PlacementDrive(id=str(uuid.uuid4()), company_id=payload.company_id, title=payload.title, job_role=payload.job_role, job_description=payload.job_description, eligibility_criteria=payload.eligibility_criteria, package_lpa=payload.package_lpa, drive_date=payload.drive_date, status=payload.status or "Upcoming")
    db.add(new_drive)
    await db.commit()
    await db.refresh(new_drive)
    await cache_service.clear_pattern("analytics:*")
    return new_drive


@router.put("/drives/{drive_id}", response_model=PlacementDriveResponse, dependencies=[Depends(admin_or_researcher)])
async def update_drive(drive_id: str, payload: PlacementDriveUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PlacementDrive).filter(PlacementDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Placement recruitment drive with ID '{drive_id}' not found.")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(drive, key, value)
    drive.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(drive)
    await cache_service.clear_pattern("analytics:*")
    return drive


@router.delete("/drives/{drive_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def delete_drive(drive_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PlacementDrive).filter(PlacementDrive.id == drive_id))
    drive = result.scalars().first()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Placement recruitment drive with ID '{drive_id}' not found.")
    await db.delete(drive)
    await db.commit()
    await cache_service.clear_pattern("analytics:*")
    return None


@router.get("/applications", response_model=List[PlacementApplicationResponse], dependencies=[Depends(viewer_or_higher)])
async def list_applications(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1), drive_id: Optional[str] = None, student_id: Optional[str] = None, status_filter: Optional[str] = None, db: AsyncSession = Depends(get_async_db)):
    stmt = select(PlacementApplication).options(selectinload(PlacementApplication.result))
    if drive_id: stmt = stmt.filter(PlacementApplication.drive_id == drive_id)
    if student_id: stmt = stmt.filter(PlacementApplication.student_id == student_id)
    if status_filter: stmt = stmt.filter(PlacementApplication.status == status_filter)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/applications/{application_id}", response_model=PlacementApplicationResponse, dependencies=[Depends(viewer_or_higher)])
async def get_application(application_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PlacementApplication).options(selectinload(PlacementApplication.result)).filter(PlacementApplication.id == application_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PlacementApplication with ID '{application_id}' not found.")
    return app


@router.post("/applications", response_model=PlacementApplicationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_application(payload: PlacementApplicationCreate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(Student).filter(Student.id == payload.student_id))
    if not r.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record with ID '{payload.student_id}' does not exist.")
    r = await db.execute(select(PlacementDrive).filter(PlacementDrive.id == payload.drive_id))
    if not r.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Recruitment drive with ID '{payload.drive_id}' does not exist.")
    r = await db.execute(select(PlacementApplication).filter(PlacementApplication.drive_id == payload.drive_id, PlacementApplication.student_id == payload.student_id))
    if r.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student has already applied to this recruitment drive.")
    if payload.resume_id:
        r = await db.execute(select(Resume).filter(Resume.id == payload.resume_id, Resume.student_id == payload.student_id))
        if not r.scalars().first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Resume '{payload.resume_id}' belongs to a different student or does not exist.")
    new_app = PlacementApplication(id=str(uuid.uuid4()), drive_id=payload.drive_id, student_id=payload.student_id, resume_id=payload.resume_id, status=payload.status or "Applied", notes=payload.notes)
    db.add(new_app)
    await db.commit()
    await db.refresh(new_app)
    await cache_service.clear_pattern("analytics:*")
    return new_app


@router.put("/applications/{application_id}", response_model=PlacementApplicationResponse, dependencies=[Depends(admin_or_researcher)])
async def update_application(application_id: str, payload: PlacementApplicationUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PlacementApplication).filter(PlacementApplication.id == application_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PlacementApplication with ID '{application_id}' not found.")
    if payload.resume_id:
        r = await db.execute(select(Resume).filter(Resume.id == payload.resume_id, Resume.student_id == app.student_id))
        if not r.scalars().first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume belongs to a different student or does not exist.")
        app.resume_id = payload.resume_id
    if payload.status: app.status = payload.status
    if payload.notes is not None: app.notes = payload.notes
    await db.commit()
    await db.refresh(app)
    await cache_service.clear_pattern("analytics:*")
    return app


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def delete_application(application_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(PlacementApplication).filter(PlacementApplication.id == application_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PlacementApplication with ID '{application_id}' not found.")
    await db.delete(app)
    await db.commit()
    await cache_service.clear_pattern("analytics:*")
    return None


@router.post("/interviews", response_model=InterviewScheduleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_interview(payload: InterviewScheduleCreate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(PlacementApplication).filter(PlacementApplication.id == payload.application_id))
    if not r.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PlacementApplication with ID '{payload.application_id}' not found.")
    new_interview = InterviewSchedule(id=str(uuid.uuid4()), application_id=payload.application_id, round_name=payload.round_name, scheduled_at=payload.scheduled_at, location_link=payload.location_link, status=payload.status or "Scheduled", feedback=payload.feedback)
    db.add(new_interview)
    await db.commit()
    await db.refresh(new_interview)
    return new_interview


@router.put("/interviews/{interview_id}", response_model=InterviewScheduleResponse, dependencies=[Depends(admin_or_researcher)])
async def update_interview(interview_id: str, payload: InterviewScheduleUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(InterviewSchedule).filter(InterviewSchedule.id == interview_id))
    interview = result.scalars().first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"InterviewSchedule with ID '{interview_id}' not found.")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(interview, key, value)
    await db.commit()
    await db.refresh(interview)
    return interview


@router.delete("/interviews/{interview_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def delete_interview(interview_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(InterviewSchedule).filter(InterviewSchedule.id == interview_id))
    interview = result.scalars().first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"InterviewSchedule with ID '{interview_id}' not found.")
    await db.delete(interview)
    await db.commit()
    return None


@router.post("/results", response_model=PlacementResultResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_result(payload: PlacementResultCreate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(PlacementApplication).filter(PlacementApplication.id == payload.application_id))
    app = r.scalars().first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PlacementApplication with ID '{payload.application_id}' not found.")
    r = await db.execute(select(PlacementResult).filter(PlacementResult.application_id == payload.application_id))
    if r.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A result has already been published for this application. Use PUT to modify instead.")
    if payload.status == "Selected": app.status = "Offered"
    elif payload.status == "Rejected": app.status = "Rejected"
    elif payload.status == "Waitlisted": app.status = "Shortlisted"
    new_result = PlacementResult(id=str(uuid.uuid4()), application_id=payload.application_id, status=payload.status or "Selected", offered_package_lpa=payload.offered_package_lpa, offer_letter_path=payload.offer_letter_path, remarks=payload.remarks)
    db.add(new_result)
    await db.commit()
    await db.refresh(new_result)
    await cache_service.clear_pattern("analytics:*")
    return new_result


@router.put("/results/{result_id}", response_model=PlacementResultResponse, dependencies=[Depends(admin_or_researcher)])
async def update_result(result_id: str, payload: PlacementResultUpdate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(PlacementResult).filter(PlacementResult.id == result_id))
    result_obj = r.scalars().first()
    if not result_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PlacementResult with ID '{result_id}' not found.")
    if payload.status:
        result_obj.status = payload.status
        ar = await db.execute(select(PlacementApplication).filter(PlacementApplication.id == result_obj.application_id))
        app = ar.scalars().first()
        if app:
            if payload.status == "Selected": app.status = "Offered"
            elif payload.status == "Rejected": app.status = "Rejected"
            elif payload.status == "Waitlisted": app.status = "Shortlisted"
    if payload.offered_package_lpa is not None: result_obj.offered_package_lpa = payload.offered_package_lpa
    if payload.offer_letter_path: result_obj.offer_letter_path = payload.offer_letter_path
    if payload.remarks is not None: result_obj.remarks = payload.remarks
    await db.commit()
    await db.refresh(result_obj)
    await cache_service.clear_pattern("analytics:*")
    return result_obj


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def delete_result(result_id: str, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(PlacementResult).filter(PlacementResult.id == result_id))
    result_obj = r.scalars().first()
    if not result_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PlacementResult with ID '{result_id}' not found.")
    ar = await db.execute(select(PlacementApplication).filter(PlacementApplication.id == result_obj.application_id))
    app = ar.scalars().first()
    if app: app.status = "Applied"
    await db.delete(result_obj)
    await db.commit()
    await cache_service.clear_pattern("analytics:*")
    return None
