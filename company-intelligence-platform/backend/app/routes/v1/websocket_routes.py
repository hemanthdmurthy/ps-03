# app/routes/v1/websocket_routes.py
"""
WebSocket Route Handlers
========================
Production-grade WebSocket endpoints supporting multi-channel real-time communication.

Endpoints:
    - /ws/{user_id}                → Legacy single-connection endpoint (backward-compatible)
    - /ws/connect                  → Unified multi-channel endpoint with JWT auth via query param
    - /ws/dashboard/{user_id}      → Dashboard-specific real-time updates
    - /ws/activity/{user_id}       → Activity stream real-time feed
    - /ws/analytics/{user_id}      → Live analytics data stream

Client Protocol:
    After connection, clients communicate via JSON messages:

    Client → Server:
        {"event": "ping"}                          → Heartbeat keepalive
        {"event": "subscribe", "channel": "..."}   → Subscribe to a channel
        {"event": "unsubscribe", "channel": "..."} → Unsubscribe from a channel

    Server → Client:
        {"event": "connection_ack", "data": {...}}  → Connection confirmed
        {"event": "pong"}                           → Heartbeat response
        {"event": "new_notification", "data": {...}} → Notification payload
        {"event": "dashboard_stats_update", "data": {...}} → Dashboard update
        {"event": "error", "data": {"message": "..."}} → Error message
"""

import json
import logging
import time
from typing import Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.utils.websocket_manager import manager
from app.utils.jwt_helper import decode_token
from app.core.metrics import track_websocket_event

logger = logging.getLogger("company_intel.routes.websocket")

router = APIRouter(tags=["WebSocket Real-Time"])


# Valid channels that clients can subscribe to
VALID_CHANNELS = {
    "notifications",
    "dashboard_updates",
    "activity_stream",
    "analytics_live",
    "system_broadcast",
}


def _validate_ws_token(token: Optional[str]) -> Optional[dict]:
    """
    Validates a JWT token provided via WebSocket query parameter.
    Returns the decoded payload or None if invalid.

    WebSocket connections cannot use HTTP headers for auth in browsers,
    so the JWT is passed as a query parameter: ws://host/ws/connect?token=<jwt>
    """
    if not token:
        return None
    try:
        payload = decode_token(token, is_refresh=False)
        if payload.get("type") != "access":
            return None
        return payload
    except (JWTError, Exception):
        return None


async def _handle_client_messages(
    websocket: WebSocket,
    user_id: str,
    conn,
):
    """
    Core message loop that handles incoming WebSocket messages from the client.
    Supports heartbeat pings, channel subscription changes, and echo for debugging.
    """
    while True:
        try:
            raw = await websocket.receive_text()
        except WebSocketDisconnect:
            raise
        except Exception:
            raise WebSocketDisconnect(code=1006)

        # Parse the incoming message
        try:
            data = json.loads(raw) if raw.strip().startswith("{") else {"event": raw.strip()}
        except (json.JSONDecodeError, TypeError):
            data = {"event": raw.strip() if raw else "unknown"}

        event = data.get("event", "").lower()
        track_websocket_event(event, "inbound")

        # ── Heartbeat ──
        if event in ("ping", "heartbeat"):
            await manager.handle_heartbeat(user_id, websocket)
            await websocket.send_json({
                "event": "pong",
                "data": {"timestamp": time.time()},
            })
            track_websocket_event("pong", "outbound")
            continue

        # ── Channel Subscribe ──
        if event == "subscribe":
            channel = data.get("channel", "")
            if channel in VALID_CHANNELS:
                await manager.subscribe_to_channel(user_id, websocket, channel)
                await websocket.send_json({
                    "event": "subscribed",
                    "data": {"channel": channel},
                })
                track_websocket_event("subscribed", "outbound")
                logger.info(f"[WS] user='{user_id}' subscribed to channel '{channel}'")
            else:
                await websocket.send_json({
                    "event": "error",
                    "data": {"message": f"Invalid channel: '{channel}'", "valid_channels": list(VALID_CHANNELS)},
                })
                track_websocket_event("error", "outbound")
            continue

        # ── Channel Unsubscribe ──
        if event == "unsubscribe":
            channel = data.get("channel", "")
            if channel in VALID_CHANNELS:
                await manager.unsubscribe_from_channel(user_id, websocket, channel)
                await websocket.send_json({
                    "event": "unsubscribed",
                    "data": {"channel": channel},
                })
                track_websocket_event("unsubscribed", "outbound")
                logger.info(f"[WS] user='{user_id}' unsubscribed from channel '{channel}'")
            continue

        # ── Echo (debug/testing) ──
        if event == "echo":
            await websocket.send_json({
                "event": "echo",
                "data": data.get("data", raw),
            })
            track_websocket_event("echo", "outbound")
            continue

        # ── Unknown event ──
        await websocket.send_json({
            "event": "error",
            "data": {
                "message": f"Unknown event type: '{event}'",
                "supported_events": ["ping", "subscribe", "unsubscribe", "echo"],
            },
        })
        track_websocket_event("error", "outbound")


# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/connect")
async def websocket_unified_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    channels: Optional[str] = Query(None),
):
    """
    Primary unified WebSocket endpoint with JWT authentication.

    Query Parameters:
        token: JWT access token for authentication
        channels: Comma-separated channel names to subscribe to
                  (e.g., "notifications,dashboard_updates,analytics_live")

    Connection Flow:
        1. Client connects with token and desired channels
        2. Server validates JWT → extracts user_id and role
        3. Server sends connection_ack with session details
        4. Client sends periodic pings to maintain heartbeat
        5. Server pushes real-time events based on subscribed channels
    """
    # Validate JWT token
    payload = _validate_ws_token(token)
    if not payload:
        await websocket.accept()
        await websocket.send_json({
            "event": "error",
            "data": {"message": "Authentication failed. Provide a valid JWT token as 'token' query parameter."},
        })
        track_websocket_event("error", "outbound")
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user_id = payload.get("sub", "anonymous")
    user_role = payload.get("role", "viewer")

    # Parse requested channels
    requested_channels: Set[str] = {"notifications"}  # Always subscribe to notifications
    if channels:
        for ch in channels.split(","):
            ch = ch.strip()
            if ch in VALID_CHANNELS:
                requested_channels.add(ch)

    # Register connection
    conn = await manager.connect(
        user_id=user_id,
        websocket=websocket,
        channels=requested_channels,
        user_role=user_role,
        client_info=websocket.headers.get("user-agent"),
    )

    # Send connection acknowledgment
    await websocket.send_json({
        "event": "connection_ack",
        "data": {
            "user_id": user_id,
            "role": user_role,
            "subscribed_channels": list(requested_channels),
            "heartbeat_interval_seconds": 30,
            "server_time": time.time(),
        },
    })
    track_websocket_event("connection_ack", "outbound")


    try:
        await _handle_client_messages(websocket, user_id, conn)
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
        logger.info(f"[WS] Unified connection closed for user '{user_id}'")
    except Exception as e:
        await manager.disconnect(user_id, websocket)
        logger.error(f"[WS] Unexpected error for user '{user_id}': {e}", exc_info=True)


@router.websocket("/ws/{user_id}")
async def websocket_legacy_endpoint(websocket: WebSocket, user_id: str):
    """
    Legacy WebSocket endpoint (backward-compatible).
    Accepts a user_id path parameter directly without JWT validation.
    Subscribes to the 'notifications' channel by default.

    Kept for backward compatibility with existing frontend clients.
    New integrations should use /ws/connect with JWT authentication.
    """
    conn = await manager.connect(
        user_id=user_id,
        websocket=websocket,
        channels={"notifications"},
    )

    # Send connection acknowledgment
    await websocket.send_json({
        "event": "connection_ack",
        "data": {
            "user_id": user_id,
            "subscribed_channels": ["notifications"],
            "heartbeat_interval_seconds": 30,
            "server_time": time.time(),
            "legacy_mode": True,
        },
    })
    track_websocket_event("connection_ack", "outbound")


    try:
        await _handle_client_messages(websocket, user_id, conn)
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
        logger.info(f"[WS Legacy] Connection closed for user '{user_id}'")
    except Exception as e:
        await manager.disconnect(user_id, websocket)
        logger.error(f"[WS Legacy] Error for user '{user_id}': {e}", exc_info=True)


@router.websocket("/ws/dashboard/{user_id}")
async def websocket_dashboard_endpoint(websocket: WebSocket, user_id: str):
    """
    Dashboard-specific WebSocket endpoint providing real-time dashboard updates.
    Automatically subscribes to: notifications, dashboard_updates, analytics_live.
    """
    conn = await manager.connect(
        user_id=user_id,
        websocket=websocket,
        channels={"notifications", "dashboard_updates", "analytics_live"},
    )

    await websocket.send_json({
        "event": "connection_ack",
        "data": {
            "user_id": user_id,
            "subscribed_channels": ["notifications", "dashboard_updates", "analytics_live"],
            "heartbeat_interval_seconds": 30,
            "server_time": time.time(),
        },
    })
    track_websocket_event("connection_ack", "outbound")


    try:
        await _handle_client_messages(websocket, user_id, conn)
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
        logger.info(f"[WS Dashboard] Connection closed for user '{user_id}'")
    except Exception as e:
        await manager.disconnect(user_id, websocket)
        logger.error(f"[WS Dashboard] Error for user '{user_id}': {e}", exc_info=True)


@router.websocket("/ws/activity/{user_id}")
async def websocket_activity_endpoint(websocket: WebSocket, user_id: str):
    """
    Activity stream WebSocket endpoint providing real-time activity feed.
    Automatically subscribes to: notifications, activity_stream.
    """
    conn = await manager.connect(
        user_id=user_id,
        websocket=websocket,
        channels={"notifications", "activity_stream"},
    )

    await websocket.send_json({
        "event": "connection_ack",
        "data": {
            "user_id": user_id,
            "subscribed_channels": ["notifications", "activity_stream"],
            "heartbeat_interval_seconds": 30,
            "server_time": time.time(),
        },
    })
    track_websocket_event("connection_ack", "outbound")


    try:
        await _handle_client_messages(websocket, user_id, conn)
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
        logger.info(f"[WS Activity] Connection closed for user '{user_id}'")
    except Exception as e:
        await manager.disconnect(user_id, websocket)
        logger.error(f"[WS Activity] Error for user '{user_id}': {e}", exc_info=True)


@router.websocket("/ws/analytics/{user_id}")
async def websocket_analytics_endpoint(websocket: WebSocket, user_id: str):
    """
    Analytics-specific WebSocket endpoint providing real-time metric updates.
    Automatically subscribes to: analytics_live, dashboard_updates.
    """
    conn = await manager.connect(
        user_id=user_id,
        websocket=websocket,
        channels={"analytics_live", "dashboard_updates"},
    )

    await websocket.send_json({
        "event": "connection_ack",
        "data": {
            "user_id": user_id,
            "subscribed_channels": ["analytics_live", "dashboard_updates"],
            "heartbeat_interval_seconds": 30,
            "server_time": time.time(),
        },
    })
    track_websocket_event("connection_ack", "outbound")


    try:
        await _handle_client_messages(websocket, user_id, conn)
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
        logger.info(f"[WS Analytics] Connection closed for user '{user_id}'")
    except Exception as e:
        await manager.disconnect(user_id, websocket)
        logger.error(f"[WS Analytics] Error for user '{user_id}': {e}", exc_info=True)
