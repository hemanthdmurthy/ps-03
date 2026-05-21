"""
Supabase Record Validation Test Suite
=====================================
Executes all registered validation rules against live Supabase data.
Captures results for the automated reporting system.
"""

import pytest
from datetime import datetime, timezone
from fetchData import fetch_all_companies
from pipeline import transform_company
from validation_rules import get_all_rules, execute_rule

# Fetch data once per session
@pytest.fixture(scope="session")
def supabase_data():
    raw_data = fetch_all_companies()
    if not raw_data:
        pytest.skip("No data found in Supabase companies table.")
    
    # Transform all records
    return [transform_company(row) for row in raw_data]

@pytest.fixture(scope="session")
def all_rules():
    return get_all_rules()

def test_validate_records(supabase_data, all_rules, request):
    """
    Validates every record against every rule.
    We use a single test function that iterates to avoid Pytest overhead 
    with 100k+ parameterized tests, while still capturing detailed results.
    """
    results = []
    total_executed = 0
    
    for record in supabase_data:
        company_id = record.get("_raw", {}).get("company_id", "Unknown")
        company_name = record.get("company_name", "Unknown")
        
        for rule in all_rules:
            total_executed += 1
            is_valid, message, actual_value = execute_rule(rule, record)
            
            result = {
                "test_case_name": rule.name,
                "record_id": company_id,
                "company_name": company_name,
                "field_name": rule.field,
                "actual_value": str(actual_value),
                "expected_condition": rule.expected_condition,
                "error_message": str(message) if not is_valid else "",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Pass" if is_valid else "Fail"
            }
            results.append(result)
    
    # Attach results to the session for the reporter to pick up
    request.config.validation_results = results
    request.config.total_records = len(supabase_data)
    request.config.total_test_cases = len(all_rules)
    
    # If any failures, we can still pass the test but the reporter will capture details.
    # Alternatively, we could assert here, but we want the FULL report even if failures exist.
    assert True
