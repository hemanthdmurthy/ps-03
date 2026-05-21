# app/core/redis_pubsub.py
"""
Redis Pub/Sub Event Bus — Scalable Cross-Instance WebSocket Event Broadcasting
===============================================================================
Provides a centralized, production-grade Redis Pub/Sub layer enabling real-time
event propagation across multiple FastAPI backend instances.

Architecture:
    Celery Worker / API Endpoint
            │ (publish)
            ▼
    ┌──────────────────────────┐
    │   Redis Pub/Sub Channels │
    │  ┌────────────────────┐  │
    │  │  notifications     │  │
    │  │  dashboard_updates │  │
    │  │  activity_stream   │  │
    │  │  analytics_live    │  │
    │  │  system_broadcast  │  │
    │  └────────────────────┘  │
    └──────────────────────────┘
            │ (subscribe)
            ▼
    FastAPI Instance N (ConnectionManager → WebSocket clients)

Channels:
    - company_intel:notifications     → Per-user live notifications (alerts, system events)
    - company_intel:dashboard_updates → Dashboard metric refreshes (global broadcast)
    - company_intel:activity_stream   → Real-time activity feed (research events, user actions)
    - company_intel:analytics_live    → Live analytics data points (counters, graphs)
    - company_intel:system_broadcast  → System-wide announcements (maintenance, releases)
"""

import json
import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable, Awaitable, Set
from enum import Enum

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.redis_client import redis_client

logger = logging.getLogger("company_intel.core.redis_pubsub")


class EventChannel(str, Enum):
    """Enumeration of all Redis Pub/Sub channels used for WebSocket event routing."""
    NOTIFICATIONS = "company_intel:notifications"
    DASHBOARD_UPDATES = "company_intel:dashboard_updates"
    ACTIVITY_STREAM = "company_intel:activity_stream"
    ANALYTICS_LIVE = "company_intel:analytics_live"
    SYSTEM_BROADCAST = "company_intel:system_broadcast"


class EventType(str, Enum):
    """Standardized WebSocket event types for frontend consumption."""
    # Notification events
    NEW_NOTIFICATION = "new_notification"
    NOTIFICATION_READ = "notification_read"
    NOTIFICATION_CLEARED = "notification_cleared"

    # Dashboard events
    DASHBOARD_STATS_UPDATE = "dashboard_stats_update"
    PLACEMENT_STATUS_CHANGE = "placement_status_change"
    COMPANY_ENRICHMENT_COMPLETE = "company_enrichment_complete"

    # Activity stream events
    RESEARCH_STARTED = "research_started"
    RESEARCH_COMPLETED = "research_completed"
    USER_ACTION = "user_action"
    WORKFLOW_PROGRESS = "workflow_progress"

    # Analytics events
    ANALYTICS_COUNTER_UPDATE = "analytics_counter_update"
    ANALYTICS_CHART_UPDATE = "analytics_chart_update"
    REALTIME_METRIC = "realtime_metric"

    # System events
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    MAINTENANCE_SCHEDULED = "maintenance_scheduled"
    SERVER_STATUS = "server_status"

    # Connection lifecycle
    CONNECTION_ACK = "connection_ack"
    HEARTBEAT = "heartbeat"
    PONG = "pong"
    ERROR = "error"


class RedisPubSubManager:
    """
    Production-grade Redis Pub/Sub manager for scalable WebSocket event distribution.

    Features:
        - Multi-channel subscription management
        - Automatic reconnection with exponential backoff
        - Event serialization/deserialization with validation
        - Per-channel callback routing
        - Health monitoring and connection metrics
        - Graceful shutdown with cleanup guarantees
    """

    def __init__(self):
        self._publisher: Optional[aioredis.Redis] = None
        self._subscriber: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        self._subscribed_channels: Set[str] = set()
        self._is_running = False
        self._is_healthy = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._base_reconnect_delay = 1.0
        self._messages_published = 0
        self._messages_received = 0
        self._last_heartbeat: Optional[float] = None
        self._instance_id = f"instance_{id(self)}_{int(time.time())}"

    @property
    def is_healthy(self) -> bool:
        return self._is_healthy and self._is_running

    @property
    def stats(self) -> Dict[str, Any]:
        """Returns operational metrics for monitoring endpoints."""
        return {
            "instance_id": self._instance_id,
            "is_healthy": self._is_healthy,
            "is_running": self._is_running,
            "subscribed_channels": list(self._subscribed_channels),
            "messages_published": self._messages_published,
            "messages_received": self._messages_received,
            "reconnect_attempts": self._reconnect_attempts,
            "last_heartbeat": self._last_heartbeat,
        }

    async def initialize(self) -> bool:
        """
        Initializes Redis publisher and subscriber connections.
        Returns True if Redis is available, False if fallback mode is needed.
        """
        try:
            # Initialize resilient client first to run DNS and OS routing checks
            await redis_client.initialize()

            if redis_client.is_fallback:
                # Sharing the in-memory FakeRedis instance if in fallback
                self._publisher = redis_client.client
                self._subscriber = redis_client.client
            else:
                # Separate connections for publisher and subscriber (Redis best practice)
                self._publisher = aioredis.Redis.from_url(
                    redis_client._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=3.0,
                    socket_timeout=3.0,
                    retry_on_timeout=True,
                )
                self._subscriber = aioredis.Redis.from_url(
                    redis_client._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=3.0,
                    socket_timeout=3.0,
                    retry_on_timeout=True,
                )

            # Verify connectivity
            await self._publisher.ping()
            await self._subscriber.ping()

            self._pubsub = self._subscriber.pubsub()
            self._is_healthy = True
            self._reconnect_attempts = 0

            logger.info(
                f"[Redis PubSub] Initialized successfully. "
                f"Instance: {self._instance_id}, Redis: {redis_client._redis_url}"
            )
            return True

        except Exception as e:
            logger.warning(
                f"[Redis PubSub] Failed to connect to Redis: {e}. "
                f"WebSocket events will be local-only (single-instance mode)."
            )
            self._is_healthy = False
            return False

    async def subscribe(
        self,
        channel: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]],
    ):
        """
        Subscribes to a Redis Pub/Sub channel with a callback handler.
        The callback receives deserialized JSON event payloads.
        """
        if not self._is_healthy or not self._pubsub:
            logger.warning(f"[Redis PubSub] Cannot subscribe to '{channel}' — Redis unavailable.")
            return

        self._callbacks[channel] = callback
        await self._pubsub.subscribe(channel)
        self._subscribed_channels.add(channel)
        logger.info(f"[Redis PubSub] Subscribed to channel: '{channel}'")

    async def unsubscribe(self, channel: str):
        """Unsubscribes from a specific Redis channel."""
        if self._pubsub and channel in self._subscribed_channels:
            await self._pubsub.unsubscribe(channel)
            self._subscribed_channels.discard(channel)
            self._callbacks.pop(channel, None)
            logger.info(f"[Redis PubSub] Unsubscribed from channel: '{channel}'")

    async def publish(self, channel: str, event: str, data: Any = None, user_id: Optional[str] = None) -> bool:
        """
        Publishes an event payload to a Redis Pub/Sub channel.

        Args:
            channel: Target Redis channel name.
            event: Event type identifier (use EventType enum values).
            data: Arbitrary JSON-serializable event data.
            user_id: Optional target user ID for per-user routing.

        Returns:
            True if published successfully, False if Redis is unavailable.
        """
        if not self._is_healthy or not self._publisher:
            logger.debug(f"[Redis PubSub] Publish skipped — Redis unavailable. Channel: {channel}")
            return False

        payload = {
            "event": event,
            "data": data,
            "user_id": user_id,
            "timestamp": time.time(),
            "source_instance": self._instance_id,
        }

        try:
            serialized = json.dumps(payload, default=str)
            receivers = await self._publisher.publish(channel, serialized)
            self._messages_published += 1

            logger.debug(
                f"[Redis PubSub] Published to '{channel}': event='{event}', "
                f"receivers={receivers}, user_id={user_id}"
            )
            return True

        except Exception as e:
            logger.error(f"[Redis PubSub] Publish failed on '{channel}': {e}", exc_info=True)
            return False

    async def start_listener(self):
        """
        Starts the background asyncio task that continuously listens for messages
        on all subscribed Redis Pub/Sub channels and dispatches to registered callbacks.
        Includes automatic reconnection with exponential backoff.
        """
        if self._is_running:
            logger.warning("[Redis PubSub] Listener already running.")
            return

        if not self._is_healthy:
            logger.warning("[Redis PubSub] Cannot start listener — Redis unavailable.")
            return

        self._is_running = True
        self._listener_task = asyncio.create_task(self._listener_loop())
        logger.info("[Redis PubSub] Background listener task started.")

    async def _listener_loop(self):
        """
        Core listener loop reading from Redis Pub/Sub with resilient error handling.
        Processes messages via registered callbacks and supports graceful shutdown.
        """
        while self._is_running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message and message.get("type") == "message":
                    channel = message.get("channel", "")
                    raw_data = message.get("data", "")

                    try:
                        payload = json.loads(raw_data)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"[Redis PubSub] Malformed message on '{channel}': {raw_data[:200]}")
                        continue

                    self._messages_received += 1
                    self._last_heartbeat = time.time()

                    # Dispatch to registered callback for this channel
                    callback = self._callbacks.get(channel)
                    if callback:
                        try:
                            await callback(payload)
                        except Exception as cb_err:
                            logger.error(
                                f"[Redis PubSub] Callback error on '{channel}': {cb_err}",
                                exc_info=True,
                            )

                # Small yield to prevent busy-looping
                await asyncio.sleep(0.05)

            except asyncio.CancelledError:
                logger.info("[Redis PubSub] Listener task cancelled.")
                break

            except Exception as loop_err:
                logger.error(f"[Redis PubSub] Listener loop error: {loop_err}", exc_info=True)
                self._is_healthy = False

                # Attempt reconnection with exponential backoff
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    delay = min(
                        self._base_reconnect_delay * (2 ** self._reconnect_attempts),
                        60.0,
                    )
                    self._reconnect_attempts += 1
                    logger.info(
                        f"[Redis PubSub] Reconnection attempt {self._reconnect_attempts}/"
                        f"{self._max_reconnect_attempts} in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)

                    # Try to re-establish connection
                    try:
                        success = await self.initialize()
                        if success:
                            # Re-subscribe to all channels
                            for channel, callback in list(self._callbacks.items()):
                                await self._pubsub.subscribe(channel)
                            self._is_healthy = True
                            logger.info("[Redis PubSub] Reconnected successfully.")
                    except Exception as reconn_err:
                        logger.error(f"[Redis PubSub] Reconnection failed: {reconn_err}")
                else:
                    logger.error(
                        "[Redis PubSub] Max reconnection attempts exceeded. "
                        "Falling back to local-only WebSocket mode."
                    )
                    break

        self._is_running = False
        logger.info("[Redis PubSub] Listener loop exited.")

    async def shutdown(self):
        """Gracefully shuts down all Redis connections and the listener task."""
        logger.info("[Redis PubSub] Initiating graceful shutdown...")
        self._is_running = False

        # Cancel the listener task
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        # Unsubscribe and close pubsub
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()
            except Exception:
                pass

        # Close Redis connections
        for client in [self._publisher, self._subscriber]:
            if client:
                try:
                    await client.close()
                except Exception:
                    pass

        self._is_healthy = False
        self._subscribed_channels.clear()
        logger.info("[Redis PubSub] Shutdown complete.")


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL SINGLETON & CONVENIENCE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

pubsub_manager = RedisPubSubManager()


async def publish_event(
    channel: EventChannel,
    event: EventType,
    data: Any = None,
    user_id: Optional[str] = None,
) -> bool:
    """
    Convenience function for publishing events from anywhere in the application.

    Usage:
        from app.core.redis_pubsub import publish_event, EventChannel, EventType

        await publish_event(
            EventChannel.NOTIFICATIONS,
            EventType.NEW_NOTIFICATION,
            data={"title": "Hello", "message": "World"},
            user_id="user-123"
        )
    """
    return await pubsub_manager.publish(
        channel=channel.value,
        event=event.value,
        data=data,
        user_id=user_id,
    )


def publish_event_sync(
    channel: EventChannel,
    event: EventType,
    data: Any = None,
    user_id: Optional[str] = None,
) -> bool:
    """
    Synchronous publish helper for use in Celery tasks or synchronous contexts.
    Creates a short-lived Redis connection to publish the event.

    Usage (inside Celery task):
        from app.core.redis_pubsub import publish_event_sync, EventChannel, EventType

        publish_event_sync(
            EventChannel.DASHBOARD_UPDATES,
            EventType.DASHBOARD_STATS_UPDATE,
            data={"total_students": 1500}
        )
    """
    payload = {
        "event": event.value,
        "data": data,
        "user_id": user_id,
        "timestamp": time.time(),
        "source_instance": "celery_worker",
    }

    try:
        # Reuse the resilient, thread-safe sync connection pool
        client = redis_client.sync_client
        serialized = json.dumps(payload, default=str)
        client.publish(channel.value, serialized)
        return True
    except Exception as e:
        logger.error(f"[Redis PubSub Sync] Publish failed: {e}", exc_info=True)
        return False
