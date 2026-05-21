# app/utils/websocket_manager.py
"""
Production-Grade WebSocket Connection Manager
==============================================
Scalable, multi-channel WebSocket connection management with:
  - Per-user multi-device connection tracking
  - Channel-based subscription groups (notifications, dashboard, analytics, activity)
  - Heartbeat TTL enforcement with automatic stale connection pruning
  - Prometheus metrics integration
  - Thread-safe operations using asyncio locks
  - Memory-leak prevention through periodic cleanup sweeps

Connection Lifecycle:
    1. Client connects via WebSocket → JWT validated → register(user_id, ws, channels)
    2. Heartbeat interval keeps connection alive (client sends ping every 30s)
    3. If no heartbeat received within TTL (90s), connection is marked stale and pruned
    4. On graceful disconnect → unregister(user_id, ws)
    5. On crash → next heartbeat sweep auto-prunes the dead connection
"""

import logging
import time
import asyncio
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("company_intel.utils.websocket_manager")

# ═══════════════════════════════════════════════════════════════════════════
# CONNECTION METADATA
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class WebSocketConnection:
    """
    Tracks metadata for a single WebSocket connection, including the channels
    it is subscribed to and its last heartbeat timestamp for TTL enforcement.
    """
    websocket: WebSocket
    user_id: str
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    subscribed_channels: Set[str] = field(default_factory=lambda: {"notifications"})
    user_role: Optional[str] = None
    client_info: Optional[str] = None

    def is_stale(self, ttl_seconds: float = 90.0) -> bool:
        """Returns True if the connection has not sent a heartbeat within the TTL window."""
        return (time.time() - self.last_heartbeat) > ttl_seconds

    def touch(self):
        """Updates the last heartbeat timestamp."""
        self.last_heartbeat = time.time()


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTION MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """
    Enterprise WebSocket Connection Manager with channel-based routing,
    heartbeat enforcement, and Prometheus metrics tracking.

    Supports horizontal scaling: Each FastAPI instance manages its own set
    of local WebSocket connections. Redis Pub/Sub bridges events across instances.
    """

    # Heartbeat TTL: If no ping within this window, the connection is pruned
    HEARTBEAT_TTL_SECONDS = 90.0
    # How often the background sweep runs to prune stale connections
    CLEANUP_INTERVAL_SECONDS = 30.0

    def __init__(self):
        # Core data structures — protected by asyncio.Lock for concurrency safety
        self._lock = asyncio.Lock()

        # user_id → List[WebSocketConnection]
        self._connections: Dict[str, List[WebSocketConnection]] = {}

        # channel_name → Set[user_id] — tracks which users are subscribed to which channels
        self._channel_subscribers: Dict[str, Set[str]] = {
            "notifications": set(),
            "dashboard_updates": set(),
            "activity_stream": set(),
            "analytics_live": set(),
            "system_broadcast": set(),
        }

        # Metrics counters
        self._total_connections_served = 0
        self._total_messages_sent = 0
        self._total_send_failures = 0

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

    # ───────────────────────────────────────────────────────────────────
    # CONNECTION LIFECYCLE
    # ───────────────────────────────────────────────────────────────────

    async def connect(
        self,
        user_id: str,
        websocket: WebSocket,
        channels: Optional[Set[str]] = None,
        user_role: Optional[str] = None,
        client_info: Optional[str] = None,
    ) -> WebSocketConnection:
        """
        Accepts and registers a WebSocket connection for a user.

        Args:
            user_id: Authenticated user identifier.
            websocket: The FastAPI WebSocket instance.
            channels: Set of channel names to subscribe to (defaults to {"notifications"}).
            user_role: The user's role for permission-based channel filtering.
            client_info: Optional user-agent or device identifier.

        Returns:
            The created WebSocketConnection metadata object.
        """
        await websocket.accept()

        if channels is None:
            channels = {"notifications"}

        conn = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            subscribed_channels=channels,
            user_role=user_role,
            client_info=client_info,
        )

        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = []
            self._connections[user_id].append(conn)

            # Register user in channel subscriber sets
            for channel in channels:
                if channel in self._channel_subscribers:
                    self._channel_subscribers[channel].add(user_id)

            self._total_connections_served += 1

        # Track metrics
        self._track_connection_opened()

        logger.info(
            f"[WS Connect] user='{user_id}', channels={channels}, "
            f"devices={len(self._connections.get(user_id, []))}, "
            f"role={user_role}"
        )

        return conn

    async def disconnect(self, user_id: str, websocket: WebSocket):
        """
        Unregisters a WebSocket connection and cleans up channel subscriptions.
        Safe to call multiple times (idempotent).
        """
        async with self._lock:
            if user_id not in self._connections:
                return

            # Find and remove the specific connection
            remaining = []
            removed_channels: Set[str] = set()

            for conn in self._connections[user_id]:
                if conn.websocket is websocket:
                    removed_channels = conn.subscribed_channels
                else:
                    remaining.append(conn)

            if remaining:
                self._connections[user_id] = remaining
            else:
                del self._connections[user_id]
                # Remove user from all channel subscriber sets
                for channel_set in self._channel_subscribers.values():
                    channel_set.discard(user_id)

            # If user still has connections, only remove from channels where
            # no remaining connection subscribes
            if remaining:
                active_channels = set()
                for conn in remaining:
                    active_channels.update(conn.subscribed_channels)

                for channel in removed_channels - active_channels:
                    if channel in self._channel_subscribers:
                        self._channel_subscribers[channel].discard(user_id)

        self._track_connection_closed()
        logger.info(f"[WS Disconnect] user='{user_id}', remaining_devices={len(remaining) if remaining else 0}")

    # ───────────────────────────────────────────────────────────────────
    # MESSAGE DELIVERY
    # ───────────────────────────────────────────────────────────────────

    async def send_personal_message(self, message: dict, user_id: str):
        """
        Sends a message to all active WebSocket connections for a specific user.
        Auto-prunes broken connections on send failure.
        """
        async with self._lock:
            connections = self._connections.get(user_id, [])
            if not connections:
                return

        stale_websockets = []
        sent_count = 0

        for conn in list(connections):
            try:
                await conn.websocket.send_json(message)
                sent_count += 1
                self._total_messages_sent += 1
                try:
                    from app.core.metrics import track_websocket_event
                    track_websocket_event(message.get("event", "unknown"), "outbound")
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"[WS Send] Failed for user '{user_id}': {e}")
                stale_websockets.append(conn.websocket)
                self._total_send_failures += 1

        # Prune failed connections
        for ws in stale_websockets:
            await self.disconnect(user_id, ws)

        if sent_count > 0:
            logger.debug(
                f"[WS Send] Delivered message to user '{user_id}' "
                f"across {sent_count} device(s)."
            )

    async def send_to_channel(self, channel: str, message: dict, exclude_user: Optional[str] = None):
        """
        Broadcasts a message to all users subscribed to a specific channel.
        Optionally excludes a specific user (e.g., the event originator).
        """
        async with self._lock:
            subscribers = self._channel_subscribers.get(channel, set()).copy()

        if not subscribers:
            return

        delivery_count = 0
        for user_id in subscribers:
            if exclude_user and user_id == exclude_user:
                continue

            # Only send to connections that are subscribed to this specific channel
            async with self._lock:
                connections = self._connections.get(user_id, [])

            for conn in list(connections):
                if channel in conn.subscribed_channels:
                    try:
                        await conn.websocket.send_json(message)
                        delivery_count += 1
                        self._total_messages_sent += 1
                        try:
                            from app.core.metrics import track_websocket_event
                            track_websocket_event(message.get("event", "unknown"), "outbound")
                        except Exception:
                            pass
                    except Exception as e:
                        logger.warning(f"[WS Channel] Failed for user '{user_id}' on '{channel}': {e}")
                        await self.disconnect(user_id, conn.websocket)
                        self._total_send_failures += 1

        logger.debug(
            f"[WS Channel] Broadcast to '{channel}': "
            f"{delivery_count} connections across {len(subscribers)} subscriber(s)."
        )

    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """Broadcasts a message to ALL active WebSocket connections system-wide."""
        async with self._lock:
            all_user_ids = list(self._connections.keys())

        for user_id in all_user_ids:
            if exclude_user and user_id == exclude_user:
                continue
            await self.send_personal_message(message, user_id)

    # ───────────────────────────────────────────────────────────────────
    # HEARTBEAT & CLEANUP
    # ───────────────────────────────────────────────────────────────────

    async def handle_heartbeat(self, user_id: str, websocket: WebSocket):
        """Updates the heartbeat timestamp for a specific connection."""
        async with self._lock:
            connections = self._connections.get(user_id, [])
            for conn in connections:
                if conn.websocket is websocket:
                    conn.touch()
                    break

    async def start_cleanup_task(self):
        """Starts the periodic background task that prunes stale connections."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("[WS Cleanup] Stale connection sweeper started.")

    async def stop_cleanup_task(self):
        """Stops the periodic cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("[WS Cleanup] Stale connection sweeper stopped.")

    async def _periodic_cleanup(self):
        """Background coroutine that periodically sweeps and prunes stale connections."""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                await self._prune_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WS Cleanup] Error during cleanup sweep: {e}", exc_info=True)

    async def _prune_stale_connections(self):
        """Identifies and removes connections that have exceeded the heartbeat TTL."""
        stale_pairs = []

        async with self._lock:
            for user_id, connections in self._connections.items():
                for conn in connections:
                    if conn.is_stale(self.HEARTBEAT_TTL_SECONDS):
                        stale_pairs.append((user_id, conn.websocket))

        if stale_pairs:
            logger.info(f"[WS Cleanup] Pruning {len(stale_pairs)} stale connection(s)...")
            for user_id, ws in stale_pairs:
                try:
                    await ws.close(code=1000, reason="Heartbeat timeout")
                except Exception:
                    pass
                await self.disconnect(user_id, ws)

    # ───────────────────────────────────────────────────────────────────
    # CHANNEL SUBSCRIPTION MANAGEMENT
    # ───────────────────────────────────────────────────────────────────

    async def subscribe_to_channel(self, user_id: str, websocket: WebSocket, channel: str):
        """Adds a channel subscription for an existing connection."""
        async with self._lock:
            connections = self._connections.get(user_id, [])
            for conn in connections:
                if conn.websocket is websocket:
                    conn.subscribed_channels.add(channel)
                    if channel in self._channel_subscribers:
                        self._channel_subscribers[channel].add(user_id)
                    break

    async def unsubscribe_from_channel(self, user_id: str, websocket: WebSocket, channel: str):
        """Removes a channel subscription for an existing connection."""
        async with self._lock:
            connections = self._connections.get(user_id, [])
            for conn in connections:
                if conn.websocket is websocket:
                    conn.subscribed_channels.discard(channel)
                    break

            # Check if any remaining connection still subscribes to this channel
            still_subscribed = False
            for conn in self._connections.get(user_id, []):
                if channel in conn.subscribed_channels:
                    still_subscribed = True
                    break

            if not still_subscribed and channel in self._channel_subscribers:
                self._channel_subscribers[channel].discard(user_id)

    # ───────────────────────────────────────────────────────────────────
    # MONITORING & STATS
    # ───────────────────────────────────────────────────────────────────

    @property
    def active_connections(self) -> Dict[str, List[WebSocket]]:
        """Legacy compatibility: Returns user_id → List[WebSocket] mapping."""
        return {
            uid: [conn.websocket for conn in conns]
            for uid, conns in self._connections.items()
        }

    @property
    def total_active_connections(self) -> int:
        """Returns the total number of active WebSocket connections across all users."""
        return sum(len(conns) for conns in self._connections.values())

    @property
    def total_active_users(self) -> int:
        """Returns the number of unique users with active connections."""
        return len(self._connections)

    def get_stats(self) -> Dict[str, Any]:
        """Returns comprehensive WebSocket manager statistics for health/monitoring endpoints."""
        channel_counts = {
            channel: len(users) for channel, users in self._channel_subscribers.items()
        }
        return {
            "active_connections": self.total_active_connections,
            "active_users": self.total_active_users,
            "total_connections_served": self._total_connections_served,
            "total_messages_sent": self._total_messages_sent,
            "total_send_failures": self._total_send_failures,
            "channel_subscribers": channel_counts,
            "heartbeat_ttl_seconds": self.HEARTBEAT_TTL_SECONDS,
            "cleanup_interval_seconds": self.CLEANUP_INTERVAL_SECONDS,
        }

    # ───────────────────────────────────────────────────────────────────
    # PROMETHEUS METRICS HOOKS
    # ───────────────────────────────────────────────────────────────────

    def _track_connection_opened(self):
        """Increments Prometheus WebSocket gauge/counter on connect."""
        try:
            from app.core.metrics import track_websocket_connection
            track_websocket_connection("opened", self.total_active_connections)
        except Exception:
            pass

    def _track_connection_closed(self):
        """Decrements Prometheus WebSocket gauge on disconnect."""
        try:
            from app.core.metrics import track_websocket_connection
            track_websocket_connection("closed", self.total_active_connections)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

manager = ConnectionManager()
