import sys
import os
import uuid

# Inject backend path for local imports
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from app.main import app

def run_suite():
    print("==========================================================")
    print("  RUNNING FASTAPI USER & STUDENT CRUD VALIDATION TEST     ")
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
        # 2. USER CRUD VALIDATION
        # -------------------------------------------------------------
        print("\n[3] Testing USER CRUD endpoints...")

        # List all users as Admin
        users_list_resp = client.get("/api/users", headers=admin_headers)
        assert users_list_resp.status_code == 200, f"Failed listing users: {users_list_resp.text}"
        users = users_list_resp.json()
        print(f"[+] User list retrieved. Total system users: {len(users)}")
        
        # Verify default accounts exist in list
        usernames = [u["username"] for u in users]
        assert "admin" in usernames
        assert "researcher" in usernames
        assert "viewer" in usernames

        # Create a new user as Admin
        new_username = f"hr_recruiter_{uuid.uuid4().hex[:4]}"
        new_email = f"{new_username}@placementintel.com"
        create_user_resp = client.post("/api/users", headers=admin_headers, json={
            "username": new_username,
            "email": new_email,
            "password": "securepassword99",
            "role": "viewer"
        })
        assert create_user_resp.status_code == 201, f"User creation failed: {create_user_resp.text}"
        created_user = create_user_resp.json()
        user_uuid = created_user["id"]
        print(f"[+] Successfully registered user: {new_username} (ID: {user_uuid})")

        # Non-admin role restriction check (Viewer trying to create user)
        viewer_fail_resp = client.post("/api/users", headers=viewer_headers, json={
            "username": "unauthorized_user",
            "email": "unauth@placementintel.com",
            "password": "somepassword"
        })
        assert viewer_fail_resp.status_code == 403, "Expected 403 Forbidden for Viewer on user creation!"
        print("[+] [SECURITY SUCCESS] Blocked non-admin user creation attempt with 403.")

        # Update newly created user
        update_user_resp = client.put(f"/api/users/{user_uuid}", headers=admin_headers, json={
            "role": "researcher",
            "is_active": False
        })
        assert update_user_resp.status_code == 200, f"User update failed: {update_user_resp.text}"
        updated_user = update_user_resp.json()
        assert updated_user["role"] == "researcher"
        assert updated_user["is_active"] is False
        print("[+] Successfully updated user role to 'researcher' and status to inactive.")

        # Delete user
        delete_user_resp = client.delete(f"/api/users/{user_uuid}", headers=admin_headers)
        assert delete_user_resp.status_code == 204
        print("[+] User deleted successfully.")

        # Verify deletion
        get_user_deleted = client.get(f"/api/users/{user_uuid}", headers=admin_headers)
        assert get_user_deleted.status_code == 404
        print("[+] Confirmed user record is fully deleted.")

        # -------------------------------------------------------------
        # 3. STUDENT CRUD VALIDATION
        # -------------------------------------------------------------
        print("\n[4] Testing STUDENT CRUD endpoints...")

        # Create a new student as Researcher
        roll_num = f"CS-{uuid.uuid4().hex[:6].upper()}"
        student_create_resp = client.post("/api/students", headers=researcher_headers, json={
            "first_name": "Jane",
            "last_name": "Doe",
            "roll_number": roll_num,
            "department": "Computer Science",
            "graduation_year": 2027,
            "cgpa": 9.5
        })
        assert student_create_resp.status_code == 201, f"Student registration failed: {student_create_resp.text}"
        student = student_create_resp.json()
        student_uuid = student["id"]
        print(f"[+] Successfully registered student: Jane Doe (Roll: {roll_num}, ID: {student_uuid})")

        # Duplicate Roll Number Check
        dup_student_resp = client.post("/api/students", headers=researcher_headers, json={
            "first_name": "John",
            "last_name": "Smith",
            "roll_number": roll_num, # Same roll number!
            "department": "Mechanical Engineering",
            "graduation_year": 2027,
            "cgpa": 8.0
        })
        assert dup_student_resp.status_code == 400, "Expected 400 Bad Request on duplicate roll number!"
        print("[+] [VALIDATION SUCCESS] Correctly rejected registration of duplicate roll number.")

        # Boundary Validation: CGPA > 10.0 Check
        cgpa_high_resp = client.post("/api/students", headers=researcher_headers, json={
            "first_name": "John",
            "last_name": "Smith",
            "roll_number": f"ME-{uuid.uuid4().hex[:4].upper()}",
            "department": "Mechanical Engineering",
            "graduation_year": 2027,
            "cgpa": 11.0 # Invalid!
        })
        assert cgpa_high_resp.status_code == 422, f"Expected 422 Unprocessable Entity for CGPA 11.0! Status: {cgpa_high_resp.status_code}"
        print("[+] [VALIDATION SUCCESS] Correctly rejected CGPA above 10.0 boundary with 422.")

        # Update Student details
        update_student_resp = client.put(f"/api/students/{student_uuid}", headers=researcher_headers, json={
            "cgpa": 9.8,
            "department": "Data Science"
        })
        assert update_student_resp.status_code == 200, f"Student update failed: {update_student_resp.text}"
        updated_student = update_student_resp.json()
        assert updated_student["cgpa"] == 9.8
        assert updated_student["department"] == "Data Science"
        print("[+] Student CGPA and department updated successfully.")

        # -------------------------------------------------------------
        # 4. STUDENT PROFILE CRUD VALIDATION
        # -------------------------------------------------------------
        print("\n[5] Testing STUDENT PROFILE CRUD endpoints...")

        # Create Profile
        create_profile_resp = client.post(f"/api/students/{student_uuid}/profile", headers=researcher_headers, json={
            "bio": "Passionate data scientist and open source developer.",
            "github_url": "https://github.com/janedoe",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "portfolio_url": "https://janedoe.dev"
        })
        assert create_profile_resp.status_code == 201, f"Profile creation failed: {create_profile_resp.text}"
        profile = create_profile_resp.json()
        print(f"[+] Student profile created. Bio: '{profile['bio']}'")

        # Retrieve Profile
        get_profile_resp = client.get(f"/api/students/{student_uuid}/profile", headers=viewer_headers)
        assert get_profile_resp.status_code == 200
        assert get_profile_resp.json()["portfolio_url"] == "https://janedoe.dev"
        print("[+] Profile fetched and verified successfully.")

        # Update Profile
        update_profile_resp = client.put(f"/api/students/{student_uuid}/profile", headers=researcher_headers, json={
            "bio": "Data Scientist | ML Engineer",
            "github_url": "https://github.com/janedoe",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "portfolio_url": "https://janedoe.me"
        })
        assert update_profile_resp.status_code == 200
        assert update_profile_resp.json()["portfolio_url"] == "https://janedoe.me"
        assert update_profile_resp.json()["bio"] == "Data Scientist | ML Engineer"
        print("[+] Student profile bio and URL updated successfully.")

        # -------------------------------------------------------------
        # 5. RESUME CRUD VALIDATION (EXCLUSIVITY CHECK)
        # -------------------------------------------------------------
        print("\n[6] Testing RESUME CRUD and Exclusivity rules...")

        # Upload first resume (primary)
        r1_resp = client.post(f"/api/students/{student_uuid}/resumes", headers=researcher_headers, json={
            "file_name": "jane_doe_cs_resume.pdf",
            "file_path": "/uploads/resumes/jane_doe_cs_resume.pdf",
            "is_primary": True
        })
        assert r1_resp.status_code == 201
        r1_uuid = r1_resp.json()["id"]
        print("[+] Resume 1 registered as primary.")

        # Upload second resume (secondary)
        r2_resp = client.post(f"/api/students/{student_uuid}/resumes", headers=researcher_headers, json={
            "file_name": "jane_doe_ml_resume.pdf",
            "file_path": "/uploads/resumes/jane_doe_ml_resume.pdf",
            "is_primary": False
        })
        assert r2_resp.status_code == 201
        r2_uuid = r2_resp.json()["id"]
        print("[+] Resume 2 registered as non-primary.")

        # Exclusivity rule: Upload third resume as primary
        # This must automatically demote Resume 1 to non-primary!
        r3_resp = client.post(f"/api/students/{student_uuid}/resumes", headers=researcher_headers, json={
            "file_name": "jane_doe_fullstack_resume.pdf",
            "file_path": "/uploads/resumes/jane_doe_fullstack_resume.pdf",
            "is_primary": True
        })
        assert r3_resp.status_code == 201
        r3_uuid = r3_resp.json()["id"]
        print("[+] Resume 3 registered as primary. Triggering automated demotion for others...")

        # Fetch resumes and assert exclusivity rule is correctly enforced!
        resumes_list_resp = client.get(f"/api/students/{student_uuid}/resumes", headers=viewer_headers)
        assert resumes_list_resp.status_code == 200
        resumes = resumes_list_resp.json()
        assert len(resumes) == 3

        # Enforce that exactly 1 resume is primary, and it is Resume 3
        primary_resumes = [r for r in resumes if r["is_primary"] is True]
        assert len(primary_resumes) == 1, "Exclusivity failure: More than one resume is marked primary!"
        assert primary_resumes[0]["id"] == r3_uuid, "Exclusivity failure: Newly uploaded primary resume is not the active primary!"
        
        # Verify that Resume 1 was successfully demoted to False
        r1_demoted = [r for r in resumes if r["id"] == r1_uuid][0]
        assert r1_demoted["is_primary"] is False, "Exclusivity failure: Old primary resume was not demoted!"
        print("[+] [BUSINESS RULE SUCCESS] Primary resume exclusivity confirmed: Resume 1 demoted, Resume 3 active primary.")

        # -------------------------------------------------------------
        # 6. SKILL CRUD & MASTER LIST SEEDING VALIDATION
        # -------------------------------------------------------------
        print("\n[7] Testing SKILL CRUD and dynamic master list seeding...")

        # Associate Skill 1 (Python)
        s1_resp = client.post(f"/api/students/{student_uuid}/skills", headers=researcher_headers, json={
            "skill_name": "Python",
            "proficiency_level": "Expert"
        })
        assert s1_resp.status_code == 201, f"Failed associating skill: {s1_resp.text}"
        s1_data = s1_resp.json()
        assert s1_data["name"] == "Python"
        assert s1_data["proficiency_level"] == "Expert"
        print("[+] Associated 'Python' as Expert.")

        # Associate Skill 2 (React)
        s2_resp = client.post(f"/api/students/{student_uuid}/skills", headers=researcher_headers, json={
            "skill_name": "React",
            "proficiency_level": "Intermediate"
        })
        assert s2_resp.status_code == 201
        print("[+] Associated 'React' as Intermediate.")

        # Verify master skills table has seeded Python and React
        master_skills_resp = client.get("/api/skills", headers=viewer_headers)
        assert master_skills_resp.status_code == 200
        master_skills = master_skills_resp.json()
        master_skill_names = [sk["name"] for sk in master_skills]
        assert "Python" in master_skill_names
        assert "React" in master_skill_names
        print("[+] [BUSINESS RULE SUCCESS] Confirmed Python and React dynamically seeded into the master Skills list!")

        # -------------------------------------------------------------
        # 7. NESTED RETRIEVAL AND INTEGRATION VERIFICATION
        # -------------------------------------------------------------
        print("\n[8] Verifying fully integrated nested Student response profile...")
        
        detail_resp = client.get(f"/api/students/{student_uuid}", headers=viewer_headers)
        assert detail_resp.status_code == 200
        full_profile = detail_resp.json()
        
        assert full_profile["first_name"] == "Jane"
        assert full_profile["profile"]["bio"] == "Data Scientist | ML Engineer"
        assert len(full_profile["resumes"]) == 3
        assert len(full_profile["skills"]) == 2
        
        skill_names = [s["name"] for s in full_profile["skills"]]
        assert "Python" in skill_names
        assert "React" in skill_names
        print("[+] [SUCCESS] Fully integrated nested JSON structure matches frontend expectations.")

        # -------------------------------------------------------------
        # 8. CASCADE DELETION POLICIES VERIFICATION
        # -------------------------------------------------------------
        print("\n[9] Testing CASCADE DELETION policy...")
        
        # Delete student record
        delete_resp = client.delete(f"/api/students/{student_uuid}", headers=researcher_headers)
        assert delete_resp.status_code == 204
        print("[+] Issued Student DELETE request. Deletion completed successfully.")

        # Check student 404
        get_fail = client.get(f"/api/students/{student_uuid}", headers=viewer_headers)
        assert get_fail.status_code == 404
        print("[+] Confirmed student core record is deleted (404).")

        # Check profile 404
        get_profile_fail = client.get(f"/api/students/{student_uuid}/profile", headers=viewer_headers)
        assert get_profile_fail.status_code == 404
        print("[+] [CASCADE SUCCESS] Confirmed student profile record was automatically deleted.")

        # Check resumes cleaned up
        get_resumes_fail = client.get(f"/api/students/{student_uuid}/resumes", headers=viewer_headers)
        assert get_resumes_fail.status_code == 404
        print("[+] [CASCADE SUCCESS] Confirmed student resumes records were automatically deleted.")

    print("\n==========================================================")
    print("  ALL USER & STUDENT CRUD INTEGRATION TESTS PASSED! [OK]  ")
    print("==========================================================")

if __name__ == "__main__":
    run_suite()
