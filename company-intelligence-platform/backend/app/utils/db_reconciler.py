# app/utils/db_reconciler.py
import logging
from sqlalchemy import inspect, text
# Import all models to ensure they are registered on Base.metadata
from app.models import (
    ResearchSession,
    AgentOutput,
    ValidationLog,
    FinalReport,
    TokenUsageLog,
    StagingCompany,
    CompanyEmbedding
)

logger = logging.getLogger("company_intel.db_reconciler")

def reconcile_database_schema():
    """
    Executes startup database schema audits and auto-reconciliation.
    - Creates any missing tables defined in SQLAlchemy metadata.
    - Programmatically adds the 'allocated_parameters' column to the 'staging_company' table if missing.
    """
    from app.core.database import engine, Base
    logger.info("🔧 [Database Reconciler] Starting database schema validation and alignment...")
    try:
        # 1. Create all missing tables
        Base.metadata.create_all(bind=engine)

        logger.info("   - Checked and created missing tables in metadata.")
        
        # 2. Inspect the database columns for staging_company
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("staging_company")]
        
        if "allocated_parameters" not in columns:
            logger.warning("⚠️ [Database Reconciler] Missing column 'allocated_parameters' in 'staging_company' table. Auto-reconciling...")
            with engine.begin() as conn:
                # SQLite, MySQL, and PostgreSQL all support ALTER TABLE ADD COLUMN.
                # In SQLite, JSON type is represented as TEXT.
                conn.execute(text("ALTER TABLE staging_company ADD COLUMN allocated_parameters TEXT"))
            logger.info("🟢 [Database Reconciler] Successfully added 'allocated_parameters' column to 'staging_company' table.")
        else:
            logger.info("   - Column 'allocated_parameters' already exists in 'staging_company' table.")
            
        logger.info("✨ [Database Reconciler] Database schema is fully aligned and reconciled.")
        return True
    except Exception as e:
        logger.error(f"❌ [Database Reconciler] Database schema reconciliation failed: {e}", exc_info=True)
        return False
