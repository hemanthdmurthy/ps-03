# app/dependencies/db_deps.py
from typing import Generator, AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal, AsyncSessionLocal
from app.services.db import db_service, SupabaseService


def get_db_service() -> SupabaseService:
    """Dependency injection helper to yield SupabaseService database instance."""
    return db_service


def get_db() -> Generator[Session, None, None]:
    """
    Synchronous dependency injection helper yielding scoped transactional database sessions.
    Retained for backward compatibility with Celery workers and sync startup routines.
    Guarantees clean connection teardown upon request lifecycle end.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency injection helper yielding non-blocking AsyncSession instances.
    Used by all FastAPI async route handlers for concurrent database I/O.
    Guarantees clean connection teardown and automatic rollback on unhandled errors.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
