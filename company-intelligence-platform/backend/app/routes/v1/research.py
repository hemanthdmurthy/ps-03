import json
import logging
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any

from app.services.db import db_service
from app.schemas.research import ResearchRequest
from app.services.orchestration_manager import orchestration_manager
from app.services.workflow_service import (
    run_langgraph_workflow,
    local_sessions_cache,
    active_streams
)

# Setup Logging
logger = logging.getLogger("company_intel.routes.research")

router = APIRouter()

@router.post("/research", tags=["Research"])
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Submits a new corporate target. Spins up the background worker
    orchestration and returns the generated UUID session_id immediately.
    Guarantees duplicate request prevention and concurrency control.
    """
    from app.services.redis_service import redis_service
    
    # Assert Redis circuit breaker health before launching orchestration
    if redis_service.circuit_breaker.state == "OPEN" or not redis_service.circuit_breaker.allow_request():
        logger.error("[Orchestration Pause] Rejected research request: Redis Circuit Breaker is OPEN.")
        raise HTTPException(
            status_code=503,
            detail="Orchestration engine is temporarily paused due to cache/broker connectivity issues. Please try again later."
        )

    company_name = request.company_name.strip()
    
    try:
        # 1. Check if same company orchestration already running
        active = await orchestration_manager.get_active_orchestration(company_name)
        if active:
            logger.info(f"[Orchestration Deduplication] Request for '{company_name}' bypassed. Returning active status response.")
            return {
                "session_id": active.get("session_id"),
                "status": active.get("status"),
                "company_name": active.get("company_name", company_name.title()),
                "confidence_score": active.get("confidence_score", 0.0),
                "created_at": active.get("created_at")
            }

        # 2. Register session in database first to obtain UUID (async)
        try:
            session_row = await db_service.acreate_session(
                company_name.title(),
                request.industry,
                request.custom_query
            )
            session_id = session_row["id"]
            logger.info(f"Successfully registered session in remote database with ID: {session_id}")
        except Exception as db_exc:
            session_id = f"local-{uuid.uuid4()}"
            logger.warning(f"Database session creation failed; using local fallback session ID: {session_id}. Error: {db_exc}")

        # Pre-populate local cache for database-less execution support
        local_sessions_cache[session_id] = {
            "session": {
                "id": session_id,
                "company_name": company_name.title(),
                "industry": request.industry,
                "custom_query": request.custom_query,
                "status": "researching",
                "confidence_score": 0.0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            "agent_outputs": {},
            "validation_history": [],
            "final_report": None
        }

        # 3. Request Orchestration Manager to initialize states and locks
        result = await orchestration_manager.start_orchestration(
            session_id=session_id,
            company_name=company_name,
            industry=request.industry,
            custom_query=request.custom_query,
            max_attempts=request.max_attempts,
            confidence_threshold=request.confidence_threshold
        )

        if result["status"] == "duplicate":
            # Active job found under race condition
            active_race = result["active_orchestration"]
            return {
                "session_id": active_race.get("session_id"),
                "status": active_race.get("status"),
                "company_name": active_race.get("company_name", company_name.title()),
                "confidence_score": active_race.get("confidence_score", 0.0),
                "created_at": active_race.get("created_at")
            }

        if result["status"] == "queued":
            # Concurrent threshold exceeded; request queued
            active_queue = result["active_orchestration"]
            logger.info(f"[Orchestration Queue] Enqueued '{company_name}' in spot {active_queue.get('queued_position')}")
            return {
                "session_id": session_id,
                "status": "queued",
                "company_name": company_name.title(),
                "confidence_score": 0.0,
                "created_at": active_queue.get("created_at")
            }

        # 4. Deploy workflow: prefer Celery worker, fall back to in-process background task
        celery_dispatched = False
        try:
            from app.core.redis_client import redis_client
            if not redis_client.is_fallback:
                from app.tasks.research_tasks import run_research_workflow_task
                run_research_workflow_task.delay(
                    session_id=session_id,
                    company_name=company_name,
                    industry=request.industry,
                    custom_query=request.custom_query,
                    max_attempts=request.max_attempts,
                    threshold=request.confidence_threshold
                )
                celery_dispatched = True
                logger.info(f"[Celery Dispatch] Research workflow dispatched to Celery worker for '{company_name}'")
        except Exception as celery_err:
            logger.warning(f"[Celery Dispatch Failed] {celery_err}. Will fall back to in-process execution.")

        if not celery_dispatched:
            # Celery/broker unavailable — run the async workflow directly inside
            # the FastAPI process so SSE events flow through local memory queues.
            logger.info(f"[In-Process Fallback] Running research workflow as FastAPI background task for '{company_name}'")
            background_tasks.add_task(
                run_langgraph_workflow,
                session_id=session_id,
                company_name=company_name,
                industry=request.industry,
                custom_query=request.custom_query,
                max_attempts=request.max_attempts,
                threshold=request.confidence_threshold
            )

        dispatch_mode = "celery" if celery_dispatched else "in-process"
        return {
            "session_id": session_id,
            "status": "initiated",
            "message": f"Orchestrator launched research pipeline for '{company_name}' ({dispatch_mode})."
        }

    except Exception as e:
        logger.error(f"Failed to submit research query: {e}")
        raise HTTPException(status_code=500, detail=f"Database or orchestration manager initialization failure: {str(e)}")

@router.get("/session/{session_id}", tags=["Research"])
async def get_session_details(session_id: str):
    """
    Returns complete detailed history, validation logs, raw intermediate
    outputs, and compiled profile reports for a session ID.
    """
    try:
        data = await db_service.aget_full_session_data(session_id)
        if data:
            if not data.get("agent_outputs") and session_id in local_sessions_cache:
                data["agent_outputs"] = local_sessions_cache[session_id].get("agent_outputs", {})
            return data
    except Exception as db_exc:
        logger.error(f"Failed to fetch session {session_id} details from database: {db_exc}")

    # Fallback to local in-memory session cache if DB query fails or tables don't exist
    if session_id in local_sessions_cache:
        logger.info(f"Serving session details from in-memory fallback cache for session: {session_id}")
        return local_sessions_cache[session_id]

    raise HTTPException(status_code=404, detail="Session ID not found in remote database or local fallback cache.")

@router.get("/session/{session_id}/parameters", tags=["Research"])
async def get_session_parameters(session_id: str):
    """
    Dynamically fetches the first row of the staging_company table,
    reads all column headers as the live schema, compares against
    domain parameter definitions, and renders live data.
    """
    from app.workflow.parameters import get_domain_allocation, MASTER_PARAMETERS, is_valid_value

    logger.info(f"Fetching dynamic schema parameters for session: {session_id}")

    # 1. Fetch the first row from staging_company (async)
    companies = await db_service.aget_all_companies()
    if not companies:
        raise HTTPException(status_code=404, detail="No data in staging_company")

    first_row = companies[0]

    company_name = None
    try:
        data = await db_service.aget_full_session_data(session_id)
        if data and "session" in data and data["session"]:
            company_name = data["session"].get("company_name")
    except Exception as e:
        logger.warning(f"Could not fetch session from DB: {e}")

    if not company_name and session_id in local_sessions_cache:
        company_name = local_sessions_cache[session_id].get("session", {}).get("company_name")

    def merge_allocated_parameters(row: dict) -> dict:
        if not row:
            return row
        allocated = row.get("allocated_parameters")
        if isinstance(allocated, dict):
            valid_allocated = {
                k: v for k, v in allocated.items() if is_valid_value(v)
            }
            merged = {**row, **valid_allocated}
            if not merged.get("company_name") and merged.get("name"):
                merged["company_name"] = merged["name"]
            return merged
        # For non-dict allocated_parameters, just ensure company_name is set
        if not row.get("company_name") and row.get("name"):
            row["company_name"] = row["name"]
        return row

    first_row = merge_allocated_parameters(first_row)

    if company_name:
        specific_record = await db_service.aget_company_by_name(company_name)
        if specific_record:
            first_row = merge_allocated_parameters(specific_record)
            logger.info(f"[DEBUG LOG] Found specific record for {company_name}")

    # If allocated_parameters JSON is empty, attempt to rescue values from agent_outputs
    session_data = {}
    try:
        session_data = await db_service.aget_full_session_data(session_id) or {}
    except Exception as e:
        logger.warning(f"Could not fetch session data from DB for agent merge: {e}")

    if not session_data and session_id in local_sessions_cache:
        session_data = local_sessions_cache[session_id]

    try:
        agent_outputs = session_data.get("agent_outputs") if isinstance(session_data, dict) else None
        if agent_outputs:
            # For each agent, merge raw_json_output keys into first_row when missing
            for agent_name, out in agent_outputs.items():
                raw = out.get("raw_json_output") if isinstance(out, dict) else None
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        # Only merge recognized MASTER_PARAMETERS, only if incoming value is valid, 
                        # and only when row lacks a valid value
                        if k in MASTER_PARAMETERS and is_valid_value(v) and not is_valid_value(first_row.get(k)):
                            first_row[k] = v
    except Exception as e:
        logger.debug(f"Could not merge agent outputs for session {session_id}: {e}")

    # 2. Reusing SHARED ALLOCATION LOGIC from orchestration layer
    enriched_domains = get_domain_allocation(first_row)

    return {
        "metadata": {
            "company_name": first_row.get("name", first_row.get("company_name", "Unknown")),
            "extraction_timestamp": "2026-05-14T00:00:00Z",
            "pipeline_version": "Schema-Driven-1.2",
            "total_columns_processed": len(first_row)
        },
        "domains": enriched_domains
    }

@router.get("/session/{session_id}/stream", tags=["Research"])
async def stream_session_events(session_id: str):
    """
    Server-Sent Events (SSE) router that allows the React UI to connect and listen
    to active graph nodes, completed tasks, and regeneration statuses in real-time.
    Uses Redis Pub/Sub to synchronize progress updates from asynchronous Celery background workers.
    """
    logger.info(f"[SSE Subscribe] Client subscribing to stream for session: {session_id}")

    async def event_generator():
        yield f"data: {json.dumps({'event': 'connected', 'data': {'session_id': session_id}})}\n\n"

        # Determine if we should use Redis Pub/Sub or local in-memory queues.
        # FakeRedis fallback does not reliably bridge sync publish → async subscribe,
        # so we must skip straight to local queues when the broker is not real Redis.
        use_redis_pubsub = False
        try:
            from app.core.redis_client import redis_client
            use_redis_pubsub = not redis_client.is_fallback
        except Exception:
            pass

        if use_redis_pubsub:
            # 1. Primary path: Stream via Redis Pub/Sub to support distributed Celery workers
            try:
                from app.core.redis_client import redis_client
                
                # Use the shared resilient client pool
                client = redis_client.client
                pubsub = client.pubsub()
                channel = f"company_intel:sse:{session_id}"
                await pubsub.subscribe(channel)
                
                logger.info(f"[SSE Redis Subscribe] Subscribed to Redis channel: {channel}")
                
                try:
                    while True:
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if message:
                            data_str = message["data"]
                            event_data = json.loads(data_str)
                            yield f"data: {data_str}\n\n"
                            
                            if event_data.get("event") in ("workflow_ended", "workflow_failed", "storage_completed"):
                                logger.info(f"[SSE Redis Subscribe] Terminal event received: {event_data['event']}. Closing stream.")
                                break
                        await asyncio.sleep(0.1)
                finally:
                    if pubsub:
                        await pubsub.unsubscribe(channel)
                        await pubsub.close()
                return  # Redis path completed; don't fall through
            except Exception as redis_exc:
                logger.warning(f"[SSE Fallback] Redis subscription failed ({redis_exc}); falling back to local memory queue.")

        # 2. Fallback path: Local in-memory queue (used when Redis is FakeRedis or unavailable)
        logger.info(f"[SSE Local Subscribe] Using in-process memory queue for session: {session_id}")
        queue = asyncio.Queue()
        if session_id not in active_streams:
            active_streams[session_id] = []
        active_streams[session_id].append(queue)
        
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"

                if event["event"] in ("workflow_ended", "workflow_failed", "storage_completed"):
                    break
        except asyncio.CancelledError:
            logger.info(f"[SSE Local Unsubscribe] Client canceled subscription for session: {session_id}")
        finally:
            if session_id in active_streams:
                if queue in active_streams[session_id]:
                    active_streams[session_id].remove(queue)
                if not active_streams[session_id]:
                    del active_streams[session_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/session/{session_id}/allocated_parameters", tags=["Research"]) 
async def get_session_allocated_parameters(session_id: str):
    """Returns the persisted `allocated_parameters` JSON for the company associated with the session.
    This helps debug and review the full consolidated 163-key profile persisted into `staging_company.allocated_parameters`.
    """
    logger.info(f"[API] Fetching allocated_parameters for session: {session_id}")
    try:
        # 1. Try to resolve company name from persisted session row
        data = {}
        try:
            data = await db_service.aget_full_session_data(session_id)
        except Exception:
            data = {}

        company_name = None
        if data and data.get("session"):
            company_name = data["session"].get("company_name")

        # 2. Fallback to in-memory session cache when DB is not available
        if not company_name and session_id in local_sessions_cache:
            company_name = local_sessions_cache[session_id].get("session", {}).get("company_name")

        if not company_name:
            return {"allocated_parameters": None, "message": "Company name not found for session."}

        # 3. Fetch company row from staging table and return JSON column
        company_row = await db_service.aget_company_by_name(company_name)
        if not company_row:
            return {"allocated_parameters": None, "message": "Company row not found in staging_company."}

        return {"allocated_parameters": company_row.get("allocated_parameters")}
    except Exception as e:
        logger.error(f"Failed to fetch allocated_parameters for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{company_name}/allocated_parameters", tags=["Research"])
async def get_company_allocated_parameters(company_name: str):
    """Direct lookup of `allocated_parameters` by company name (staging_company table).
    """
    try:
        company_row = await db_service.aget_company_by_name(company_name)
        if not company_row:
            raise HTTPException(status_code=404, detail="Company not found")
        return {"allocated_parameters": company_row.get("allocated_parameters")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch allocated_parameters for company {company_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
