"""
Record Validator Module
Provides logic for aggregate record-level validation and quality scoring.
"""

from typing import Dict, Any, Tuple, List


def validate_null_density(record: Dict[str, Any], threshold: int = 5) -> Tuple[bool, str]:
    """
    TC_014_006: Validate excessive NULL values in a single entity record.
    """
    null_count = sum(1 for v in record.values() if v is None)
    if null_count >= threshold:
        return False, f"Excessive NULL values ({null_count} fields); violates completeness threshold"
    return True, "Valid"


def calculate_quality_scores(metrics: Dict[str, float]) -> Dict[str, float]:
    """
    Section 15.5: Weighted scoring model for record quality.
    Weights: Accuracy (40%), Completeness (40%), Recency (20%).
    """
    accuracy = metrics.get("accuracy", 0)
    completeness = metrics.get("completeness", 0)
    recency = metrics.get("recency", 0)
    
    overall = (accuracy * 0.4) + (completeness * 0.4) + (recency * 0.2)
    return {
        "accuracy": accuracy,
        "completeness": completeness,
        "recency": recency,
        "overall": overall
    }


def assign_quality_grade(score: float) -> str:
    """
    Assign A-F grade based on overall quality score.
    """
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


def validate_regional_uniqueness(entities: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    TC-11.3-002: Ensure different regional entities are treated as same record.
    Actually, the requirement says they SHOULD be separate.
    This validator checks if they are accidentally merged.
    """
    # If two entities have same name but different regions, they should have different IDs
    seen_names = {}
    for entity in entities:
        name = entity.get("name")
        region = entity.get("region")
        if name in seen_names and seen_names[name] == region:
            return False, f"Duplicate regional entity detected: {name} ({region})"
        seen_names[name] = region
    return True, "Valid"


def validate_canonical_unification(name1: str, name2: str, mapping_db: Dict[str, str]) -> Tuple[bool, str]:
    """
    TC-11.4-001: Validate that acronym and full name map to same entity.
    """
    id1 = mapping_db.get(name1.upper())
    id2 = mapping_db.get(name2.upper())
    if id1 and id2 and id1 == id2:
        return True, f"Unified: {name1} and {name2} map to ID {id1}"
    return False, f"Fragmented entities: {name1} and {name2} map to different IDs"


def validate_data_type(value: Any, expected_type: type, field_name: str) -> Tuple[bool, str]:
    """
    TC_8.1: Validate that fields match their expected data types.
    """
    if value is not None and not isinstance(value, expected_type):
        return False, f"Data type mismatch for {field_name}: expected {expected_type.__name__}, got {type(value).__name__}"
    return True, "Valid"
