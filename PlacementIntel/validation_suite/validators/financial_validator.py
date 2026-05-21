import re
from typing import Tuple, Optional, List, Any


def validate_revenue(revenue: any) -> Tuple[bool, str]:
    """
    TC-3.4-034, 035: Validate revenue field.
    Must not be null. Supports numeric and formatted strings ($50B, $50,000).
    """
    if revenue is None or revenue == "":
        return False, "Revenue cannot be null"
    
    if isinstance(revenue, bool) or revenue == 0 or revenue == "0":
        return False, "Revenue cannot be 0 or False"

    if isinstance(revenue, (int, float)):
        if revenue <= 0:
            return False, "Revenue cannot be 0 or negative"
        return True, "Valid"

    if isinstance(revenue, str):
        # Reject negative strings or zero strings
        if revenue.startswith("-") or "$-" in revenue or revenue == "$0":
            return False, "Revenue cannot be 0 or negative"
        
        # MUST start with $ for string format
        if not revenue.startswith("$"):
            return False, f"Formatted revenue must start with $, got: {revenue}"

        # Regex for $50.3B or $50,000
        pattern = r'^\$\d{1,3}(,\d{3})*(\.\d+)?(B|M|K)?$'
        if not re.match(pattern, revenue.replace(" ", "")):
            return False, f"Invalid revenue format: {revenue}"
            
    return True, "Valid"


def validate_market_share(share: any) -> Tuple[bool, str]:
    """
    Validate market share percentage. MUST contain % if string.
    """
    if share is None:
        return False, "Market share cannot be null"
        
    try:
        if isinstance(share, str):
            if "%" not in share:
                return False, f"Market share string must contain %, got: {share}"
            val = float(share.replace("%", "").strip())
        else:
            val = float(share)
            
        if val < 0 or val > 100:
            return False, f"Market share {val}% out of range (0-100)"
        return True, "Valid"
    except:
        return False, f"Invalid market share format: {share}"


def validate_profitability_status(status: str) -> Tuple[bool, str]:
    """
    Validate profitability status enum.
    Must match predefined Enums.
    """
    valid_enums = ["Profitable", "Non-Profit", "Break Even", "Loss Making"]
    
    if not status or not status.strip():
        return False, "Profitability status cannot be empty"
    
    # Case-insensitive match
    status_normalized = status.strip()
    for valid_enum in valid_enums:
        if status_normalized.lower() == valid_enum.lower():
            return True, valid_enum
    
    return False, f"Invalid profitability status: {status}. Must be one of {valid_enums}"


def validate_sales_motion(motion: str) -> Tuple[bool, str]:
    """
    Validate sales motion enum.
    Must match predefined Enums.
    """
    valid_enums = ["Product-Led", "Sales-Led", "Marketing-Led", "Partner-Led"]
    
    if motion is None:
        return False, "Sales motion cannot be null (Not Null field)"
    
    if not motion.strip():
        return False, "Sales motion cannot be empty"
    
    # Case-insensitive match
    motion_normalized = motion.strip()
    for valid_enum in valid_enums:
        if motion_normalized.lower() == valid_enum.lower():
            return True, valid_enum
    
    return False, f"Invalid sales motion: {motion}. Must be one of {valid_enums}"


def validate_profitability_consistency(status: str, annual_profits: float) -> Tuple[bool, str]:
    """
    TC-3.4-032, 033, 4.3-04: Validate consistency between profitability status and actual profits.
    """
    status_lower = status.lower()
    if "profitable" in status_lower and annual_profits <= 0:
        return False, "Profitable status cannot have negative or zero profits"
    if "loss" in status_lower and annual_profits >= 0:
        return False, "Loss-making status should have negative profits"
    return True, "Valid"


def validate_market_share_hierarchy(tam: float, sam: float, som: float) -> Tuple[bool, str]:
    """
    TC-3.4-046, 048, 049: Validate TAM > SAM > SOM hierarchy.
    """
    if sam > tam:
        return False, "SAM cannot exceed TAM"
    if som > sam:
        return False, "SOM cannot exceed SAM"
    return True, "Valid"


def validate_market_share_calculation(tam: float, revenues: float, reported_share: float) -> Tuple[bool, str]:
    """
    TC-3.4-034, 035, 5.5-04: Validate reported market share against revenues and TAM.
    """
    if revenues > tam:
        return False, "Revenues cannot exceed TAM"
    
    if tam == 0:
        return False, "TAM cannot be zero for market share calculation"
        
    implied_share = (revenues / tam) * 100
    if abs(implied_share - reported_share) > 5:
        return False, f"Market share mismatch: implied {implied_share:.1f}% vs reported {reported_share}%"
    
    return True, "Valid"


def validate_funding_consistency(total_capital: float, max_round: float = 0, rounds: List[float] = None) -> Tuple[bool, str]:
    """
    TC-3.4-036, 037: Validate total capital against individual rounds.
    """
    if max_round > total_capital:
        return False, f"Total capital ({total_capital}) must be at least the largest single round ({max_round})"
    
    if rounds:
        actual_sum = sum(rounds)
        if abs(actual_sum - total_capital) > 0.1:
            return False, f"Funding mismatch: sum of rounds ({actual_sum}) != total capital ({total_capital})"
            
    return True, "Valid"


def validate_concentration_risk(revenue_mix: str, risk_flag: str) -> Tuple[bool, str]:
    """
    TC-3.4-040: Validate if concentration risk is correctly flagged.
    """
    try:
        # Example: "95%/5%"
        primary_percentage = float(revenue_mix.split("/")[0].replace("%", ""))
        if primary_percentage > 20 and risk_flag.lower() == "no":
            return False, f"Concentration risk not flagged: {primary_percentage}% revenue from single client"
        return True, "Valid"
    except:
        return False, f"Invalid revenue mix format: {revenue_mix}"


def validate_revenue_mix(mix: str) -> Tuple[bool, str]:
    """
    Validate revenue mix ratio (sum must be 100).
    """
    if not mix:
        return False, "Revenue mix cannot be empty"
        
    try:
        parts = mix.replace("%", "").split("/")
        total = sum(float(p.strip()) for p in parts)
        if abs(total - 100) > 0.1:
            return False, f"Revenue mix total {total}% != 100%"
        return True, "Valid"
    except:
        return False, f"Invalid revenue mix format: {mix}"


def validate_churn_rate(churn: any) -> Tuple[bool, str]:
    """
    Validate churn rate percentage. MUST contain % if string.
    """
    if churn is None:
        return False, "Churn rate cannot be null"
        
    try:
        if isinstance(churn, str):
            if "%" not in churn:
                return False, f"Churn rate string must contain %, got: {churn}"
            val = float(churn.replace("%", "").strip())
        else:
            val = float(churn)
            
        if val < 0 or val > 100:
            return False, f"Churn rate {val}% out of range (0-100)"
        return True, "Valid"
    except:
        return False, f"Invalid churn rate format: {churn}"


def validate_burn_multiplier(multiplier: Any) -> Tuple[bool, str]:
    """
    Validate burn multiplier.
    Threshold: > 5.0 is inefficient.
    """
    if multiplier is None:
        return False, "Burn multiplier cannot be null"
    
    try:
        val = float(multiplier)
        import math
        if math.isinf(val) or math.isnan(val):
            return False, "Burn multiplier is infinite or NaN"
        if val < 0:
            return False, "Burn multiplier cannot be negative"
        if val > 5.0:
            return False, f"Burn multiplier {val} exceeds sustainable threshold (>5)"
        return True, "Valid"
    except (ValueError, TypeError):
        return False, f"Burn multiplier must be a number, got {type(multiplier).__name__}"


def validate_employee_revenue_ratio(employees: Any, revenue: float) -> Tuple[bool, str]:
    """
    TC-4.3-06: Detect unrealistic revenue for employee size.
    """
    try:
        if isinstance(employees, str) and "-" in employees:
            max_employees = int(employees.split("-")[-1])
        else:
            max_employees = int(employees)
            
        if max_employees < 50 and revenue > 1000000000:
            return False, f"Unrealistic revenue (${revenue}) for small headcount ({max_employees})"
        return True, "Valid"
    except:
        return False, "Invalid employee count format"