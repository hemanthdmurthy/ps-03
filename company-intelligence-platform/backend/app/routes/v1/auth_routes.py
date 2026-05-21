import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.dependencies.auth_deps import get_active_user
from app.models.user import User
from app.schemas.auth_schemas import (
    UserRegister,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    TokenRefreshRequest
)
from app.utils.security import hash_password, verify_password
from app.utils.jwt_helper import create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: AsyncSession = Depends(get_async_db)):
    """
    Registers a new system account. Checks for existing duplicates, hashes the password, and returns profile.
    """
    # Check if username or email is already registered
    result = await db.execute(
        select(User).filter(
            (User.username == body.username) | (User.email == body.email)
        )
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered"
        )

    # Enforce safe role names
    valid_roles = ["admin", "researcher", "viewer"]
    role = body.role.lower() if body.role else "viewer"
    if role not in valid_roles:
        role = "viewer"

    new_user = User(
        id=str(uuid.uuid4()),
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=role,
        is_active=True
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLoginRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Authenticates user credentials. Supports dual matching on either username or email for a seamless UX.
    Returns access and refresh tokens.
    """
    # Support logging in via either username or email
    result = await db.execute(
        select(User).filter(
            (User.username == credentials.username) | (User.email == credentials.username)
        )
    )
    user = result.scalars().first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: username/email or password does not match"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive. Please contact support."
        )

    # Generate JWT payloads
    token_data = {"sub": user.username, "role": user.role}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        username=user.username
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(body: TokenRefreshRequest, db: AsyncSession = Depends(get_async_db)):
    """
    Decodes the refresh token and yields a new access and refresh token pair (Refresh Token Rotation).
    """
    try:
        payload = decode_token(body.refresh_token, is_refresh=True)
        username: str = payload.get("sub")
        token_type: str = payload.get("type")

        if username is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token claims"
            )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired"
        )

    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is invalid or inactive"
        )

    # Generate new payloads
    token_data = {"sub": user.username, "role": user.role}
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        role=user.role,
        username=user.username
    )

@router.post("/logout")
async def logout(current_user: User = Depends(get_active_user)):
    """
    Stateless endpoint confirming client session invalidation.
    Clears the cached session from Redis.
    """
    from app.services.cache_service import cache_service
    if current_user:
        await cache_service.delete(f"session:{current_user.username}")
    return {"status": "success", "message": "Tokens invalidated successfully."}

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_active_user)):
    """
    Returns the Safe authenticated user details.
    """
    return current_user
