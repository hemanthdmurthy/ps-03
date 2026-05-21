# scratch/test_websocket_architecture.py
"""
WebSocket Architecture Validation Suite
========================================
Comprehensive automated test suite to verify the new scalable Redis Pub/Sub
WebSocket architecture, including unified query JWT auth, purpose-specific
endpoints, ping-pong heartbeat, multi-channel subscriptions, and metrics.
"""

import sys
import os
import json
import time

# Inject backend path for local imports
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from app.main import app
from app.core.metrics import WEBSOCKET_CONNECTIONS_ACTIVE, WEBSOCKET_EVENTS_TOTAL

def run_ws_suite():
    print("======================================================================")
    print("      RUNNING SCALABLE REDIS WEBSOCKET ARCHITECTURE VALIDATION        ")
    print("======================================================================")

    # Initialize TestClient using context manager to trigger lifecycle startup/shutdown events
    with TestClient(app) as client:
        print("[+] TestClient successfully initialized with lifecycle events.")

        # -------------------------------------------------------------
        # 1. AUTHENTICATE AND OBTAIN TOKENS
        # -------------------------------------------------------------
        print("\n[1] Authenticating 'admin' user to fetch valid JWT access token...")
        login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
        login_json = login_resp.json()
        assert login_json["success"] is True, "Response structure wrapping missing/incorrect!"
        
        auth_data = login_json["data"]
        access_token = auth_data["access_token"]
        user_id = auth_data["username"]
        role = auth_data["role"]
        print(f"    -> Token acquired for user='{user_id}' (role='{role}').")

        # -------------------------------------------------------------
        # 2. TEST UNIFIED WEBSOCKET CONNECTION WITH VALID JWT
        # -------------------------------------------------------------
        print("\n[2] Connecting to unified endpoint (/ws/connect) with JWT token...")
        ws_url = f"/ws/connect?token={access_token}&channels=dashboard_updates,analytics_live"
        
        with client.websocket_connect(ws_url) as ws:
            print("    [+] WebSocket connection established successfully!")
            
            # Receive connection acknowledgment envelope
            ack = ws.receive_json()
            print("    [+] Received connection acknowledgment from server:")
            print(f"        {json.dumps(ack, indent=8)}")
            
            assert ack["event"] == "connection_ack"
            assert ack["data"]["user_id"] == "admin"
            assert "dashboard_updates" in ack["data"]["subscribed_channels"]
            assert "analytics_live" in ack["data"]["subscribed_channels"]
            assert "notifications" in ack["data"]["subscribed_channels"] # always subscribed to notifications

            # -------------------------------------------------------------
            # 3. TEST HEARTBEAT PING-PONG PROTOCOL
            # -------------------------------------------------------------
            print("\n[3] Testing heartbeat keepalive ping-pong protocol...")
            ws.send_json({"event": "ping"})
            pong = ws.receive_json()
            print("    [+] Ping sent, received pong response:")
            print(f"        {json.dumps(pong, indent=8)}")
            assert pong["event"] == "pong"
            assert "timestamp" in pong["data"]

            # -------------------------------------------------------------
            # 4. TEST CHANNEL SUBSCRIPTION CHANGES (ON-THE-FLY)
            # -------------------------------------------------------------
            print("\n[4] Testing dynamic on-the-fly channel subscriptions...")
            # Subscribe to activity_stream
            ws.send_json({"event": "subscribe", "channel": "activity_stream"})
            sub_res = ws.receive_json()
            print(f"    [+] Subscribe request response: {json.dumps(sub_res)}")
            assert sub_res["event"] == "subscribed"
            assert sub_res["data"]["channel"] == "activity_stream"

            # Try invalid channel subscription
            ws.send_json({"event": "subscribe", "channel": "invalid_channel_name"})
            err_res = ws.receive_json()
            print(f"    [+] Invalid channel response: {json.dumps(err_res)}")
            assert err_res["event"] == "error"
            assert "Invalid channel" in err_res["data"]["message"]

            # -------------------------------------------------------------
            # 5. TEST ECHO/DEBUG EVENT
            # -------------------------------------------------------------
            print("\n[5] Testing custom echo event...")
            ws.send_json({"event": "echo", "data": {"message": "Verification text"}})
            echo_res = ws.receive_json()
            print(f"    [+] Echo response: {json.dumps(echo_res)}")
            assert echo_res["event"] == "echo"
            assert echo_res["data"]["message"] == "Verification text"

        # -------------------------------------------------------------
        # 6. TEST PURPOSE-SPECIFIC ENDPOINTS
        # -------------------------------------------------------------
        print("\n[6] Testing purpose-specific endpoints...")
        
        # Test dashboard endpoint
        print("    -> Connecting to /ws/dashboard/{user_id}...")
        with client.websocket_connect(f"/ws/dashboard/{user_id}") as ws_dash:
            ack_dash = ws_dash.receive_json()
            print(f"       Dashboard Ack: {json.dumps(ack_dash)}")
            assert ack_dash["event"] == "connection_ack"
            assert "dashboard_updates" in ack_dash["data"]["subscribed_channels"]
            assert "analytics_live" in ack_dash["data"]["subscribed_channels"]
            
        # Test analytics endpoint
        print("    -> Connecting to /ws/analytics/{user_id}...")
        with client.websocket_connect(f"/ws/analytics/{user_id}") as ws_ana:
            ack_ana = ws_ana.receive_json()
            print(f"       Analytics Ack: {json.dumps(ack_ana)}")
            assert ack_ana["event"] == "connection_ack"
            assert "analytics_live" in ack_ana["data"]["subscribed_channels"]
            assert "dashboard_updates" in ack_ana["data"]["subscribed_channels"]

        # -------------------------------------------------------------
        # 7. METRICS INSTRUMENTATION CHECKS
        # -------------------------------------------------------------
        print("\n[7] Verifying Prometheus Metrics integration...")
        # Since we ran active connections and closed them, check metrics registers
        print(f"    Active connections count: {WEBSOCKET_CONNECTIONS_ACTIVE._value.get()}")
        # Check total events registered
        inbound_count = sum(child._value.get() for labels, child in WEBSOCKET_EVENTS_TOTAL._metrics.items() if labels[1] == "inbound")
        outbound_count = sum(child._value.get() for labels, child in WEBSOCKET_EVENTS_TOTAL._metrics.items() if labels[1] == "outbound")
        print(f"    Total WebSocket events captured - Inbound: {inbound_count}, Outbound: {outbound_count}")
        assert inbound_count > 0, "No inbound WebSocket events tracked!"
        assert outbound_count > 0, "No outbound WebSocket events tracked!"
        print("    [+] Prometheus Metrics instrumentation successfully validated!")


    print("\n======================================================================")
    print("      ALL SCALABLE WEBSOCKET ARCHITECTURE TESTS PASSED! [OK]         ")
    print("======================================================================")

if __name__ == "__main__":
    run_ws_suite()
