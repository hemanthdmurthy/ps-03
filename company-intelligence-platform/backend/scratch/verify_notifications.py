import sys
import os
import uuid
import json

# Inject backend path for local imports
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.db_deps import get_db
from app.models.notification import Notification

def run_suite():
    print("==========================================================")
    print("  RUNNING FASTAPI REAL-TIME WEBSOCKETS & NOTIFICATIONS   ")
    print("==========================================================")

    # Initialize TestClient using context manager
    with TestClient(app) as client:
        print("[1] TestClient successfully initialized.")

        # -------------------------------------------------------------
        # 1. AUTHENTICATE AND OBTAIN TOKENS
        # -------------------------------------------------------------
        print("\n[2] Logging in seeded account to obtain authorization token...")
        
        # Admin Login
        admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert admin_login.status_code == 200, "Admin login failed!"
        admin_data = admin_login.json()
        admin_token = admin_data["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Query current user profile to obtain User ID
        me_resp = client.get("/api/auth/me", headers=admin_headers)
        assert me_resp.status_code == 200, "Get profile /me failed!"
        admin_id = me_resp.json()["id"]
        print(f"[+] Admin authenticated. User ID: {admin_id}")

        # -------------------------------------------------------------
        # 2. ESTABLISH WEBSOCKET CONNECTION & VERIFY PING HEARTBEAT
        # -------------------------------------------------------------
        print("\n[3] Connecting to live WebSocket channel (/api/notifications/ws/{user_id})...")
        
        # Connect to WebSocket
        with client.websocket_connect(f"/api/notifications/ws/{admin_id}") as websocket:
            print("[+] WebSocket connection established successfully!")

            # Test Ping-Pong Heartbeat
            print("\n[4] Testing WebSocket Ping-Pong Heartbeat...")
            websocket.send_text("ping")
            response = websocket.receive_json()
            assert response["event"] == "pong"
            assert response["data"] == "heartbeat acknowledged"
            print("[+] Ping Heartbeat acknowledged in real-time.")

            # ---------------------------------------------------------
            # 3. TRIGGER REAL-TIME NOTIFICATION PUSH
            # ---------------------------------------------------------
            print("\n[5] Triggering real-time test notification push via REST endpoint...")
            trigger_resp = client.post("/api/notifications/trigger-test", headers=admin_headers)
            assert trigger_resp.status_code == 200, f"Trigger failed: {trigger_resp.text}"
            triggered = trigger_resp.json()
            notification_id = triggered["id"]
            print(f"[+] Persistent notification generated (ID: {notification_id})")

            # Receive push alert on active WebSocket
            print("\n[6] Listening for instant push alert on active WebSocket...")
            push_alert = websocket.receive_json()
            assert push_alert["event"] == "new_notification"
            assert push_alert["data"]["id"] == notification_id
            assert push_alert["data"]["title"] == "Test Real-Time Notification"
            assert push_alert["data"]["type"] == "system"
            assert push_alert["data"]["is_read"] is False
            print("[+] [REAL-TIME DELIVERY PASSED] Instant WebSocket alert successfully received!")
            print(f"    Message: '{push_alert['data']['message']}'")

        # -------------------------------------------------------------
        # 4. VERIFY DATABASE PERSISTENCE & REST ENDPOINTS
        # -------------------------------------------------------------
        print("\n[7] Querying user notifications list (/api/notifications)...")
        list_resp = client.get("/api/notifications", headers=admin_headers)
        assert list_resp.status_code == 200, f"List failed: {list_resp.text}"
        notifications = list_resp.json()
        assert len(notifications) >= 1
        # Match the generated notification
        matched = [n for n in notifications if n["id"] == notification_id]
        assert len(matched) == 1
        assert matched[0]["is_read"] is False
        print("[+] Persistence verified. Notification retrieved successfully via REST.")

        print("\n[8] Marking notification as READ (/api/notifications/{id})...")
        read_resp = client.put(f"/api/notifications/{notification_id}", headers=admin_headers, json={"is_read": True})
        assert read_resp.status_code == 200, f"Mark read failed: {read_resp.text}"
        assert read_resp.json()["is_read"] is True
        print("[+] Notification successfully marked as READ.")

        print("\n[9] Testing bulk mark all as read (/api/notifications/mark-all-read)...")
        bulk_resp = client.post("/api/notifications/mark-all-read", headers=admin_headers)
        assert bulk_resp.status_code == 200, f"Bulk read failed: {bulk_resp.text}"
        print(f"[+] Bulk result: {bulk_resp.json()['message']}")

        # -------------------------------------------------------------
        # 5. TEARDOWN NOTIFICATIONS TEST RECORDS
        # -------------------------------------------------------------
        print("\n[10] Tearing down notifications test records...")
        db = next(get_db())
        try:
            db.query(Notification).filter(Notification.user_id == admin_id).delete()
            db.commit()
            print("[+] Database test notification records cleanly purged.")
        except Exception as e:
            db.rollback()
            print(f"[-] Database teardown failure: {e}")
            raise e

    print("\n==========================================================")
    print("  ALL REAL-TIME & NOTIFICATION TESTS PASSED! [OK]         ")
    print("==========================================================")

if __name__ == "__main__":
    run_suite()
