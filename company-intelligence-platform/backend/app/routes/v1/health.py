import logging
import shutil
import time
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST

from app.services.db import db_service
from app.services.cache_service import cache_service
from app.services.orchestration_manager import orchestration_manager
from app.core.celery_app import celery_app
from app.core.metrics import export_metrics

logger = logging.getLogger("company_intel.routes.health")

router = APIRouter()

@router.get("/metrics", tags=["Monitoring"], include_in_schema=False)
def get_metrics():
    """
    Exposes system and application metrics in standard Prometheus format.
    Scraped by Prometheus server at regular intervals.
    """
    try:
        metrics_data = export_metrics()
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Failed to export Prometheus metrics: {e}", exc_info=True)
        return Response(
            content=f"# Error exporting metrics: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="text/plain"
        )

@router.get("/", tags=["Health"], include_in_schema=False)
async def health_endpoint():
    """Quick health check endpoint for liveness probes."""
    db_alive = await db_service.atest_connection()
    return {
        "status": "healthy",
        "service": "Company Intelligence Platform API",
        "timestamp": time.time(),
        "supabase_connection": db_alive
    }

@router.get("/health", tags=["Health"])
async def detailed_health_check():
    """
    Production-ready readiness probe checking all downstream services:
    - PostgreSQL/Supabase database connectivity
    - Redis cache ping, latencies and fallback status
    - Celery background worker availability
    - Host system resources & Memory metrics
    - Active orchestrations & queue sizes
    """
    health_status = "healthy"
    details = {}
    start_time = time.time()

    # 1. Test Database Connection
    try:
        db_start = time.time()
        db_alive = await db_service.atest_connection()
        db_latency = time.time() - db_start
        details["database"] = {
            "status": "connected" if db_alive else "disconnected",
            "latency_seconds": round(db_latency, 4)
        }
        if not db_alive:
            health_status = "degraded"
    except Exception as e:
        logger.error(f"Health check: Database error: {e}")
        details["database"] = {"status": "error", "error": str(e)}
        health_status = "degraded"

    # 2. Test Redis Connection & Connectivity
    try:
        from app.services.redis_service import redis_service
        if redis_service.client:
            redis_start = time.time()
            await redis_service.client.ping()
            redis_latency = time.time() - redis_start
            details["redis"] = {
                "status": "connected",
                "fallback_mode": redis_service.is_fallback,
                "latency_seconds": round(redis_latency, 4),
                "circuit_breaker_state": redis_service.circuit_breaker.state
            }
        else:
            details["redis"] = {"status": "uninitialized"}
            health_status = "degraded"
    except Exception as e:
        logger.error(f"Health check: Redis error: {e}")
        details["redis"] = {"status": "error", "error": str(e)}
        health_status = "degraded"

    # 3. Test Celery Workers availability
    try:
        celery_inspector = celery_app.control.inspect(timeout=1.0)
        active_workers = celery_inspector.ping()
        details["celery"] = {
            "status": "active" if active_workers else "inactive",
            "active_nodes_count": len(active_workers) if active_workers else 0
        }
    except Exception as e:
        logger.warning(f"Health check: Celery inspect failed: {e}")
        details["celery"] = {"status": "offline_or_inspect_timeout", "info": "Could not contact worker nodes."}

    # 4. Host System Resources Check (Disk & Memory)
    try:
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        details["system_disk"] = {
            "status": "healthy" if free_percent >= 5.0 else "critical_low_disk",
            "disk_free_percent": round(free_percent, 2),
            "disk_total_gb": round(total / (1024**3), 2),
            "disk_free_gb": round(free / (1024**3), 2)
        }
        if free_percent < 5.0:
            health_status = "degraded"
            
        import psutil
        mem = psutil.virtual_memory()
        details["system_memory"] = {
            "percent_used": mem.percent,
            "used_mb": round(mem.used / (1024**2), 2),
            "total_mb": round(mem.total / (1024**2), 2)
        }
    except Exception as e:
        details["system_disk"] = {"status": "error", "error": str(e)}

    # 5. Orchestration Metrics
    try:
        details["orchestration"] = {
            "active_count": await orchestration_manager.get_active_count(),
            "queue_size": await orchestration_manager.get_queue_size(),
            "concurrency_limit": orchestration_manager.concurrency_limit
        }
    except Exception as e:
        details["orchestration"] = {"status": "error", "error": str(e)}

    # 6. OpenTelemetry Observability Health
    try:
        from app.core.telemetry import get_telemetry_status
        tel_status = get_telemetry_status()
        tel_health = "healthy"
        if not tel_status.get("otel_enabled"):
            tel_health = "disabled"
        elif not tel_status.get("initialized"):
            tel_health = "uninitialized"
        elif tel_status.get("exporter") and tel_status["exporter"].get("permanently_disabled"):
            tel_health = "degraded"
        elif tel_status.get("exporter") and tel_status["exporter"].get("circuit_open"):
            tel_health = "circuit_open"
        details["telemetry"] = {
            "status": tel_health,
            "initialized": tel_status.get("initialized"),
            "service_name": tel_status.get("service_name"),
            "exporter": tel_status.get("exporter"),
            "watchdog": tel_status.get("watchdog"),
        }
    except Exception as e:
        details["telemetry"] = {"status": "error", "error": str(e)}

    http_status = status.HTTP_200_OK if health_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    total_latency_seconds = time.time() - start_time

    return JSONResponse(
        content={
            "status": health_status,
            "timestamp": time.time(),
            "latency_seconds": round(total_latency_seconds, 4),
            "details": details
        },
        status_code=http_status
    )

@router.get("/info", tags=["Health"])
async def info_endpoint():
    """Public system info endpoint returning the system status."""
    return {"status": "ok"}


@router.get("/redis-health", tags=["Health"])
@router.get("/health/redis", tags=["Health"])
async def redis_health_check():
    """
    Detailed standalone check targeting the Redis connection layer.
    Returns:
    - Connectivity status
    - Operation latency
    - Fallback modes
    - Circuit breaker states
    - Operation retry stats
    """
    from app.core.redis_client import redis_client
    from app.services.redis_service import redis_service
    
    is_alive = False
    ping_latency_ms = -1.0
    start_time = time.time()
    
    try:
        if redis_service.client:
            await redis_service.client.ping()
            ping_latency_ms = round((time.time() - start_time) * 1000, 2)
            is_alive = True
    except Exception as ping_exc:
        logger.warning(f"Stand-alone Redis health check ping failed: {ping_exc}")

    stats = redis_client.stats
    status_label = "healthy"
    if not is_alive:
        status_label = "unhealthy"
    elif redis_service.is_fallback:
        status_label = "degraded"

    return {
        "status": status_label,
        "is_alive": is_alive,
        "latency_ms": ping_latency_ms,
        "circuit_breaker_state": redis_service.circuit_breaker.state,
        "details": {
            "host": stats.get("host"),
            "port": stats.get("port"),
            "in_docker": stats.get("in_docker"),
            "fallback_mode": stats.get("is_fallback"),
            "reconnect_attempts": stats.get("reconnect_attempts"),
            "last_error": stats.get("last_error"),
            "error_type": stats.get("error_type"),
            "total_operations": stats.get("ops_count"),
            "failure_count": stats.get("failure_count")
        }
    }


@router.get("/orchestration-health", tags=["Health"])
async def orchestration_health_check():
    """
    Detailed check targeting active corporate target workflows.
    Returns:
    - Active orchestrations
    - Waiting queue size
    - Concurrency metrics
    - System memory metrics
    - Redis connectivity/latency
    """
    from app.services.redis_service import redis_service
    import psutil
    
    start_time = time.time()
    redis_alive = False
    redis_latency_ms = -1.0
    
    try:
        if redis_service.client:
            redis_start = time.time()
            await redis_service.client.ping()
            redis_latency_ms = round((time.time() - redis_start) * 1000, 2)
            redis_alive = True
    except Exception:
        pass

    # System Memory usage
    try:
        mem = psutil.virtual_memory()
        memory_usage = {
            "total_mb": round(mem.total / (1024**2), 2),
            "available_mb": round(mem.available / (1024**2), 2),
            "percent_used": mem.percent,
            "used_mb": round(mem.used / (1024**2), 2)
        }
    except Exception as e:
        memory_usage = {"status": "error", "error": str(e)}

    # Process resident set size (RSS)
    try:
        process = psutil.Process()
        process_memory_mb = round(process.memory_info().rss / (1024**2), 2)
    except Exception:
        process_memory_mb = -1.0

    active_count = await orchestration_manager.get_active_count()
    queue_size = await orchestration_manager.get_queue_size()
    total_latency_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "status": "healthy" if redis_alive and active_count < orchestration_manager.concurrency_limit else "degraded",
        "timestamp": time.time(),
        "latency_ms": total_latency_ms,
        "metrics": {
            "active_orchestrations": active_count,
            "queue_size": queue_size,
            "concurrency_limit": orchestration_manager.concurrency_limit,
            "system_memory": memory_usage,
            "process_memory_mb": process_memory_mb,
            "redis_connected": redis_alive,
            "redis_latency_ms": redis_latency_ms
        }
    }


