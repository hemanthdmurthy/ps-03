import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, backref
from app.core.database import Base

class PlacementDrive(Base):
    __tablename__ = "placement_drives"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(50), ForeignKey("staging_company.company_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    job_role = Column(String(100), nullable=False)
    job_description = Column(Text, nullable=True)
    eligibility_criteria = Column(Text, nullable=True)
    package_lpa = Column(Float, nullable=True)
    drive_date = Column(DateTime, nullable=False)
    status = Column(String(50), default="Upcoming", nullable=False)  # Upcoming, Ongoing, Completed, Cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("StagingCompany", backref=backref("placement_drives", cascade="all, delete-orphan"))
    applications = relationship("PlacementApplication", back_populates="drive", cascade="all, delete-orphan")


class PlacementApplication(Base):
    __tablename__ = "placement_applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    drive_id = Column(String(36), ForeignKey("placement_drives.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(String(36), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="Applied", nullable=False)  # Applied, Shortlisted, Rejected, Offered
    applied_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    drive = relationship("PlacementDrive", back_populates="applications")
    student = relationship("Student", backref=backref("placement_applications", cascade="all, delete-orphan"))
    resume = relationship("Resume", backref="placement_applications")
    interviews = relationship("InterviewSchedule", back_populates="application", cascade="all, delete-orphan")
    result = relationship("PlacementResult", back_populates="application", uselist=False, cascade="all, delete-orphan")


class InterviewSchedule(Base):
    __tablename__ = "interview_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("placement_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    round_name = Column(String(100), nullable=False)  # Tech Round 1, Technical Round 2, HR Round, etc.
    scheduled_at = Column(DateTime, nullable=False)
    location_link = Column(String(255), nullable=True)  # Physical room or video conference URL
    status = Column(String(50), default="Scheduled", nullable=False)  # Scheduled, Completed, Cancelled, NoShow
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("PlacementApplication", back_populates="interviews")


class PlacementResult(Base):
    __tablename__ = "placement_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("placement_applications.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    status = Column(String(50), default="Selected", nullable=False)  # Selected, Rejected, Waitlisted
    offered_package_lpa = Column(Float, nullable=True)
    offer_letter_path = Column(String(500), nullable=True)
    released_at = Column(DateTime, default=datetime.utcnow)
    remarks = Column(Text, nullable=True)

    # Relationships
    application = relationship("PlacementApplication", back_populates="result")
