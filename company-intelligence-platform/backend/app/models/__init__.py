# app/models/__init__.py
from app.core.database import Base
from app.models.staging_company import StagingCompany, CompanyEmbedding
from app.models.research_session import (
    ResearchSession,
    AgentOutput,
    ValidationLog,
    FinalReport,
    TokenUsageLog
)
from app.models.validation_run import (
    ValidationRun,
    ValidationResultsDetail,
    ValidationCorrectionSuggestion
)
from app.models.user import User
from app.models.student import (
    Student,
    StudentProfile,
    Skill,
    StudentSkill,
    Resume
)
from app.models.placement import (
    PlacementDrive,
    PlacementApplication,
    InterviewSchedule,
    PlacementResult
)
from app.models.notification import Notification

__all__ = [
    "Base",
    "StagingCompany",
    "CompanyEmbedding",
    "ResearchSession",
    "AgentOutput",
    "ValidationLog",
    "FinalReport",
    "TokenUsageLog",
    "ValidationRun",
    "ValidationResultsDetail",
    "ValidationCorrectionSuggestion",
    "User",
    "Student",
    "StudentProfile",
    "Skill",
    "StudentSkill",
    "Resume",
    "PlacementDrive",
    "PlacementApplication",
    "InterviewSchedule",
    "PlacementResult",
    "Notification"
]
