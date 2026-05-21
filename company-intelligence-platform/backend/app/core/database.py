# app/core/database.py
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

logger = logging.getLogger("company_intel.database")

# ═══════════════════════════════════════════════════════════════════════════
# SYNCHRONOUS ENGINE (retained for Alembic migrations, Celery workers, and
# startup seed operations that run outside the async event loop)
# ═══════════════════════════════════════════════════════════════════════════

# Adaptively configure connect arguments for different database dialects.
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    logger.info("Configuring SQLite database engine with check_same_thread=False.")
else:
    logger.info(f"Configuring SQL engine for database dialect: {settings.DATABASE_URL.split(':')[0]}")

# Create synchronous database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True  # Automatically check & refresh stale/dead database connections
)

# Create thread-safe synchronous session class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Share base model class
Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════
# ASYNCHRONOUS ENGINE & SESSION FACTORY
# Enables non-blocking database I/O for FastAPI route handlers, improving
# concurrency, throughput, and scalability under heavy load.
# ═══════════════════════════════════════════════════════════════════════════

def _build_async_url(sync_url: str) -> str:
    """
    Converts a synchronous database URL to its async driver equivalent.
    - sqlite:///... → sqlite+aiosqlite:///...
    - postgresql://... → postgresql+asyncpg://...
    - postgresql+psycopg2://... → postgresql+asyncpg://...
    - mysql://... → mysql+aiomysql://...
    """
    if sync_url.startswith("sqlite:///"):
        return sync_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    elif sync_url.startswith("postgresql+psycopg2://"):
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    elif sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif sync_url.startswith("mysql://"):
        return sync_url.replace("mysql://", "mysql+aiomysql://", 1)
    elif sync_url.startswith("mysql+pymysql://"):
        return sync_url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
    else:
        # Fallback: return as-is (user may have already specified async driver)
        return sync_url


ASYNC_DATABASE_URL = _build_async_url(settings.DATABASE_URL)
logger.info(f"Async database URL dialect: {ASYNC_DATABASE_URL.split(':')[0]}")

# Async connect args (aiosqlite doesn't need check_same_thread)
async_connect_args = {}

# Build pool configuration based on database dialect
_is_sqlite = ASYNC_DATABASE_URL.startswith("sqlite")

async_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

if not _is_sqlite:
    # Production pool settings for PostgreSQL / MySQL
    async_engine_kwargs.update({
        "pool_size": 50,           # Optimized base persistent connections
        "max_overflow": 100,       # Optimized burst connections beyond pool_size
        "pool_timeout": 60,        # Seconds to wait for a free connection
        "pool_recycle": 1800,      # Recycle connections after 30 minutes
    })

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    connect_args=async_connect_args,
    **async_engine_kwargs
)

# Async session factory — each request gets its own scoped session
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Prevent lazy-load exceptions after commit
    autocommit=False,
    autoflush=False,
)


# ═══════════════════════════════════════════════════════════════════════════
# SQLALCHEMY EVENT LISTENERS FOR METRICS (Sync engine only — async engine
# uses its own instrumentation via middleware-level timing)
# ═══════════════════════════════════════════════════════════════════════════
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.core.metrics import track_db_query

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Stores query execution start timestamp on the query context."""
    if context:
        context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Calculates query duration and records it to Prometheus metrics."""
    if context and hasattr(context, "_query_start_time"):
        duration = time.time() - context._query_start_time
        
        # Categorize the query type (e.g. SELECT, INSERT, UPDATE, DELETE)
        query_type = "other"
        if statement:
            stripped = statement.strip()
            if stripped:
                first_word = stripped.split()[0].upper()
                # Clean up any comments or syntax tokens
                first_word = "".join(c for c in first_word if c.isalnum())
                if first_word in {"SELECT", "INSERT", "UPDATE", "DELETE"}:
                    query_type = first_word.lower()
                    
        track_db_query(query_type=query_type, duration=duration)

# ═══════════════════════════════════════════════════════════════════════════
# SELF-HEALING AUTO-RECONCILIATION ON IMPORT
# ═══════════════════════════════════════════════════════════════════════════
# Deferred schema reconciliation during database module boot has been removed.
# Database migrations are now executed exclusively via prestart.sh,
# docker entrypoints, and CI/CD pipelines to prevent Uvicorn blocking.

