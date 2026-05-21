import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.models.user import User
from app.schemas.auth_schemas import UserResponse, UserRegister
from app.schemas.student_schemas import UserUpdate
from app.dependencies.auth_deps import get_current_user, RoleChecker
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["Users"])

# Protect all routes in this router with RoleChecker (Admin only or Researcher/Admin)
admin_checker = RoleChecker(["admin"])
admin_or_researcher = RoleChecker(["admin", "researcher"])

@router.get("", response_model=List[UserResponse], dependencies=[Depends(admin_or_researcher)])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """
    List all system users. Optional filtering by role.
    """
    stmt = select(User)
    if role:
        stmt = stmt.filter(User.role == role)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(admin_or_researcher)])
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Retrieve user details by unique User UUID.
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found."
        )
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_checker)])
async def create_user(
    payload: UserRegister,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new user account (Admin only).
    """
    # Check duplicate username
    result = await db.execute(select(User).filter(User.username == payload.username))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already registered."
        )

    # Check duplicate email
    result = await db.execute(select(User).filter(User.email == payload.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered."
        )

    new_user = User(
        id=str(uuid.uuid4()),
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role or "viewer",
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(admin_checker)])
async def update_user(
    user_id: str,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Update an existing user account (Admin only).
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found."
        )

    # Validate username uniqueness if changed
    if payload.username and payload.username != user.username:
        dup = await db.execute(select(User).filter(User.username == payload.username))
        if dup.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken."
            )
        user.username = payload.username

    # Validate email uniqueness if changed
    if payload.email and payload.email != user.email:
        dup = await db.execute(select(User).filter(User.email == payload.email))
        if dup.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already taken."
            )
        user.email = payload.email

    # Hash new password if provided
    if payload.password:
        user.hashed_password = hash_password(payload.password)

    # Update role and status
    if payload.role:
        if payload.role not in ["admin", "researcher", "viewer"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'admin', 'researcher', or 'viewer'."
            )
        user.role = payload.role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    from app.services.cache_service import cache_service
    await cache_service.delete(f"session:{user.username}")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_checker)])
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Delete a user account. Blocks self-deletion (Admin only).
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-deletion is prohibited."
        )

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found."
        )

    username = user.username
    await db.delete(user)
    await db.commit()
    from app.services.cache_service import cache_service
    await cache_service.delete(f"session:{username}")
    return None
