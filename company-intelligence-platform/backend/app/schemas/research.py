from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ResearchRequest(BaseModel):
    company_name: str = Field(..., description="Name of the company to research.")
    industry: Optional[str] = Field("Technology", description="Industry domain of the company.")
    custom_query: Optional[str] = Field(None, description="Optional custom requirements or fields to focus on.")
    max_attempts: Optional[int] = Field(3, ge=1, le=5, description="Maximum validation regeneration attempts.")
    confidence_threshold: Optional[float] = Field(0.85, ge=0.5, le=1.0, description="Minimum score to pass validation.")

class StatusResponse(BaseModel):
    session_id: str
    status: str
    company_name: str
    confidence_score: float
    created_at: str

class ErrorResponse(BaseModel):
    error: str
