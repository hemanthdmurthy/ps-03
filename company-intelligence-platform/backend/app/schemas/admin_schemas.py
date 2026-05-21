from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# ===========================================================================
# 1. VALIDATION RUNS SCHEMAS
# ===========================================================================
class ValidationResultsDetailResponse(BaseModel):
    id: str
    run_id: str
    company_id: str
    rule_id: str
    category: str
    status: str
    actual_value: Optional[str] = None
    expected_condition: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ValidationRunResponse(BaseModel):
    id: str
    executed_at: datetime
    triggered_by: str
    total_records_checked: int
    passed_records: int
    failed_records: int
    overall_quality_score: float
    execution_time_seconds: float

    class Config:
        from_attributes = True

class ValidationRunDetailResponse(BaseModel):
    run: ValidationRunResponse
    details: List[ValidationResultsDetailResponse]

# ===========================================================================
# 2. AI CORRECTION SUGGESTIONS SCHEMAS (HITL Pipeline)
# ===========================================================================
class CorrectionSuggestionResponse(BaseModel):
    id: str
    company_id: str
    field_name: str
    original_value: Optional[str] = None
    suggested_value: str
    rationale: Optional[str] = None
    confidence: float
    source: str
    status: str  # 'pending', 'applied', 'rejected'
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ===========================================================================
# 3. PLATFORM SYSTEM MONITORING SCHEMAS
# ===========================================================================
class SystemMonitoringResponse(BaseModel):
    total_users: int
    total_students: int
    total_companies: int
    total_validation_runs: int
    total_validation_details: int
    total_correction_suggestions: int
    total_research_sessions: int
    database_file_size_bytes: int
    system_status: str  # 'healthy', 'degraded', 'offline'
