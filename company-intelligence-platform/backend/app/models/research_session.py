# app/models/research_session.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class ResearchSession(Base):
    """SQLAlchemy model representing an execution context of a company research pipeline run."""
    __tablename__ = "research_sessions"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(255), nullable=False, index=True)
    industry = Column(String(255), nullable=True)
    custom_query = Column(Text, nullable=True)
    status = Column(String(100), default="initiated", index=True)
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (Cascading ensures complete deletion of linked records)
    agent_outputs = relationship(
        "AgentOutput",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    validation_logs = relationship(
        "ValidationLog",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    final_report = relationship(
        "FinalReport",
        uselist=False,
        back_populates="session",
        cascade="all, delete-orphan"
    )

    token_usage_logs = relationship(
        "TokenUsageLog",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class AgentOutput(Base):
    """SQLAlchemy model representing the raw/structured data returned by a specialized agent."""
    __tablename__ = "agent_outputs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(50),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    agent_name = Column(String(100), nullable=False, index=True)
    status = Column(String(100), nullable=False)
    raw_json_output = Column(JSON, nullable=True)
    token_usage = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Back-relationship
    session = relationship("ResearchSession", back_populates="agent_outputs")


class ValidationLog(Base):
    """SQLAlchemy model representing validation retry metrics and rule auditing attempts."""
    __tablename__ = "validation_logs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(50),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attempt_number = Column(Integer, nullable=False, index=True)
    rules_checked = Column(JSON, nullable=True)
    overall_confidence = Column(Float, default=0.0)
    failed_fields = Column(JSON, nullable=True)
    needs_regeneration = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Back-relationship
    session = relationship("ResearchSession", back_populates="validation_logs")


class FinalReport(Base):
    """SQLAlchemy model representing the completed dynamic Business Intelligence Brief report."""
    __tablename__ = "final_reports"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(50),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    company_name = Column(String(255), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    market_analysis = Column(JSON, nullable=True)
    competitor_insights = Column(JSON, nullable=True)
    technology_stack = Column(JSON, nullable=True)
    funding_status = Column(JSON, nullable=True)
    risk_opportunity_analysis = Column(JSON, nullable=True)
    token_usage_summary = Column(JSON, nullable=True)
    field_observability = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Back-relationship
    session = relationship("ResearchSession", back_populates="final_report")


class TokenUsageLog(Base):
    """SQLAlchemy model representing granular cost and LLM consumption tokens per request."""
    __tablename__ = "token_usage_logs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(50),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    company_name = Column(String(255), nullable=True, index=True)
    model_name = Column(String(100), nullable=True, index=True)
    domain_name = Column(String(255), nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Back-relationship
    session = relationship("ResearchSession", back_populates="token_usage_logs")
