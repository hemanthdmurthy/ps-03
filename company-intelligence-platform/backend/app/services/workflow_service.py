import json
import logging
import asyncio
import uuid
from typing import Dict, Any, List
from langsmith import traceable

from app.core.config import settings
from app.core.observability import client as ls_client, TracingHelper
from app.services.db import db_service
from app.services.orchestration_manager import orchestration_manager

# Setup Logging
logger = logging.getLogger("company_intel.workflow_service")

# Active event queues to manage Server-Sent Events (SSE) subscriptions
# session_id -> list of asyncio.Queue
active_streams: Dict[str, List[asyncio.Queue]] = {}

# In-memory session cache for seamless database-less running fallback
local_sessions_cache: Dict[str, Dict[str, Any]] = {}

def publish_event(session_id: str, event_type: str, data: Dict[str, Any]):
    """Pushes a workflow progress event to both local memory and Redis Pub/Sub for worker synchronization."""
    payload = {
        "event": event_type,
        "data": data
    }
    
    # 1. Publish locally in the current process (for local synchronous runs or FastAPI if in same process)
    if session_id in active_streams:
        logger.info(f"[SSE Publish Local] Pushing event '{event_type}' to session {session_id}")
        for q in active_streams[session_id]:
            q.put_nowait(payload)
            
    # 2. Publish to Redis Pub/Sub so that other processes (FastAPI if Celery worker is running this) receive it
    try:
        from app.core.redis_client import redis_client
        r = redis_client.sync_client
        channel = f"company_intel:sse:{session_id}"
        r.publish(channel, json.dumps(payload))
        logger.info(f"[SSE Publish Redis] Published event '{event_type}' to channel {channel}")
    except Exception as e:
        logger.warning(f"Failed to publish event to Redis: {e}")

@traceable(name="Company Research Pipeline", tags=["main-orchestrator", "production"])
async def run_langgraph_workflow(session_id: str, company_name: str, industry: str, custom_query: str, max_attempts: int, threshold: float):
    """
    Asynchronous runner that steps through our compiled LangGraph workflow.
    Publishes real-time state events to active UI streaming connections.
    """
    logger.info(f"Starting LangGraph workflow in background for session: {session_id}")

    # Brief yield to let the event loop process the incoming SSE stream request
    # from the frontend before we start publishing events.  Without this, the
    # first events can fire before the SSE queue is registered in active_streams.
    await asyncio.sleep(0.5)

    # Inject Production Metadata
    TracingHelper.set_standard_metadata(
        company=company_name,
        session_id=session_id,
        stage="Pipeline-Execution",
        extra={
            "industry": industry,
            "max_attempts": max_attempts,
            "threshold": threshold
        }
    )
    TracingHelper.add_tags(["company-research", "perplexity", "langgraph", "production"])

    # Initialize state variables
    initial_state = {
        "session_id": session_id,
        "company_name": company_name,
        "industry": industry,
        "custom_query": custom_query,
        "regeneration_attempts": 0,
        "max_attempts": max_attempts,
        "confidence_threshold": threshold,
        "agent_data": {},
        "agent_status": {},
        "consolidated_profile": {},
        "validation_passed": False,
        "confidence_score": 0.0,
        "failed_fields": [],
        "validation_history": [],
        "final_report": None,
        "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        "errors": []
    }

    # Prepare LangChain/LangSmith configuration
    ls_config = {
        "metadata": {
            "session_id": session_id,
            "company_name": company_name,
            "industry": industry,
            "max_attempts": max_attempts,
            "environment": settings.ENVIRONMENT
        },
        "tags": ["production", "research-pipeline", "company-research"],
        "run_name": f"Research: {company_name}"
    }

    current_state = dict(initial_state)
    try:
        from app.workflow.graph import workflow_graph
        # Step through the graph execution
        async for state_update in workflow_graph.astream(initial_state, config=ls_config, stream_mode="updates"):
            node_name = list(state_update.keys())[0]
            node_values = state_update[node_name] or {}

            logger.info(f"[Graph Stream Update] Completed Node: '{node_name}'")

            # Merge node updates into current state for cache accuracy
            for k, v in node_values.items():
                if isinstance(v, dict) and k in current_state and isinstance(current_state[k], dict):
                    current_state[k] = {**(current_state[k] or {}), **v}
                else:
                    current_state[k] = v

            # Store/update in-memory cache to support seamless database-less running fallback
            local_sessions_cache[session_id] = {
                "session": {
                    "id": session_id,
                    "company_name": current_state.get("company_name", company_name),
                    "industry": current_state.get("industry", industry),
                    "custom_query": current_state.get("custom_query", custom_query),
                    "status": "completed" if current_state.get("final_report") else "researching",
                    "confidence_score": current_state.get("confidence_score", 0.0),
                    "created_at": "2026-05-11T12:00:00Z",
                    "updated_at": "2026-05-11T12:00:00Z"
                },
                "agent_outputs": {
                    agent_name: {
                        "agent_name": agent_name,
                        "status": (current_state.get("agent_status") or {}).get(agent_name, "completed"),
                        "raw_json_output": (current_state.get("agent_data") or {}).get(agent_name, {}),
                        "token_usage": 0
                    }
                    for agent_name in (current_state.get("agent_data") or {})
                },
                "validation_history": current_state.get("validation_history", []),
                "final_report": current_state.get("final_report")
            }

            # Map node completions to semantic frontend progress events and update Redis orchestration progress
            await orchestration_manager.update_progress(
                company_name=company_name,
                node_name=node_name,
                updates={
                    "confidence_score": current_state.get("confidence_score", 0.0),
                    "regeneration_attempts": current_state.get("regeneration_attempts", 0)
                }
            )

            if node_name == "input":
                await orchestration_manager.update_status(company_name, "researching", current_state.get("confidence_score", 0.0))
                publish_event(session_id, "input_normalized", {
                    "company_name": node_values.get("company_name", company_name),
                    "status": "researching"
                })
            elif node_name == "research_agents":
                publish_event(session_id, "research_completed", {
                    "agent_status": node_values.get("agent_status", {}),
                    "token_usage": node_values.get("token_usage", {})
                })
            elif node_name == "consolidation":
                await orchestration_manager.update_status(company_name, "validating", current_state.get("confidence_score", 0.0))
                publish_event(session_id, "consolidation_completed", {
                    "consolidated_profile": node_values.get("consolidated_profile", {}),
                    "status": "validating"
                })
            elif node_name == "validation":
                publish_event(session_id, "validation_completed", {
                    "validation_passed": node_values.get("validation_passed", False),
                    "confidence_score": node_values.get("confidence_score", 0.0),
                    "failed_fields": node_values.get("failed_fields", []),
                    "validation_history": node_values.get("validation_history", [])
                })
            elif node_name == "regeneration":
                await orchestration_manager.update_status(company_name, "regenerating", current_state.get("confidence_score", 0.0))
                publish_event(session_id, "regeneration_triggered", {
                    "regeneration_attempts": node_values.get("regeneration_attempts", 1),
                    "status": "regenerating"
                })
            elif node_name == "final_output":
                publish_event(session_id, "report_compiled", {
                    "final_report": node_values.get("final_report", {})
                })
            elif node_name == "supabase_storage":
                publish_event(session_id, "storage_completed", {
                    "status": "completed"
                })

        # Release the distributed lock and update final status in Redis
        await orchestration_manager.complete_orchestration(
            company_name=company_name,
            session_id=session_id,
            final_status="completed",
            confidence_score=current_state.get("confidence_score", 0.0)
        )
        publish_event(session_id, "workflow_ended", {"status": "completed"})

    except Exception as exc:
        logger.error(f"Error executing LangGraph background workflow: {exc}", exc_info=True)
        try:
            db_service.update_session(session_id, {"status": "failed"})
        except Exception:
            pass
            
        # Release the lock on failure
        await orchestration_manager.complete_orchestration(
            company_name=company_name,
            session_id=session_id,
            final_status="failed",
            confidence_score=current_state.get("confidence_score", 0.0)
        )
        publish_event(session_id, "workflow_failed", {"error": str(exc)})

