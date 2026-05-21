# app/services/websocket_event_handlers.py
"""
WebSocket Event Handlers — Redis Pub/Sub ↔ WebSocket Bridge
============================================================
Defines callback handlers that receive Redis Pub/Sub messages and route
them to the appropriate local WebSocket connections via the ConnectionManager.

This module is the critical bridge between the cross-instance Redis event bus
and the per-instance local WebSocket connection pool.

Architecture:
    Redis Pub/Sub Channel → Callback Handler → ConnectionManager → WebSocket Clients

Each handler:
    1. Deserializes the incoming Redis message payload
    2. Determines the target audience (per-user, per-channel, or broadcast)
    3. Constructs the frontend-compatible WebSocket event envelope
    4. Dispatches via the ConnectionManager
"""

import logging
import time
from typing import Dict, Any, Optional

from app.utils.websocket_manager import manager
from app.core.redis_pubsub import EventChannel, EventType

logger = logging.getLogger("company_intel.services.ws_event_handlers")


def _build_ws_event(event: str, data: Any = None, channel: Optional[str] = None) -> dict:
    """
    Constructs a standardized WebSocket event envelope for frontend consumption.

    Frontend Event Schema:
        {
            "event": "event_type_name",
            "data": { ... payload ... },
            "channel": "source_channel_name",
            "timestamp": 1716000000.123
        }
    """
    envelope = {
        "event": event,
        "data": data,
        "timestamp": time.time(),
    }
    if channel:
        envelope["channel"] = channel
    return envelope


# ═══════════════════════════════════════════════════════════════════════════
# CHANNEL-SPECIFIC EVENT HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

async def handle_notification_event(payload: Dict[str, Any]):
    """
    Handler for the 'company_intel:notifications' Redis channel.
    Routes notification events to specific users' WebSocket connections.

    Expected payload:
        {
            "event": "new_notification",
            "user_id": "target-user-id",
            "data": { notification details... },
            "timestamp": ...,
            "source_instance": ...
        }
    """
    event = payload.get("event", EventType.NEW_NOTIFICATION.value)
    user_id = payload.get("user_id")
    data = payload.get("data")

    if not data:
        logger.warning("[WS Handler] Notification event received with no data payload.")
        return

    ws_event = _build_ws_event(event=event, data=data, channel="notifications")

    if user_id:
        # Per-user delivery
        await manager.send_personal_message(ws_event, user_id)
        logger.info(
            f"[WS Handler] Delivered notification '{event}' to user '{user_id}'"
        )
    else:
        # Broadcast to all notification subscribers
        await manager.send_to_channel("notifications", ws_event)
        logger.info(f"[WS Handler] Broadcast notification '{event}' to all subscribers")


async def handle_dashboard_update_event(payload: Dict[str, Any]):
    """
    Handler for the 'company_intel:dashboard_updates' Redis channel.
    Broadcasts dashboard metric updates to all dashboard subscribers.

    Expected payload:
        {
            "event": "dashboard_stats_update" | "placement_status_change" | ...,
            "data": { updated stats or status info... },
            "user_id": optional (for targeted updates),
            "timestamp": ...
        }
    """
    event = payload.get("event", EventType.DASHBOARD_STATS_UPDATE.value)
    user_id = payload.get("user_id")
    data = payload.get("data")

    if not data:
        return

    ws_event = _build_ws_event(event=event, data=data, channel="dashboard_updates")

    if user_id:
        await manager.send_personal_message(ws_event, user_id)
    else:
        await manager.send_to_channel("dashboard_updates", ws_event)

    logger.debug(f"[WS Handler] Dashboard update '{event}' dispatched.")


async def handle_activity_stream_event(payload: Dict[str, Any]):
    """
    Handler for the 'company_intel:activity_stream' Redis channel.
    Broadcasts real-time activity events (research sessions, user actions, workflow progress).

    Expected payload:
        {
            "event": "research_started" | "research_completed" | "user_action" | ...,
            "data": { activity details... },
            "user_id": optional (exclude self from broadcast),
            "timestamp": ...
        }
    """
    event = payload.get("event", EventType.USER_ACTION.value)
    user_id = payload.get("user_id")
    data = payload.get("data")

    if not data:
        return

    ws_event = _build_ws_event(event=event, data=data, channel="activity_stream")

    # Activity stream broadcasts to all subscribers, optionally excluding originator
    await manager.send_to_channel("activity_stream", ws_event, exclude_user=user_id)
    logger.debug(f"[WS Handler] Activity stream event '{event}' dispatched.")


async def handle_analytics_live_event(payload: Dict[str, Any]):
    """
    Handler for the 'company_intel:analytics_live' Redis channel.
    Pushes real-time analytics data points to analytics subscribers.

    Expected payload:
        {
            "event": "analytics_counter_update" | "realtime_metric" | ...,
            "data": { metric name, value, chart data... },
            "user_id": optional,
            "timestamp": ...
        }
    """
    event = payload.get("event", EventType.REALTIME_METRIC.value)
    user_id = payload.get("user_id")
    data = payload.get("data")

    if not data:
        return

    ws_event = _build_ws_event(event=event, data=data, channel="analytics_live")

    if user_id:
        await manager.send_personal_message(ws_event, user_id)
    else:
        await manager.send_to_channel("analytics_live", ws_event)

    logger.debug(f"[WS Handler] Analytics live event '{event}' dispatched.")


async def handle_system_broadcast_event(payload: Dict[str, Any]):
    """
    Handler for the 'company_intel:system_broadcast' Redis channel.
    Broadcasts system-wide announcements to ALL connected clients regardless of channel.

    Expected payload:
        {
            "event": "system_announcement" | "maintenance_scheduled" | ...,
            "data": { announcement text, severity, scheduled_at... },
            "timestamp": ...
        }
    """
    event = payload.get("event", EventType.SYSTEM_ANNOUNCEMENT.value)
    data = payload.get("data")

    if not data:
        return

    ws_event = _build_ws_event(event=event, data=data, channel="system_broadcast")

    # System broadcasts go to ALL connected clients
    await manager.broadcast(ws_event)
    logger.info(f"[WS Handler] System broadcast '{event}' sent to all connected clients.")


# ═══════════════════════════════════════════════════════════════════════════
# REGISTRATION HELPER
# ═══════════════════════════════════════════════════════════════════════════

# Maps Redis channel names to their handler functions
CHANNEL_HANDLER_MAP = {
    EventChannel.NOTIFICATIONS.value: handle_notification_event,
    EventChannel.DASHBOARD_UPDATES.value: handle_dashboard_update_event,
    EventChannel.ACTIVITY_STREAM.value: handle_activity_stream_event,
    EventChannel.ANALYTICS_LIVE.value: handle_analytics_live_event,
    EventChannel.SYSTEM_BROADCAST.value: handle_system_broadcast_event,
}


async def register_all_handlers(pubsub_mgr):
    """
    Subscribes all event handlers to their respective Redis Pub/Sub channels.
    Called during application startup after Redis initialization.
    """
    for channel, handler in CHANNEL_HANDLER_MAP.items():
        await pubsub_mgr.subscribe(channel, handler)
        logger.info(f"[WS Handler] Registered handler for channel: '{channel}'")

    logger.info(
        f"[WS Handler] All {len(CHANNEL_HANDLER_MAP)} channel handlers registered successfully."
    )
