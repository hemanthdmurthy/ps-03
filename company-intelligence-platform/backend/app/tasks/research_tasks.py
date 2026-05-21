# app/tasks/research_tasks.py
import logging
import asyncio
from celery import Task
from app.core.celery_app import celery_app
from app.services.workflow_service import run_langgraph_workflow, publish_event
from app.services.db import db_service

logger = logging.getLogger("company_intel.tasks.research")

class ResearchWorkflowTask(Task):
    """
    Custom Celery Task subclass to handle task failures and success callbacks 
    gracefully to ensure database session integrity.
    """
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        session_id = kwargs.get("session_id") or (args[0] if len(args) > 0 else None)
        company_name = kwargs.get("company_name") or (args[1] if len(args) > 1 else None)
        logger.error(f"[Task Failure] Research pipeline failed for task {task_id}, session {session_id}. Error: {exc}")
        
        # Dead-Letter Queue (DLQ) Integration
        try:
            dlq_task_name = "app.tasks.research_tasks.run_research_workflow_task"
            logger.warning(f"[DLQ] Sending fatally failed task {task_id} to DLQ")
            celery_app.send_task(
                "app.tasks.scheduled_tasks.dlq_handler", # Will implement a basic DLQ logger/handler
                args=[dlq_task_name, task_id, str(exc)],
                queue="dlq"
            )
        except Exception as dlq_err:
            logger.error(f"[DLQ Error] Failed to route to DLQ: {dlq_err}")
        
        if session_id:
            try:
                # Thread-safe database session update via db_service
                db_service.update_session(session_id, {"status": "failed"})
                # Broadcast terminal failure event to all active SSE streaming subscribers
                publish_event(session_id, "workflow_failed", {
                    "error": f"Asynchronous processing engine reported a fatal execution error: {str(exc)}",
                    "status": "failed"
                })
                logger.info(f"[DB Status Cleaned] Updated session {session_id} status to 'failed' on failure hook.")
                
                # Cleanup Redis Locks & States safely
                if company_name:
                    from app.services.orchestration_manager import orchestration_manager
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    loop.run_until_complete(
                        orchestration_manager.complete_orchestration(company_name, session_id, "failed")
                    )
                    logger.info(f"[Redis Status Cleaned] Released lock and failed state for '{company_name}' in failure hook.")
            except Exception as db_err:
                logger.error(f"Failed to execute database rollback/Redis lock state cleanup in Celery hook: {db_err}")

    def on_success(self, retval, task_id, args, kwargs):
        session_id = kwargs.get("session_id") or (args[0] if len(args) > 0 else None)
        logger.info(f"[Task Success] Research pipeline completed successfully for task {task_id}, session {session_id}")

@celery_app.task(
    base=ResearchWorkflowTask,
    name="app.tasks.research_tasks.run_research_workflow_task",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    time_limit=1800,       # Strict 30 min hard limit
    soft_time_limit=1700   # Graceful degradation at 28.3 min
)
def run_research_workflow_task(self, session_id: str, company_name: str, industry: str, custom_query: str, max_attempts: int, threshold: float):
    """
    Asynchronous Celery task running the complete Multi-Agent Corporate Research Orchestration.
    Integrates our Python asyncio LangGraph runtime loop within the worker process.
    """
    logger.info(f"[Celery Worker] Starting corporate research workflow task for '{company_name}' (Session: {session_id})")
    
    # 1. Initialize or fetch event loop inside background worker process
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        logger.info("No active event loop found in current worker thread. Initializing new loop.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    # 2. Run the async workflow until complete
    try:
        loop.run_until_complete(
            run_langgraph_workflow(
                session_id=session_id,
                company_name=company_name,
                industry=industry,
                custom_query=custom_query,
                max_attempts=max_attempts,
                threshold=threshold
            )
        )
        return {
            "status": "success",
            "session_id": session_id,
            "company_name": company_name
        }
    except Exception as exc:
        logger.error(f"[Task Exception] Error during LangGraph run: {exc}", exc_info=True)
        # Attempt to retry the task if under max limits
        try:
            # Exponential backoff based on attempts: 60s, 120s
            countdown = self.default_retry_delay * (self.request.retries + 1)
            logger.info(f"Retrying research task for session {session_id} in {countdown} seconds...")
            self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.error(f"[Max Retries Exceeded] Failed all research attempts for session: {session_id}")
            # Raise the exception so it propagates to on_failure hook
            raise exc
