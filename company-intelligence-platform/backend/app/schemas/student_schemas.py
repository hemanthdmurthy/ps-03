from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, validator

# ===========================================================================
# 1. USER SCHEMA UPDATES
# ===========================================================================
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None)
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    role: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


# ===========================================================================
# 2. SKILL SCHEMAS
# ===========================================================================
class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Skill name (e.g. Python, React)")
    category: Optional[str] = Field(None, max_length=100, description="Category (e.g. Frontend, Backend)")

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class StudentSkillCreate(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100, description="Name of the skill to associate")
    proficiency_level: Optional[str] = Field("Intermediate", description="Beginner, Intermediate, Expert")

class StudentSkillResponse(BaseModel):
    skill_id: str
    name: str
    category: Optional[str]
    proficiency_level: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 3. RESUME SCHEMAS
# ===========================================================================
class ResumeBase(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    is_primary: Optional[bool] = False

class ResumeCreate(ResumeBase):
    pass

class ResumeUpdate(BaseModel):
    file_name: Optional[str] = Field(None, min_length=1, max_length=255)
    file_path: Optional[str] = Field(None, min_length=1, max_length=500)
    is_primary: Optional[bool] = None

class ResumeResponse(ResumeBase):
    id: str
    student_id: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 4. STUDENT PROFILE SCHEMAS
# ===========================================================================
class StudentProfileBase(BaseModel):
    bio: Optional[str] = Field(None, max_length=1000)
    github_url: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=255)
    twitter_url: Optional[str] = Field(None, max_length=255)
    portfolio_url: Optional[str] = Field(None, max_length=255)

class StudentProfileCreate(StudentProfileBase):
    pass

class StudentProfileUpdate(StudentProfileBase):
    pass

class StudentProfileResponse(StudentProfileBase):
    id: str
    student_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================================================
# 5. STUDENT SCHEMAS
# ===========================================================================
class StudentBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    roll_number: str = Field(..., min_length=1, max_length=50)
    department: str = Field(..., min_length=1, max_length=100)
    graduation_year: int = Field(..., gt=1900, lt=2100)
    cgpa: Optional[float] = Field(None, ge=0.0, le=10.0)

    @validator("cgpa")
    def validate_cgpa(cls, v):
        if v is not None and (v < 0.0 or v > 10.0):
            raise ValueError("CGPA must be between 0.0 and 10.0")
        return v

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    roll_number: Optional[str] = Field(None, min_length=1, max_length=50)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    graduation_year: Optional[int] = Field(None, gt=1900, lt=2100)
    cgpa: Optional[float] = Field(None, ge=0.0, le=10.0)

    @validator("cgpa")
    def validate_cgpa(cls, v):
        if v is not None and (v < 0.0 or v > 10.0):
            raise ValueError("CGPA must be between 0.0 and 10.0")
        return v

class StudentResponse(StudentBase):
    id: str
    created_at: datetime
    updated_at: datetime
    profile: Optional[StudentProfileResponse] = None
    resumes: List[ResumeResponse] = []
    skills: List[StudentSkillResponse] = []

    class Config:
        from_attributes = True
