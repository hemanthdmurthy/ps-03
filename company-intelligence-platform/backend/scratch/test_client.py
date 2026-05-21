import sys
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.INFO)

# Force stdout to use UTF-8 on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from app.core.config import settings
settings.ENVIRONMENT = "testing"

from fastapi.testclient import TestClient
from app.main import app

print("Initializing TestClient...")
client = TestClient(app)

print("\n--- TEST /placement-agent/config_schema ---")
try:
    response = client.get("/placement-agent/config_schema")
    print("Config Schema Status:", response.status_code)
    print("Config Schema Body:", response.json())
except Exception as e:
    print("Config Schema failed:", e)

print("\n--- TEST /placement-agent/invoke with configurable thread_id ---")
try:
    payload = {
        "input": {
            "messages": [
                {
                    "type": "human",
                    "content": "Hello, my name is John and I want to prep for software engineer interviews"
                }
            ]
        },
        "config": {
            "configurable": {
                "thread_id": "john-session-123"
            }
        }
    }
    response = client.post("/placement-agent/invoke", json=payload)
    print("Invoke Status:", response.status_code)
    if response.status_code == 200:
        print("Invoke Body:", response.json())
    else:
        print("Invoke Body (Error):", response.text)
except Exception as e:
    print("Invoke failed:", e)

print("\n--- TEST /placement-agent/invoke SECOND call (verifying context memory) ---")
try:
    payload = {
        "input": {
            "messages": [
                {
                    "type": "human",
                    "content": "What is my name?"
                }
            ]
        },
        "config": {
            "configurable": {
                "thread_id": "john-session-123"
            }
        }
    }
    response = client.post("/placement-agent/invoke", json=payload)
    print("Second Invoke Status:", response.status_code)
    if response.status_code == 200:
        print("Second Invoke Body:", response.json())
    else:
        print("Second Invoke Body (Error):", response.text)
except Exception as e:
    print("Second Invoke failed:", e)
