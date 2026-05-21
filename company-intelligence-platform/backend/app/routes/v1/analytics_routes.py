from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.cache_service import cache_response
from sqlalchemy import func, distinct, case, select

from app.dependencies.db_deps import get_async_db
from app.models.user import User
from app.models.student import Student
from app.models.staging_company import StagingCompany
from app.models.placement import PlacementDrive, PlacementApplication, PlacementResult
# Defensive import of Research/Agent models
try:
    from app.models.research import ResearchSession, ValidationRun, ValidationCorrectionSuggestion, TokenUsageLog
except ImportError:
    ResearchSession = None
    ValidationRun = None
    ValidationCorrectionSuggestion = None
    TokenUsageLog = None

from app.schemas.analytics_schemas import (
    DashboardOverviewResponse, PlacementStatsResponse, DepartmentStat, YearlyStat,
    CompanyAnalyticsResponse, CategoryCompanyCount, TopHiringCompany,
    PackageAnalyticsResponse, PackageMetrics, PackageBucket,
    ActivityAnalyticsResponse, RoleCount, ActivityMetrics
)
from app.dependencies.auth_deps import RoleChecker

router = APIRouter(prefix="/analytics", tags=["Analytics & Dashboards"])
viewer_or_higher = RoleChecker(["admin", "researcher", "viewer"])

@router.get("/dashboard", response_model=DashboardOverviewResponse, dependencies=[Depends(viewer_or_higher)])
@cache_response(ttl=300, key_prefix="analytics")
async def get_dashboard_overview(request: Request, db: AsyncSession = Depends(get_async_db)):
    total_students = (await db.execute(select(func.count(Student.id)))).scalar() or 0
    total_companies = (await db.execute(select(func.count(StagingCompany.company_id)))).scalar() or 0
    total_drives = (await db.execute(select(func.count(PlacementDrive.id)))).scalar() or 0
    total_applications = (await db.execute(select(func.count(PlacementApplication.id)))).scalar() or 0
    placed_students_count = (await db.execute(select(func.count(distinct(PlacementApplication.student_id))).filter(PlacementApplication.status == "Offered"))).scalar() or 0
    placement_ratio = (placed_students_count / total_students * 100.0) if total_students > 0 else 0.0
    average_package = (await db.execute(select(func.avg(PlacementResult.offered_package_lpa)).filter(PlacementResult.status == "Selected"))).scalar() or 0.0
    highest_package = (await db.execute(select(func.max(PlacementResult.offered_package_lpa)).filter(PlacementResult.status == "Selected"))).scalar() or 0.0
    return DashboardOverviewResponse(total_students=total_students, total_companies=total_companies, total_drives=total_drives, total_applications=total_applications, placed_students_count=placed_students_count, placement_ratio=round(placement_ratio, 2), average_package_lpa=round(average_package, 2), highest_package_lpa=round(highest_package, 2))


@router.get("/placements", response_model=PlacementStatsResponse, dependencies=[Depends(viewer_or_higher)])
@cache_response(ttl=300, key_prefix="analytics")
async def get_placement_stats(request: Request, db: AsyncSession = Depends(get_async_db)):
    placed_select = select(PlacementApplication.student_id).filter(PlacementApplication.status == "Offered")
    dept_raw = (await db.execute(select(Student.department, func.count(Student.id).label("total"), func.sum(case((Student.id.in_(placed_select), 1), else_=0)).label("placed"), func.avg(Student.cgpa).label("avg_cgpa")).group_by(Student.department))).all()
    dept_pkg_raw = (await db.execute(select(Student.department, func.avg(PlacementResult.offered_package_lpa)).join(PlacementApplication, Student.id == PlacementApplication.student_id).join(PlacementResult, PlacementApplication.id == PlacementResult.application_id).filter(PlacementResult.status == "Selected").group_by(Student.department))).all()
    dept_packages = dict(dept_pkg_raw)
    departments = []
    for row in dept_raw:
        dept_name = row[0] or "Unknown"; tot = row[1] or 0; plc = row[2] or 0; ratio = (plc / tot * 100.0) if tot > 0 else 0.0; avg_cgpa = row[3] or 0.0; avg_lpa = dept_packages.get(dept_name, 0.0) or 0.0
        departments.append(DepartmentStat(department=dept_name, total_students=tot, placed_students=plc, placement_percentage=round(ratio, 2), average_cgpa=round(avg_cgpa, 2), average_package_lpa=round(avg_lpa, 2)))
    year_raw = (await db.execute(select(Student.graduation_year, func.count(Student.id).label("total"), func.sum(case((Student.id.in_(placed_select), 1), else_=0)).label("placed")).group_by(Student.graduation_year))).all()
    year_pkg_raw = (await db.execute(select(Student.graduation_year, func.avg(PlacementResult.offered_package_lpa)).join(PlacementApplication, Student.id == PlacementApplication.student_id).join(PlacementResult, PlacementApplication.id == PlacementResult.application_id).filter(PlacementResult.status == "Selected").group_by(Student.graduation_year))).all()
    year_packages = dict(year_pkg_raw)
    yearly_trends = []
    for row in year_raw:
        yr = row[0] or 0; tot = row[1] or 0; plc = row[2] or 0; ratio = (plc / tot * 100.0) if tot > 0 else 0.0; avg_lpa = year_packages.get(yr, 0.0) or 0.0
        yearly_trends.append(YearlyStat(graduation_year=yr, total_students=tot, placed_students=plc, placement_percentage=round(ratio, 2), average_package_lpa=round(avg_lpa, 2)))
    return PlacementStatsResponse(departments=departments, yearly_trends=yearly_trends)


@router.get("/companies", response_model=CompanyAnalyticsResponse, dependencies=[Depends(viewer_or_higher)])
@cache_response(ttl=300, key_prefix="analytics")
async def get_company_analytics(request: Request, db: AsyncSession = Depends(get_async_db)):
    cats_raw = (await db.execute(select(StagingCompany.category, func.count(StagingCompany.company_id)).group_by(StagingCompany.category))).all()
    by_category = [CategoryCompanyCount(category=row[0] or "Other", company_count=row[1] or 0) for row in cats_raw]
    top_raw = (await db.execute(select(StagingCompany.name, func.count(PlacementApplication.id).label("apps"), func.sum(case((PlacementApplication.status == "Offered", 1), else_=0)).label("offers"), func.max(PlacementResult.offered_package_lpa).label("max_lpa"), func.avg(PlacementResult.offered_package_lpa).label("avg_lpa")).join(PlacementDrive, StagingCompany.company_id == PlacementDrive.company_id).join(PlacementApplication, PlacementDrive.id == PlacementApplication.drive_id).outerjoin(PlacementResult, PlacementApplication.id == PlacementResult.application_id).group_by(StagingCompany.name).order_by(func.sum(case((PlacementApplication.status == "Offered", 1), else_=0)).desc()).limit(10))).all()
    top_hiring = [TopHiringCompany(company_name=row[0], total_applications=row[1] or 0, total_offers=row[2] or 0, highest_offered_lpa=round(row[3] or 0.0, 2), average_offered_lpa=round(row[4] or 0.0, 2)) for row in top_raw]
    return CompanyAnalyticsResponse(by_category=by_category, top_hiring=top_hiring)


@router.get("/packages", response_model=PackageAnalyticsResponse, dependencies=[Depends(viewer_or_higher)])
@cache_response(ttl=300, key_prefix="analytics")
async def get_package_analytics(request: Request, db: AsyncSession = Depends(get_async_db)):
    packages_raw = (await db.execute(select(PlacementResult.offered_package_lpa).filter(PlacementResult.status == "Selected").order_by(PlacementResult.offered_package_lpa))).all()
    packages = [r[0] for r in packages_raw if r[0] is not None]
    if packages:
        n = len(packages); median = packages[n // 2] if n % 2 == 1 else (packages[(n // 2) - 1] + packages[n // 2]) / 2.0
        minimum = packages[0]; maximum = packages[-1]; average = sum(packages) / len(packages)
    else:
        median = minimum = maximum = average = 0.0
    overall_metrics = PackageMetrics(minimum=round(minimum, 2), average=round(average, 2), median=round(median, 2), maximum=round(maximum, 2))
    b1 = (await db.execute(select(func.count(PlacementResult.id)).filter(PlacementResult.status == "Selected", PlacementResult.offered_package_lpa < 5.0))).scalar() or 0
    b2 = (await db.execute(select(func.count(PlacementResult.id)).filter(PlacementResult.status == "Selected", PlacementResult.offered_package_lpa >= 5.0, PlacementResult.offered_package_lpa < 10.0))).scalar() or 0
    b3 = (await db.execute(select(func.count(PlacementResult.id)).filter(PlacementResult.status == "Selected", PlacementResult.offered_package_lpa >= 10.0, PlacementResult.offered_package_lpa < 15.0))).scalar() or 0
    b4 = (await db.execute(select(func.count(PlacementResult.id)).filter(PlacementResult.status == "Selected", PlacementResult.offered_package_lpa >= 15.0))).scalar() or 0
    package_distribution = [PackageBucket(range_label="Below 5 LPA", student_count=b1), PackageBucket(range_label="5 - 10 LPA", student_count=b2), PackageBucket(range_label="10 - 15 LPA", student_count=b3), PackageBucket(range_label="15+ LPA", student_count=b4)]
    return PackageAnalyticsResponse(overall_metrics=overall_metrics, package_distribution=package_distribution)


@router.get("/activity", response_model=ActivityAnalyticsResponse, dependencies=[Depends(viewer_or_higher)])
@cache_response(ttl=300, key_prefix="analytics")
async def get_user_activity_analytics(request: Request, db: AsyncSession = Depends(get_async_db)):
    roles_raw = (await db.execute(select(User.role, func.count(User.id)).group_by(User.role))).all()
    users_by_role = [RoleCount(role=row[0] or "viewer", user_count=row[1] or 0) for row in roles_raw]
    total_research = total_val_runs = total_suggestions = total_token_usage = 0
    if ResearchSession is not None:
        try: total_research = (await db.execute(select(func.count(ResearchSession.session_id)))).scalar() or 0
        except Exception: pass
    if ValidationRun is not None:
        try: total_val_runs = (await db.execute(select(func.count(ValidationRun.run_id)))).scalar() or 0
        except Exception: pass
    if ValidationCorrectionSuggestion is not None:
        try: total_suggestions = (await db.execute(select(func.count(ValidationCorrectionSuggestion.suggestion_id)))).scalar() or 0
        except Exception: pass
    if TokenUsageLog is not None:
        try: total_token_usage = (await db.execute(select(func.sum(TokenUsageLog.total_tokens)))).scalar() or 0
        except Exception: pass
    researcher_activity = ActivityMetrics(total_research_sessions=total_research, total_validation_runs=total_val_runs, total_correction_suggestions=total_suggestions, total_token_usage=total_token_usage)
    return ActivityAnalyticsResponse(users_by_role=users_by_role, researcher_activity=researcher_activity)
