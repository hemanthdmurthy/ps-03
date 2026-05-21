# test_redis_and_celery.py
import sys
import os

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_redis_celery")

def test_redis_connection():
    logger.info("Testing Redis Connection...")
    try:
        import redis
        from app.core.config import settings
        
        logger.info(f"Connecting to Redis at: {settings.CELERY_BROKER_URL}")
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        ping_res = r.ping()
        logger.info(f"Redis Ping Response: {ping_res} (Connection Successful!)")
        return True
    except Exception as e:
        logger.error(f"Redis Connection Failed: {e}", exc_info=True)
        return False

def test_celery_task_discovery():
    logger.info("Testing Celery Task Discovery...")
    try:
        from app.core.celery_app import celery_app
        
        logger.info("Loading Celery App and Registered Tasks...")
        tasks = sorted(list(celery_app.tasks.keys()))
        logger.info(f"Discovered {len(tasks)} Celery Tasks:")
        for t in tasks:
            logger.info(f"  - {t}")
            
        expected_tasks = [
            "app.tasks.research_tasks.run_research_workflow_task",
            "app.tasks.notification_tasks.send_notification_task",
            "app.tasks.scheduled_tasks.system_heartbeat",
            "app.tasks.scheduled_tasks.precompute_analytics_dashboard_stats",
            "app.tasks.scheduled_tasks.cleanup_expired_cache"
        ]
        
        missing = [et for et in expected_tasks if et not in tasks]
        if missing:
            logger.error(f"Missing expected tasks in registry: {missing}")
            return False
        else:
            logger.info("All expected tasks are registered successfully!")
            return True
    except Exception as e:
        logger.error(f"Celery Task Discovery Failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    redis_ok = test_redis_connection()
    celery_ok = test_celery_task_discovery()
    if redis_ok and celery_ok:
        logger.info("All basic Redis and Celery registration checks passed successfully!")
        sys.exit(0)
    else:
        logger.error("Some checks failed. Please see log messages above.")
        sys.exit(1)
