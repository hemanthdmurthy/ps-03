# app/models/validation_run.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ValidationRun(Base):
    """SQLAlchemy model representing a data quality validation execution run."""
    __tablename__ = "validation_runs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    executed_at = Column(DateTime, default=datetime.utcnow)
    triggered_by = Column(String(50), default="system")
    total_records_checked = Column(Integer, nullable=False)
    passed_records = Column(Integer, nullable=False)
    failed_records = Column(Integer, nullable=False)
    overall_quality_score = Column(Float, nullable=False)
    execution_time_seconds = Column(Float, nullable=False)

    # Relationships
    results = relationship(
        "ValidationResultsDetail",
        back_populates="run",
        cascade="all, delete-orphan"
    )


class ValidationResultsDetail(Base):
    """SQLAlchemy model representing detailed failures during data quality rules check."""
    __tablename__ = "validation_results_detail"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(
        String(50),
        ForeignKey("validation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    company_id = Column(
        String(50),
        ForeignKey("staging_company.company_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rule_id = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    status = Column(String(10), nullable=False, index=True)
    actual_value = Column(Text, nullable=True)
    expected_condition = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Back-relationships
    run = relationship("ValidationRun", back_populates="results")
    company = relationship("StagingCompany", back_populates="validation_results")


class ValidationCorrectionSuggestion(Base):
    """SQLAlchemy model representing proposed values for AI self-healing or HITL reviews."""
    __tablename__ = "validation_correction_suggestions"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(
        String(50),
        ForeignKey("staging_company.company_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    field_name = Column(String(100), nullable=False)
    original_value = Column(Text, nullable=True)
    suggested_value = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False)
    source = Column(String(50), default="LLM_Remediation")
    status = Column(String(20), default="pending", index=True)  # 'pending', 'applied', 'rejected'
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Back-relationship
    company = relationship("StagingCompany", back_populates="correction_suggestions")
