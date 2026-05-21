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
    print("  RUNNING FASTAPI COMPANY & PLACEMENT CRUD VALIDATION     ")
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

        # Viewer Login
        viewer_login = client.post("/api/auth/login", json={"username": "viewer", "password": "viewer123"})
        assert viewer_login.status_code == 200, "Viewer login failed!"
        viewer_token = viewer_login.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        print("[+] Viewer authenticated successfully.")

        # -------------------------------------------------------------
        # 2. COMPANY CRUD VALIDATION
        # -------------------------------------------------------------
        print("\n[3] Testing COMPANY CRUD endpoints...")

        # Create StagingCompany
        company_name = f"Global Tech Solutions {uuid.uuid4().hex[:4].upper()}"
        create_company_resp = client.post("/api/companies", headers=researcher_headers, json={
            "name": company_name,
            "category": "Technology & AI Services",
            "incorporation_year": "2018",
            "website_url": "https://globaltech.ai",
            "primary_contact_email": "careers@globaltech.ai",
            "overview_text": "Pioneering state-of-the-art enterprise ML systems."
        })
        assert create_company_resp.status_code == 201, f"Company creation failed: {create_company_resp.text}"
        company = create_company_resp.json()
        company_id = company["company_id"]
        print(f"[+] Successfully registered company: '{company_name}' (ID: {company_id})")

        # Duplicate Name Check
        dup_company_resp = client.post("/api/companies", headers=researcher_headers, json={
            "name": company_name,
            "category": "Different Category"
        })
        assert dup_company_resp.status_code == 400, "Expected 400 Bad Request on duplicate company name!"
        print("[+] [VALIDATION SUCCESS] Correctly blocked duplicate company name registration.")

        # Update Company Profile
        update_company_resp = client.put(f"/api/companies/{company_id}", headers=researcher_headers, json={
            "employee_size": "500-1000",
            "website_url": "https://globaltech.io"
        })
        assert update_company_resp.status_code == 200
        assert update_company_resp.json()["employee_size"] == "500-1000"
        assert update_company_resp.json()["website_url"] == "https://globaltech.io"
        print("[+] Successfully updated company web details and employee size.")

        # -------------------------------------------------------------
        # 3. PLACEMENT DRIVE CRUD VALIDATION
        # -------------------------------------------------------------
        print("\n[4] Testing PLACEMENT DRIVE CRUD endpoints...")

        # Create Placement Drive for the company
        drive_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        create_drive_resp = client.post("/api/placements/drives", headers=researcher_headers, json={
            "company_id": company_id,
            "title": "Software Development Engineer Campus Drive 2026",
            "job_role": "Associate SDE",
            "job_description": "Work on distributed cloud architectures.",
            "eligibility_criteria": "CGPA >= 8.0, B.Tech CSE/ECE",
            "package_lpa": 12.5,
            "drive_date": drive_date,
            "status": "Upcoming"
        })
        assert create_drive_resp.status_code == 201, f"Drive creation failed: {create_drive_resp.text}"
        drive = create_drive_resp.json()
        drive_id = drive["id"]
        print(f"[+] Registered drive: '{drive['title']}' (ID: {drive_id})")

        # List Drives (Verify joinedload company eager optimization works!)
        list_drives_resp = client.get("/api/placements/drives", headers=viewer_headers)
        assert list_drives_resp.status_code == 200, f"List drives failed: {list_drives_resp.text}"
        drives = list_drives_resp.json()
        assert len(drives) >= 1
        
        # Verify eager company is populated
        matching_drive = [d for d in drives if d["id"] == drive_id][0]
        assert matching_drive["company"]["company_id"] == company_id
        assert matching_drive["company"]["name"] == company_name
        print("[+] [OPTIMIZATION SUCCESS] Eager loading checked: Company details successfully nested in drive response.")

        # -------------------------------------------------------------
        # 4. APPLICATION TRACKING VALIDATION
        # -------------------------------------------------------------
        print("\n[5] Testing APPLICATION TRACKING CRUD endpoints...")

        # Create a Student to apply
        student_roll = f"EE-{uuid.uuid4().hex[:6].upper()}"
        student_create_resp = client.post("/api/students", headers=researcher_headers, json={
            "first_name": "Alex",
            "last_name": "Smith",
            "roll_number": student_roll,
            "department": "Electrical Engineering",
            "graduation_year": 2026,
            "cgpa": 8.7
        })
        assert student_create_resp.status_code == 201
        student_id = student_create_resp.json()["id"]
        print(f"[+] Seeded student: Alex Smith (ID: {student_id})")

        # Apply Student to Seagate Drive
        apply_resp = client.post("/api/placements/applications", headers=researcher_headers, json={
            "drive_id": drive_id,
            "student_id": student_id,
            "notes": "Eagerly excited to join the enterprise ML infrastructure team!"
        })
        assert apply_resp.status_code == 201, f"Application submission failed: {apply_resp.text}"
        application = apply_resp.json()
        application_id = application["id"]
        assert application["status"] == "Applied"
        print(f"[+] Successfully submitted application. Application ID: {application_id}")

        # Duplicate Application Prevention Check
        dup_apply_resp = client.post("/api/placements/applications", headers=researcher_headers, json={
            "drive_id": drive_id,
            "student_id": student_id
        })
        assert dup_apply_resp.status_code == 400
        print("[+] [VALIDATION SUCCESS] Correctly blocked duplicate student drive application submission.")

        # -------------------------------------------------------------
        # 5. INTERVIEW SCHEDULING VALIDATION
        # -------------------------------------------------------------
        print("\n[6] Testing INTERVIEW SCHEDULING CRUD endpoints...")

        interview_time = (datetime.utcnow() + timedelta(days=5)).isoformat()
        interview_create_resp = client.post("/api/placements/interviews", headers=researcher_headers, json={
            "application_id": application_id,
            "round_name": "Technical Interview - Systems Round",
            "scheduled_at": interview_time,
            "location_link": "https://meet.google.com/abc-defg-hij",
            "status": "Scheduled"
        })
        assert interview_create_resp.status_code == 201, f"Interview schedule failed: {interview_create_resp.text}"
        interview = interview_create_resp.json()
        interview_id = interview["id"]
        print(f"[+] Scheduled interview: '{interview['round_name']}' (ID: {interview_id})")

        # Update Interview Schedule (Reschedule, Log feedback)
        update_interview_resp = client.put(f"/api/placements/interviews/{interview_id}", headers=researcher_headers, json={
            "status": "Completed",
            "feedback": "Strong problem solver. Excellent systems design depth. Recommend proceeding."
        })
        assert update_interview_resp.status_code == 200
        assert update_interview_resp.json()["status"] == "Completed"
        assert "Strong problem solver" in update_interview_resp.json()["feedback"]
        print("[+] Interview marked as Completed and feedback logged successfully.")

        # -------------------------------------------------------------
        # 6. PLACEMENT RESULTS & STATE SYNC VALIDATION
        # -------------------------------------------------------------
        print("\n[7] Testing PLACEMENT SELECTION RESULTS & state synchronizations...")

        # Publish Selection Result as "Selected"
        result_publish_resp = client.post("/api/placements/results", headers=researcher_headers, json={
            "application_id": application_id,
            "status": "Selected",
            "offered_package_lpa": 14.0,
            "remarks": "Offered after excellent overall feedback across all technical rounds."
        })
        assert result_publish_resp.status_code == 201, f"Result publishing failed: {result_publish_resp.text}"
        result = result_publish_resp.json()
        result_id = result["id"]
        print(f"[+] Result published successfully. Status: Selected, Package: 14.0 LPA (ID: {result_id})")

        # Verify EXCLUSIVITY and STATE SYNC: Does the application state dynamically sync to "Offered"?
        get_app_resp = client.get(f"/api/placements/applications/{application_id}", headers=viewer_headers)
        assert get_app_resp.status_code == 200
        assert get_app_resp.json()["status"] == "Offered", f"Sync state failure: Application status is {get_app_resp.json()['status']} instead of 'Offered'!"
        print("[+] [BUSINESS RULE SUCCESS] Sync state verified: publication of 'Selected' result set application status to 'Offered'.")

        # Delete result record
        delete_result_resp = client.delete(f"/api/placements/results/{result_id}", headers=researcher_headers)
        assert delete_result_resp.status_code == 204
        
        # Verify State Rollback: Does application state reset to "Applied"?
        get_app_reset_resp = client.get(f"/api/placements/applications/{application_id}", headers=viewer_headers)
        assert get_app_reset_resp.json()["status"] == "Applied", "Sync state rollback failure: Application status not reset!"
        print("[+] [BUSINESS RULE SUCCESS] Sync state rollback verified: deletion of result successfully rolled back application status to 'Applied'.")

        # -------------------------------------------------------------
        # 7. CASCADE DELETION POLICIES VALIDATION
        # -------------------------------------------------------------
        print("\n[8] Testing parent StagingCompany CASCADE DELETIONS...")

        # Delete Seagate Company profile
        delete_company_resp = client.delete(f"/api/companies/{company_id}", headers=researcher_headers)
        assert delete_company_resp.status_code == 204
        print("[+] Issued StagingCompany DELETE request. Deletion completed successfully.")

        # Check Company 404
        get_company_fail = client.get(f"/api/companies/{company_id}", headers=viewer_headers)
        assert get_company_fail.status_code == 404
        print("[+] Confirmed company record is deleted (404).")

        # Check Placement Drive 404 (Cascaded!)
        get_drive_fail = client.get(f"/api/placements/drives/{drive_id}", headers=viewer_headers)
        assert get_drive_fail.status_code == 404
        print("[+] [CASCADE SUCCESS] Confirmed recruitment drive record was automatically deleted.")

        # Check Application 404 (Cascaded!)
        get_app_fail = client.get(f"/api/placements/applications/{application_id}", headers=viewer_headers)
        assert get_app_fail.status_code == 404
        print("[+] [CASCADE SUCCESS] Confirmed student application record was automatically deleted.")

        # Cleanup student record
        client.delete(f"/api/students/{student_id}", headers=researcher_headers)

    print("\n==========================================================")
    print("  ALL COMPANY & PLACEMENT CRUD TESTS PASSED! [OK]       ")
    print("==========================================================")

if __name__ == "__main__":
    run_suite()
