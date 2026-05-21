import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.models.staging_company import StagingCompany
from app.schemas.placement_schemas import CompanyCreate, CompanyUpdate, CompanyResponse
from app.dependencies.auth_deps import RoleChecker
from app.services.cache_service import cache_service

router = APIRouter(prefix="/companies", tags=["Companies"])

# Read by all, write by admin/researcher
admin_or_researcher = RoleChecker(["admin", "researcher"])
viewer_or_higher = RoleChecker(["admin", "researcher", "viewer"])

@router.get("", response_model=List[CompanyResponse], dependencies=[Depends(viewer_or_higher)])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    category: Optional[str] = None,
    name_query: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    List consolidated company profiles. Optional filter by category or case-insensitive name match.
    """
    stmt = select(StagingCompany)
    if category:
        stmt = stmt.filter(StagingCompany.category == category)
    if name_query:
        stmt = stmt.filter(StagingCompany.name.ilike(f"%{name_query}%"))

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    companies = result.scalars().all()
    return companies


@router.get("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(viewer_or_higher)])
async def get_company(
    company_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Retrieve single company profile details.
    """
    result = await db.execute(
        select(StagingCompany).filter(StagingCompany.company_id == company_id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"StagingCompany with ID '{company_id}' not found."
        )
    return company


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_or_researcher)])
async def create_company(
    payload: CompanyCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Add a new consolidated company profile. Checks duplicate name case-insensitively.
    """
    cleaned_name = payload.name.strip()
    result = await db.execute(
        select(StagingCompany).filter(StagingCompany.name.ilike(cleaned_name))
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A company profile with the name '{cleaned_name}' already exists."
        )

    new_company = StagingCompany(
        company_id=str(uuid.uuid4()),
        name=cleaned_name,
        short_name=payload.short_name,
        category=payload.category,
        incorporation_year=payload.incorporation_year,
        nature_of_company=payload.nature_of_company or "Private",
        headquarters_address=payload.headquarters_address,
        office_count=payload.office_count,
        employee_size=payload.employee_size,
        website_url=payload.website_url,
        linkedin_url=payload.linkedin_url,
        twitter_handle=payload.twitter_handle,
        facebook_url=payload.facebook_url,
        instagram_url=payload.instagram_url,
        primary_contact_email=payload.primary_contact_email,
        primary_phone_number=payload.primary_phone_number,
        overview_text=payload.overview_text,
        vision_statement=payload.vision_statement,
        mission_statement=payload.mission_statement,
        legal_issues=payload.legal_issues,
        carbon_footprint=payload.carbon_footprint,
        processing_status="completed"
    )
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)
    await cache_service.clear_pattern("analytics:*")
    return new_company


@router.put("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(admin_or_researcher)])
async def update_company(
    company_id: str,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Update details for an existing company profile.
    """
    result = await db.execute(
        select(StagingCompany).filter(StagingCompany.company_id == company_id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"StagingCompany with ID '{company_id}' not found."
        )

    # Validate unique name if changed
    if payload.name:
        cleaned_name = payload.name.strip()
        if cleaned_name.lower() != company.name.lower():
            dup_result = await db.execute(
                select(StagingCompany).filter(StagingCompany.name.ilike(cleaned_name))
            )
            if dup_result.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"A company profile with the name '{cleaned_name}' already exists."
                )
            company.name = cleaned_name

    # Apply other updates
    update_data = payload.dict(exclude_unset=True)
    if "name" in update_data:
        del update_data["name"]

    for key, value in update_data.items():
        setattr(company, key, value)

    company.processed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(company)
    await cache_service.clear_pattern("analytics:*")
    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_or_researcher)])
async def delete_company(
    company_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Delete a company profile. Cascades delete to all dependent placements and embeddings.
    """
    result = await db.execute(
        select(StagingCompany).filter(StagingCompany.company_id == company_id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"StagingCompany with ID '{company_id}' not found."
        )

    await db.delete(company)
    await db.commit()
    await cache_service.clear_pattern("analytics:*")
    return None
