# app/core/celery_app.py
import os
import logging
from celery import Celery
from app.core.config import settings

logger = logging.getLogger("company_intel.celery")

# Initialize Celery application
celery_app = Celery(
    "company_intel",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Dynamic Windows-compatible pool selection
import sys
is_windows = sys.platform.startswith("win")
default_pool = "solo" if is_windows else "prefork"
worker_pool = os.environ.get("CELERY_WORKER_POOL", default_pool)

# Standard and highly resilient production configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour limit
    task_soft_time_limit=3000,
    task_acks_late=True,   # Late acknowledgment ensures tasks are retried if worker crashes mid-execution
    worker_prefetch_multiplier=4, # Optimized prefetching for higher throughput
    
    # Resource Guards and Memory Optimization
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=256000, # 256MB limit per worker to prevent memory leaks
    
    # Windows compatibility and safe execution model configuration
    worker_pool=worker_pool,
    worker_concurrency=1 if worker_pool == "solo" else 8, # Tuned concurrency
    
    # Task Isolation & Bulkhead Patterns (Queue Segregation)
    task_default_queue="default",
    task_create_missing_queues=True,
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "research": {"exchange": "research", "routing_key": "research"},
        "notifications": {"exchange": "notifications", "routing_key": "notifications"},
        "dlq": {"exchange": "dlq", "routing_key": "dlq"}, # Dead-Letter Queue for fatally failed tasks
    },
    task_routes={
        "app.tasks.research_tasks.*": {"queue": "research"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.scheduled_tasks.*": {"queue": "default"},
    },
    
    # Resilient Celery Broker and Result Backend settings
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,  # Infinite retries to survive long Redis outages
    broker_connection_retry=True,        # Auto-reconnect on connection loss
    result_backend_always_retry=True,    # Auto-retry writing results to Redis
    result_backend_max_retries=10,       # Retry writing up to 10 times to backend
    result_backend_base_sleep_between_retries_ms=1000,
    result_backend_max_sleep_between_retries_ms=5000,
    broker_transport_options={
        "max_connections": 10,
        "visibility_timeout": 3600,
        "retry_policy": {
            "timeout": 5.0,
            "max_retries": None,  # Infinite retries for connection pool
            "interval_start": 1.0,
            "interval_step": 2.0,
            "interval_max": 30.0,
        }
    },
    result_backend_transport_options={
        "retry_policy": {
            "timeout": 5.0,
            "max_retries": 10,
            "interval_start": 1.0,
            "interval_step": 2.0,
            "interval_max": 10.0,
        }
    }
)

# Autodiscover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])

# Celery Beat periodic schedules
celery_app.conf.beat_schedule = {
    "system-heartbeat-check": {
        "task": "app.tasks.scheduled_tasks.system_heartbeat",
        "schedule": 30.0,  # Runs every 30 seconds to audit worker link health
    },
    "hourly-dashboard-analytics-precompute": {
        "task": "app.tasks.scheduled_tasks.precompute_analytics_dashboard_stats",
        "schedule": 3600.0,  # Pre-aggregates analytics to Redis every hour (3600s)
    },
    "daily-expired-cache-cleanup": {
        "task": "app.tasks.scheduled_tasks.cleanup_expired_cache",
        "schedule": 86400.0,  # Clears expired staging data and response caches every 24 hours (86400s)
    },
    "stuck-task-sweeper": {
        "task": "app.tasks.scheduled_tasks.stuck_task_sweeper",
        "schedule": 300.0,  # Scans for stuck/orphaned tasks every 5 minutes
    },
}

# Explicitly import all task modules to register them with the Celery loader
# This prevents discovery bugs when starting workers in distributed container environments
try:
    import app.tasks.research_tasks
    import app.tasks.notification_tasks
    import app.tasks.scheduled_tasks
    logger.info("[Celery Init] All modular worker and scheduled tasks successfully registered.")
except Exception as e:
    logger.error(f"[Celery Init Error] Failed to register modular tasks: {e}", exc_info=True)

# Deprecated legacy/fallback tasks kept for backwards-compatibility or quick system verification
@celery_app.task(name="app.core.celery_app.system_heartbeat")
def system_heartbeat():
    """A periodic heartbeat task validating Redis and Celery integrations are healthy."""
    logger.info("[Heartbeat] Celery beat and worker communication link verified successfully.")
    return {"status": "healthy", "service": "celery-beat-worker"}

@celery_app.task(name="app.core.celery_app.add_numbers")
def add_numbers(x: int, y: int) -> int:
    """A simple demo task for testing task queues."""
    logger.info(f"Executing addition task for parameters: x={x}, y={y}")
    return x + y


# ═══════════════════════════════════════════════════════════════════════════
# CELERY SIGNALS FOR PROMETHEUS METRIC REPORTING
# ═══════════════════════════════════════════════════════════════════════════
import time
from celery.signals import task_prerun, task_postrun, celeryd_after_setup

@task_prerun.connect
def celery_task_prerun(sender=None, task_id=None, task=None, *args, **kwargs):
    """Fired immediately before a task is executed by a Celery worker."""
    if task:
        # Save start time as an attribute on the task instance
        task._prometheus_start_time = time.time()
        
        # Increment started counter
        from app.core.metrics import track_celery_task
        task_name = task.name or getattr(sender, "name", "unknown")
        track_celery_task(task_name=task_name, status="started")

@task_postrun.connect
def celery_task_postrun(sender=None, task_id=None, task=None, retval=None, state=None, *args, **kwargs):
    """Fired immediately after a task finishes (whether successfully or failed)."""
    if task:
        start_time = getattr(task, "_prometheus_start_time", None)
        duration = time.time() - start_time if start_time else None
        
        # Map Celery task state to simple metric status
        status = "success" if state == "SUCCESS" else "failure"
        
        from app.core.metrics import track_celery_task
        task_name = task.name or getattr(sender, "name", "unknown")
        track_celery_task(task_name=task_name, status=status, duration=duration)

@celeryd_after_setup.connect
def setup_direct_prometheus_exporter(sender, instance, **kwargs):
    """
    Fires inside the Celery worker process upon complete initialization.
    Spawns a dedicated Prometheus HTTP metrics scraper server on port 9100.
    Handles multiprocess aggregation directories if specified.
    """
    try:
        import os
        import prometheus_client
        
        # Prepare the multiprocess directory if enabled
        multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROCESS_DIR")
        registry = prometheus_client.REGISTRY
        
        if multiproc_dir:
            os.makedirs(multiproc_dir, exist_ok=True)
            # Clear stale metric files from any previous run
            for f in os.listdir(multiproc_dir):
                fp = os.path.join(multiproc_dir, f)
                if os.path.isfile(fp):
                    try:
                        os.unlink(fp)
                    except Exception:
                        pass
            
            # Use MultiProcessCollector to aggregate metrics across child prefork processes
            registry = prometheus_client.CollectorRegistry()
            prometheus_client.multiprocess.MultiProcessCollector(registry)
            logger.info(f"[Metrics] Enabled Prometheus Multiprocess registry at: {multiproc_dir}")
            
        port = 9100
        bound = False
        while port < 9110 and not bound:
            try:
                logger.info(f"[Metrics] Attempting to start Celery Prometheus HTTP metrics server on port {port}...")
                prometheus_client.start_http_server(port=port, registry=registry)
                logger.info(f"[Metrics] Celery Prometheus HTTP metrics server active on port {port}!")
                bound = True
            except OSError as e:
                # 98 is EADDRINUSE on Linux, 10048 is WSAEADDRINUSE on Windows
                if e.errno in (98, 10048):
                    logger.warning(f"[Metrics] Port {port} is occupied. Retrying with next port...")
                    port += 1
                else:
                    raise e
        if not bound:
            logger.error("[Metrics Error] Could not bind Prometheus metrics server on ports 9100-9109. All ports occupied.")
    except Exception as e:
        logger.error(f"[Metrics Error] Failed to start Celery Prometheus HTTP server: {e}", exc_info=True)

@celeryd_after_setup.connect
def wait_for_redis_ready(sender, instance, **kwargs):
    """
    Blocks Celery worker startup until Redis broker is fully accessible.
    Ensures the worker does not boot in an unstable, disconnected state.
    """
    logger.info("[Celery Startup] Verifying Redis broker connectivity...")
    import time
    import redis
    
    max_attempts = 15
    attempt = 0
    while attempt < max_attempts:
        try:
            # Create a simple test connection and ping
            r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2.0)
            r.ping()
            logger.info("🟢 [Celery Startup] Redis broker is ready! Proceeding with worker boot.")
            return
        except Exception as e:
            attempt += 1
            logger.warning(
                f"⚠️ [Celery Startup] Redis broker not ready (attempt {attempt}/{max_attempts}): {e}. "
                f"Retrying in 2 seconds..."
            )
            time.sleep(2.0)
            
    logger.critical("🚨 [Celery Startup] Redis broker failed to become ready in time. Proceeding with worker boot in degraded fallback state.")


