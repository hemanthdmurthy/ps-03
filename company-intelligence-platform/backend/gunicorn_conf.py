"""
Gunicorn Configuration — Multi-Worker Telemetry Safety
======================================================
Ensures each forked worker gets its own TracerProvider.
Prevents cross-process state corruption of gRPC channels.

Usage:
  gunicorn app.main:app -c gunicorn_conf.py -w 4 -k uvicorn.workers.UvicornWorker
"""
import logging
import os

logger = logging.getLogger("company_intel.gunicorn")

# ── Worker Configuration ──
workers = int(os.environ.get("GUNICORN_WORKERS", "4"))
worker_class = "uvicorn.workers.UvicornWorker"
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 1000           # Recycle workers to prevent memory leaks
max_requests_jitter = 50      # Stagger recycling to avoid thundering herd


def post_fork(server, worker):
    """
    Called after each worker is forked. Re-initializes telemetry
    in the child process to avoid sharing gRPC channels across forks.
    """
    try:
        from app.core.telemetry import setup_telemetry, TELEMETRY_AVAILABLE
        if TELEMETRY_AVAILABLE:
            # Override service name to include worker PID for trace distinction
            os.environ["OTEL_SERVICE_NAME"] = (
                os.environ.get("OTEL_SERVICE_NAME", "placement-intel-backend")
                + f"-w{worker.pid}"
            )
            setup_telemetry()
            logger.info("[Gunicorn] Worker %d telemetry initialized.", worker.pid)
    except Exception as e:
        logger.warning("[Gunicorn] Worker %d telemetry init failed: %s", worker.pid, e)


def worker_exit(server, worker):
    """
    Called when a worker exits. Flushes and shuts down telemetry
    to ensure no spans are lost during graceful shutdown.
    """
    try:
        from app.core.telemetry import shutdown_telemetry
        shutdown_telemetry()
        logger.info("[Gunicorn] Worker %d telemetry shut down.", worker.pid)
    except Exception as e:
        logger.warning("[Gunicorn] Worker %d telemetry shutdown failed: %s", worker.pid, e)
