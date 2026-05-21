from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl

# ===========================================================================
# 1. COMPANY MANAGEMENT SCHEMAS
# ===========================================================================
class CompanyBase(BaseModel):
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="Official registered name of the corporate target",
        examples=["NVIDIA Corporation"]
    )
    short_name: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Common or trade name of the company",
        examples=["NVIDIA"]
    )
    category: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Industry sector or category division",
        examples=["Semiconductors & AI Hardware"]
    )
    incorporation_year: Optional[str] = Field(
        None, 
        max_length=50, 
        description="Year when the company was incorporated",
        examples=["1993"]
    )
    nature_of_company: Optional[str] = Field(
        "Private", 
        max_length=255, 
        description="Legal constitution of the company (e.g. Private, Public, LLC)",
        examples=["Public"]
    )
    headquarters_address: Optional[str] = Field(
        None, 
        description="Full postal address of corporate global headquarters",
        examples=["Santa Clara, California, United States"]
    )
    office_count: Optional[int] = Field(
        None, 
        ge=0, 
        description="Total number of active physical regional/global offices",
        examples=[45]
    )
    employee_size: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Approximate classification of global employee headcount",
        examples=["10,000+ employees"]
    )
    website_url: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Official primary public website address",
        examples=["https://nvidia.com"]
    )
    linkedin_url: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Link to the official corporate LinkedIn landing page",
        examples=["https://linkedin.com/company/nvidia"]
    )
    twitter_handle: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Official corporate Twitter handle",
        examples=["nvidia"]
    )
    facebook_url: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Official company Facebook landing page",
        examples=["https://facebook.com/NVIDIA"]
    )
    instagram_url: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Official company Instagram handle/profile url",
        examples=["https://instagram.com/nvidia"]
    )
    primary_contact_email: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Primary generic corporate email for queries",
        examples=["contact@nvidia.com"]
    )
    primary_phone_number: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Primary general customer care or corporate reception telephone line",
        examples=["+1-408-486-2000"]
    )
    overview_text: Optional[str] = Field(
        None, 
        description="Comprehensive summary or description of target core business operations",
        examples=["NVIDIA is the pioneer of GPU-accelerated computing, specializing in AI chips, computer graphics, and autonomous vehicle platforms."]
    )
    vision_statement: Optional[str] = Field(
        None, 
        description="Corporate vision and futuristic direction",
        examples=["To build computers that act as engines for human imagination and intelligence."]
    )
    mission_statement: Optional[str] = Field(
        None, 
        description="Official corporate mission statement",
        examples=["To accelerate computing to solve problems that are otherwise unsolvable."]
    )
    legal_issues: Optional[str] = Field(
        None, 
        description="Noted legal litigations, regulatory audits, or compliance cases if any",
        examples=["None recorded."]
    )
    carbon_footprint: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Reported carbon emission statistics or sustainability metrics",
        examples=["Carbon neutral goals target 2030 across direct operations."]
    )

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated company name", examples=["NVIDIA Corporation"])
    short_name: Optional[str] = Field(None, max_length=255, description="Updated short name", examples=["NVIDIA"])
    category: Optional[str] = Field(None, max_length=255, description="Updated division sector", examples=["AI & Autonomous Platforms"])
    incorporation_year: Optional[str] = Field(None, max_length=50, description="Updated incorporation year", examples=["1993"])
    nature_of_company: Optional[str] = Field(None, max_length=255, description="Updated company nature", examples=["Public"])
    headquarters_address: Optional[str] = Field(None, description="Updated headquarters address", examples=["Santa Clara, California, USA"])
    office_count: Optional[int] = Field(None, ge=0, description="Updated physical office count", examples=[50])
    employee_size: Optional[str] = Field(None, max_length=255, description="Updated company workforce size bracket", examples=["20,000+ employees"])
    website_url: Optional[str] = Field(None, max_length=255, description="Updated official website", examples=["https://www.nvidia.com"])
    linkedin_url: Optional[str] = Field(None, max_length=255, description="Updated company LinkedIn profile", examples=["https://linkedin.com/company/nvidia"])
    twitter_handle: Optional[str] = Field(None, max_length=255, description="Updated twitter handle", examples=["NVIDIAAIDev"])
    facebook_url: Optional[str] = Field(None, max_length=255, description="Updated Facebook page link")
    instagram_url: Optional[str] = Field(None, max_length=255, description="Updated Instagram page link")
    primary_contact_email: Optional[str] = Field(None, max_length=255, description="Updated generic contact email", examples=["info@nvidia.com"])
    primary_phone_number: Optional[str] = Field(None, max_length=255, description="Updated telephone number")
    overview_text: Optional[str] = Field(None, description="Updated business summary")
    vision_statement: Optional[str] = Field(None, description="Updated vision statement")
    mission_statement: Optional[str] = Field(None, description="Updated mission statement")
    legal_issues: Optional[str] = Field(None, description="Updated corporate compliance comments")
    carbon_footprint: Optional[str] = Field(None, max_length=255, description="Updated carbon output status")

class CompanyResponse(CompanyBase):
    company_id: str = Field(..., description="Unique company record UUID", examples=["comp-c734914c-12bf-4bad-9876-efdb138976a2"])
    processing_status: str = Field(..., description="Status of multi-agent validation loops. Options: pending, validating, completed, failed", examples=["completed"])
    processed_at: Optional[datetime] = Field(None, description="UTC Timestamp when company was enriched by pipeline")
    inserted_at: datetime = Field(..., description="UTC Timestamp when the profile record was inserted")

    class Config:
        from_attributes = True


# ===========================================================================
# 2. PLACEMENT DRIVE SCHEMAS
# ===========================================================================
class PlacementDriveBase(BaseModel):
    company_id: str = Field(..., description="StagingCompany identifier UUID", examples=["comp-c734914c-12bf-4bad-9876-efdb138976a2"])
    title: str = Field(..., min_length=1, max_length=255, description="Title of the placement drive", examples=["NVIDIA Campus Recruitment Drive 2026"])
    job_role: str = Field(..., min_length=1, max_length=100, description="Specific professional job role offered", examples=["ASIC Verification Engineer"])
    job_description: Optional[str] = Field(None, description="Detailed job description listing projects, stack, and responsibilities", examples=["Responsible for pre-silicon verification of next-generation GPU processors using SystemVerilog and UVM."])
    eligibility_criteria: Optional[str] = Field(None, description="Mandatory academic score, branch, and backlogs eligibility limits", examples=["B.Tech/M.Tech in ECE/EE. CGPA >= 8.0. Zero active backlogs."])
    package_lpa: Optional[float] = Field(None, ge=0.0, description="Offered annual package package in Lakhs Per Annum (LPA)", examples=[28.5])
    drive_date: datetime = Field(..., description="UTC Timestamp for the recruitment drive")
    status: Optional[str] = Field("Upcoming", description="Drive workflow status. Options: Upcoming, Ongoing, Completed, Cancelled", examples=["Upcoming"])

class PlacementDriveCreate(PlacementDriveBase):
    pass

class PlacementDriveUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated drive title")
    job_role: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated job role")
    job_description: Optional[str] = Field(None, description="Updated job description")
    eligibility_criteria: Optional[str] = Field(None, description="Updated eligibility criteria")
    package_lpa: Optional[float] = Field(None, ge=0.0, description="Updated package LPA")
    drive_date: Optional[datetime] = Field(None, description="Updated drive schedule date")
    status: Optional[str] = Field(None, description="Updated status")

class PlacementDriveResponse(PlacementDriveBase):
    id: str = Field(..., description="Recruitment drive UUID", examples=["drv-39b1deb4-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    created_at: datetime = Field(..., description="UTC Timestamp when the drive record was registered")
    updated_at: datetime = Field(..., description="UTC Timestamp when the drive details were last updated")

    class Config:
        from_attributes = True


# ===========================================================================
# 3. INTERVIEW SCHEDULE SCHEMAS
# ===========================================================================
class InterviewScheduleBase(BaseModel):
    application_id: str = Field(..., description="Associated placement application UUID", examples=["app-d5c519f6-037d-4dce-823f-fa5e0150e519"])
    round_name: str = Field(..., min_length=1, max_length=100, description="Name or number of the interview round", examples=["Technical Round 1: System Design"])
    scheduled_at: datetime = Field(..., description="UTC Timestamp for the interview appointment")
    location_link: Optional[str] = Field(None, max_length=255, description="Video conferencing URL or physical office room details", examples=["https://teams.microsoft.com/l/meetup-join/..."])
    status: Optional[str] = Field("Scheduled", description="Interview round status. Options: Scheduled, Completed, Cancelled, NoShow", examples=["Scheduled"])
    feedback: Optional[str] = Field(None, description="Interviewer feedback, observations, and assessment scores", examples=["Strong system design fundamentals, excellent communication skills. Recommendation: Advance to next round."])

class InterviewScheduleCreate(InterviewScheduleBase):
    pass

class InterviewScheduleUpdate(BaseModel):
    round_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated round name")
    scheduled_at: Optional[datetime] = Field(None, description="Updated scheduled date")
    location_link: Optional[str] = Field(None, max_length=255, description="Updated conference link")
    status: Optional[str] = Field(None, description="Updated interview status")
    feedback: Optional[str] = Field(None, description="Updated evaluation feedback")

class InterviewScheduleResponse(InterviewScheduleBase):
    id: str = Field(..., description="Interview round UUID", examples=["int-7ec11d0a-7dec-11d0-a765-00a0c91e6bf6"])
    created_at: datetime = Field(..., description="UTC Timestamp when the interview appointment was scheduled")

    class Config:
        from_attributes = True


# ===========================================================================
# 4. PLACEMENT RESULT SCHEMAS
# ===========================================================================
class PlacementResultBase(BaseModel):
    application_id: str = Field(..., description="Associated placement application UUID", examples=["app-d5c519f6-037d-4dce-823f-fa5e0150e519"])
    status: Optional[str] = Field("Selected", description="Recruitment decision outcome. Options: Selected, Rejected, Waitlisted", examples=["Selected"])
    offered_package_lpa: Optional[float] = Field(None, ge=0.0, description="Offered annual package package in Lakhs Per Annum (LPA)", examples=[32.0])
    offer_letter_path: Optional[str] = Field(None, max_length=500, description="Relative path or secure URL to the official corporate offer letter PDF", examples=["/offers/2026/john_doe_nvidia.pdf"])
    remarks: Optional[str] = Field(None, description="Special notes regarding hiring parameters or joining terms", examples=["Requires immediate joining. Medical clearance certificate pending."])

class PlacementResultCreate(PlacementResultBase):
    pass

class PlacementResultUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated decision outcome")
    offered_package_lpa: Optional[float] = Field(None, ge=0.0, description="Updated offered package LPA")
    offer_letter_path: Optional[str] = Field(None, max_length=500, description="Updated file path to PDF offer letter")
    remarks: Optional[str] = Field(None, description="Updated remarks")

class PlacementResultResponse(PlacementResultBase):
    id: str = Field(..., description="Result record UUID", examples=["res-12345678-abcd-ef01-2345-6789abcdef01"])
    released_at: datetime = Field(..., description="UTC Timestamp when the placement outcome was released")

    class Config:
        from_attributes = True


# ===========================================================================
# 5. PLACEMENT APPLICATION SCHEMAS
# ===========================================================================
class PlacementApplicationBase(BaseModel):
    drive_id: str = Field(..., description="Target recruitment drive UUID", examples=["drv-39b1deb4-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    student_id: str = Field(..., description="Applying student record UUID", examples=["std-f81d4fae-7dec-11d0-a765-00a0c91e6bf6"])
    resume_id: Optional[str] = Field(None, description="UUID of the selected resume profile attachment", examples=["res-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    status: Optional[str] = Field("Applied", description="Current application status. Options: Applied, Shortlisted, Rejected, Offered", examples=["Applied"])
    notes: Optional[str] = Field(None, description="Candidate-provided special comments or references", examples=["Referred by senior software engineer inside corporate silicon division."])

class PlacementApplicationCreate(PlacementApplicationBase):
    pass

class PlacementApplicationUpdate(BaseModel):
    resume_id: Optional[str] = Field(None, description="Updated resume UUID")
    status: Optional[str] = Field(None, description="Updated application status")
    notes: Optional[str] = Field(None, description="Updated applicant notes")

class PlacementApplicationResponse(PlacementApplicationBase):
    id: str = Field(..., description="Application record UUID", examples=["app-d5c519f6-037d-4dce-823f-fa5e0150e519"])
    applied_at: datetime = Field(..., description="UTC Timestamp when the application was submitted")
    interviews: List[InterviewScheduleResponse] = Field([], description="List of all associated interview rounds scheduled")
    result: Optional[PlacementResultResponse] = Field(None, description="Released recruitment outcome record details if resolved")

    class Config:
        from_attributes = True


# Aggregated schemas for detailed reports
class DriveDetailedResponse(PlacementDriveResponse):
    company: CompanyResponse = Field(..., description="Complete profile details of company organizing recruitment")
    applications_count: int = Field(0, description="Total number of students who applied to this drive", examples=[128])

    class Config:
        from_attributes = True

