from .precision_validator import validate_precision

"""
Validators Package
Reusable validation functions for Placement Compass data quality.
"""
from .string_validator import (
    validate_company_name,
    validate_short_name,
    validate_ceo_name,
    validate_contact_name,
    validate_not_null,
    validate_min_length,
    validate_placeholder_prevention,
    normalize_to_title_case,
    normalize_to_lowercase,
    validate_tone_neutrality,
    validate_precision
)

from .numeric_validator import (
    validate_year,
    validate_positive_number,
    validate_numeric_range,
    validate_nps
)

from .url_validator import (
    validate_https_url,
    validate_url_case_insensitive,
    validate_twitter_handle,
    validate_email
)

from .financial_validator import (
    validate_revenue,
    validate_profitability_status,
    validate_sales_motion,
    validate_market_share,
    validate_revenue_mix,
    validate_churn_rate,
    validate_burn_multiplier,
    validate_profitability_consistency,
    validate_market_share_calculation,
    validate_employee_revenue_ratio
)

from .dependency_validator import (
    validate_remote_policy,
    validate_category,
    validate_nature_of_company,
    validate_enum_case_insensitive,
    validate_field_dependency,
    validate_entitydisambiguation,
    validate_chronological_order,
    validate_future_event,
    validate_implied_presence,
    validate_derived_null,
    validate_office_scale_consistency,
    validate_nps_churn_consistency,
    validate_acquisition_competitor_consistency,
    validate_structural_propagation,
    validate_ratio_calculation,
    validate_recency_threshold,
    validate_hiring_consistency,
    validate_source_traceability,
    validate_entity_existence,
    validate_name_consistency
)

__all__ = [
    # String validators
    "validate_company_name",
    "validate_short_name", 
    "validate_ceo_name",
    "validate_contact_name",
    "validate_not_null",
    "validate_min_length",
    "validate_placeholder_prevention",
    "normalize_to_title_case",
    "normalize_to_lowercase",
    "validate_precision",
    "validate_tone_neutrality",
    # Numeric validators
    "validate_year",
    "validate_positive_number",
    "validate_numeric_range",
    "validate_nps",
    # URL validators
    "validate_https_url",
    "validate_url_case_insensitive",
    "validate_twitter_handle",
    "validate_email",
    # Financial validators
    "validate_revenue",
    "validate_profitability_status",
    "validate_sales_motion",
    "validate_market_share",
    "validate_revenue_mix",
    "validate_churn_rate",
    "validate_burn_multiplier",
    "validate_profitability_consistency",
    "validate_market_share_calculation",
    "validate_employee_revenue_ratio",
    # Dependency validators
    "validate_remote_policy",
    "validate_category",
    "validate_nature_of_company",
    "validate_enum_case_insensitive",
    "validate_field_dependency",
    "validate_entitydisambiguation",
    "validate_chronological_order",
    "validate_future_event",
    "validate_implied_presence",
    "validate_derived_null",
    "validate_office_scale_consistency",
    "validate_nps_churn_consistency",
    "validate_acquisition_competitor_consistency",
    "validate_structural_propagation",
    "validate_ratio_calculation",
    "validate_recency_threshold",
    "validate_hiring_consistency",
    "validate_source_traceability",
    "validate_entity_existence",
    "validate_name_consistency",
]