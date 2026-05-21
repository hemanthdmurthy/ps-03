import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from langchain_core.messages import HumanMessage, AIMessage

from app.graphs.placement_graph import placement_graph
from app.core.config import settings

logger = logging.getLogger("company_intel.routes.ai")

router = APIRouter(tags=["Placement AI Agent"])

@router.get("/placement-agent/health", response_model=Dict[str, Any])
async def ai_agent_health():
    """
    Checks the status of the AI agent workflow and its LLM connectivity.
    """
    logger.info("[AI Route] Processing GET /health")
    from app.services.llm_service import llm_service
    
    llm_connected = False
    try:
        # Run a small sanity check
        llm = llm_service.get_llm()
        if llm:
            llm_connected = True
    except Exception as e:
        logger.error(f"[AI Route] Health check LLM connection failed: {e}")

    return {
        "status": "healthy",
        "agent": "Placement Intelligence Agent Workflow",
        "timestamp": time.time(),
        "provider": settings.MODEL_PROVIDER,
        "model": settings.MODEL_NAME,
        "llm_connected": llm_connected
    }

@router.post("/placement-agent/invoke", response_model=Dict[str, Any])
async def invoke_agent(payload: Dict[str, Any]):
    """
    Custom wrapper to invoke the Placement Agent directly and return a
    structured JSON response with metadata, model details, and token usage.
    """
    logger.info("[AI Route] Processing POST /placement-agent/invoke")
    
    user_message = payload.get("message")
    if not user_message:
        raise HTTPException(status_code=400, detail="Missing required field: 'message'")

    session_id = payload.get("session_id", "default-session")
    
    # Construct state matching PlacementState
    inputs = {
        "messages": [HumanMessage(content=user_message)],
        "metadata": {
            "session_id": session_id,
            "source": "api_invoke",
            "request_timestamp": time.time()
        }
    }

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    try:
        start_time = time.time()
        # Execute the compiled LangGraph workflow asynchronously
        result = await placement_graph.ainvoke(inputs, config=config)
        latency_ms = int((time.time() - start_time) * 1000)

        # Extract last AIMessage content
        last_msg = result["messages"][-1]
        response_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        logger.info(f"[AI Route] Graph invocation completed in {latency_ms}ms with agent: {result.get('selected_agent')}")

        return {
            "success": True,
            "data": {
                "message": response_text,
                "selected_agent": result.get("selected_agent", "general"),
                "chat_history_length": len(result.get("messages", []))
            },
            "model_info": {
                "provider": result.get("provider", settings.MODEL_PROVIDER),
                "model_name": result.get("model_name", settings.MODEL_NAME)
            },
            "token_usage": result.get("token_usage", {}),
            "meta": {
                "session_id": session_id,
                "latency_ms": latency_ms,
                "timestamp": time.time()
            }
        }

    except Exception as e:
        logger.error(f"[AI Route] Error in invoke_agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Placement agent invocation failed: {str(e)}"
        )

@router.post("/placement-agent/stream")
async def stream_agent(payload: Dict[str, Any]):
    """
    Placeholder endpoint for streaming. The standard SSE/streaming routes are
    fully managed and exposed natively by LangServe on '/placement-agent/stream'.
    """
    logger.info("[AI Route] POST /placement-agent/stream was redirected to LangServe")
    raise HTTPException(
        status_code=501,
        detail="Streaming should be accessed via the standard LangServe mount: '/placement-agent/stream'."
    )

@router.post("/placement-agent/batch")
async def batch_agent(payload: Dict[str, Any]):
    """
    Placeholder endpoint for batch processing. The standard batch routes are
    fully managed and exposed natively by LangServe on '/placement-agent/batch'.
    """
    logger.info("[AI Route] POST /placement-agent/batch was redirected to LangServe")
    raise HTTPException(
        status_code=501,
        detail="Batch execution should be accessed via the standard LangServe mount: '/placement-agent/batch'."
    )
