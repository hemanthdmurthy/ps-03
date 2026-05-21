"""
Validation Tool — LangChain Agent-Ready Wrapper
================================================
Wraps the validation pipeline's record-level validation as a
standalone, reusable "tool" function that:

  1. Accepts a single company data dict.
  2. Runs the full validation suite against it.
  3. Returns structured JSON results.

This module is a **pure Python function** — it does NOT require
LangChain to be installed. When you're ready to plug into a
LangChain agent, wrap it with:

    from langchain.tools import StructuredTool
    from validationTool import company_validation_tool, TOOL_METADATA

    tool = StructuredTool.from_function(
        func=company_validation_tool,
        name=TOOL_METADATA["name"],
        description=TOOL_METADATA["description"],
    )

Usage (standalone):
    from validationTool import company_validation_tool

    result = company_validation_tool({
        "name": "Microsoft Corporation",
        "short_name": "MSFT",
        "website_url": "https://www.microsoft.com",
        "category": "Enterprise",
    })
    print(result)
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List

# ---------------------------------------------------------------------------
# Re-use the pipeline's transform + validate logic
# ---------------------------------------------------------------------------
from pipeline import transform_company, validate_record


# ═══════════════════════════════════════════════════════════════════════════
# TOOL METADATA  (for LangChain StructuredTool registration)
# ═══════════════════════════════════════════════════════════════════════════

TOOL_METADATA: Dict[str, Any] = {
    "name": "company_data_validator",
    "description": (
        "Validates a company data record against enterprise-grade business rules. "
        "Checks company name format, URL validity, category enums, year format, "
        "placeholder prevention, null-density, and more. "
        "Input: a dict with company fields (name, website_url, category, etc.). "
        "Output: structured JSON with per-field pass/fail results."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name":                  {"type": "string",  "description": "Legal company name (required)"},
            "short_name":            {"type": "string",  "description": "Abbreviated brand name"},
            "headquarters_address":  {"type": "string",  "description": "HQ location / address"},
            "category":              {"type": "string",  "description": "Business category (e.g. AI Developer Tools, Electric Vehicles)"},
            "nature_of_company":     {"type": "string",  "description": "Private / Public Limited Company / etc."},
            "incorporation_year":    {"type": "string",  "description": "Year the company was founded (e.g. '2013')"},
            "overview_text":         {"type": "string",  "description": "Company overview / description"},
            "website_url":           {"type": "string",  "description": "Company website (HTTPS)"},
            "linkedin_url":          {"type": "string",  "description": "LinkedIn company page URL"},
            "twitter_handle":        {"type": "string",  "description": "Twitter/X handle"},
            "facebook_url":          {"type": "string",  "description": "Facebook page URL"},
            "instagram_url":         {"type": "string",  "description": "Instagram profile URL"},
            "primary_contact_email": {"type": "string",  "description": "Primary contact email"},
            "primary_phone_number":  {"type": "string",  "description": "Primary contact phone"},
            "employee_size":         {"type": "string",  "description": "Employee count or range"},
            "office_count":          {"type": "string",  "description": "Number of offices"},
            "vision_statement":      {"type": "string",  "description": "Company vision statement"},
            "mission_statement":     {"type": "string",  "description": "Company mission statement"},
            "legal_issues":          {"type": "string",  "description": "Known legal issues"},
            "carbon_footprint":      {"type": "string",  "description": "Carbon footprint details"},
        },
        "required": ["name"],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# CORE TOOL FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def company_validation_tool(company_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a single company record against the enterprise validation suite.

    This function is designed to be wrapped as a LangChain tool. It:
      1. Transforms raw input into the canonical validation format.
      2. Runs every applicable validator from the validators/ package.
      3. Returns structured JSON with per-field results.

    Args:
        company_data: Dict with company fields. At minimum, must contain "name".
                      Fields can use either Supabase column names (e.g. "overview_text")
                      or the canonical names (e.g. "overview").

    Returns:
        Dict with keys:
            - company_name (str)
            - status ("PASS" | "FAIL")
            - checks_run (int)
            - checks_passed (int)
            - checks_failed (int)
            - timestamp (str, ISO 8601)
            - details (list of {field, valid, message})
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # ── Input guard ───────────────────────────────────────────
    if not company_data or not isinstance(company_data, dict):
        return {
            "company_name": "(invalid input)",
            "status": "ERROR",
            "checks_run": 0,
            "checks_passed": 0,
            "checks_failed": 0,
            "timestamp": timestamp,
            "details": [{"field": "input", "valid": False, "message": "Input must be a non-empty dict"}],
        }

    if "name" not in company_data and "company_name" not in company_data:
        return {
            "company_name": "(missing)",
            "status": "ERROR",
            "checks_run": 0,
            "checks_passed": 0,
            "checks_failed": 0,
            "timestamp": timestamp,
            "details": [{"field": "name", "valid": False, "message": "Required field 'name' is missing"}],
        }

    # ── Transform (uses the pipeline's transform_company) ────
    # If input already uses canonical keys (company_name, overview, etc.)
    # we need to map back to Supabase-style keys for transform_company.
    supabase_row = _normalize_to_supabase_keys(company_data)
    record = transform_company(supabase_row)

    # ── Validate ──────────────────────────────────────────────
    result = validate_record(record)
    result["timestamp"] = timestamp

    return result


def validate_multiple(companies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a batch of company records.

    Args:
        companies: List of company data dicts.

    Returns:
        Aggregated report with per-company results.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    results = []
    pass_count = 0
    fail_count = 0

    for company in companies:
        result = company_validation_tool(company)
        results.append(result)
        if result.get("status") == "PASS":
            pass_count += 1
        else:
            fail_count += 1

    return {
        "timestamp": timestamp,
        "total_companies": len(companies),
        "validated": pass_count,
        "failed": fail_count,
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════

# Mapping from canonical (validation) keys → Supabase column names.
# This lets the tool accept EITHER format transparently.
_CANONICAL_TO_SUPABASE = {
    "company_name":          "name",
    "year_of_incorporation": "incorporation_year",
    "overview":              "overview_text",
    "location":              "headquarters_address",
    "contact_person_email":  "primary_contact_email",
    "contact_person_phone":  "primary_phone_number",
}


def _normalize_to_supabase_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept input in either canonical or Supabase key format
    and normalise to Supabase keys for transform_company().
    """
    result = dict(data)  # shallow copy

    for canonical_key, supabase_key in _CANONICAL_TO_SUPABASE.items():
        if canonical_key in result and supabase_key not in result:
            result[supabase_key] = result.pop(canonical_key)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Validation Tool — Self-Test")
    print("=" * 60)

    # Test with a sample record (using Supabase column names)
    sample = {
        "name": "Acme Corporation",
        "short_name": "Acme",
        "website_url": "https://www.acme.com",
        "category": "Enterprise",
        "incorporation_year": "2010",
        "overview_text": "Acme Corporation is a leading provider of innovative solutions for modern enterprises across the globe.",
        "nature_of_company": "Private",
        "employee_size": "50-100",
    }

    result = company_validation_tool(sample)
    print(json.dumps(result, indent=2))

    print(f"\nTool metadata:")
    print(f"  Name:        {TOOL_METADATA['name']}")
    print(f"  Description: {TOOL_METADATA['description'][:80]}...")
