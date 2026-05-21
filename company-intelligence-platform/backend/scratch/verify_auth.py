# scratch/verify_auth.py
import sys
import os
from fastapi import Depends
from fastapi.testclient import TestClient

# Ensure the backend directory is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.dependencies.auth_deps import RoleChecker, get_active_user

# -------------------------------------------------------------
# 1. Dynamically Register Test Routes to Verify Role Guards
# -------------------------------------------------------------
@app.get("/api/test/admin-only")
def test_admin_route(user=Depends(RoleChecker(["admin"]))):
    return {"status": "success", "message": f"Welcome Admin '{user.username}'!"}

@app.get("/api/test/researcher-or-admin")
def test_researcher_route(user=Depends(RoleChecker(["admin", "researcher"]))):
    return {"status": "success", "message": f"Welcome '{user.username}' (Role: {user.role})!"}

@app.get("/api/test/any-active")
def test_any_active_route(user=Depends(get_active_user)):
    return {"status": "success", "message": f"Welcome active user '{user.username}'!"}


def main():
    print("==========================================================")
    print("  RUNNING FASTAPI JWT AUTH & ROLE AUTHORIZATION TEST")
    print("==========================================================")

    # Initialize the FastAPI TestClient within a context manager block
    # This guarantees that Starlette triggers all startup hooks (seeding default accounts)
    with TestClient(app) as client:
        print("[1] FastAPI TestClient successfully initialized and seeded default accounts.")

        # -------------------------------------------------------------
        # 2. Login verification with default seeded users
        # -------------------------------------------------------------
        print("\n[2] Testing login credentials...")
        
        # Successful login
        login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        if login_resp.status_code != 200:
            print(f"[-] Login failed with status {login_resp.status_code}: {login_resp.text}")
        assert login_resp.status_code == 200, "Seeded Admin login failed!"
        admin_tokens = login_resp.json()
        admin_access_token = admin_tokens["access_token"]
        admin_refresh_token = admin_tokens["refresh_token"]
        print(f"[+] [SUCCESS] Logged in 'admin'. Got Access Token starting with: {admin_access_token[:20]}...")

        # Login using email (dual matching UX check!)
        email_login_resp = client.post("/api/auth/login", json={"username": "admin@placementintel.com", "password": "admin123"})
        assert email_login_resp.status_code == 200, "Login via email failed!"
        print("[+] [SUCCESS] Dual login UX confirmed: successfully logged in 'admin' via email address.")

        # Incorrect password check
        bad_login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
        assert bad_login_resp.status_code == 401, "Expected login failure on incorrect password!"
        print("[+] [SUCCESS] Hashing verified: rejected login on incorrect credentials.")

        # -------------------------------------------------------------
        # 3. Register a new user
        # -------------------------------------------------------------
        import uuid
        new_username = f"user_{uuid.uuid4().hex[:6]}"
        new_email = f"{new_username}@placementintel.com"
        print(f"\n[3] Registering a new researcher account: '{new_username}'...")
        
        register_resp = client.post("/api/auth/register", json={
            "username": new_username,
            "email": new_email,
            "password": "securepassword123",
            "role": "researcher"
        })
        assert register_resp.status_code == 201, "User registration failed!"
        registered_data = register_resp.json()
        assert registered_data["username"] == new_username
        assert registered_data["role"] == "researcher"
        print(f"[+] [SUCCESS] User registration completed. Registered ID: {registered_data['id']}")

        # -------------------------------------------------------------
        # 4. Protected User Profile Profile Route (/me)
        # -------------------------------------------------------------
        print("\n[4] Accessing protected '/me' profile endpoint...")
        
        headers = {"Authorization": f"Bearer {admin_access_token}"}
        me_resp = client.get("/api/auth/me", headers=headers)
        assert me_resp.status_code == 200, "Failed to fetch profile details!"
        me_data = me_resp.json()
        assert me_data["username"] == "admin"
        assert me_data["role"] == "admin"
        print(f"[+] [SUCCESS] Profile fetched. Logged-in Username: '{me_data['username']}', Role: '{me_data['role']}'.")

        # Access without header
        unauth_resp = client.get("/api/auth/me")
        assert unauth_resp.status_code == 401, "Profile route accessible without token!"
        print("[+] [SUCCESS] Blocked access to protected profile without token.")

        # -------------------------------------------------------------
        # 5. Token Refresh verification
        # -------------------------------------------------------------
        print("\n[5] Testing Token Refresh lifecycle...")
        refresh_resp = client.post("/api/auth/refresh", json={"refresh_token": admin_refresh_token})
        assert refresh_resp.status_code == 200, "Token refresh failed!"
        refreshed_tokens = refresh_resp.json()
        new_access_token = refreshed_tokens["access_token"]
        print(f"[+] [SUCCESS] Access token refreshed. New Access Token: {new_access_token[:20]}...")

        # Validate that the refreshed access token works
        refreshed_headers = {"Authorization": f"Bearer {new_access_token}"}
        refreshed_me = client.get("/api/auth/me", headers=refreshed_headers)
        assert refreshed_me.status_code == 200
        print("[+] [SUCCESS] Confirmed refreshed access token is fully valid.")

        # -------------------------------------------------------------
        # 6. Verification of Role-Based Authorization Guards (RoleChecker)
        # -------------------------------------------------------------
        print("\n[6] Testing Role-Based Route Guards (Admin, Researcher, Viewer)...")

        # Fetch tokens for different roles
        researcher_token = client.post("/api/auth/login", json={"username": "researcher", "password": "researcher123"}).json()["access_token"]
        viewer_token = client.post("/api/auth/login", json={"username": "viewer", "password": "viewer123"}).json()["access_token"]

        researcher_headers = {"Authorization": f"Bearer {researcher_token}"}
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # Route: ADMIN ONLY
        # Admin access -> OK
        admin_only_resp = client.get("/api/test/admin-only", headers=headers)
        assert admin_only_resp.status_code == 200
        # Researcher access -> Forbidden 403
        admin_only_res = client.get("/api/test/admin-only", headers=researcher_headers)
        assert admin_only_res.status_code == 403
        # Viewer access -> Forbidden 403
        admin_only_view = client.get("/api/test/admin-only", headers=viewer_headers)
        assert admin_only_view.status_code == 403
        print("[+] [SUCCESS] Admin-only route guard fully verified (Admin passed, Researcher & Viewer blocked with 403).")

        # Route: RESEARCHER OR ADMIN
        # Admin access -> OK
        res_or_admin_adm = client.get("/api/test/researcher-or-admin", headers=headers)
        assert res_or_admin_adm.status_code == 200
        # Researcher access -> OK
        res_or_admin_res = client.get("/api/test/researcher-or-admin", headers=researcher_headers)
        assert res_or_admin_res.status_code == 200
        # Viewer access -> Forbidden 403
        res_or_admin_view = client.get("/api/test/researcher-or-admin", headers=viewer_headers)
        assert res_or_admin_view.status_code == 403
        print("[+] [SUCCESS] Researcher-or-admin route guard fully verified (Admin & Researcher passed, Viewer blocked with 403).")

        # Route: ANY ACTIVE USER
        # Viewer access -> OK
        any_active_view = client.get("/api/test/any-active", headers=viewer_headers)
        assert any_active_view.status_code == 200
        print("[+] [SUCCESS] General active user route guard fully verified (Viewer passed).")

    print("\n==========================================================")
    print("  ALL FASTAPI JWT AUTH AND ROLE GUARD TESTS PASSED! [OK]")
    print("==========================================================")


if __name__ == "__main__":
    main()
