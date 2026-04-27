"""
Fetch Data Module
=================
Fetches company data from Supabase's "companies" table.
Handles pagination (Supabase default limit is 1000 rows) and error handling.

Actual table schema (21 columns):
    company_id, name, short_name, category, incorporation_year,
    nature_of_company, headquarters_address, office_count, employee_size,
    website_url, linkedin_url, twitter_handle, facebook_url, instagram_url,
    primary_contact_email, primary_phone_number, overview_text,
    vision_statement, mission_statement, legal_issues, carbon_footprint

Usage:
    from fetchData import fetch_all_companies, fetch_company_by_name

    companies = fetch_all_companies()
    single = fetch_company_by_name("Microsoft Corporation")
"""

from typing import List, Dict, Any, Optional
from supabaseClient import get_supabase_client


# We select ALL columns so the transform layer can map whatever it needs.
SELECT_COLUMNS = "*"

# Supabase REST API returns max 1000 rows per request by default.
PAGE_SIZE = 1000


def fetch_all_companies() -> List[Dict[str, Any]]:
    """
    Fetch every row from the 'companies' table, handling pagination.

    Returns:
        List of dicts — one dict per company row.

    Raises:
        RuntimeError: If the Supabase query fails.
    """
    client = get_supabase_client()
    all_rows: List[Dict[str, Any]] = []
    offset = 0

    print("[FetchData] Fetching all companies from Supabase...")

    while True:
        try:
            response = (
                client
                .table("companies")
                .select(SELECT_COLUMNS)
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
        except Exception as exc:
            raise RuntimeError(
                f"[FetchData] Supabase query failed at offset {offset}: {exc}"
            ) from exc

        # Check for empty / end-of-data
        if not response.data:
            break

        all_rows.extend(response.data)
        fetched = len(response.data)
        print(f"[FetchData] Fetched {fetched} rows (total so far: {len(all_rows)})")

        # If we got fewer rows than the page size, we've reached the end
        if fetched < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    print(f"[FetchData] Done — {len(all_rows)} total companies fetched.")
    return all_rows


def fetch_company_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single company by exact name match.

    Args:
        name: The company name to search for (case-sensitive).

    Returns:
        Dict of the company row, or None if not found.
    """
    client = get_supabase_client()

    try:
        response = (
            client
            .table("companies")
            .select(SELECT_COLUMNS)
            .eq("name", name)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        print(f"[FetchData] ERROR fetching company '{name}': {exc}")
        return None

    if response.data and len(response.data) > 0:
        print(f"[FetchData] Found company: {name}")
        return response.data[0]

    print(f"[FetchData] Company not found: {name}")
    return None


def fetch_companies_by_ids(ids: List[int]) -> List[Dict[str, Any]]:
    """
    Fetch multiple companies by their company_id values.

    Args:
        ids: List of company_id integers.

    Returns:
        List of matching company dicts.
    """
    client = get_supabase_client()

    try:
        response = (
            client
            .table("companies")
            .select(SELECT_COLUMNS)
            .in_("company_id", ids)
            .execute()
        )
    except Exception as exc:
        print(f"[FetchData] ERROR fetching companies by IDs: {exc}")
        return []

    return response.data if response.data else []


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    companies = fetch_all_companies()
    if companies:
        print(f"\nTotal companies: {len(companies)}")
        print(f"Sample company: {companies[0].get('name', 'N/A')}")
        print(f"Fields available: {list(companies[0].keys())}")
    else:
        print("No companies returned.")
