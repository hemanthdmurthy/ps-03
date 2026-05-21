import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.models.student import Student, StudentProfile, Skill, StudentSkill, Resume
from app.schemas.student_schemas import (
    StudentCreate, StudentUpdate, StudentResponse,
    StudentProfileCreate, StudentProfileUpdate, StudentProfileResponse,
    SkillCreate, SkillResponse, StudentSkillCreate, StudentSkillResponse,
    ResumeCreate, ResumeUpdate, ResumeResponse
)
from app.dependencies.auth_deps import get_current_user, RoleChecker
from app.services.cache_service import cache_service

router = APIRouter(prefix="/students", tags=["Students"])
admin_or_researcher = RoleChecker(["admin", "researcher"])
viewer_or_higher = RoleChecker(["admin", "researcher", "viewer"])


async def _build_skills(db: AsyncSession, student_id: str) -> List[StudentSkillResponse]:
    r = await db.execute(select(StudentSkill).filter(StudentSkill.student_id == student_id))
    out = []
    for sa in r.scalars().all():
        sr = await db.execute(select(Skill).filter(Skill.id == sa.skill_id))
        sk = sr.scalars().first()
        if sk:
            out.append(StudentSkillResponse(skill_id=sa.skill_id, name=sk.name, category=sk.category, proficiency_level=sa.proficiency_level, created_at=sa.created_at))
    return out


@router.get("", response_model=List[StudentResponse], dependencies=[Depends(viewer_or_higher)])
async def list_students(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1), department: Optional[str] = None, graduation_year: Optional[int] = None, min_cgpa: Optional[float] = None, db: AsyncSession = Depends(get_async_db)):
    stmt = select(Student).options(selectinload(Student.profile), selectinload(Student.resumes))
    if department: stmt = stmt.filter(Student.department == department)
    if graduation_year: stmt = stmt.filter(Student.graduation_year == graduation_year)
    if min_cgpa is not None: stmt = stmt.filter(Student.cgpa >= min_cgpa)
    result = await db.execute(stmt.offset(skip).limit(limit))
    students = result.scalars().all()
    results = []
    for s in students:
        res = StudentResponse.model_validate(s)
        res.skills = await _build_skills(db, s.id)
        results.append(res)
    return results


@router.get("/{student_id}", response_model=StudentResponse, dependencies=[Depends(viewer_or_higher)])
async def get_student(student_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Student).filter(Student.id == student_id).options(selectinload(Student.profile), selectinload(Student.resumes)))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record with ID '{student_id}' not found.")
    res = StudentResponse.model_validate(student)
    res.skills = await _build_skills(db, student_id)
    return res


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(Student).filter(Student.roll_number == payload.roll_number))
    if r.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Student with roll number '{payload.roll_number}' already registered.")
    new_student = Student(id=str(uuid.uuid4()), first_name=payload.first_name, last_name=payload.last_name, roll_number=payload.roll_number, department=payload.department, graduation_year=payload.graduation_year, cgpa=payload.cgpa)
    db.add(new_student)
    await db.commit()
    await db.refresh(new_student)
    await cache_service.clear_pattern("analytics:*")
    new_student.profile = None
    new_student.resumes = []
    res = StudentResponse.model_validate(new_student)
    res.skills = []
    return res


@router.put("/{student_id}", response_model=StudentResponse, dependencies=[Depends(admin_or_researcher)])
async def update_student(student_id: str, payload: StudentUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Student).filter(Student.id == student_id).options(selectinload(Student.profile), selectinload(Student.resumes)))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record with ID '{student_id}' not found.")
    if payload.roll_number and payload.roll_number != student.roll_number:
        dup = await db.execute(select(Student).filter(Student.roll_number == payload.roll_number))
        if dup.scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Roll number '{payload.roll_number}' is already assigned to another student.")
        student.roll_number = payload.roll_number
    if payload.first_name: student.first_name = payload.first_name
    if payload.last_name: student.last_name = payload.last_name
    if payload.department: student.department = payload.department
    if payload.graduation_year: student.graduation_year = payload.graduation_year
    if payload.cgpa is not None: student.cgpa = payload.cgpa
    student.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(student)
    await cache_service.clear_pattern("analytics:*")
    res = StudentResponse.model_validate(student)
    res.skills = await _build_skills(db, student_id)
    return res


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def delete_student(student_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Student).filter(Student.id == student_id))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record with ID '{student_id}' not found.")
    await db.delete(student)
    await db.commit()
    await cache_service.clear_pattern("analytics:*")
    return None


@router.get("/{student_id}/profile", response_model=StudentProfileResponse, dependencies=[Depends(viewer_or_higher)])
async def get_student_profile(student_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(StudentProfile).filter(StudentProfile.student_id == student_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Profile for student '{student_id}' does not exist.")
    return profile


@router.post("/{student_id}/profile", response_model=StudentProfileResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_student_profile(student_id: str, payload: StudentProfileCreate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(Student).filter(Student.id == student_id))
    if not r.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record '{student_id}' does not exist.")
    dup = await db.execute(select(StudentProfile).filter(StudentProfile.student_id == student_id))
    if dup.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student profile already exists. Use PUT to update instead.")
    new_profile = StudentProfile(id=str(uuid.uuid4()), student_id=student_id, bio=payload.bio, github_url=payload.github_url, linkedin_url=payload.linkedin_url, twitter_url=payload.twitter_url, portfolio_url=payload.portfolio_url)
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    return new_profile


@router.put("/{student_id}/profile", response_model=StudentProfileResponse, dependencies=[Depends(admin_or_researcher)])
async def update_student_profile(student_id: str, payload: StudentProfileUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(StudentProfile).filter(StudentProfile.student_id == student_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student profile for ID '{student_id}' does not exist.")
    profile.bio = payload.bio
    profile.github_url = payload.github_url
    profile.linkedin_url = payload.linkedin_url
    profile.twitter_url = payload.twitter_url
    profile.portfolio_url = payload.portfolio_url
    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/{student_id}/profile", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def delete_student_profile(student_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(StudentProfile).filter(StudentProfile.student_id == student_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student profile for ID '{student_id}' does not exist.")
    await db.delete(profile)
    await db.commit()
    return None


@router.post("/{student_id}/skills", response_model=StudentSkillResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def associate_skill(student_id: str, payload: StudentSkillCreate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(Student).filter(Student.id == student_id))
    if not r.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record '{student_id}' does not exist.")
    cleaned_name = payload.skill_name.strip()
    sr = await db.execute(select(Skill).filter(Skill.name.ilike(cleaned_name)))
    skill = sr.scalars().first()
    if not skill:
        skill = Skill(id=str(uuid.uuid4()), name=cleaned_name, category="General")
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
    ar = await db.execute(select(StudentSkill).filter(StudentSkill.student_id == student_id, StudentSkill.skill_id == skill.id))
    assoc = ar.scalars().first()
    if assoc:
        assoc.proficiency_level = payload.proficiency_level
        await db.commit()
        await db.refresh(assoc)
    else:
        assoc = StudentSkill(student_id=student_id, skill_id=skill.id, proficiency_level=payload.proficiency_level)
        db.add(assoc)
        await db.commit()
        await db.refresh(assoc)
    return StudentSkillResponse(skill_id=assoc.skill_id, name=skill.name, category=skill.category, proficiency_level=assoc.proficiency_level, created_at=assoc.created_at)


@router.delete("/{student_id}/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def dissociate_skill(student_id: str, skill_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(StudentSkill).filter(StudentSkill.student_id == student_id, StudentSkill.skill_id == skill_id))
    assoc = result.scalars().first()
    if not assoc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill mapping for this student not found.")
    await db.delete(assoc)
    await db.commit()
    return None


@router.get("/{student_id}/resumes", response_model=List[ResumeResponse], dependencies=[Depends(viewer_or_higher)])
async def list_student_resumes(student_id: str, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(Student).filter(Student.id == student_id))
    if not r.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record '{student_id}' does not exist.")
    rr = await db.execute(select(Resume).filter(Resume.student_id == student_id))
    return rr.scalars().all()


@router.post("/{student_id}/resumes", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_resume(student_id: str, payload: ResumeCreate, db: AsyncSession = Depends(get_async_db)):
    r = await db.execute(select(Student).filter(Student.id == student_id))
    if not r.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student record '{student_id}' does not exist.")
    if payload.is_primary:
        pr = await db.execute(select(Resume).filter(Resume.student_id == student_id, Resume.is_primary == True))
        for res in pr.scalars().all():
            res.is_primary = False
        await db.commit()
    new_resume = Resume(id=str(uuid.uuid4()), student_id=student_id, file_name=payload.file_name, file_path=payload.file_path, is_primary=payload.is_primary)
    db.add(new_resume)
    await db.commit()
    await db.refresh(new_resume)
    return new_resume


@router.put("/{student_id}/resumes/{resume_id}", response_model=ResumeResponse, dependencies=[Depends(admin_or_researcher)])
async def update_resume(student_id: str, resume_id: str, payload: ResumeUpdate, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Resume).filter(Resume.id == resume_id, Resume.student_id == student_id))
    resume = result.scalars().first()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Resume '{resume_id}' for student '{student_id}' not found.")
    if payload.file_name: resume.file_name = payload.file_name
    if payload.file_path: resume.file_path = payload.file_path
    if payload.is_primary is not None:
        if payload.is_primary and not resume.is_primary:
            pr = await db.execute(select(Resume).filter(Resume.student_id == student_id, Resume.is_primary == True))
            for res in pr.scalars().all():
                res.is_primary = False
            await db.commit()
        resume.is_primary = payload.is_primary
    await db.commit()
    await db.refresh(resume)
    return resume


@router.delete("/{student_id}/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def delete_resume(student_id: str, resume_id: str, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Resume).filter(Resume.id == resume_id, Resume.student_id == student_id))
    resume = result.scalars().first()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Resume '{resume_id}' for student '{student_id}' not found.")
    await db.delete(resume)
    await db.commit()
    return None
