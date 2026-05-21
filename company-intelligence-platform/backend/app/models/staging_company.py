# app/models/staging_company.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON, TypeDecorator
from sqlalchemy.orm import relationship
from app.core.database import Base

class SafeEmbeddingVector(TypeDecorator):
    """
    Saves and retrieves 1536-dimensional semantic float vectors.
    Dynamically resolves to pgvector.sqlalchemy.Vector on PostgreSQL systems,
    and cleanly falls back to generic JSON array storage on SQLite and MySQL.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(1536))
            except ImportError:
                pass
        return dialect.type_descriptor(JSON)

class StagingCompany(Base):
    """SQLAlchemy model representing consolidated intelligence dataset per company."""
    __tablename__ = "staging_company"

    company_id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True, index=True)
    short_name = Column(String(255), nullable=True)
    category = Column(String(255), nullable=True)
    incorporation_year = Column(String(50), nullable=True)
    nature_of_company = Column(String(255), nullable=True, default="Private")
    headquarters_address = Column(Text, nullable=True)
    office_count = Column(Integer, nullable=True)
    employee_size = Column(String(255), nullable=True)
    website_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    twitter_handle = Column(String(255), nullable=True)
    facebook_url = Column(String(255), nullable=True)
    instagram_url = Column(String(255), nullable=True)
    primary_contact_email = Column(String(255), nullable=True)
    primary_phone_number = Column(String(255), nullable=True)
    overview_text = Column(Text, nullable=True)
    vision_statement = Column(Text, nullable=True)
    mission_statement = Column(Text, nullable=True)
    legal_issues = Column(Text, nullable=True)
    carbon_footprint = Column(String(255), nullable=True)
    processing_status = Column(String(100), default="completed")
    processed_at = Column(DateTime, default=datetime.utcnow)
    inserted_at = Column(DateTime, default=datetime.utcnow)
    allocated_parameters = Column(JSON, nullable=True)


    # Relationships
    embedding = relationship(
        "CompanyEmbedding",
        uselist=False,
        back_populates="company",
        cascade="all, delete-orphan"
    )

    validation_results = relationship(
        "ValidationResultsDetail",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    correction_suggestions = relationship(
        "ValidationCorrectionSuggestion",
        back_populates="company",
        cascade="all, delete-orphan"
    )


class CompanyEmbedding(Base):
    """SQLAlchemy model representing high-confidence semantic company embeddings."""
    __tablename__ = "company_embeddings"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(
        String(50),
        ForeignKey("staging_company.company_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    metadata_text = Column(Text, nullable=False)
    embedding = Column(SafeEmbeddingVector, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Back-relationships
    company = relationship("StagingCompany", back_populates="embedding")
