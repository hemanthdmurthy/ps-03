from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# ===========================================================================
# 1. DASHBOARD OVERVIEW SCHEMAS
# ===========================================================================
class DashboardOverviewResponse(BaseModel):
    total_students: int
    total_companies: int
    total_drives: int
    total_applications: int
    placed_students_count: int
    placement_ratio: float  # (placed_students / total_students) * 100
    average_package_lpa: float
    highest_package_lpa: float

# ===========================================================================
# 2. PLACEMENT STATISTICS SCHEMAS
# ===========================================================================
class DepartmentStat(BaseModel):
    department: str
    total_students: int
    placed_students: int
    placement_percentage: float
    average_cgpa: float
    average_package_lpa: float

class YearlyStat(BaseModel):
    graduation_year: int
    total_students: int
    placed_students: int
    placement_percentage: float
    average_package_lpa: float

class PlacementStatsResponse(BaseModel):
    departments: List[DepartmentStat]
    yearly_trends: List[YearlyStat]

# ===========================================================================
# 3. COMPANY ANALYTICS SCHEMAS
# ===========================================================================
class CategoryCompanyCount(BaseModel):
    category: str
    company_count: int

class TopHiringCompany(BaseModel):
    company_name: str
    total_applications: int
    total_offers: int
    highest_offered_lpa: float
    average_offered_lpa: float

class CompanyAnalyticsResponse(BaseModel):
    by_category: List[CategoryCompanyCount]
    top_hiring: List[TopHiringCompany]

# ===========================================================================
# 4. PACKAGE ANALYTICS SCHEMAS
# ===========================================================================
class PackageMetrics(BaseModel):
    minimum: float
    average: float
    median: float
    maximum: float

class PackageBucket(BaseModel):
    range_label: str  # e.g. "Below 5 LPA", "5 - 10 LPA", "10 - 15 LPA", "15+ LPA"
    student_count: int

class PackageAnalyticsResponse(BaseModel):
    overall_metrics: PackageMetrics
    package_distribution: List[PackageBucket]

# ===========================================================================
# 5. USER & ACTIVITY ANALYTICS SCHEMAS
# ===========================================================================
class RoleCount(BaseModel):
    role: str
    user_count: int

class ActivityMetrics(BaseModel):
    total_research_sessions: int
    total_validation_runs: int
    total_correction_suggestions: int
    total_token_usage: int

class ActivityAnalyticsResponse(BaseModel):
    users_by_role: List[RoleCount]
    researcher_activity: ActivityMetrics
