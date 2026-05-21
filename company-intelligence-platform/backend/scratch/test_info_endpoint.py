import sys
import os
import json

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_info_endpoint():
    print("=" * 80)
    print("Testing GET /info (Root level)")
    print("=" * 80)
    response = client.get("/info")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("[+] Root /info passed!")

def test_api_info_endpoint():
    print("=" * 80)
    print("Testing GET /api/info")
    print("=" * 80)
    response = client.get("/api/info")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("[+] /api/info passed!")

def test_api_v1_info_endpoint():
    print("=" * 80)
    print("Testing GET /api/v1/info")
    print("=" * 80)
    response = client.get("/api/v1/info")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("[+] /api/v1/info passed!")

if __name__ == "__main__":
    test_info_endpoint()
    test_api_info_endpoint()
    test_api_v1_info_endpoint()
    print("\nALL INFO ENDPOINT TESTS PASSED SUCCESSFULLY!")
