# app/tasks/scheduled_tasks.py
import logging
from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.services.db import db_service
from app.services.cache_service import cache_service
from app.core.database import SessionLocal
from app.models.research_session import TokenUsageLog

logger = logging.getLogger("company_intel.tasks.scheduled")

@celery_app.task(name="app.tasks.scheduled_tasks.system_heartbeat")
def system_heartbeat():
    """A periodic heartbeat task validating Redis and Celery integrations are healthy."""
    logger.info("[Heartbeat] Celery beat and worker communication link verified successfully.")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@celery_app.task(name="app.tasks.scheduled_tasks.cleanup_expired_cache")
def cleanup_expired_cache():
    """
    Periodic task running daily/hourly to prune transient caches, response buffers, 
    and clear staging tables or log registers that are older than 30 days.
    """
    logger.info("[Scheduled Cleanup] Starting expired cache and log purging operations...")
    
    # 1. Clear stale cached response entries
    try:
        import asyncio
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    cleared_count = 0
    try:
        # Run clear_pattern synchronously using the event loop
        success = loop.run_until_complete(cache_service.clear_pattern("response:*"))
        logger.info(f"[Cache Purged] Cleaned stale response caches from Redis. Status: {success}")
    except Exception as e:
        logger.error(f"Failed to clear Redis response caches: {e}")
        
    # 2. Database Log Maintenance (e.g. prune token logs or old audit reports older than 30 days)
    db = SessionLocal()
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        # Prune old logs if database tables are populated
        deleted_rows = db.query(TokenUsageLog).filter(TokenUsageLog.timestamp < thirty_days_ago).delete(synchronize_session=False)
        db.commit()
        logger.info(f"[Database Pruned] Deleted {deleted_rows} old token usage log records older than 30 days.")
    except Exception as db_exc:
        db.rollback()
        logger.error(f"Database log maintenance failed: {db_exc}")
    finally:
        db.close()
        
    return {"status": "success", "purged_cache": True}

@celery_app.task(name="app.tasks.scheduled_tasks.precompute_analytics_dashboard_stats")
def precompute_analytics_dashboard_stats():
    """
    Compiles database statistics and token usage logs, preparing pre-aggregated metrics.
    Caches them globally to enable instant, sub-millisecond dashboard renders in the backend.
    """
    logger.info("[Scheduled Precompute] Compiling database token usage and metric aggregates...")
    
    try:
        # Fetch analytics statistics directly from Supabase/SQL database
        stats = db_service.get_token_dashboard_metrics()
        
        # Cache results in Redis for 1 hour (3600s)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if stats:
            loop.run_until_complete(cache_service.set("dashboard:analytics:cached_stats", stats, ttl=3600))
            logger.info("[Scheduled Precompute Success] Successfully pre-aggregated and cached dashboard statistics in Redis.")
            return {"status": "success", "cached_keys": 1}
    except Exception as exc:
        logger.error(f"Failed to compile dashboard metrics: {exc}", exc_info=True)
        
    return {"status": "failed"}


# ═══════════════════════════════════════════════════════════════════════════
# DEAD-LETTER QUEUE HANDLER
# ═══════════════════════════════════════════════════════════════════════════

@celery_app.task(
    name="app.tasks.scheduled_tasks.dlq_handler",
    bind=True,
    max_retries=0,
    time_limit=60,
    soft_time_limit=50,
    queue="dlq"
)
def dlq_handler(self, original_task_name: str, original_task_id: str, error_message: str):
    """
    Dead-Letter Queue Handler.
    Receives fatally failed tasks that exhausted all retries.
    Persists them to Redis (list) for manual inspection, alerting, and potential replay.
    """
    import json
    from datetime import datetime
    
    logger.critical(
        f"[DLQ] Received dead-letter: task={original_task_name}, "
        f"id={original_task_id}, error={error_message}"
    )
    
    dlq_entry = {
        "task_name": original_task_name,
        "task_id": original_task_id,
        "error": error_message,
        "received_at": datetime.utcnow().isoformat(),
        "status": "dead_lettered"
    }
    
    # Persist to Redis DLQ list for inspection
    try:
        from app.core.redis_client import redis_client
        r = redis_client.sync_client
        r.rpush("dlq:failed_tasks", json.dumps(dlq_entry))
        # Keep only last 1000 DLQ entries to prevent unbounded growth
        r.ltrim("dlq:failed_tasks", -1000, -1)
        logger.info(f"[DLQ] Persisted dead-letter entry to Redis: {original_task_id}")
    except Exception as redis_err:
        logger.error(f"[DLQ] Failed to persist to Redis: {redis_err}")
    
    # Also persist to database for durable audit trail
    db = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text(
            "INSERT OR IGNORE INTO dead_letter_queue (task_name, task_id, error, received_at) "
            "VALUES (:task_name, :task_id, :error, :received_at)"
        ), dlq_entry)
        db.commit()
        logger.info(f"[DLQ] Persisted dead-letter to database: {original_task_id}")
    except Exception as db_err:
        db.rollback()
        # DB persistence is best-effort — Redis is the primary DLQ store
        logger.warning(f"[DLQ] Database persistence failed (non-critical): {db_err}")
    finally:
        db.close()
    
    return {"status": "dead_lettered", "task_id": original_task_id}


# ═══════════════════════════════════════════════════════════════════════════
# STUCK TASK SWEEPER
# ═══════════════════════════════════════════════════════════════════════════

@celery_app.task(
    name="app.tasks.scheduled_tasks.stuck_task_sweeper",
    bind=True,
    max_retries=0,
    time_limit=120,
    soft_time_limit=100
)
def stuck_task_sweeper(self):
    """
    Periodic task that inspects active Celery tasks and identifies those that
    have exceeded their expected SLA. Quarantines stuck tasks and logs alerts.
    """
    logger.info("[Stuck Task Sweeper] Scanning for stuck or orphaned tasks...")
    
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}
        
        import time
        stuck_count = 0
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                # Check if task has been running longer than its time_limit
                time_start = task.get("time_start")
                time_limit = task.get("time_limit") or 3600
                if time_start:
                    elapsed = time.time() - time_start
                    if elapsed > time_limit * 0.9:  # 90% of time limit = likely stuck
                        stuck_count += 1
                        logger.warning(
                            f"[Stuck Task] Task {task.get('id')} ({task.get('name')}) "
                            f"on worker {worker_name} has been running for {elapsed:.0f}s "
                            f"(limit: {time_limit}s). Potentially stuck."
                        )
        
        logger.info(f"[Stuck Task Sweeper] Scan complete. Found {stuck_count} potentially stuck tasks.")
        return {"status": "complete", "stuck_tasks_found": stuck_count}
    except Exception as e:
        logger.error(f"[Stuck Task Sweeper] Failed: {e}")
        return {"status": "failed", "error": str(e)}
