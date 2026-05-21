# app/dependencies/auth_deps.py
from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.models.user import User
from app.utils.jwt_helper import decode_token

# Define standard OAuth2 password flow scheme pointing to our login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

from fastapi import Request

async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Decodes the JWT bearer token, validates the session, and retrieves the caller's User record.
    Optimized to reuse the authenticated user resolved by AuthenticationMiddleware in request.state.
    Uses async database queries for non-blocking I/O.
    """
    if hasattr(request.state, "user") and request.state.user is not None:
        return request.state.user

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token, is_refresh=False)
        username: str = payload.get("sub")
        token_type: str = payload.get("type")

        if username is None or token_type != "access":
            raise credentials_exception

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception

    return user

def get_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Verifies that the authenticated caller account is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is inactive"
        )
    return current_user

class RoleChecker:
    """
    Authorization guard class verifying user roles.
    Example: Depends(RoleChecker(["admin", "researcher"]))
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_active_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{current_user.role}' lacks required permissions."
            )
        return current_user
