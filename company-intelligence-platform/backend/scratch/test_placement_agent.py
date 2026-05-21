import os
import sys
import time
import subprocess
import requests

# Force UTF-8 encoding for Windows standard streams to prevent UnicodeEncodeError with emojis/box-draws
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_endpoints():
    print("=" * 60)
    print("PLACEMENT AGENT INTEGRATION TEST SUITE")
    print("=" * 60)
    
    server_port = 8080
    env = os.environ.copy()
    env["PORT"] = str(server_port)
    env["ENVIRONMENT"] = "testing"
    env["PYTHONIOENCODING"] = "utf-8"
    
    # Start FastAPI server locally in background using virtual env python
    server_cmd = [
        "venv\\Scripts\\python", "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", str(server_port)
    ]
    
    print(f"[*] Starting local FastAPI server on 127.0.0.1:{server_port}...")
    # Inherit parent streams to output server logs directly to terminal for real-time trace
    server_proc = subprocess.Popen(server_cmd, env=env)
    
    # Dynamic wait loop for server startup readiness
    base_url = f"http://127.0.0.1:{server_port}"
    server_ready = False
    max_wait = 25  # seconds
    print(f"[*] Waiting up to {max_wait} seconds for server to be ready...")
    
    for i in range(max_wait):
        # Check if the process crashed
        if server_proc.poll() is not None:
            print("[!] Server process terminated prematurely.")
            break
            
        try:
            # Try our fast, lightweight AI health check route (exempt from JWT auth)
            r = requests.get(f"{base_url}/api/v1/placement-agent/health", timeout=5.0)
            if r.status_code == 200:
                print(f"[+] Server is ready and listening (Status: {r.status_code}) after {i+1} seconds!")
                server_ready = True
                break
        except Exception:
            pass
        time.sleep(1.0)

    if not server_ready:
        print("[!] Server failed to start or respond within timeout. Terminating...")
        server_proc.terminate()
        return False

    passed = True

    try:
        # 1. Test AI Health Route
        print("\n[Test 1] GET /api/v1/placement-agent/health...")
        r = requests.get(f"{base_url}/api/v1/placement-agent/health")
        print(f"Status Code: {r.status_code}")
        print(f"Response: {r.text}")
        if r.status_code == 200 and "status" in r.json().get("data", {}):
            print("[SUCCESS] GET /api/v1/placement-agent/health PASSED!")
        else:
            print("[FAILURE] GET /api/v1/placement-agent/health FAILED!")
            passed = False

        # 2. Test LangServe Input Schema Route
        print("\n[Test 2] GET /placement-agent/input_schema (LangServe)...")
        r = requests.get(f"{base_url}/placement-agent/input_schema")
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            print("[SUCCESS] GET /placement-agent/input_schema PASSED!")
        else:
            print("[FAILURE] GET /placement-agent/input_schema FAILED!")
            passed = False

        # 3. Test Custom Invoke Wrapper with General Conversational query
        print("\n[Test 3] POST /api/v1/placement-agent/invoke (General Intent)...")
        payload = {"message": "Hi, tell me how you can assist me.", "session_id": "test-session-123"}
        r = requests.post(f"{base_url}/api/v1/placement-agent/invoke", json=payload)
        print(f"Status Code: {r.status_code}")
        print(f"Response: {r.text}")
        if r.status_code == 200 and r.json().get("success"):
            print("[SUCCESS] General Invoke PASSED!")
        else:
            print("[FAILURE] General Invoke FAILED!")
            passed = False

        # 4. Test Custom Invoke Wrapper with Resume Analysis query
        print("\n[Test 4] POST /api/v1/placement-agent/invoke (Resume Specialized Intent)...")
        payload = {
            "message": "analyze this resume: Experienced Python and React Developer who built high-latency APIs.",
            "session_id": "test-session-123"
        }
        r = requests.post(f"{base_url}/api/v1/placement-agent/invoke", json=payload)
        print(f"Status Code: {r.status_code}")
        print(f"Response: {r.text}")
        if r.status_code == 200 and r.json().get("success") and "Resume Analysis Report" in r.json().get("data", {}).get("message", ""):
            print("[SUCCESS] Resume Analysis Intent Routing PASSED!")
        else:
            print("[FAILURE] Resume Analysis Intent Routing FAILED!")
            passed = False

        # 5. Test LangServe Native Invoke Route
        print("\n[Test 5] POST /placement-agent/invoke (LangServe Native API)...")
        langserve_payload = {
            "input": {
                "messages": [{"type": "human", "content": "Recommend companies for me."}]
            },
            "config": {
                "configurable": {
                    "thread_id": "langserve-test-session"
                }
            }
        }
        r = requests.post(f"{base_url}/placement-agent/invoke", json=langserve_payload)
        print(f"Status Code: {r.status_code}")
        response_json = r.json()
        data_field = response_json.get("data", response_json) # Fallback if not enveloped
        if r.status_code == 200 and "output" in data_field:
            print("[SUCCESS] LangServe Native Invoke PASSED!")
            print(f"Agent matched: {data_field['output'].get('selected_agent')}")
        else:
            print("[FAILURE] LangServe Native Invoke FAILED!")
            passed = False

    except Exception as e:
        print(f"[!] Test execution failed with exception: {e}")
        passed = False
    finally:
        print("\n[*] Terminating local test server...")
        try:
            server_proc.terminate()
            server_proc.wait(timeout=2.0)
        except Exception:
            pass
        print("[*] Test server stopped.")

    print("\n" + "=" * 60)
    if passed:
        print("ALL PLACEMENT AGENT INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    else:
        print("SOME INTEGRATION TESTS FAILED. CHECK LOGS ABOVE.")
    print("=" * 60)
    return passed

if __name__ == "__main__":
    success = test_endpoints()
    sys.exit(0 if success else 1)
