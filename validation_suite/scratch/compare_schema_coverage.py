# d:\ps_03\PlacementIntel\validation_suite\scratch\compare_schema_coverage.py
"""
Schema Coverage Comparator
==========================
Compares a JSON data file (or final dossier report) against the master 163 BI parameters list.
Reports on coverage metrics, missing keys grouped by logical cluster, and agent assignments.
"""

import os
import sys
import json
import argparse

# Append backend directory to sys.path to import the master parameters
BACKEND_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "company-intelligence-platform", "backend"))
sys.path.append(BACKEND_PATH)

try:
    from app.workflow.parameters import MASTER_PARAMETERS
except ImportError:
    # Fallback to absolute file loading or hardcoded if import fails
    print("[Error] Failed to import app.workflow.parameters. Please ensure BACKEND_PATH is correct.")
    sys.exit(1)


def find_all_keys(data, found_keys=None):
    """Recursively search for all keys present in a JSON structure."""
    if found_keys is None:
        found_keys = set()
        
    if isinstance(data, dict):
        for k, v in data.items():
            found_keys.add(k)
            find_all_keys(v, found_keys)
    elif isinstance(data, list):
        for item in data:
            find_all_keys(item, found_keys)
            
    return found_keys


def run_coverage_audit(json_path):
    """Performs coverage analysis of a JSON file against the 163 master parameters."""
    if not os.path.exists(json_path):
        print(f"[Error] Target file not found: {json_path}")
        return
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[Error] Failed to parse JSON file {json_path}: {e}")
        return

    print("=" * 80)
    print(f"               PLACEMENTINTEL SCHEMA AUDIT REPORT")
    print(f"  Target File: {os.path.basename(json_path)}")
    print("=" * 80)

    # 1. Discover keys present in target JSON
    found_keys = find_all_keys(data)
    
    # 2. Match against master 163 parameters
    total_master = len(MASTER_PARAMETERS)
    matched_keys = [k for k in MASTER_PARAMETERS if k in found_keys]
    missing_keys = [k for k in MASTER_PARAMETERS if k not in found_keys]
    
    coverage_pct = (len(matched_keys) / total_master) * 100
    
    print(f"--> SCHEMA COVERAGE: {len(matched_keys)} / {total_master} Parameters ({coverage_pct:.2f}% Coverage)")
    print("-" * 80)
    
    # 3. Group Missing Keys by Logical Cluster
    missing_by_cluster = {}
    for key in missing_keys:
        cluster = MASTER_PARAMETERS[key]["cluster"]
        missing_by_cluster.setdefault(cluster, []).append(key)
        
    print("\n[!] MISSING PARAMETERS BY LOGICAL CLUSTER:")
    if not missing_by_cluster:
        print("  [OK] Perfect Coverage! No missing parameters.")
    else:
        for cluster, keys in sorted(missing_by_cluster.items()):
            print(f"\n  * Cluster: {cluster} ({len(keys)} missing)")
            for key in sorted(keys):
                agent = MASTER_PARAMETERS[key]["agent"]
                diff = MASTER_PARAMETERS[key]["difficulty"]
                diff_tag = f" [{diff}]" if diff != "Low" else ""
                print(f"    - {key:<35} | Agent: {agent:<10}{diff_tag}")
                
    # 4. Group Matched Keys by Agent
    matched_by_agent = {}
    for key in matched_keys:
        agent = MASTER_PARAMETERS[key]["agent"]
        matched_by_agent.setdefault(agent, []).append(key)
        
    print("\n" + "-" * 80)
    print("[OK] COVERED PARAMETERS BY RESEARCH AGENT:")
    for agent, keys in sorted(matched_by_agent.items()):
        print(f"  * {agent.capitalize()} Agent: {len(keys)} parameters covered")
        
    # 5. High-Difficulty Parameter Audit
    high_diff_params = [k for k, m in MASTER_PARAMETERS.items() if m["difficulty"] == "High"]
    matched_high = [k for k in high_diff_params if k in found_keys]
    missing_high = [k for k in high_diff_params if k not in found_keys]
    
    print("\n" + "-" * 80)
    print(f"[HIGH DIFFICULTY] HIGH-DIFFICULTY PARAMETERS STATUS ({len(matched_high)} / {len(high_diff_params)} Covered):")
    for key in sorted(high_diff_params):
        status = "COVERED" if key in found_keys else "MISSING"
        agent = MASTER_PARAMETERS[key]["agent"]
        print(f"  - {key:<35} | Status: {status:<10} | Agent: {agent}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Schema Coverage Audit Tool")
    parser.add_argument("--report", required=True, help="Path to the JSON dossier report to audit")
    args = parser.parse_args()
    
    run_coverage_audit(args.report)
