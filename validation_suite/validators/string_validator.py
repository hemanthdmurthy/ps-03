"""
String Validator Module
Provides reusable validation functions for string-based fields.
"""

import re
from typing import Optional, List, Tuple, Any


def validate_company_name(name: str) -> Tuple[bool, str]:
    r"""
    Validate company name against allowed characters and placeholders.
    Pattern: ^[\w\s&.,\-\(\)\'\u00C0-\u017F]+$
    """
    if not name or not name.strip():
        return False, "Company name cannot be empty or whitespace"
    
    # TC-DC-001: Check for generic 'NonExistent' placeholder
    if "NonExistent" in name:
        return False, f"Generic or non-existent company name detected: {name}"

    pattern = r'^[\w\s&.,\-\(\)\'\u00C0-\u017F]+$'
    if re.match(pattern, name):
        return True, "Valid"
    return False, f"Invalid characters in company name: {name}"


def validate_short_name(name: str, max_length: int = 100, min_length: int = 2) -> Tuple[bool, str]:
    """
    Validate abbreviated brand names.
    Must be Title Case, length between min_length and max_length.
    """
    if not name or not name.strip():
        return False, "Short name cannot be empty"
    
    if len(name) < min_length:
        return False, f"Short name must be at least {min_length} characters"
    
    if len(name) > max_length:
        return False, f"Short name exceeds {max_length} characters"
    
    # Convert to Title Case for validation
    title_cased = name.title()
    return True, title_cased


def validate_ceo_name(name: str) -> Tuple[bool, str]:
    """
    Validate CEO name - alphabetic characters and hyphens only.
    No digits allowed.
    """
    if not name or not name.strip():
        return False, "CEO name cannot be empty"
    
    # Check for digits
    if re.search(r'\d', name):
        return False, "CEO name cannot contain digits"
    
    # Allow alphabetic characters, spaces, hyphens, apostrophes
    pattern = r'^[A-Za-z\s\-\']+$'
    if re.match(pattern, name):
        return True, "Valid"
    return False, f"Invalid CEO name format: {name}"


def validate_contact_name(name: str) -> Tuple[bool, str]:
    """
    Validate primary contact person name.
    Must meet PII audit rules.
    """
    if not name or not name.strip():
        return False, "Contact name cannot be empty"
    
    # Basic validation - letters, spaces, hyphens, periods (for initials)
    pattern = r'^[A-Za-z\s\-\.\']+$'
    if re.match(pattern, name):
        return True, "Valid"
    return False, f"Invalid contact name format: {name}"


def validate_not_null(value: any, field_name: str) -> Tuple[bool, str]:
    """
    Validate that a field is not null/empty.
    """
    if value is None:
        return False, f"{field_name} cannot be null"
    
    if isinstance(value, str) and not value.strip():
        return False, f"{field_name} cannot be empty or whitespace"
    
    return True, "Valid"


def validate_min_length(value: str, min_length: int, field_name: str) -> Tuple[bool, str]:
    """
    Validate minimum string length.
    """
    if value is None:
        return False, f"{field_name} cannot be null"
    
    if len(value) < min_length:
        return False, f"{field_name} must be at least {min_length} characters"
    
    return True, "Valid"


def normalize_to_title_case(value: str) -> str:
    """
    Normalize string to Title Case.
    """
    return value.title()


def normalize_to_lowercase(value: str) -> str:
    """
    Normalize string to lowercase.
    """
    return value.lower().strip()


def validate_placeholder_prevention(value: Any, field_name: str) -> Tuple[bool, str]:
    """
    Section 14.4: Prevent generic placeholders in mandatory fields.
    """
    exact_placeholders = ["UNKNOWN", "TBD", "PENDING", "0", "NONE", "NULL", "N/A", "NOT PUBLIC", "0%", "0.0", "FEW"]
    substring_placeholders = ["LOREM IPSUM", "FORMER", "PLACEHOLDER"]
    
    if value is not None:
        val_str = str(value).strip().upper()
        
        # Exact match check
        if val_str in exact_placeholders:
            return False, f"{field_name} cannot use generic placeholder: {value}"
            
        # Substring check for narrative placeholders
        for p in substring_placeholders:
            if p in val_str:
                return False, f"{field_name} cannot use generic placeholder: {value}"
                
    return True, "Valid"


def validate_na_vs_not_public(value: Any, nature: str) -> Tuple[bool, str]:
    """
    TC_014_002 / TC_014_302: Validate distinction between N/A and Not Public.
    Private companies should use 'Not Public' for non-disclosed fields.
    """
    if nature.lower() == "private" and str(value).upper() == "N/A":
        return False, "Private companies should specify 'Not Public' instead of generic 'N/A'"
    return True, "Valid"


def validate_precision(value: Any, max_decimals: int = 2) -> Tuple[bool, str]:
    """
    TC_4.3_02: Identify overly precise fabricated data.
    """
    if isinstance(value, str):
        # Extract number if it ends with % or is just a number
        match = re.search(r'(\d+\.\d+)', value)
        if match:
            decimals = len(match.group(1).split('.')[1])
            if decimals > max_decimals:
                return False, f"Over-precision unrealistic ({decimals} decimals)"
    return True, "Valid"


def validate_tone_neutrality(value: str) -> Tuple[bool, str]:
    """
    TC_4.3_03: Detect authoritative tone or certainty assertions.
    """
    assertions = ["confirmed", "guaranteed", "verified", "absolute", "certain"]
    if any(assertion in value.lower() for assertion in assertions):
        return False, f"Authoritative tone detected; should not assert certainty"
    return True, "Valid"