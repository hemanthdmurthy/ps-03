import sys
import asyncio
import json
import os

# Ensure app package is importable
# Script is located at backend/tools; the app package lives at backend/app
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.workflow import nodes


class DummyDB:
    def update_session(self, *a, **k):
        return None

    def insert_validation_log(self, *a, **k):
        return None


class DummyTracing:
    @staticmethod
    def set_standard_metadata(*a, **k):
        return None

    @staticmethod
    def add_tags(*a, **k):
        return None

    @staticmethod
    def log_error(*a, **k):
        return None


async def run_check():
    # Monkeypatch nodes module to avoid external I/O
    nodes.db_service = DummyDB()
    nodes.TracingHelper = DummyTracing

    async def noop_run_in_executor(func, *a, **k):
        return None

    nodes.run_in_executor = noop_run_in_executor

    tests = []

    # 1) All critical fields present -> should pass
    full_profile = {k: None for k in nodes.MASTER_PARAMETERS}
    # Populate critical fields with sensible types
    full_profile["company_overview"] = "Test overview"
    full_profile["headquarters_city"] = "Test City"
    full_profile["approximate_headcount"] = 42
    full_profile["total_capital_raised"] = 1000000
    full_profile["founder_or_ceo"] = "Alice Example"
    full_profile["technological_stack"] = ["python", "react"]
    full_profile["key_executives"] = [{"name": "Alice Example"}]

    state_ok = {
        "session_id": "test-ok-1",
        "company_name": "TestCo",
        "consolidated_profile": full_profile,
        "regeneration_attempts": 0,
        "confidence_threshold": 0.85,
        "already_researched": False,
        "token_usage": {}
    }
    tests.append(("All critical fields present", state_ok))

    # 2) Missing critical fields -> should fail
    empty_profile = {k: None for k in nodes.MASTER_PARAMETERS}
    state_fail = {
        "session_id": "test-fail-1",
        "company_name": "TestCo",
        "consolidated_profile": empty_profile,
        "regeneration_attempts": 0,
        "confidence_threshold": 0.85,
        "already_researched": False,
        "token_usage": {}
    }
    tests.append(("Missing critical fields", state_fail))

    # 3) Conflicting CEO vs execs -> should flag founder_or_ceo
    profile_conflict = {k: None for k in nodes.MASTER_PARAMETERS}
    profile_conflict["founder_or_ceo"] = "Alice Example"
    profile_conflict["key_executives"] = [{"name": "Bob Other"}]
    state_conflict = {
        "session_id": "test-conflict-1",
        "company_name": "TestCo",
        "consolidated_profile": profile_conflict,
        "regeneration_attempts": 0,
        "confidence_threshold": 0.85,
        "already_researched": False,
        "token_usage": {}
    }
    tests.append(("Executive conflict", state_conflict))

    results = {}
    for label, st in tests:
        print(f"\n=== Running test: {label} ===")
        try:
            out = await nodes.validation_node(st, None)
            print(json.dumps({"validation_passed": out.get("validation_passed"),
                              "confidence_score": out.get("confidence_score"),
                              "failed_fields": out.get("failed_fields")}, indent=2))
            results[label] = out
        except Exception as e:
            print(f"Test {label} raised exception: {e}")
            results[label] = {"error": str(e)}

    print("\n=== Summary ===")
    for k, v in results.items():
        print(f"- {k}: {('error' in v) and v['error'] or f'passed={v.get("validation_passed")}, failed_fields={v.get("failed_fields")}, confidence={v.get("confidence_score"):.3f}'}")


if __name__ == "__main__":
    asyncio.run(run_check())
