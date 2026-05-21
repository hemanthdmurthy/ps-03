"""
Validation Categorization System
================================
Defines categorical groupings for the 300+ validation test cases 
so that metrics are reported cleanly by category on dashboards.
"""

from enum import Enum
from typing import Dict, Any, List

class ValidationCategory(str, Enum):
    SCHEMA_ERROR = "schema_error"
    MISSING_FIELD = "missing_field"
    FORMATTING_ISSUE = "formatting_issue"
    DUPLICATE_CONFLICT = "duplicate_conflict"
    INVALID_DOMAIN = "invalid_domain"
    INCOMPLETE_METADATA = "incomplete_metadata"

# Dictionary mapping specific test-case prefixes and full IDs to categories
RULE_CATEGORIES_MAP: Dict[str, ValidationCategory] = {
    # --- Format Violations (TC-FMT) ---
    "TC-FMT-001": ValidationCategory.FORMATTING_ISSUE,       # Company Name format
    "TC-FMT-003": ValidationCategory.FORMATTING_ISSUE,       # Logo HTTPS URL format
    "TC-FMT-005": ValidationCategory.FORMATTING_ISSUE,       # Incorporation Year format
    "TC-FMT-014": ValidationCategory.FORMATTING_ISSUE,       # Website URL format
    "TC-FMT-020": ValidationCategory.FORMATTING_ISSUE,       # Twitter Handle format
    "TC-FMT-021": ValidationCategory.FORMATTING_ISSUE,       # Contact Person Email format
    "TC-LIST-01": ValidationCategory.FORMATTING_ISSUE,       # Comma Separated Locations

    # --- Cross-Field Consistency & Logical Integrity (TC-3.4 / TC-5.5) ---
    "TC-3.4-001": ValidationCategory.DUPLICATE_CONFLICT,     # Name Consistency (short vs full)
    "TC-3.4-004": ValidationCategory.DUPLICATE_CONFLICT,     # Logo consistency
    "TC-3.4-005": ValidationCategory.DUPLICATE_CONFLICT,     # Nature & category consistency
    "TC-3.4-009": ValidationCategory.DUPLICATE_CONFLICT,     # Office locations consistency
    "TC-3.4-051": ValidationCategory.DUPLICATE_CONFLICT,     # GTM Motion consistency
    "TC-5.5-02":  ValidationCategory.DUPLICATE_CONFLICT,     # Office Scale vs Headcount consistency
    "TC-5.5-03":  ValidationCategory.DUPLICATE_CONFLICT,     # NPS vs Churn consistency
    "TC-STRUCT-08": ValidationCategory.DUPLICATE_CONFLICT,   # Acquisition Competitor conflict

    # --- Structural/Schema Integrity (TC-STRUCT / TC-11) ---
    "TC-STRUCT-04": ValidationCategory.SCHEMA_ERROR,         # Structural propagation
    "TC-11.2-012": ValidationCategory.SCHEMA_ERROR,          # Inheritance logic checks
    "TC-FMT-TYP":  ValidationCategory.SCHEMA_ERROR,          # Type mismatch errors
    "TC-FMT-LEN":  ValidationCategory.SCHEMA_ERROR,          # Length constraint errors

    # --- Missing Fields & Completeness (TC-014 / TC-14) ---
    "TC-014-004": ValidationCategory.MISSING_FIELD,          # Implied presence null dependency
    "TC-014-011": ValidationCategory.MISSING_FIELD,          # Implied presence null dependency 2
    "TC-14.1-001": ValidationCategory.MISSING_FIELD,         # Overview placeholder (Data missing)
    "TC-14.1-002": ValidationCategory.MISSING_FIELD,         # Vision Statement placeholder
    "TC-14.1-003": ValidationCategory.MISSING_FIELD,         # Mission Statement placeholder
    "TC-14.1-004": ValidationCategory.MISSING_FIELD,         # Employee Size placeholder
    "TC-14.1-005": ValidationCategory.MISSING_FIELD,         # Nature of Company placeholder
    "TC-14.1-006": ValidationCategory.MISSING_FIELD,         # Category placeholder
    "TC-014-ALL":  ValidationCategory.MISSING_FIELD,         # General null density

    # --- Domain, Connection & Reachability ---
    "TC-DOM-001": ValidationCategory.INVALID_DOMAIN,         # Broken website link
    "TC-DOM-002": ValidationCategory.INVALID_DOMAIN,         # Unregistered domain
    "TC-DOM-003": ValidationCategory.INVALID_DOMAIN,         # Mailbox/MX record invalid

    # --- Incomplete Placement Metadata & Recency (TC-15) ---
    "TC-15.3-001": ValidationCategory.INCOMPLETE_METADATA,   # Quality Recency check
    "TC-15.2-204": ValidationCategory.INCOMPLETE_METADATA,   # Source traceability
    "TC-META-GTM": ValidationCategory.INCOMPLETE_METADATA,   # Missing core classification
}

def get_category_for_rule(rule_id: str) -> ValidationCategory:
    """
    Lookup the quality category for a given rule_id.
    Fallback to a logical categorization based on prefix mapping if not explicitly defined.
    """
    # Direct match lookup
    if rule_id in RULE_CATEGORIES_MAP:
        return RULE_CATEGORIES_MAP[rule_id]
        
    # Prefix mapping fallback
    rule_id_upper = rule_id.upper()
    if rule_id_upper.startswith("TC-FMT"):
        return ValidationCategory.FORMATTING_ISSUE
    elif rule_id_upper.startswith("TC-014") or rule_id_upper.startswith("TC-14"):
        return ValidationCategory.MISSING_FIELD
    elif rule_id_upper.startswith("TC-3.4") or rule_id_upper.startswith("TC-5.5"):
        return ValidationCategory.DUPLICATE_CONFLICT
    elif rule_id_upper.startswith("TC-STRUCT") or rule_id_upper.startswith("TC-11"):
        return ValidationCategory.SCHEMA_ERROR
    elif rule_id_upper.startswith("TC-15") or rule_id_upper.startswith("TC-META"):
        return ValidationCategory.INCOMPLETE_METADATA
    elif rule_id_upper.startswith("TC-DOM"):
        return ValidationCategory.INVALID_DOMAIN
        
    # Default fallback
    return ValidationCategory.SCHEMA_ERROR

def get_category_label(category: ValidationCategory) -> str:
    """
    Returns a human-readable display label for a category.
    """
    labels = {
        ValidationCategory.SCHEMA_ERROR: "Schema & Type Integrity",
        ValidationCategory.MISSING_FIELD: "Missing Fields & Completeness",
        ValidationCategory.FORMATTING_ISSUE: "Formatting & Standards",
        ValidationCategory.DUPLICATE_CONFLICT: "Duplicates & Data Conflicts",
        ValidationCategory.INVALID_DOMAIN: "Reachability & Domains",
        ValidationCategory.INCOMPLETE_METADATA: "Classification & Placement Metadata"
    }
    return labels.get(category, "General Quality Constraint")
