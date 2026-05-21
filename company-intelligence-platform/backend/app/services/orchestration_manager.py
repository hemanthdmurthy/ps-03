# app/services/orchestration_manager.py
"""
Centralized Orchestration Queue & Concurrency Manager
======================================================
Manages company research workflow state machines, prevents duplicate requests,
controls process concurrency, implements distributed locking, and provides
real-time status/progress tracking in Redis.
"""

import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.services.redis_service import redis_service
from app.services.db import db_service

logger = logging.getLogger("company_intel.services.orchestration_manager")


class OrchestrationManager:
    """
    Centralized controller for managing state, concurrency, and locking
    of company intelligence orchestration processes.
    """
    def __init__(self, concurrency_limit: int = 5, key_ttl_seconds: int = 3600):
        self.concurrency_limit = concurrency_limit
        self.key_ttl_seconds = key_ttl_seconds

    def get_company_id(self, company_name: str) -> str:
        """Normalizes a company name into a unique lowercase snake_case identifier."""
        return company_name.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "")

    def _get_keys(self, company_name: str) -> Dict[str, str]:
        """Generates structured Redis keys for a company."""
        company_id = self.get_company_id(company_name)
        return {
            "status": f"orchestration:{company_id}:status",
            "lock": f"orchestration:{company_id}:lock",
            "progress": f"orchestration:{company_id}:progress"
        }

    async def get_active_orchestration(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Checks if an orchestration is actively running for the company.
        If running, returns the active status object from Redis.
        """
        keys = self._get_keys(company_name)
        
        # Check if lock exists and is active using non-JSON raw helper
        lock_holder = await redis_service.get_raw(keys["lock"])
        status_data = await redis_service.get(keys["status"])
        if lock_holder:
            # Active lock found! Fetch status payload
            if status_data:
                logger.info(f"🔄 [Orchestration Manager] Active workflow found for '{company_name}' (Session: {lock_holder})")
                return status_data
            
            # Fallback if lock exists but status key expired
            return {
                "session_id": lock_holder,
                "status": "researching",
                "company_name": company_name,
                "confidence_score": 0.0,
                "created_at": datetime.utcnow().isoformat()
            }

        # Treat queued orchestration state as active until completion
        if status_data and status_data.get("status") in ("queued", "researching", "validating", "regenerating"):
            logger.info(f"🔄 [Orchestration Manager] Found queued/non-terminal workflow for '{company_name}' (Session: {status_data.get('session_id')})")
            return status_data

        return None

    async def start_orchestration(
        self,
        session_id: str,
        company_name: str,
        industry: str,
        custom_query: str,
        max_attempts: int = 3,
        confidence_threshold: float = 0.85,
        enqueue_if_full: bool = True
    ) -> Dict[str, Any]:
        """
        Tries to start a new company research orchestration.
        Guarantees duplicate request prevention and distributed lock acquisition.
        If already running, returns the active state dict.
        """
        keys = self._get_keys(company_name)
        
        # 1. Double check if already running (CORS/race-conditions protection)
        active = await self.get_active_orchestration(company_name)
        if active:
            logger.warning(f"⚠️ [Orchestration Manager] Rejected duplicate launch for '{company_name}'. Workflow already running.")
            return {
                "status": "duplicate",
                "active_orchestration": active
            }

        # 2. Concurrency Throttle check
        active_count = await self.get_active_count()
        if active_count >= self.concurrency_limit:
            logger.warning(
                f"🚨 [Orchestration Manager] Concurrency limit ({self.concurrency_limit}) reached! "
                f"Active count: {active_count}. Queuing research request for '{company_name}'."
            )
            # Add to a Redis list queue to track waiting items
            if enqueue_if_full:
                await self._enqueue_job(
                    company_name,
                    session_id,
                    industry,
                    custom_query,
                    max_attempts,
                    confidence_threshold
                )
            
            status_payload = {
                "session_id": session_id,
                "status": "queued",
                "company_name": company_name.strip().title(),
                "confidence_score": 0.0,
                "created_at": datetime.utcnow().isoformat(),
                "queued_position": await self.get_queue_size()
            }
            await redis_service.set(keys["status"], status_payload, ttl=self.key_ttl_seconds)
            return {
                "status": "queued",
                "active_orchestration": status_payload
            }

        # 3. Try to acquire the distributed lock
        # Lock expires in 30 minutes to safeguard crashes
        lock_acquired = await redis_service.acquire_lock(keys["lock"], session_id, ttl_seconds=1800)
        if not lock_acquired:
            # Fallback race condition check
            active_race = await self.get_active_orchestration(company_name)
            if active_race:
                return {"status": "duplicate", "active_orchestration": active_race}
            
            return {
                "status": "error",
                "message": "Failed to acquire distributed Redis lock. Please try again."
            }

        # 4. Initialize orchestration state keys in Redis
        status_payload = {
            "session_id": session_id,
            "status": "researching",
            "company_name": company_name.strip().title(),
            "confidence_score": 0.0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        progress_payload = {
            "session_id": session_id,
            "company_name": company_name.strip().title(),
            "nodes_completed": [],
            "last_active_node": "startup",
            "last_updated": datetime.utcnow().isoformat()
        }

        # Save to Redis
        await redis_service.set(keys["status"], status_payload, ttl=self.key_ttl_seconds)
        await redis_service.set(keys["progress"], progress_payload, ttl=self.key_ttl_seconds)
        
        logger.info(f"🚀 [Orchestration Manager] Successfully locked and started pipeline for '{company_name}' (Session: {session_id})")
        
        return {
            "status": "started",
            "active_orchestration": status_payload
        }

    async def update_status(self, company_name: str, new_status: str, confidence_score: float = 0.0) -> bool:
        """Updates the active orchestration status state in Redis."""
        keys = self._get_keys(company_name)
        status_payload = await redis_service.get(keys["status"])
        
        if not status_payload:
            # Create a simple wrapper if not found
            status_payload = {
                "company_name": company_name,
                "created_at": datetime.utcnow().isoformat()
            }
            
        status_payload["status"] = new_status
        status_payload["confidence_score"] = confidence_score
        status_payload["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"📊 [Orchestration Status] '{company_name}' transitioned to: '{new_status}' (Score: {confidence_score:.2f})")
        return await redis_service.set(keys["status"], status_payload, ttl=self.key_ttl_seconds)

    async def update_progress(self, company_name: str, node_name: str, updates: Dict[str, Any]) -> bool:
        """Updates the active workflow node progress registry in Redis."""
        keys = self._get_keys(company_name)
        progress = await redis_service.get(keys["progress"])
        
        if not progress:
            progress = {
                "company_name": company_name,
                "nodes_completed": [],
                "last_active_node": "startup"
            }
            
        if node_name not in progress["nodes_completed"]:
            progress["nodes_completed"].append(node_name)
            
        progress["last_active_node"] = node_name
        progress["last_updated"] = datetime.utcnow().isoformat()
        if updates:
            progress["extra_telemetry"] = {**(progress.get("extra_telemetry") or {}), **updates}
            
        logger.info(f"📈 [Orchestration Progress] '{company_name}' completed node: '{node_name}'")
        return await redis_service.set(keys["progress"], progress, ttl=self.key_ttl_seconds)

    async def complete_orchestration(self, company_name: str, session_id: str, final_status: str = "completed", confidence_score: float = 0.0) -> bool:
        """
        Releases the distributed lock and marks the company orchestration as finalized.
        Optionally triggers next job in queue if available.
        """
        keys = self._get_keys(company_name)
        
        # 1. Update status to terminal
        await self.update_status(company_name, final_status, confidence_score)
        
        # 2. Release distributed lock
        lock_released = await redis_service.release_lock(keys["lock"], session_id)
        
        # 3. Clean up queue if this job was in queue
        await self._dequeue_job(company_name)
        
        # 4. Trigger next queued job
        await self._process_next_in_queue()
        
        logger.info(f"✅ [Orchestration Manager] Finalized corporate pipeline for '{company_name}' (Session: {session_id}, Status: {final_status})")
        return lock_released

    # ==========================================
    # QUEUE & CONCURRENCY CONTROLS
    # ==========================================
    async def get_active_count(self) -> int:
        """Scans and counts all active distributed company locks in Redis."""
        locks = await redis_service.scan_keys("orchestration:*:lock")
        return len(locks)

    async def get_queue_size(self) -> int:
        """Returns the number of jobs waiting in the orchestration list queue."""
        if not redis_service.client:
            await redis_service.initialize()
        try:
            return int(await redis_service._execute_async(redis_service.client.llen, "orchestration:queue"))
        except Exception:
            return 0

    async def _enqueue_job(
        self,
        company_name: str,
        session_id: str,
        industry: str,
        custom_query: str,
        max_attempts: int,
        confidence_threshold: float
    ):
        """Adds a company job metadata onto the waiting list queue."""
        try:
            payload = json.dumps({
                "company_name": company_name,
                "session_id": session_id,
                "industry": industry,
                "custom_query": custom_query,
                "max_attempts": max_attempts,
                "confidence_threshold": confidence_threshold,
                "queued_at": time.time()
            })
            await redis_service._execute_async(redis_service.client.rpush, "orchestration:queue", payload)
        except Exception as e:
            logger.error(f"Failed to enqueue job for '{company_name}': {e}")

    async def _dequeue_job(self, company_name: str):
        """Removes a company job from the waiting queue list if present."""
        try:
            # We fetch all queue items, filter out company_name, and rebuild list
            client = redis_service.client
            items = await redis_service._execute_async(client.lrange, "orchestration:queue", 0, -1)
            
            for item in items:
                data = json.loads(item)
                if data.get("company_name") == company_name:
                    await redis_service._execute_async(client.lrem, "orchestration:queue", 0, item)
                    break
        except Exception as e:
            logger.error(f"Failed to dequeue job for '{company_name}': {e}")

    async def _process_next_in_queue(self):
        """Pulls and launches the next research job waiting in queue."""
        try:
            active_count = await self.get_active_count()
            if active_count >= self.concurrency_limit:
                logger.info(
                    f"⏳ [Orchestration Queue] Active concurrency limit still reached ({active_count}/{self.concurrency_limit}). "
                    f"Delaying queue processing."
                )
                return

            client = redis_service.client
            next_job_payload = await redis_service._execute_async(client.lindex, "orchestration:queue", 0)
            if not next_job_payload:
                return

            job_data = json.loads(next_job_payload)
            company_name = job_data["company_name"]
            session_id = job_data["session_id"]
            industry = job_data.get("industry", "Technology")
            custom_query = job_data.get("custom_query", "")
            max_attempts = job_data.get("max_attempts", 3)
            confidence_threshold = job_data.get("confidence_threshold", 0.85)

            logger.info(f"🔔 [Orchestration Queue] Pulling next job: '{company_name}' (Session: {session_id})")

            # Prefer persisted request metadata, fallback to in-memory session cache for local fallback sessions.
            session_row = await db_service.aget_session(session_id)
            if session_row:
                industry = session_row.get("industry", industry)
                custom_query = session_row.get("custom_query", custom_query)
                max_attempts = session_row.get("max_attempts", max_attempts)
                confidence_threshold = session_row.get("confidence_threshold", confidence_threshold)
            else:
                from app.services.workflow_service import local_sessions_cache
                if session_id in local_sessions_cache:
                    local_session = local_sessions_cache[session_id].get("session", {})
                    industry = local_session.get("industry", industry)
                    custom_query = local_session.get("custom_query", custom_query)

            start_result = await self.start_orchestration(
                session_id=session_id,
                company_name=company_name,
                industry=industry,
                custom_query=custom_query,
                max_attempts=max_attempts,
                confidence_threshold=confidence_threshold,
                enqueue_if_full=False
            )

            if start_result["status"] == "started":
                from app.tasks.research_tasks import run_research_workflow_task
                try:
                    run_research_workflow_task.delay(
                        session_id=session_id,
                        company_name=company_name,
                        industry=industry,
                        custom_query=custom_query,
                        max_attempts=max_attempts,
                        threshold=confidence_threshold
                    )
                    await redis_service._execute_async(client.lpop, "orchestration:queue")
                except Exception as dispatch_err:
                    logger.error(
                        f"❌ [Orchestration Queue] Failed to dispatch queued job for '{company_name}' (Session: {session_id}): {dispatch_err}"
                    )
            elif start_result["status"] == "duplicate":
                logger.warning(
                    f"🔁 [Orchestration Queue] dequeued stale duplicate job for '{company_name}' (Session: {session_id})."
                )
                await redis_service._execute_async(client.lpop, "orchestration:queue")
            else:
                logger.info(
                    f"🔄 [Orchestration Queue] Next job for '{company_name}' remains queued due to limiting conditions."
                )
        except Exception as e:
            logger.error(f"Failed to process next queued orchestration job: {e}")


# Central Orchestration Queue Manager Singleton instance
orchestration_manager = OrchestrationManager()
