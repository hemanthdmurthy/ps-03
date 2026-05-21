import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base

class StudentSkill(Base):
    __tablename__ = "student_skills"

    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    proficiency_level = Column(String(50), nullable=True)  # Beginner, Intermediate, Expert
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="student_skills")
    skill = relationship("Skill", back_populates="student_skills")


class Student(Base):
    __tablename__ = "students"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    roll_number = Column(String(50), unique=True, nullable=False, index=True)
    department = Column(String(100), nullable=False)
    graduation_year = Column(Integer, nullable=False)
    cgpa = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("StudentProfile", back_populates="student", uselist=False, cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="student", cascade="all, delete-orphan")

    # Many-to-many through association model StudentSkill
    student_skills = relationship("StudentSkill", back_populates="student", cascade="all, delete-orphan")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False)
    bio = Column(String(1000), nullable=True)
    github_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    twitter_url = Column(String(255), nullable=True)
    portfolio_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="profile")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=True)  # Frontend, Backend, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student_skills = relationship("StudentSkill", back_populates="skill", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="resumes")
