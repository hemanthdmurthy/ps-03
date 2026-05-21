import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.models.student import Skill
from app.schemas.student_schemas import SkillCreate, SkillResponse
from app.dependencies.auth_deps import RoleChecker

router = APIRouter(prefix="/skills", tags=["Skills"])

# Master skill operations are protected: read by any, write by admin/researcher
admin_or_researcher = RoleChecker(["admin", "researcher"])
viewer_or_higher = RoleChecker(["admin", "researcher", "viewer"])

@router.get("", response_model=List[SkillResponse], dependencies=[Depends(viewer_or_higher)])
async def list_skills(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    List all master skills defined in the system. Optional filtering by category.
    """
    stmt = select(Skill)
    if category:
        stmt = stmt.filter(Skill.category == category)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    skills = result.scalars().all()
    return skills


@router.get("/{skill_id}", response_model=SkillResponse, dependencies=[Depends(viewer_or_higher)])
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Retrieve single master skill details.
    """
    result = await db.execute(select(Skill).filter(Skill.id == skill_id))
    skill = result.scalars().first()
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master skill with ID '{skill_id}' not found."
        )
    return skill


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_skill(
    payload: SkillCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new master skill definition. Checks duplicate names case-insensitively.
    """
    cleaned_name = payload.name.strip()
    result = await db.execute(select(Skill).filter(Skill.name.ilike(cleaned_name)))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Master skill with name '{cleaned_name}' already exists."
        )

    new_skill = Skill(
        id=str(uuid.uuid4()),
        name=cleaned_name,
        category=payload.category or "General"
    )
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    return new_skill
