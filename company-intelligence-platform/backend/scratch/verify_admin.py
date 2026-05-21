import sys
import os
import uuid
from datetime import datetime

# Inject backend path for local imports
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.db_deps import get_db
from app.models.validation_run import ValidationRun, ValidationResultsDetail, ValidationCorrectionSuggestion
from app.models.staging_company import StagingCompany

def run_suite():
    print("==========================================================")
    print("  RUNNING FASTAPI ADMINISTRATIVE WORKFLOWS VALIDATION     ")
    print("==========================================================")

    # Initialize TestClient using context manager
    with TestClient(app) as client:
        print("[1] TestClient successfully initialized.")

        # -------------------------------------------------------------
        # 1. AUTHENTICATE AND OBTAIN TOKENS
        # -------------------------------------------------------------
        print("\n[2] Logging in seeded accounts to obtain authorization tokens...")
        
        # Admin Login
        admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert admin_login.status_code == 200, "Admin login failed!"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("[+] Admin authenticated successfully.")

        # Researcher Login
        researcher_login = client.post("/api/auth/login", json={"username": "researcher", "password": "researcher123"})
        assert researcher_login.status_code == 200, "Researcher login failed!"
        researcher_token = researcher_login.json()["access_token"]
        researcher_headers = {"Authorization": f"Bearer {researcher_token}"}
        print("[+] Researcher authenticated successfully.")

        # -------------------------------------------------------------
        # 2. SEED ADMIN TEST RECORDSET
        # -------------------------------------------------------------
        print("\n[3] Seeding database with a staging company and validation failures...")

        # A. Register Staging Company
        company_name = f"Beta Corp {uuid.uuid4().hex[:4].upper()}"
        c_resp = client.post("/api/companies", headers=researcher_headers, json={
            "name": company_name,
            "category": "Education",
            "website_url": "http://old-beta-site.com"
        })
        company_id = c_resp.json()["company_id"]
        print(f"[+] Seeded staging company '{company_name}' (ID: {company_id})")

        # B. Manually seed a Validation Run, Failure Detail, and Suggestions using DB Session
        db = next(get_db())
        try:
            # Seed Validation Run
            run_id = f"test-run-{uuid.uuid4().hex[:6]}"
            val_run = ValidationRun(
                id=run_id,
                triggered_by="admin",
                total_records_checked=10,
                passed_records=9,
                failed_records=1,
                overall_quality_score=90.0,
                execution_time_seconds=2.4
            )
            db.add(val_run)

            # Seed Validation Failure Detail (Website URL is using insecure HTTP)
            detail_id = f"test-detail-{uuid.uuid4().hex[:6]}"
            val_detail = ValidationResultsDetail(
                id=detail_id,
                run_id=run_id,
                company_id=company_id,
                rule_id="RULE-SEC-01",
                category="Security",
                status="fail",
                actual_value="http://old-beta-site.com",
                expected_condition="Must use secure HTTPS protocol",
                error_message="Website URL is using HTTP protocol instead of HTTPS."
            )
            db.add(val_detail)

            # Seed Correction Suggestion 1 (To be Approved)
            sugg1_id = f"test-sugg1-{uuid.uuid4().hex[:6]}"
            suggestion1 = ValidationCorrectionSuggestion(
                id=sugg1_id,
                company_id=company_id,
                field_name="website_url",
                original_value="http://old-beta-site.com",
                suggested_value="https://secure-beta-site.com",
                rationale="Updated corporate domain to HTTPS format to resolve validation rule failure.",
                confidence=0.98,
                status="pending"
            )
            db.add(suggestion1)

            # Seed Correction Suggestion 2 (To be Rejected)
            sugg2_id = f"test-sugg2-{uuid.uuid4().hex[:6]}"
            suggestion2 = ValidationCorrectionSuggestion(
                id=sugg2_id,
                company_id=company_id,
                field_name="website_url",
                original_value="http://old-beta-site.com",
                suggested_value="http://wrong-url.com",
                rationale="Incorrect suggestion for testing rejection workflow.",
                confidence=0.45,
                status="pending"
            )
            db.add(suggestion2)

            db.commit()
            print("[+] Successfully seeded ValidationRun, failure details, and 2 pending suggestions.")
        except Exception as e:
            db.rollback()
            print(f"[-] Database seed failure: {e}")
            raise e

        # -------------------------------------------------------------
        # 3. VERIFY VALIDATION RUNS ENDPOINTS
        # -------------------------------------------------------------
        print("\n[4] Querying Validation Runs list (/api/admin/validation/runs)...")
        runs_resp = client.get("/api/admin/validation/runs", headers=admin_headers)
        assert runs_resp.status_code == 200, f"Runs list failed: {runs_resp.text}"
        runs = runs_resp.json()
        assert len(runs) >= 1
        print(f"[+] Successfully retrieved {len(runs)} validation runs from database.")

        print("\n[5] Querying specific Validation Run details...")
        details_resp = client.get(f"/api/admin/validation/runs/{run_id}", headers=admin_headers)
        assert details_resp.status_code == 200, f"Run details failed: {details_resp.text}"
        run_detail = details_resp.json()
        assert run_detail["run"]["id"] == run_id
        assert len(run_detail["details"]) >= 1
        assert run_detail["details"][0]["id"] == detail_id
        print("[+] Validation run details and nested failures successfully matched.")

        # -------------------------------------------------------------
        # 4. VERIFY ROLE PROTECTION CONTROLS
        # -------------------------------------------------------------
        print("\n[6] Testing Role-Based Security Protection on Approvals...")
        
        # A researcher tries to approve a suggestion
        blocked_resp = client.post(f"/api/admin/validation/suggestions/{sugg1_id}/approve", headers=researcher_headers)
        assert blocked_resp.status_code == 403, "Security Error: Allowed non-admin role to perform approval!"
        print("[+] [SECURITY PASSED] Correctly blocked non-admin user from performing approvals.")

        # -------------------------------------------------------------
        # 5. VERIFY HITL APPROVAL WORKFLOW & DYNAMIC RE-WRITES
        # -------------------------------------------------------------
        print("\n[7] Processing AI Suggestion HITL APPROVAL workflow...")
        
        # Approve the secure URL suggestion as Admin
        approve_resp = client.post(f"/api/admin/validation/suggestions/{sugg1_id}/approve", headers=admin_headers)
        assert approve_resp.status_code == 200, f"Approval failed: {approve_resp.text}"
        approved = approve_resp.json()
        assert approved["status"] == "applied"
        assert approved["reviewed_by"] == "admin"
        print("[+] Suggestion marked as 'applied' and reviewer set to 'admin'.")

        # ASSERT THAT STAGING_COMPANY RECORD WAS DYNAMICALLY UPDATED
        company_resp = client.get(f"/api/companies/{company_id}", headers=admin_headers)
        assert company_resp.status_code == 200, f"Company retrieval failed: {company_resp.text}"
        company_data = company_resp.json()
        assert company_data["website_url"] == "https://secure-beta-site.com"
        print("[+] [BUSINESS RULE PASSED] Verified company 'website_url' was dynamically re-written in the database!")

        # -------------------------------------------------------------
        # 6. VERIFY HITL REJECTION WORKFLOW
        # -------------------------------------------------------------
        print("\n[8] Processing AI Suggestion HITL REJECTION workflow...")
        
        # Reject the second suggestion
        reject_resp = client.post(f"/api/admin/validation/suggestions/{sugg2_id}/reject", headers=admin_headers)
        assert reject_resp.status_code == 200, f"Rejection failed: {reject_resp.text}"
        rejected = reject_resp.json()
        assert rejected["status"] == "rejected"
        assert rejected["reviewed_by"] == "admin"
        print("[+] Suggestion marked as 'rejected' and discarded cleanly.")

        # -------------------------------------------------------------
        # 7. VERIFY SYSTEM MONITORING METRICS
        # -------------------------------------------------------------
        print("\n[9] Querying System Monitoring Metrics (/api/admin/monitoring/stats)...")
        stats_resp = client.get("/api/admin/monitoring/stats", headers=admin_headers)
        assert stats_resp.status_code == 200, f"Stats failed: {stats_resp.text}"
        stats = stats_resp.json()
        assert stats["total_users"] >= 1
        assert stats["total_companies"] >= 1
        assert stats["system_status"] == "healthy"
        print(f"[+] Real-time stats: {stats['total_users']} users, {stats['total_companies']} companies, DB Size: {stats['database_file_size_bytes']} bytes.")
        print("[+] System health metrics successfully verified.")

        # -------------------------------------------------------------
        # 8. TEARDOWN ADMIN TEST RECORDSET
        # -------------------------------------------------------------
        print("\n[10] Tearing down admin test records...")
        
        # Delete Staging Company (cascades and deletes all validation runs/failures/suggestions too!)
        client.delete(f"/api/companies/{company_id}", headers=researcher_headers)
        print("[+] Database test records cleanly purged.")

    print("\n==========================================================")
    print("  ALL ADMINISTRATIVE SYSTEM TESTS PASSED! [OK]            ")
    print("==========================================================")

if __name__ == "__main__":
    run_suite()
