"""
Numeric Validator Module
Provides reusable validation functions for numeric fields.
"""

import re
from typing import Optional, Tuple, Any, Dict


def validate_year(year: Any, max_year: int = None) -> Tuple[bool, str]:
    """
    TC-5.2-02: Validate year of incorporation.
    Must be 4-digit integer (YYYY) not in the future.
    """
    from datetime import datetime
    if max_year is None:
        max_year = datetime.now().year

    if year is None:
        return False, "Year cannot be null"
    
    # Strict type check if it's a string like "2001.0" or "01"
    if isinstance(year, str):
        if not year.isdigit() or len(year) != 4:
            return False, f"Invalid year format: {year}"
    
    try:
        year_int = int(year)
    except (ValueError, TypeError):
        return False, f"Year must be an integer, got: {type(year).__name__}"
    
    if year_int < 1800 or year_int > max_year:
        return False, f"Year {year_int} is outside valid range (1800-{max_year})"
    
    return True, "Valid"


def validate_nps(nps: Any) -> Tuple[bool, str]:
    """
    TC-5.2-28: Validate Net Promoter Score.
    Must be integer between -100 and 100.
    """
    if nps is None:
        return False, "NPS cannot be null"
        
    if not isinstance(nps, int):
        return False, f"NPS must be an integer, got {type(nps).__name__}"
        
    if nps < -100 or nps > 100:
        return False, f"NPS {nps} out of range (-100 to 100)"
        
    return True, "Valid"


def validate_positive_number(value: Any, field_name: str) -> Tuple[bool, str]:
    """
    Validate that a numeric field is positive.
    """
    if value is None:
        return False, f"{field_name} cannot be null"
    
    try:
        num = float(value)
        if num <= 0:
            return False, f"{field_name} must be a positive number"
        return True, "Valid"
    except (ValueError, TypeError):
        return False, f"{field_name} must be a numeric value"


def validate_numeric_range(
    value: Any, 
    field_name: str, 
    min_value: Optional[float] = None, 
    max_value: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Validate numeric value is within specified range.
    """
    if value is None:
        return False, f"{field_name} cannot be null"
    
    try:
        num = float(value)
    except (ValueError, TypeError):
        return False, f"{field_name} must be a numeric value"
    
    if min_value is not None and num < min_value:
        return False, f"{field_name} must be at least {min_value}"
    
    if max_value is not None and num > max_value:
        return False, f"{field_name} must be at most {max_value}"
    
    return True, "Valid"


def validate_burn_multiplier(burn: float, arr: float, claimed_multiplier: float) -> Tuple[bool, str]:
    """
    TC_5.1_07: Validate Burn Multiplier calculation.
    """
    if arr == 0:
        return False, "ARR cannot be zero for multiplier calculation"
    actual = burn / arr
    if abs(actual - claimed_multiplier) > 0.01:
        return False, f"Multiplier mismatch: {claimed_multiplier} vs actual {actual:.2f}"
    if actual > 1.0:
        return False, f"Inefficient burn detected (multiplier {actual:.2f} > 1)"
    return True, "Valid"


def validate_runway(capital: float, burn: float, claimed_runway: float) -> Tuple[bool, str]:
    """
    TC_5.1_11: Validate Runway calculation.
    """
    if burn == 0:
        return False, "Burn rate cannot be zero for runway calculation"
    actual = capital / burn
    if abs(actual - claimed_runway) > 0.1:
        return False, f"Runway mismatch: {claimed_runway} vs actual {actual:.1f}"
    if actual < 6:
        return False, f"Critical runway risk ({actual:.1f} months < 6)"
    return True, "Valid"


def validate_hiring_scaling(headcount: int, hiring_velocity: int) -> Tuple[bool, str]:
    """
    TC-3.4-013, 014: Validate hiring velocity vs headcount.
    """
    if hiring_velocity > headcount * 10:
        return False, f"Extreme scaling anomaly: hiring velocity ({hiring_velocity}) > 10x headcount ({headcount})"
    
    if headcount > 1000 and hiring_velocity == 0:
        return False, "Zero hiring for large company is unusual"
        
    return True, "Valid"


def validate_turnover_tenure_consistency(turnover: float, tenure: float) -> Tuple[bool, str]:
    """
    TC-3.4-015, 017: Validate consistency between turnover and average tenure.
    """
    if turnover > 100:
        return False, f"Invalid turnover: {turnover}% exceeds 100% ceiling"
    if turnover > 50 and tenure > 5:
        return False, f"Inconsistent metrics: High turnover ({turnover}%) contradicts high average tenure ({tenure} years)"
    return True, "Valid"


def validate_social_metrics_consistency(platform_counts: Dict[str, int], combined_count: int, sources_exist: bool) -> Tuple[bool, str]:
    """
    TC-3.4-030, 031: Validate social media follower counts.
    """
    if not sources_exist and combined_count > 0:
        return False, "Cannot aggregate followers without source fields"
        
    actual_sum = sum(platform_counts.values())
    if abs(actual_sum - combined_count) > 1:
        return False, f"Follower count mismatch: sum of platforms ({actual_sum}) != combined ({combined_count})"
        
    return True, "Valid"