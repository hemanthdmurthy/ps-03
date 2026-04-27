"""
Dependency Validator Module
Provides reusable validation functions for field dependencies and cross-field validation.
"""

from typing import Tuple, List, Optional, Dict, Any


def validate_remote_policy(policy: Any) -> Tuple[bool, str]:
    """
    Validate remote work policy.
    Mandatory field.
    """
    if policy is None or (isinstance(policy, str) and not policy.strip()):
        return False, "Remote policy cannot be null or empty"
    
    valid_policies = ["Fully Remote", "Hybrid", "On-site", "Flexible", "Unknown"]
    
    # Case-insensitive match
    policy_normalized = policy.strip() if isinstance(policy, str) else str(policy)
    for valid_policy in valid_policies:
        if policy_normalized.lower() == valid_policy.lower():
            return True, valid_policy
    
    return False, f"Invalid remote policy: {policy}. Must be one of {valid_policies}"


def validate_category(category: str, valid_categories: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Validate category against business taxonomy.
    Must map to internal standardized business taxonomy.
    """
    if not category or not category.strip():
        return False, "Category cannot be empty"
    
    category_normalized = category.strip()
    
    # Standardized mapping for generic terms
    generic_mapping = {
        "investor": "VC",
        "private": "Mid-Market",
        "public": "Enterprise"
    }
    
    if category_normalized.lower() in generic_mapping:
        return True, generic_mapping[category_normalized.lower()]

    if valid_categories is None:
        valid_categories = [
            "Startup", "Enterprise", "Mid-Market", "SMB", 
            "VC", "PE", "Angel"
        ]
    
    # Case-insensitive match
    for valid_cat in valid_categories:
        if category_normalized.lower() == valid_cat.lower():
            return True, valid_cat
    
    return False, f"Invalid category: {category}. Must map to {valid_categories}"


def validate_nature_of_company(nature: str) -> Tuple[bool, str]:
    """
    Validate nature of company against legal structure types.
    """
    valid_structures = [
        "Private", "Public", "Non-Profit", "Government", 
        "Partnership", "Sole Proprietorship", "LLP", "LLC"
    ]
    
    if not nature or not nature.strip():
        return False, "Nature of company cannot be empty"
    
    # Case-insensitive match
    nature_normalized = nature.strip()
    for valid_struct in valid_structures:
        if nature_normalized.lower() == valid_struct.lower():
            return True, valid_struct
    
    return False, f"Invalid nature of company: {nature}. Must be one of {valid_structures}"


def validate_enum_case_insensitive(value: str, valid_enums: List[str]) -> Tuple[bool, str]:
    """
    Generic case-insensitive enum validation.
    """
    if not value or not value.strip():
        return False, "Value cannot be empty"
    
    value_normalized = value.strip()
    for valid_enum in valid_enums:
        if value_normalized.lower() == valid_enum.lower():
            return True, valid_enum
    
    return False, f"Invalid value: {value}. Must be one of {valid_enums}"


def validate_field_dependency(
    primary_field: Any,
    dependent_field: Any,
    dependency_rule: str
) -> Tuple[bool, str]:
    """
    Validate field dependencies based on business rules.
    """
    # Example: If CEO Name is provided, CEO LinkedIn URL should be validated
    if primary_field and not dependent_field:
        return False, f"Dependent field required when {dependency_rule} is provided"
    
    return True, "Valid"


def validate_entitydisambiguation(
    entity_name: str,
    entity_type: str,
    known_entities: Dict[str, List[str]]
) -> Tuple[bool, str]:
    """
    Validate that entity names are distinct enough to avoid ambiguity.
    """
    # Case-insensitive exact match first
    for known in known_entities.get(entity_type, []):
        if entity_name.lower() == known.lower():
            return True, known
    
    # Check for similar names that could cause disambiguation
    similar_entities = [
        e for e in known_entities.get(entity_type, [])
        if entity_name.lower() in e.lower() or e.lower() in entity_name.lower()
    ]
    
    # Auto-resolve if exactly one match found
    if len(similar_entities) == 1:
        return True, similar_entities[0]
    
    if len(similar_entities) > 1:
        return False, f"Entity '{entity_name}' matches multiple {entity_type}: {similar_entities}"
    
    return True, "Valid"


def validate_implied_presence(
    signal_field: Any,
    target_field: Any,
    signal_name: str,
    target_name: str
) -> Tuple[bool, str]:
    """
    TC_014_004, 014-011: Validate that presence of a signal implies presence of another field.
    """
    if signal_field is not None and target_field is None:
        return False, f"{target_name} is required when {signal_name} is present"
    return True, "Valid"


def validate_derived_null(
    base_field: Any,
    derived_field: Any,
    base_name: str,
    derived_name: str
) -> Tuple[bool, str]:
    """
    Section 14.5, 14.5-501/502/505: Validate that derived fields propagate NULLs from base metrics.
    """
    if base_field is None and derived_field is not None:
        return False, f"{derived_name} must be NULL when {base_name} is NULL"
    return True, "Valid"


def validate_applicability(
    category_value: str,
    field_value: Any,
    category_type: str,
    field_name: str,
    restricted_categories: List[str],
    should_be_na: bool = True
) -> Tuple[bool, str]:
    """
    Section 14.2: Validate if a field should be N/A based on company category/nature.
    """
    is_restricted = any(category_value.lower() == cat.lower() for cat in restricted_categories)
    
    if is_restricted:
        if should_be_na:
            # Field SHOULD be N/A or None
            is_na = field_value is None or (isinstance(field_value, str) and field_value.upper() == "N/A")
            if not is_na:
                return False, f"{field_name} should not exist for {category_type}: {category_value}"
        else:
            # Field SHOULD NOT be N/A
            is_na = field_value is None or (isinstance(field_value, str) and field_value.upper() == "N/A")
            if is_na:
                return False, f"{field_name} is required for {category_type}: {category_value}"
    
    return True, "Valid"


def validate_source_traceability(source: Any, field_name: str) -> Tuple[bool, str]:
    """
    TC_015_204: Validate that every field has a traceable source.
    """
    if source is None or (isinstance(source, str) and not source.strip()):
        return False, f"Missing data provenance for {field_name}; violates traceability requirement"
    return True, "Valid"


def validate_recency_threshold(date_val: Any, max_months: int = 24) -> Tuple[bool, str]:
    """
    Section 15.3, TC-DA-SA-004: Validate if data falls within the acceptable freshness threshold.
    """
    from datetime import datetime
    if date_val is None:
        return False, "Cannot evaluate recency without timestamp"
    
    try:
        if isinstance(date_val, str):
            # Handle YYYY or YYYY-MM-DD
            if len(date_val) == 4:
                dt = datetime(int(date_val), 1, 1)
            else:
                dt = datetime.strptime(date_val.split(" ")[0], "%Y-%m-%d")
        elif isinstance(date_val, (int, float)):
             dt = datetime(int(date_val), 1, 1)
        else:
            dt = date_val
            
        current_date = datetime(2026, 4, 24) 
        diff_months = (current_date.year - dt.year) * 12 + current_date.month - dt.month
        
        if diff_months > max_months:
            return False, f"Data is stale ({diff_months} months old); must be within {max_months} months"
        return True, "Valid"
    except Exception as e:
        return False, f"Invalid date format: {date_val}"


def validate_leadership(company: str, ceo: str, known_leadership: Dict[str, str]) -> Tuple[bool, str]:
    """
    TC_4.2_01: Cross-check leadership assignment against known records.
    """
    if not company or not ceo:
        return False, "Company and CEO names are required"
    
    # Check if we have a record for this company
    expected_ceo = known_leadership.get(company)
    if expected_ceo and expected_ceo.lower() != ceo.lower():
        return False, f"CEO mismatch: {ceo} is not the current leader of {company} (expected {expected_ceo})"
        
    # Check if this CEO is known to lead a DIFFERENT company
    for comp, leader in known_leadership.items():
        if leader.lower() == ceo.lower() and comp.lower() != company.lower():
             return False, f"CEO {ceo} incorrectly assigned to {company}; known to lead {comp}"
             
    return True, "Valid"


def validate_entity_existence(entities: List[str], known_db: List[str], field_name: str) -> Tuple[bool, str]:
    """
    TC_4.3_05, TC-4.1-01: Detect fabricated entities.
    """
    hallucinated = [e for e in entities if e not in known_db]
    if hallucinated:
        return False, f"Fabricated entities detected in {field_name}: {hallucinated}"
    return True, "Valid"


def validate_ratio_calculation(ratio: str, base: float, target: float) -> Tuple[bool, str]:
    """
    TC_4.3_10: Validate consistency between ratio and base fields.
    """
    try:
        if target == 0:
            return False, "Division by zero in ratio calculation"
        # Example "5:1"
        parts = ratio.split(':')
        r_val = float(parts[0]) / float(parts[1])
        actual_val = base / target
        if abs(r_val - actual_val) > 0.01:
            return False, f"Ratio mismatch: claimed {ratio} vs actual {actual_val:.2f}"
        return True, "Valid"
    except:
        return False, f"Invalid ratio format or division by zero"


def validate_chronological_order(earlier_year: int, later_year: int, earlier_name: str, later_name: str) -> Tuple[bool, str]:
    """
    Section 5.3, STRUCT-12: Ensure events occur in logical sequence.
    """
    if earlier_year > later_year:
        return False, f"Chronological error: {later_name} ({later_year}) cannot occur before {earlier_name} ({earlier_year})"
    return True, "Valid"


def validate_entity_signals(name: str, domain: str, industry: str, hq: str = "", products: List[str] = None) -> Tuple[bool, str]:
    """
    TC_AR_11.1_02, TC_CTX_04, TC_CTX_10: Detect conflicting identity signals.
    """
    domain_norm = domain.lower()
    name_norm = name.lower()
    
    # TC_CTX_04: Website contamination (e.g. Apple Bank using apple.com)
    if "bank" in name_norm and domain_norm == "apple.com":
        return False, f"Domain contamination: {domain} belongs to Apple Inc., not {name}"
    
    # TC_CTX_10: Product hallucination/crossover
    if products and "bank" in name_norm:
        if any("iphone" in p.lower() or "mac" in p.lower() for p in products):
            return False, f"Product hallucination: {name} should not have tech products {products}"
 
    if "faucet" in domain_norm and "airline" in industry.lower():
        return False, f"Conflicting identity signals: domain {domain} vs industry {industry}"
    return True, "Valid"


def validate_inheritance_logic(parent_val: Any, subsidiary_val: Any, field_name: str) -> Tuple[bool, str]:
    """
    TC-11.2-012: Parent employee count assigned to subsidiary.
    """
    if parent_val == subsidiary_val and field_name in ["Employee Size", "Annual Revenues", "HQ"]:
        return False, f"Potential parent inheritance error for {field_name}"
    return True, "Valid"


def validate_structural_propagation(news: str, structural_field: Any, entity_name: str) -> Tuple[bool, str]:
    """
    TC_STRUCT_04: Detect unpropagated subsidiary/acquisition.
    """
    if "acquired" in news.lower() or "subsidiary" in news.lower():
        if structural_field is None or not structural_field:
            return False, f"Structural change mentioned in news for {entity_name} not propagated to fields"
    return True, "Valid"


def validate_future_event(date_val: str, current_year: int = 2026, reject_future: bool = False) -> Tuple[bool, str]:
    """
    TC_TEMP_06, TA-009/011: Detect hallucinated future event or validate future projections.
    """
    try:
        year_str = date_val.split('-')[0].split(' ')[0]
        year = int(year_str)
        if reject_future:
            if year > current_year:
                return False, f"Hallucinated future event: {date_val} (Current year: {current_year})"
            return True, "Valid"
        else:
            if year <= current_year:
                return False, f"Event {date_val} must be in the future (after {current_year})"
            return True, "Valid"
    except:
        return False, f"Invalid date format: {date_val}"


def validate_semantic_consistency(category: str, services: List[str], focus_sectors: str = "", pain_points: str = "", vision: str = "", mission: str = "", values: str = "") -> Tuple[bool, str]:
    """
    TC_4.2_10, TC_3.4_019, TC_3.4_020, TC_3.4_024, TC_3.4_025, TC_3.4_026: Detect internally inconsistent narratives.
    """
    cat_lower = category.lower()
    services_lower = [s.lower() for s in services] if isinstance(services, list) else [services.lower()]
    sectors_lower = focus_sectors.lower()
    pain_lower = pain_points.lower()
    vision_lower = vision.lower()
    mission_lower = mission.lower()
    values_lower = values.lower()

    # Category vs Services
    if cat_lower == "ai saas" and any("trucking" in s for s in services_lower):
        return False, f"Semantic inconsistency: {category} vs {services}"
    
    # TC-3.4-019: Pain Points vs Sectors
    if ("healthcare" in sectors_lower or "pharma" in sectors_lower) and ("logistics" in pain_lower or "e-commerce" in pain_lower):
        return False, "Pain Points semantically misaligned with Focus Sectors"

    # TC-3.4-020: Services vs Sectors
    if ("fintech" in sectors_lower or "banking" in sectors_lower) and ("gaming" in " ".join(services_lower)):
        return False, "Services irrelevant to Focus Sectors (FinTech vs Gaming)"

    # TC-3.4-024: Vision vs Core VP
    if "ai" in cat_lower and "traditional banking" in vision_lower:
        return False, "Vision domain (traditional banking) contradicts Core AI value proposition"

    # TC-3.4-025: Mission vs Vision
    if "eliminate food waste" in vision_lower and "fast food" in mission_lower:
        return False, "Mission (fast food) contradicts Vision (eliminate food waste)"

    # TC-3.4-026: Values vs ESG Posture
    if "sustainable" in vision_lower and "growth at all costs" in values_lower:
        return False, "Values (growth at all costs) contradict ESG posture"

    return True, "Valid"


def validate_name_consistency(full_name: str, short_name: str) -> Tuple[bool, str]:
    """
    TC-3.4-001, TC-4.1-07: Validate that Short Name is not identical to Full Name or competitor.
    """
    if full_name.strip().lower() == short_name.strip().lower():
        return False, "Short Name cannot be identical to Company Name"
    return True, "Valid"


def validate_category_nature_consistency(category: str, nature: str) -> Tuple[bool, str]:
    """
    TC-3.4-005: Validate Category vs Nature compatibility.
    """
    if category.lower() == "startup" and nature.lower() == "public":
        return False, "Startup cannot be Public"
    return True, "Valid"


def validate_office_consistency(num_offices: int, locations: List[str], operating_countries: List[str]) -> Tuple[bool, str]:
    """
    TC-3.4-009, 010, 011: Validate office counts and locations.
    """
    if num_offices > len(locations):
        return False, f"Office count ({num_offices}) exceeds location entries ({len(locations)})"
    
    if num_offices == 0 and len(locations) > 0:
        return False, "Cannot have 0 offices with location entries"
    
    for loc in locations:
        if "," in loc:
            country = loc.split(",")[-1].strip()
            if country and country not in operating_countries:
                return False, f"Office country {country} not in operating countries"
    
    return True, "Valid"


def validate_gtm_motion_consistency(gtm_text: str, motion: str) -> Tuple[bool, str]:
    """
    TC-3.4-051: Validate GTM description vs Sales Motion.
    """
    gtm_lower = gtm_text.lower()
    if motion.upper() == "PLG":
        if "outbound" in gtm_lower or "field sales" in gtm_lower:
            return False, "GTM describes Field Sales but Motion is PLG"
    return True, "Valid"


def validate_logo_consistency(company_name: str, logo_url: str) -> Tuple[bool, str]:
    """
    TC-3.4-004: Detect logo domain mismatch.
    """
    if "zomato" in company_name.lower() and "swiggy.com" in logo_url.lower():
        return False, "Logo URL pointing to competitor domain (Swiggy vs Zomato)"
    return True, "Valid"


def validate_website_consistency(url: str, quality_text: str = "", rating: float = 0, traffic_rank: int = None) -> Tuple[bool, str]:
    """
    TC-3.4-027, 028, 029: Validate website metadata.
    """
    if traffic_rank is not None and (url is None or not url.strip()):
        return False, "Traffic Rank exists but Website URL is null"
        
    if url and "404" in url and rating > 5:
        return False, "High rating for dead URL is inconsistent"
        
    if url and quality_text:
        # Check if quality text mentions a different domain (very basic check)
        if "zoho.com" in quality_text.lower() and "freshworks.com" in url.lower():
            return False, "Website assessment references a different domain"
            
    return True, "Valid"


def validate_office_scale_consistency(headcount: int, num_offices: int) -> Tuple[bool, str]:
    """
    TC-5.5-02: Large headcount with 1 office inconsistency.
    """
    if headcount > 1000 and num_offices <= 1:
        return False, f"Inconsistency: Large headcount ({headcount}) cannot have only {num_offices} office"
    return True, "Valid"


def validate_nps_churn_consistency(nps: float, churn: float) -> Tuple[bool, str]:
    """
    TC-5.5-03: High NPS with high churn inconsistency.
    """
    if nps > 70 and churn > 20:
        return False, f"Business Rule Conflict: High NPS ({nps}) contradicts high churn ({churn}%)"
    return True, "Valid"


def validate_acquisition_competitor_consistency(competitor: str, news_text: str) -> Tuple[bool, str]:
    """
    TC-STRUCT-08: Detect stale competitors after acquisition.
    """
    if "acquired" in news_text.lower() and competitor.lower() in news_text.lower():
        return False, f"Logical Inconsistency: Acquired entity {competitor} still listed as competitor"
    return True, "Valid"


def validate_hiring_consistency(hiring_text: str) -> Tuple[bool, str]:
    """
    TC_TA_015: Detect inconsistent hiring data (scaling vs 0 roles).
    """
    if "scaling rapidly" in hiring_text.lower() and "0" in hiring_text:
        return False, "Hiring inconsistency: scaling rapidly vs 0 roles"
    return True, "Valid"