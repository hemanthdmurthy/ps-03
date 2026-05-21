# app/core/metrics.py
import time
import re
import logging
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger("company_intel.metrics")

# Create a dedicated registry for our application metrics
REGISTRY = CollectorRegistry()

# ═══════════════════════════════════════════════════════════════════════════
# PROMETHEUS METRIC DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

# 1. FastAPI HTTP Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests processed.",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf")),
    registry=REGISTRY
)

# 2. Database (SQLAlchemy) Metrics
DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query execution latency in seconds.",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float("inf")),
    registry=REGISTRY
)

DB_CONNECTIONS_ACTIVE = Gauge(
    "db_connections_active",
    "Estimated number of active database connections.",
    registry=REGISTRY
)

# 3. Redis / Cache Metrics
REDIS_CACHE_OPS = Counter(
    "redis_cache_operations_total",
    "Total number of Redis cache operations.",
    ["operation", "status"],  # status: hit, miss, success, failure
    registry=REGISTRY
)

REDIS_OP_DURATION = Histogram(
    "redis_op_duration_seconds",
    "Redis operation latency in seconds.",
    ["operation"],
    buckets=(0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1, float("inf")),
    registry=REGISTRY
)

# 4. Celery Task Metrics
CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Total number of Celery tasks executed.",
    ["task_name", "status"],  # status: started, success, failure
    registry=REGISTRY
)

CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task runtime in seconds.",
    ["task_name"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0, float("inf")),
    registry=REGISTRY
)

# 5. WebSocket Metrics
WEBSOCKET_CONNECTIONS_ACTIVE = Gauge(
    "websocket_connections_active",
    "Number of currently active WebSocket connections.",
    registry=REGISTRY
)

WEBSOCKET_EVENTS_TOTAL = Counter(
    "websocket_events_total",
    "Total number of WebSocket events handled.",
    ["event_type", "direction"],  # direction: inbound, outbound
    registry=REGISTRY
)


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT PATH NORMALIZATION (Prevents Cardinality Explosion)
# ═══════════════════════════════════════════════════════════════════════════

# Compile standard replacement regexes for dynamic path parameters
UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
ID_PATTERN = re.compile(r"/\d+(/|$)")

def normalize_path(path: str) -> str:
    """
    Normalizes dynamic path components in URLs to prevent Prometheus cardinality explosion.
    Example: 
      /api/companies/seed-admin-uuid-111 -> /api/companies/{id}
      /api/placement/123 -> /api/placement/{id}
    """
    if not path:
        return "/"
        
    # Replace UUIDs with {id}
    path = UUID_PATTERN.sub("{id}", path)
    
    # Replace numeric segments with /{id}
    path = ID_PATTERN.sub("/{id}/", path)
    if path.endswith("/{id}/"):
        path = path[:-1]
        
    # Standardize specific known dynamic segments if needed
    # e.g., company names in research or scraping routes
    segments = path.split("/")
    if len(segments) > 3 and segments[1] == "api" and segments[2] == "companies":
        # /api/companies/<name> -> /api/companies/{company_name}
        if segments[3] not in {"tokens", "metrics", "logs", "analytics"}:
            segments[3] = "{company_name}"
            path = "/".join(segments)
            
    return path


# ═══════════════════════════════════════════════════════════════════════════
# METRICS TRACKING HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def track_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Safely records HTTP request count and latency."""
    try:
        normalized = normalize_path(endpoint)
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=normalized, status_code=str(status_code)).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=normalized).observe(duration)
    except Exception as e:
        logger.error(f"Error tracking API request metric: {e}", exc_info=True)

def track_redis_op(operation: str, status: str, duration: float):
    """Safely records Redis cache operation count and latency."""
    try:
        REDIS_CACHE_OPS.labels(operation=operation, status=status).inc()
        REDIS_OP_DURATION.labels(operation=operation).observe(duration)
    except Exception as e:
        logger.error(f"Error tracking Redis operation metric: {e}", exc_info=True)

def track_db_query(query_type: str, duration: float):
    """Safely records Database query latency."""
    try:
        DB_QUERY_DURATION.labels(query_type=query_type).observe(duration)
    except Exception as e:
        logger.error(f"Error tracking database query metric: {e}", exc_info=True)

def track_celery_task(task_name: str, status: str, duration: Optional[float] = None):
    """Safely records Celery task run status and execution time."""
    try:
        CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()
        if duration is not None:
            CELERY_TASK_DURATION.labels(task_name=task_name).observe(duration)
    except Exception as e:
        logger.error(f"Error tracking Celery task metric: {e}", exc_info=True)

def track_websocket_connection(action: str, active_count: int):
    """Safely updates active WebSocket connections metric."""
    try:
        WEBSOCKET_CONNECTIONS_ACTIVE.set(active_count)
    except Exception as e:
        logger.error(f"Error tracking WebSocket connection metric: {e}", exc_info=True)

def track_websocket_event(event_type: str, direction: str):
    """Safely records WebSocket events count."""
    try:
        WEBSOCKET_EVENTS_TOTAL.labels(event_type=event_type, direction=direction).inc()
    except Exception as e:
        logger.error(f"Error tracking WebSocket event metric: {e}", exc_info=True)


import os
from prometheus_client import multiprocess

def export_metrics() -> str:
    """Generates the latest Prometheus-formatted metrics payload."""
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROCESS_DIR")
    if multiproc_dir:
        try:
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
            return generate_latest(registry).decode("utf-8")
        except Exception as e:
            logger.error(f"Multiprocess metrics collection failed: {e}. Falling back to default registry.")
            
    return generate_latest(REGISTRY).decode("utf-8")

