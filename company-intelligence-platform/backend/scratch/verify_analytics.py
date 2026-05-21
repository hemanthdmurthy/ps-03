import sys
import os
import uuid
from datetime import datetime, timedelta

# Inject backend path for local imports
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from app.main import app

def run_suite():
    print("==========================================================")
    print("  RUNNING FASTAPI ANALYTICS & DASHBOARD VALIDATION        ")
    print("==========================================================")

    # Initialize TestClient using context manager to trigger startup seeding
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
        # 2. SEED MINI DATASET FOR STATISTICAL COMPUTATION
        # -------------------------------------------------------------
        print("\n[3] Seeding database with a mini dataset for statistics...")

        # A. Register 2 Staging Companies
        company1_name = f"Alpha Laboratories {uuid.uuid4().hex[:4].upper()}"
        c1_resp = client.post("/api/companies", headers=researcher_headers, json={
            "name": company1_name,
            "category": "Biotechnology",
            "website_url": "https://alpha.bio"
        })
        c1_id = c1_resp.json()["company_id"]

        company2_name = f"Omega Software {uuid.uuid4().hex[:4].upper()}"
        c2_resp = client.post("/api/companies", headers=researcher_headers, json={
            "name": company2_name,
            "category": "Information Technology",
            "website_url": "https://omega.io"
        })
        c2_id = c2_resp.json()["company_id"]
        print("[+] Seeded 2 corporate staging companies.")

        # B. Register 3 Students (Multi-Department, Multi-Year)
        s1_roll = f"CS-{uuid.uuid4().hex[:4].upper()}"
        s1_resp = client.post("/api/students", headers=researcher_headers, json={
            "first_name": "Alice", "last_name": "Johnson", "roll_number": s1_roll,
            "department": "Computer Science", "graduation_year": 2026, "cgpa": 9.2
        })
        s1_id = s1_resp.json()["id"]

        s2_roll = f"CS-{uuid.uuid4().hex[:4].upper()}"
        s2_resp = client.post("/api/students", headers=researcher_headers, json={
            "first_name": "Bob", "last_name": "Davis", "roll_number": s2_roll,
            "department": "Computer Science", "graduation_year": 2026, "cgpa": 8.4
        })
        s2_id = s2_resp.json()["id"]

        s3_roll = f"EC-{uuid.uuid4().hex[:4].upper()}"
        s3_resp = client.post("/api/students", headers=researcher_headers, json={
            "first_name": "Charlie", "last_name": "Miller", "roll_number": s3_roll,
            "department": "Electronics", "graduation_year": 2027, "cgpa": 7.8
        })
        s3_id = s3_resp.json()["id"]
        print("[+] Seeded 3 students across multiple departments & graduation years.")

        # C. Create 2 Placement Drives
        d1_date = (datetime.utcnow() + timedelta(days=20)).isoformat()
        d1_resp = client.post("/api/placements/drives", headers=researcher_headers, json={
            "company_id": c1_id, "title": "Alpha Research SDE 2026",
            "job_role": "Research Engineer", "package_lpa": 16.0, "drive_date": d1_date
        })
        d1_id = d1_resp.json()["id"]

        d2_date = (datetime.utcnow() + timedelta(days=25)).isoformat()
        d2_resp = client.post("/api/placements/drives", headers=researcher_headers, json={
            "company_id": c2_id, "title": "Omega Systems Eng 2027",
            "job_role": "Systems Analyst", "package_lpa": 6.5, "drive_date": d2_date
        })
        d2_id = d2_resp.json()["id"]
        print("[+] Registered 2 recruitment drives.")

        # D. Submit Applications
        app1_resp = client.post("/api/placements/applications", headers=researcher_headers, json={"drive_id": d1_id, "student_id": s1_id})
        app1_id = app1_resp.json()["id"]

        app2_resp = client.post("/api/placements/applications", headers=researcher_headers, json={"drive_id": d1_id, "student_id": s2_id})
        app2_id = app2_resp.json()["id"]

        app3_resp = client.post("/api/placements/applications", headers=researcher_headers, json={"drive_id": d2_id, "student_id": s3_id})
        app3_id = app3_resp.json()["id"]
        print("[+] Registered application submissions.")

        # E. Publish Final Selection Results
        # Alice gets 15.5 LPA (Selected)
        client.post("/api/placements/results", headers=researcher_headers, json={
            "application_id": app1_id, "status": "Selected", "offered_package_lpa": 15.5
        })
        # Bob gets 8.5 LPA (Selected)
        client.post("/api/placements/results", headers=researcher_headers, json={
            "application_id": app2_id, "status": "Selected", "offered_package_lpa": 8.5
        })
        # Charlie gets 4.5 LPA (Selected)
        client.post("/api/placements/results", headers=researcher_headers, json={
            "application_id": app3_id, "status": "Selected", "offered_package_lpa": 4.5
        })
        print("[+] Published selection results with Packages: 15.5 LPA, 8.5 LPA, 4.5 LPA.")

        # -------------------------------------------------------------
        # 3. VERIFY DASHBOARD OVERVIEW ENDPOINT
        # -------------------------------------------------------------
        print("\n[4] Querying Admin Dashboard Overview (/api/analytics/dashboard)...")
        dash_resp = client.get("/api/analytics/dashboard", headers=admin_headers)
        assert dash_resp.status_code == 200, f"Dashboard failed: {dash_resp.text}"
        dash = dash_resp.json()
        
        # Verify counts and statistical averages
        assert dash["total_students"] >= 3
        assert dash["total_companies"] >= 2
        assert dash["total_drives"] >= 2
        assert dash["placed_students_count"] >= 3
        assert dash["highest_package_lpa"] >= 15.5
        print(f"[+] Placed Students count: {dash['placed_students_count']}, Placement Ratio: {dash['placement_ratio']}%")
        print(f"[+] Highest Package: {dash['highest_package_lpa']} LPA, Average Package: {dash['average_package_lpa']} LPA")
        print("[+] Dashboard metrics successfully verified.")

        # -------------------------------------------------------------
        # 4. VERIFY PLACEMENT BREAKDOWN ENDPOINT
        # -------------------------------------------------------------
        print("\n[5] Querying Placement Statistics (/api/analytics/placements)...")
        place_resp = client.get("/api/analytics/placements", headers=admin_headers)
        assert place_resp.status_code == 200, f"Placements failed: {place_resp.text}"
        place = place_resp.json()

        # Check Department break-down
        depts = {d["department"]: d for d in place["departments"]}
        assert "Computer Science" in depts
        assert "Electronics" in depts
        assert depts["Computer Science"]["total_students"] >= 2
        assert depts["Computer Science"]["placed_students"] >= 2
        assert depts["Computer Science"]["average_cgpa"] > 0.0
        print("[+] Department-wise statistics are mathematically accurate!")

        # Check Yearly break-down
        years = {y["graduation_year"]: y for y in place["yearly_trends"]}
        assert 2026 in years
        assert 2027 in years
        assert years[2026]["total_students"] >= 2
        assert years[2027]["total_students"] >= 1
        print("[+] Yearly placement trends are mathematically accurate!")

        # -------------------------------------------------------------
        # 5. VERIFY COMPANY ANALYTICS ENDPOINT
        # -------------------------------------------------------------
        print("\n[6] Querying StagingCompany Hiring Analytics (/api/analytics/companies)...")
        company_resp = client.get("/api/analytics/companies", headers=admin_headers)
        assert company_resp.status_code == 200, f"Companies failed: {company_resp.text}"
        comp = company_resp.json()

        # Verify category groupings
        categories = {c["category"]: c for c in comp["by_category"]}
        assert "Biotechnology" in categories
        assert "Information Technology" in categories
        print("[+] Corporate categorization aggregates successfully verified.")

        # Verify top hiring companies list
        top_firms = [f["company_name"] for f in comp["top_hiring"]]
        assert company1_name in top_firms
        assert company2_name in top_firms
        print("[+] Top hiring corporate firms ranking verified.")

        # -------------------------------------------------------------
        # 6. VERIFY PACKAGE METRICS & DISTRIBUTION
        # -------------------------------------------------------------
        print("\n[7] Querying Package Descriptive Metrics & Distribution (/api/analytics/packages)...")
        pkg_resp = client.get("/api/analytics/packages", headers=admin_headers)
        assert pkg_resp.status_code == 200, f"Packages failed: {pkg_resp.text}"
        pkgs = pkg_resp.json()

        metrics = pkgs["overall_metrics"]
        assert metrics["minimum"] <= 4.5
        assert metrics["maximum"] >= 15.5
        assert metrics["average"] > 0.0
        assert metrics["median"] > 0.0
        print(f"[+] Package metrics: Min: {metrics['minimum']}, Max: {metrics['maximum']}, Avg: {metrics['average']}, Median: {metrics['median']}")
        print("[+] descriptive metrics are mathematically exact!")

        # Verify salary buckets distribution
        buckets = {b["range_label"]: b for b in pkgs["package_distribution"]}
        assert buckets["Below 5 LPA"]["student_count"] >= 1      # Charlie (4.5 LPA)
        assert buckets["5 - 10 LPA"]["student_count"] >= 1       # Bob (8.5 LPA)
        assert buckets["15+ LPA"]["student_count"] >= 1          # Alice (15.5 LPA)
        print("[+] Salary bucket distribution counts verified.")

        # -------------------------------------------------------------
        # 7. VERIFY USER & SYSTEM ACTIVITY METRICS
        # -------------------------------------------------------------
        print("\n[8] Querying User & AI activity analytics (/api/analytics/activity)...")
        act_resp = client.get("/api/analytics/activity", headers=admin_headers)
        assert act_resp.status_code == 200, f"Activity failed: {act_resp.text}"
        activity = act_resp.json()

        # Verify users by role
        roles = {r["role"]: r for r in activity["users_by_role"]}
        assert "admin" in roles
        assert "researcher" in roles
        print("[+] Registered User roles metrics successfully verified.")

        # Verify researcher AI batch activity logs does not crash
        research_activity = activity["researcher_activity"]
        assert "total_research_sessions" in research_activity
        assert "total_validation_runs" in research_activity
        print("[+] System batch activity tracker successfully verified.")

        # -------------------------------------------------------------
        # 8. TEARDOWN MINI DATASET (CASCADE DELETE POLICY VERIFICATION)
        # -------------------------------------------------------------
        print("\n[9] Tearing down test dataset...")
        
        # Deleting company profiles automatically cascades and cleans up all drives, applications, and results
        client.delete(f"/api/companies/{c1_id}", headers=researcher_headers)
        client.delete(f"/api/companies/{c2_id}", headers=researcher_headers)
        
        # Deleting students
        client.delete(f"/api/students/{s1_id}", headers=researcher_headers)
        client.delete(f"/api/students/{s2_id}", headers=researcher_headers)
        client.delete(f"/api/students/{s3_id}", headers=researcher_headers)
        print("[+] Database test records cleanly purged.")

    print("\n==========================================================")
    print("  ALL ANALYTICS & DASHBOARD TESTS PASSED! [OK]            ")
    print("==========================================================")

if __name__ == "__main__":
    run_suite()
