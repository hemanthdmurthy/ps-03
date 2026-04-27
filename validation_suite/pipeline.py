"""
Validation Pipeline
===================
Three-stage pipeline: Fetch → Transform → Validate.

Fetches real company data from Supabase, transforms it into the format
expected by the existing validation suite, and runs comprehensive
validation checks on every record.

Actual Supabase 'companies' table columns (21):
    company_id, name, short_name, category, incorporation_year,
    nature_of_company, headquarters_address, office_count, employee_size,
    website_url, linkedin_url, twitter_handle, facebook_url, instagram_url,
    primary_contact_email, primary_phone_number, overview_text,
    vision_statement, mission_statement, legal_issues, carbon_footprint

Usage:
    python pipeline.py                  # One-shot run
    python pipeline.py --schedule 5     # Run every 5 minutes

Programmatic:
    from pipeline import run_pipeline, run_pipeline_scheduled
    results = run_pipeline()
    run_pipeline_scheduled(interval_minutes=5)
"""

import sys
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Import the data-fetching layer
# ---------------------------------------------------------------------------
from fetchData import fetch_all_companies

# ---------------------------------------------------------------------------
# Import existing validators (UNCHANGED — used as-is)
# ---------------------------------------------------------------------------
from validators.string_validator import (
    validate_company_name,
    validate_short_name,
    validate_ceo_name,
    validate_contact_name,
    validate_not_null,
    validate_min_length,
    validate_placeholder_prevention,
)
from validators.numeric_validator import (
    validate_year,
    validate_positive_number,
    validate_numeric_range,
)
from validators.url_validator import (
    validate_https_url,
    validate_email,
    validate_twitter_handle,
)
from validators.financial_validator import (
    validate_profitability_status,
)
from validators.dependency_validator import (
    validate_category,
    validate_nature_of_company,
)
from validators.record_validator import validate_null_density


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2 — TRANSFORM
# ═══════════════════════════════════════════════════════════════════════════

def _safe(value: Any, fallback: str = "") -> Any:
    """
    Return *fallback* when *value* is None or the literal string "null"/"N/A".
    This prevents downstream validators from receiving unusable sentinel values.
    """
    if value is None:
        return fallback
    # Supabase sometimes stores literal "null" / "N/A" strings
    if isinstance(value, str) and value.strip().lower() in ("null", "n/a", ""):
        return fallback
    return value


def transform_company(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a raw Supabase 'companies' row into the canonical format
    expected by the validation suite.

    Handles missing/null values with sensible fallbacks so
    downstream validators never receive unexpected None values
    for mandatory string fields.

    Supabase columns → Canonical keys mapping:
        name                  → company_name
        short_name            → short_name
        headquarters_address  → location
        incorporation_year    → year_of_incorporation  (kept as-is, may be str)
        overview_text         → overview
        primary_contact_email → contact_person_email
        ...
    """
    return {
        # ── Identity ──────────────────────────────────────────
        "company_name":           _safe(row.get("name"), ""),
        "short_name":             _safe(row.get("short_name"), _safe(row.get("name"), "")),
        "location":               _safe(row.get("headquarters_address"), "Unknown"),

        # ── Classification ────────────────────────────────────
        "category":               _safe(row.get("category"), ""),
        "nature_of_company":      _safe(row.get("nature_of_company"), ""),

        # ── Temporal ──────────────────────────────────────────
        # incorporation_year comes as a string from Supabase (e.g. "2013")
        "year_of_incorporation":  row.get("incorporation_year"),

        # ── Descriptive ──────────────────────────────────────
        "overview":               _safe(row.get("overview_text"), ""),
        "vision_statement":       _safe(row.get("vision_statement"), ""),
        "mission_statement":      _safe(row.get("mission_statement"), ""),

        # ── Web / Social ─────────────────────────────────────
        "website_url":            _safe(row.get("website_url"), ""),
        "linkedin_url":           _safe(row.get("linkedin_url"), ""),
        "twitter_handle":         _safe(row.get("twitter_handle"), ""),
        "facebook_url":           _safe(row.get("facebook_url"), ""),
        "instagram_url":          _safe(row.get("instagram_url"), ""),

        # ── Contact ──────────────────────────────────────────
        "contact_person_email":   _safe(row.get("primary_contact_email"), ""),
        "contact_person_phone":   _safe(row.get("primary_phone_number"), ""),

        # ── Workforce ────────────────────────────────────────
        "employee_size":          _safe(row.get("employee_size"), ""),
        "office_count":           row.get("office_count"),

        # ── Compliance / ESG ─────────────────────────────────
        "legal_issues":           _safe(row.get("legal_issues"), ""),
        "carbon_footprint":       _safe(row.get("carbon_footprint"), ""),

        # ── Raw row (for null-density and full-record checks) ─
        "_raw": row,
    }


def transform_all(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform a batch of raw Supabase rows."""
    transformed = []
    for row in raw_rows:
        try:
            transformed.append(transform_company(row))
        except Exception as exc:
            cid = row.get("company_id", "?")
            print(f"[Pipeline] WARN — transform skipped for company_id={cid}: {exc}")
    print(f"[Pipeline] Transformed {len(transformed)} / {len(raw_rows)} records.")
    return transformed


# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3 — VALIDATE
# ═══════════════════════════════════════════════════════════════════════════

def validate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the full validation suite against a single transformed company record.
    Returns a structured result dict.
    """
    checks: List[Dict[str, Any]] = []

    def _run(field: str, validator_fn, *args):
        """Helper — run a single validator and capture the result."""
        try:
            is_valid, message = validator_fn(*args)
            checks.append({
                "field": field,
                "valid": is_valid,
                "message": message,
            })
        except Exception as exc:
            checks.append({
                "field": field,
                "valid": False,
                "message": f"Validator error: {exc}",
            })

    # ── 1. Company Name (mandatory) ───────────────────────────
    name = record.get("company_name", "")
    if name:
        _run("company_name", validate_company_name, name)
    else:
        checks.append({"field": "company_name", "valid": False, "message": "Company name is missing"})

    _run("company_name_not_null", validate_not_null, name, "company_name")

    # ── 2. Short Name ────────────────────────────────────────
    short = record.get("short_name", "")
    if short:
        _run("short_name", validate_short_name, short)

    # ── 3. Website URL ───────────────────────────────────────
    website = record.get("website_url", "")
    if website:
        _run("website_url", validate_https_url, website)

    # ── 4. Contact Email ─────────────────────────────────────
    email = record.get("contact_person_email", "")
    if email:
        _run("contact_person_email", validate_email, email)

    # ── 5. Twitter Handle ────────────────────────────────────
    twitter = record.get("twitter_handle", "")
    if twitter:
        _run("twitter_handle", validate_twitter_handle, twitter)

    # ── 6. Year of Incorporation ─────────────────────────────
    year = record.get("year_of_incorporation")
    if year is not None:
        # The Supabase column stores this as a string (e.g. "2013")
        # validate_year handles both int and str inputs
        _run("year_of_incorporation", validate_year, year)

    # ── 7. Category ──────────────────────────────────────────
    category = record.get("category", "")
    if category:
        _run("category", validate_category, category)

    # ── 8. Nature of Company ─────────────────────────────────
    nature = record.get("nature_of_company", "")
    if nature:
        _run("nature_of_company", validate_nature_of_company, nature)

    # ── 9. Overview (min length + placeholder prevention) ────
    overview = record.get("overview", "")
    if overview:
        _run("overview_min_length", validate_min_length, overview, 50, "Overview")
        _run("overview_placeholder", validate_placeholder_prevention, overview, "Overview")

    # ── 10. Vision Statement (placeholder prevention) ────────
    vision = record.get("vision_statement", "")
    if vision:
        _run("vision_placeholder", validate_placeholder_prevention, vision, "Vision Statement")

    # ── 11. Mission Statement (placeholder prevention) ───────
    mission = record.get("mission_statement", "")
    if mission:
        _run("mission_placeholder", validate_placeholder_prevention, mission, "Mission Statement")

    # ── 12. Record-level null-density check ──────────────────
    raw = record.get("_raw", record)
    _run("null_density", validate_null_density, raw)

    # ── 13. Employee size (not-null for populated records) ───
    emp = record.get("employee_size", "")
    if emp:
        _run("employee_size_placeholder", validate_placeholder_prevention, emp, "Employee Size")

    # ── Aggregate ─────────────────────────────────────────────
    passed = sum(1 for c in checks if c["valid"])
    failed = len(checks) - passed
    status = "PASS" if failed == 0 else "FAIL"

    return {
        "company_name": name or "(unknown)",
        "status": status,
        "checks_run": len(checks),
        "checks_passed": passed,
        "checks_failed": failed,
        "details": checks,
    }


# ═══════════════════════════════════════════════════════════════════════════
# PIPELINE ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════

def run_pipeline() -> Dict[str, Any]:
    """
    Execute the full pipeline: Fetch → Transform → Validate.
    Returns a structured report dict.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"\n{'='*70}")
    print(f"  VALIDATION PIPELINE -- {timestamp}")
    print(f"{'='*70}\n")

    # Stage 1 — Fetch
    try:
        raw_data = fetch_all_companies()
    except Exception as exc:
        return {
            "timestamp": timestamp,
            "error": f"Fetch failed: {exc}",
            "total_companies": 0,
            "validated": 0,
            "failed": 0,
            "results": [],
        }

    if not raw_data:
        return {
            "timestamp": timestamp,
            "total_companies": 0,
            "validated": 0,
            "failed": 0,
            "results": [],
            "message": "No data returned from Supabase.",
        }

    # Stage 2 — Transform
    records = transform_all(raw_data)

    # Stage 3 — Validate
    results: List[Dict[str, Any]] = []
    pass_count = 0
    fail_count = 0

    for record in records:
        result = validate_record(record)
        results.append(result)
        if result["status"] == "PASS":
            pass_count += 1
        else:
            fail_count += 1

    # ── Summary ───────────────────────────────────────────────
    report = {
        "timestamp": timestamp,
        "total_companies": len(raw_data),
        "transformed": len(records),
        "validated": pass_count,
        "failed": fail_count,
        "results": results,
    }

    print(f"\n{'-'*70}")
    print(f"  RESULTS: {pass_count} PASSED | {fail_count} FAILED | {len(records)} TOTAL")
    print(f"{'-'*70}")

    # Print per-company summary
    for r in results:
        icon = "[PASS]" if r["status"] == "PASS" else "[FAIL]"
        print(f"  {icon}  {r['company_name']:<45}  {r['checks_passed']}/{r['checks_run']} checks passed")

    return report


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULED EXECUTION (optional interval-based re-runs)
# ═══════════════════════════════════════════════════════════════════════════

_scheduler_active = False


def run_pipeline_scheduled(interval_minutes: int = 5):
    """
    Run the pipeline immediately, then repeat every *interval_minutes*.
    Uses a daemon thread so it won't block the main process.
    Press Ctrl+C to stop.
    """
    global _scheduler_active
    _scheduler_active = True

    def _tick():
        if not _scheduler_active:
            return
        run_pipeline()
        # Schedule next run
        timer = threading.Timer(interval_minutes * 60, _tick)
        timer.daemon = True
        timer.start()

    print(f"[Pipeline] Scheduled mode -- running every {interval_minutes} minutes.")
    print(f"[Pipeline] Press Ctrl+C to stop.\n")
    _tick()


def stop_scheduled():
    """Stop the scheduled pipeline (for programmatic use)."""
    global _scheduler_active
    _scheduler_active = False
    print("[Pipeline] Scheduled execution stopped.")


# ═══════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Supabase → Validation Pipeline")
    parser.add_argument(
        "--schedule",
        type=int,
        default=0,
        metavar="MINUTES",
        help="Re-run every N minutes (0 = one-shot, default).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as raw JSON to stdout.",
    )
    args = parser.parse_args()

    if args.schedule > 0:
        try:
            run_pipeline_scheduled(args.schedule)
            # Keep main thread alive for the scheduler
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_scheduled()
            print("\nGoodbye.")
    else:
        report = run_pipeline()
        if args.json:
            print(json.dumps(report, indent=2, default=str))
