"""
Automated Validation Reporting System
=====================================
Main orchestrator that:
1. Fetches data from Supabase
2. Runs Pytest-based validation suite
3. Generates validation_error_report.xlsx
4. Outputs final summary metrics to console
"""

import os
import sys
import pytest
import pandas as pd
import io
import contextlib
import re
from datetime import datetime
from fetchData import fetch_all_companies
from validation_categories import get_category_for_rule, get_category_label, ValidationCategory

def run_automated_validation():
    print("\n" + "="*70)
    print("  AUTOMATED VALIDATION REPORTING SYSTEM")
    print("="*70 + "\n")

    # Step 1: Health check / Fetch data count
    print("[1/4] Connecting to Supabase and fetching records...")
    try:
        raw_data = fetch_all_companies()
        num_records = len(raw_data)
        if num_records == 0:
            print("[Error] No records found in Supabase companies table.")
            return
        print(f"Found {num_records} records.")
    except Exception as e:
        print(f"[Error] Failed to fetch data: {e}")
        return

    # Step 2: Execute Pytest
    print("\n[2/4] Executing Pytest validation suite (300+ test points)...")
    
    # We use a custom object to collect results from Pytest
    class ResultCollector:
        def __init__(self):
            self.results = []
            self.total_records = 0
            self.total_test_cases = 0

    collector = ResultCollector()
    
    # Run pytest programmatically
    # We pass the collector via a custom plugin or just rely on the conftest modification
    # Actually, the best way programmatically is to use a plugin object
    class ReporterPlugin:
        def __init__(self, collector):
            self.collector = collector
            
        def pytest_configure(self, config):
            self.config = config
            
        def pytest_unconfigure(self, config):
            self.collector.results = getattr(config, "validation_results", [])
            self.collector.total_records = getattr(config, "total_records", 0)
            self.collector.total_test_cases = getattr(config, "total_test_cases", 0)

    plugin = ReporterPlugin(collector)
    
    # Run only our specific test file
    # We capture stdout/stderr to extract setup errors (NameError, ImportError, etc.)
    pytest_output_stream = io.StringIO()
    print("Running validations...")
    with contextlib.redirect_stdout(pytest_output_stream), contextlib.redirect_stderr(pytest_output_stream):
        # Use -v to ensure verbose output for traceback parsing
        exit_code = pytest.main(["test_supabase_records.py", "-v"], plugins=[plugin])
    
    full_output = pytest_output_stream.getvalue()
    # Print the full output to console as requested (it was redirected before)
    print(full_output)
    
    # Determine if this was a setup failure or normal execution
    setup_keywords = ["ERROR at setup", "NameError", "ImportError", "SyntaxError", "FixtureLookupError", "AttributeError", "ModuleNotFoundError"]
    validation_keywords = ["TypeError", "ValueError", "IndexError", "KeyError", "AssertionError"]
    
    is_setup_failure = any(kw in full_output for kw in setup_keywords)
    # If collector has no results but tests were attempted and failed, it's a validation crash
    is_validation_failure = not is_setup_failure and (collector.total_test_cases == 0 and num_records > 0) and ("FAILED" in full_output or any(kw in full_output for kw in validation_keywords))

    # Step 3: Generate Excel Report
    print("\n[3/4] Generating validation_error_report.xlsx...")
    
    results = collector.results
    failed_results = [r for r in results if r["status"] == "Fail"]
    
    validation_status = "Success"
    setup_failure_cause = ""
    
    # Enrichment of failed results with categories
    for r in failed_results:
        cat = get_category_for_rule(r["test_case_name"])
        r["category"] = cat.value
        r["category_label"] = get_category_label(cat)
        
    if is_setup_failure or is_validation_failure:
        validation_status = "Setup Failure" if is_setup_failure else "Validation Failed"
        
        # Extract specific root cause
        root_cause_type = "Setup Failure" if is_setup_failure else "Validation Failure"
        root_cause_msg = "Pytest execution failed."
        
        # Combined list of keywords to look for
        all_error_keywords = setup_keywords + validation_keywords
        
        # Parse the real exception from the output
        for line in full_output.split('\n'):
            line = line.strip()
            # Look for lines like "E   NameError: ..." or "TypeError: ..."
            if any(kw in line for kw in all_error_keywords) and ":" in line:
                clean_line = line
                if line.startswith("E   "):
                    clean_line = line[4:].strip()
                
                if ":" in clean_line:
                    parts = clean_line.split(':', 1)
                    potential_type = parts[0].strip()
                    if potential_type in all_error_keywords or "Error" in potential_type:
                        root_cause_type = potential_type
                        root_cause_msg = parts[1].strip()
        
        report_df = pd.DataFrame([{
            "Error Type": root_cause_type,
            "Error Message": str(root_cause_msg),
            "Status": "Failed",
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        
        # Store root cause for console output
        setup_failure_cause = f"{root_cause_type} - {root_cause_msg}"
    elif not failed_results:
        # Success case: Generate report with summary row
        report_df = pd.DataFrame([{
            "Total Records Validated": collector.total_records,
            "Total Test Cases Executed": collector.total_test_cases * collector.total_records,
            "Total Error Messages": 0,
            "Validation Status": "Success",
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
    else:
        # Failure case: Record all failures with category headers
        validation_status = "Fail"
        report_df = pd.DataFrame(failed_results)
        # Reorder columns to include category classification
        cols = [
            "test_case_name", 
            "category", 
            "category_label", 
            "record_id", 
            "company_name", 
            "field_name", 
            "actual_value", 
            "expected_condition", 
            "error_message", 
            "timestamp", 
            "status"
        ]
        report_df = report_df[cols]

    report_path = "validation_error_report.xlsx"
    try:
        report_df.to_excel(report_path, index=False, engine='openpyxl')
        print(f"Excel report saved to: {report_path}")
    except Exception as e:
        print(f"[Error] Failed to save Excel report: {e}")

    # Step 4: Final Console Output & Supabase Sync
    total_test_executions = collector.total_test_cases * collector.total_records
    total_failed = len(failed_results)
    total_passed = max(0, total_test_executions - total_failed)
    quality_score = round((total_passed / total_test_executions) * 100, 2) if total_test_executions > 0 else 100.0
    
    print("\n" + "-"*70)
    print("  FINAL VALIDATION SUMMARY")
    print("-"*70)
    print(f"Total Records Validated: {collector.total_records}")
    print(f"Total Test Cases Executed: {total_test_executions}")
    print(f"Total Passed Validations: {total_passed}")
    print(f"Total Failed Validations: {total_failed}")
    print(f"Overall Data Quality Score: {quality_score}%")
    print(f"Validation Status: {validation_status}")
    if is_setup_failure or is_validation_failure:
        print(f"Root Cause: {setup_failure_cause}")
    print("-"*70)
    
    # Print Modular Categorized Breakdown
    if failed_results:
        print("\n  FAILURES BY DATA QUALITY CATEGORY:")
        print("  " + "~"*40)
        category_counts = {cat: 0 for cat in ValidationCategory}
        for r in failed_results:
            cat = get_category_for_rule(r["test_case_name"])
            category_counts[cat] = category_counts.get(cat, 0) + 1
            
        for cat, count in category_counts.items():
            percentage = round((count / total_failed) * 100, 1) if total_failed > 0 else 0.0
            label = get_category_label(cat)
            print(f"  * {label:<40}: {count:>4} ({percentage:>5}%)")
        print("  " + "~"*40 + "\n")

    # Sync Run Results to Supabase
    if not (is_setup_failure or is_validation_failure) and collector.total_records > 0:
        print("[4/4] Synchronizing run data to Supabase...")
        try:
            from supabaseClient import get_supabase_client
            client = get_supabase_client()
            
            # 1. Insert validation run metadata
            run_data = {
                "triggered_by": "system",
                "total_records_checked": collector.total_records,
                "passed_records": total_passed,
                "failed_records": total_failed,
                "overall_quality_score": quality_score,
                "execution_time_seconds": 15.5
            }
            run_res = client.table("validation_runs").insert(run_data).execute()
            if run_res.data and len(run_res.data) > 0:
                run_id = run_res.data[0]["id"]
                print(f"[Supabase] Saved run record. Run ID: {run_id}")
                
                # 2. Insert detail failures (limit to 200 for payload safety in HTTP REST calls)
                details_to_insert = []
                for r in failed_results[:200]:
                    details_to_insert.append({
                        "run_id": run_id,
                        "company_id": int(r["record_id"]) if str(r["record_id"]).isdigit() else None,
                        "rule_id": r["test_case_name"],
                        "category": r["category"],
                        "status": "FAIL",
                        "actual_value": str(r["actual_value"])[:2000],
                        "expected_condition": str(r["expected_condition"])[:1000],
                        "error_message": str(r["error_message"])[:2000]
                    })
                
                if details_to_insert:
                    # Batch inserts by 50
                    for i in range(0, len(details_to_insert), 50):
                        client.table("validation_results_detail").insert(details_to_insert[i:i+50]).execute()
                    print(f"[Supabase] Saved {len(details_to_insert)} fail details.")
            else:
                print("[Supabase] Note: Validation run creation returned empty result.")
        except Exception as e:
            print(f"[Supabase] Note: Database insert skipped or failed (Table may not exist yet): {e}")
            
    print("="*70 + "\n")

if __name__ == "__main__":
    run_automated_validation()
