from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict

class ResearchState(TypedDict):
    # --- Session Context ---
    session_id: str
    company_name: str
    industry: Optional[str]
    custom_query: Optional[str]
    already_researched: Optional[bool]

    # --- Pipeline Configuration & Controls ---
    regeneration_attempts: int
    max_attempts: int                  # Default: 3
    confidence_threshold: float         # Default: 0.85

    # --- Agent Execution Outputs ---
    # Stores the raw research outputs of each agent
    agent_data: Dict[str, Any]         # e.g. {"website": {...}, "linkedin": {...}}
    agent_status: Dict[str, str]       # e.g. {"website": "completed", "linkedin": "running"}

    # --- Consolidation State ---
    consolidated_profile: Dict[str, Any] # Merged and normalized draft

    # --- Validation State ---
    validation_passed: bool
    confidence_score: float
    failed_fields: List[str]           # Fields requiring regeneration
    validation_history: List[Dict[str, Any]]

    # --- Final Deliverables ---
    final_report: Optional[Dict[str, Any]]

    # --- Diagnostics ---
    token_usage: Dict[str, Any]        # Structured accounting: {"total": {...}, "by_node": {...}, "by_model": {...}, "by_retry": {...}}
    field_observability: Dict[str, Dict[str, Any]] # Detailed tracking for 163 fields
    conflicting_parameters: List[Dict[str, Any]]
    missing_parameters: List[Dict[str, Any]]
    errors: List[str]
    performance_metrics: Dict[str, Any]
    error_observability: Dict[str, Any]
