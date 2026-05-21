import sys
import os
import io

# Enforce UTF-8 encoding on Windows standard streams to prevent charmap codec crashes on box characters
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import json
import time


# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def print_separator(title):
    print("\n" + "=" * 80)
    print(f" {title} ")
    print("=" * 80)

def test_1_health_check():
    """Verify that versioned public health check route bypasses authentication and returns the custom shape."""
    print_separator("TEST 1: Health Check V1 (Public Route Bypass)")

    response = client.get("/api/v1/")
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    print(f"  X-Request-ID: {response.headers.get('X-Request-ID')}")
    print(f"  X-Process-Time: {response.headers.get('X-Process-Time')}")
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))

    assert response.status_code == 200
    assert "supabase_connection" in response.json()
    # Check that public route is not wrapped by StandardResponseMiddleware
    assert "success" not in response.json()
    print("[+] Test Passed!")

def test_2_failed_authentication():
    """Verify that accessing protected versioned routes without a token yields a standardized 401 response."""
    print_separator("TEST 2: Access Protected Route V1 Without Token")

    response = client.get("/api/v1/students")
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AUTHENTICATION_ERROR"
    assert "required" in data["error"]["message"]
    assert "request_id" in data["meta"]
    print("[+] Test Passed!")

def test_3_invalid_login_validation():
    """Verify that bad login credentials on versioned endpoints trigger standard bad request/unauthorized structures."""
    print_separator("TEST 3: Login V1 With Invalid Credentials")

    body = {
        "username": "wronguser",
        "password": "wrongpassword"
    }
    response = client.post("/api/v1/auth/login", json=body)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))

    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    print("[+] Test Passed!")

def test_4_pydantic_validation_error():
    """Verify that Pydantic validation failures on versioned endpoints trigger structured 422 errors."""
    print_separator("TEST 4: Pydantic Validation Handlers V1 (Register)")

    # Missing required field 'email', too short password
    body = {
        "username": "us", # too short, min is 3
        "password": "123", # too short, min is 6
    }
    response = client.post("/api/v1/auth/register", json=body)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(json.dumps(response.json(), indent=2))

    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert len(data["error"]["details"]) > 0
    print("[+] Test Passed!")

def test_5_successful_authentication_and_envelope():
    """Verify that successful login on versioned endpoints issues tokens, and successful calls to protected endpoints wrap responses."""
    print_separator("TEST 5: Successful Login V1 & Standardized Response Wrapping")

    body = {
        "username": "admin",
        "password": "admin123"
    }
    response = client.post("/api/v1/auth/login", json=body)
    print(f"Login Status Code: {response.status_code}")

    assert response.status_code == 200
    login_data = response.json()

    assert login_data["success"] is True
    assert "access_token" in login_data["data"]
    token = login_data["data"]["access_token"]
    print("Issued Bearer Access Token successfully.")

    # Now query a protected versioned route using this token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/students", headers=headers)
    print(f"\nStudents GET Status Code: {response.status_code}")
    print("Response Body Structure:")
    print(json.dumps(response.json(), indent=2)[:500] + "\n...[truncated]...")

    assert response.status_code == 200
    students_data = response.json()
    assert students_data["success"] is True
    assert isinstance(students_data["data"], list)
    assert students_data["meta"]["request_id"] is not None
    print("[+] Test Passed!")

def test_6_rate_limiting():
    """Verify rate-limiting restrictions on versioned endpoints by triggering multiple rapid calls."""
    print_separator("TEST 6: Sliding Window Rate Limiting Enforcement V1")

    body = {
        "username": "admin",
        "password": "admin123"
    }
    login_res = client.post("/api/v1/auth/login", json=body)
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("Flooding versioned backend with requests to trigger rate limit...")

    from app.middleware.rate_limit import global_rate_limiter
    original_limit = global_rate_limiter.requests_per_minute

    try:
        global_rate_limiter.requests_per_minute = 5 # Set threshold to 5 for rapid testing

        limit_triggered = False
        for i in range(10):
            response = client.get("/api/v1/students", headers=headers)
            print(f"Request #{i+1} status: {response.status_code}")
            if response.status_code == 429:
                limit_triggered = True
                print("\nStandardized 429 Rate Limited Response:")
                print(json.dumps(response.json(), indent=2))
                print(f"Retry-After Header: {response.headers.get('Retry-After')}s")
                break

        assert limit_triggered is True
        print("[+] Test Passed!")
    finally:
        global_rate_limiter.requests_per_minute = original_limit

def test_7_frontend_remediation_integration():
    """Verify that versioned frontend compatibility remediation routes work and update DB state correctly."""
    print_separator("TEST 7: Frontend Remediation V1 Integration")

    response = client.get("/api/v1/remediation/suggestions")
    print(f"GET /api/v1/remediation/suggestions status: {response.status_code}")
    assert response.status_code == 200
    suggestions = response.json()
    assert isinstance(suggestions, list)
    print(f"Suggestions count currently in DB: {len(suggestions)}")

    from app.core.database import SessionLocal
    from app.models.staging_company import StagingCompany
    from app.models.validation_run import ValidationCorrectionSuggestion

    db = SessionLocal()
    try:
        test_company = db.query(StagingCompany).filter(StagingCompany.name == "Test Remediation Co").first()
        if not test_company:
            test_company = StagingCompany(
                company_id="test-remed-co-uuid",
                name="Test Remediation Co",
                nature_of_company="pvt ltd",
                website_url="http://remediation.co",
                processing_status="completed"
            )
            db.add(test_company)
            db.commit()
            db.refresh(test_company)

        sugg_id = "test-sugg-uuid-999"
        suggestion = db.query(ValidationCorrectionSuggestion).filter(ValidationCorrectionSuggestion.id == sugg_id).first()
        if suggestion:
            db.delete(suggestion)
            db.commit()

        suggestion = ValidationCorrectionSuggestion(
            id=sugg_id,
            company_id=test_company.company_id,
            field_name="nature_of_company",
            original_value="pvt ltd",
            suggested_value="Private Limited",
            rationale="Standardised corporate legal suffix to official Private Limited naming conventions.",
            confidence=0.92,
            status="pending"
        )
        db.add(suggestion)
        db.commit()
        print("[+] Seeded test company and pending correction suggestion successfully.")

        response = client.get("/api/v1/remediation/suggestions")
        assert response.status_code == 200
        suggestions = response.json()
        seeded_suggs = [s for s in suggestions if s["id"] == sugg_id]
        assert len(seeded_suggs) == 1
        assert seeded_suggs[0]["company_name"] == "Test Remediation Co"
        assert seeded_suggs[0]["status"] == "pending"
        print("[+] GET list successfully includes company_name and details.")

        approve_resp = client.post(f"/api/v1/remediation/suggestion/{sugg_id}/approve")
        print(f"POST Approve status: {approve_resp.status_code}")
        assert approve_resp.status_code == 200
        approve_data = approve_resp.json()
        assert approve_data["success"] is True
        assert approve_data["status"] == "applied"

        db.refresh(suggestion)
        assert suggestion.status == "applied"
        db.refresh(test_company)
        assert test_company.nature_of_company == "Private Limited"
        print("[+] Approve flow successfully updated DB suggestion status and company field!")

        db.delete(suggestion)
        db.delete(test_company)
        db.commit()
        print("[+] Cleaned up integration test seed records.")
        print("[+] Test Passed!")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def test_8_redis_caching():
    """Verify Redis caching service GET/SET, pattern invalidation, and versioned endpoint response caching."""
    print_separator("TEST 8: Redis Caching and Response Decorator Validation V1")

    from app.services.cache_service import cache_service
    import asyncio

    async def run_manual_tests():
        await cache_service.initialize()
        assert cache_service.redis is not None
        print(f"[+] Redis client is active. Fallback state: {cache_service.is_fallback}")

        test_key = "test:integration:op:v1"
        await cache_service.set(test_key, {"status": "ok", "count": 100}, ttl=30)
        
        val = await cache_service.get(test_key)
        assert val == {"status": "ok", "count": 100}
        print("[+] Cache GET/SET dictionary validation succeeded.")

        await cache_service.delete(test_key)
        val = await cache_service.get(test_key)
        assert val is None
        print("[+] Cache DELETE validation succeeded.")

        await cache_service.close()

    # Step 1: Run manual async cache operations in a fresh event loop
    asyncio.run(run_manual_tests())

    # Step 2: Query analytics dashboard synchronously within TestClient lifecycle context.
    body = {
        "username": "admin",
        "password": "admin123"
    }
    
    with TestClient(app) as test_client:
        login_res = test_client.post("/api/v1/auth/login", json=body)
        token = login_res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = test_client.get("/api/v1/analytics/dashboard", headers=headers)
        assert res.status_code == 200
        dashboard_data = res.json()
        assert dashboard_data["success"] is True
        print("[+] Query to /api/v1/analytics/dashboard succeeded.")

    # Step 3: Run verification async in a second fresh event loop to check Redis cache state.
    async def run_verify_test(expected_data):
        await cache_service.initialize()
        assert cache_service.redis is not None
        
        cache_key = "analytics:/api/v1/analytics/dashboard"
        cached_data = await cache_service.get(cache_key)
        assert cached_data is not None
        assert cached_data["total_students"] == expected_data["data"]["total_students"]
        print(f"[+] API response successfully cached under key: '{cache_key}'")
        
        await cache_service.close()

    asyncio.run(run_verify_test(dashboard_data))
    print("[+] Test Passed!")

if __name__ == "__main__":
    print("Starting integration test suite for versioned V1 production API...")
    try:
        test_1_health_check()
        test_2_failed_authentication()
        test_3_invalid_login_validation()
        test_4_pydantic_validation_error()
        test_5_successful_authentication_and_envelope()
        test_6_rate_limiting()
        test_7_frontend_remediation_integration()
        test_8_redis_caching()
        print("\n" + "=" * 80)
        print(" ALL V1 TESTS PASSED SUCCESSFULLY! ")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n[!] Test failed: Assertion Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
