import json
import asyncio
import time
import logging
import os
import re
import traceback
from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig
from langsmith import traceable
import langsmith as ls
from app.core.observability import client as ls_client

def get_safe_loop():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

from app.workflow.state import ResearchState
from app.workflow.parameters import MASTER_PARAMETERS, DOMAIN_MAPPING, get_domain_allocation, is_valid_value
from app.services.db import db_service
from app.agents.specialized_agents import (
    WebsiteResearchAgent,
    LinkedInResearchAgent,
    NewsResearchAgent,
    FundingInvestorAgent,
    ProductResearchAgent,
    SocialMediaAgent
)
from app.agents.base_agent import BaseResearchAgent

logger = logging.getLogger("company_intel.nodes")

async def run_in_executor(func, *args, **kwargs):
    """Utility to run synchronous blocking functions in a thread pool executor."""
    loop = get_safe_loop()
    if kwargs:
        from functools import partial
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))
    return await loop.run_in_executor(None, func, *args)

def update_token_metadata(state: ResearchState, node_name: str, metrics: Dict[str, Any], retry_count: int = 0):
    """
    Central helper to update structured token accounting in state and push to LangSmith.
    """
    token_usage = state.get("token_usage", {})
    if not isinstance(token_usage, dict) or "total" not in token_usage:
        # Initialize if flat or empty
        token_usage = {
            "total": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
            "by_node": {},
            "by_model": {},
            "by_retry": {}
        }

    prompt = metrics.get("prompt_tokens", 0)
    completion = metrics.get("completion_tokens", 0)
    total = metrics.get("total_tokens", 0)
    cost = metrics.get("estimated_cost", 0.0)
    model = metrics.get("model_name", "unknown")

    # Update Global Total
    token_usage["total"]["prompt"] += prompt
    token_usage["total"]["completion"] += completion
    token_usage["total"]["total"] += total
    token_usage["total"]["cost"] += cost

    # Update By Node
    if node_name not in token_usage["by_node"]:
        token_usage["by_node"][node_name] = {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0}
    token_usage["by_node"][node_name]["prompt"] += prompt
    token_usage["by_node"][node_name]["completion"] += completion
    token_usage["by_node"][node_name]["total"] += total
    token_usage["by_node"][node_name]["cost"] += cost

    # Update By Model
    if model not in token_usage["by_model"]:
        token_usage["by_model"][model] = {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0}
    token_usage["by_model"][model]["prompt"] += prompt
    token_usage["by_model"][model]["completion"] += completion
    token_usage["by_model"][model]["total"] += total
    token_usage["by_model"][model]["cost"] += cost

    # Update By Retry
    retry_key = str(retry_count)
    if retry_key not in token_usage["by_retry"]:
        token_usage["by_retry"][retry_key] = {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0}
    token_usage["by_retry"][retry_key]["prompt"] += prompt
    token_usage["by_retry"][retry_key]["completion"] += completion
    token_usage["by_retry"][retry_key]["total"] += total
    token_usage["by_retry"][retry_key]["cost"] += cost

    # Sync with LangSmith tags/metadata
    TracingHelper.set_standard_metadata(
        extra={
            "total_tokens": token_usage["total"]["total"],
            "total_cost": round(token_usage["total"]["cost"], 6),
            "retry_index": retry_count
        }
    )

    return token_usage

def update_field_observability(state: ResearchState, field_name: str, updates: Dict[str, Any]):
    """Helper to update field-level metadata in state."""
    obs = state.get("field_observability", {})
    if field_name not in obs:
        obs[field_name] = {
            "generated_value": None,
            "source_llm": None,
            "validation_status": "pending",
            "retry_count": 0,
            "confidence_score": 0.0,
            "final_consolidated_value": None,
            "validation_failure_reason": None,
            "repair_attempts": 0,
            "timestamp_history": [],
            "trace_lineage": []
        }

    # Update fields
    for k, v in updates.items():
        if k == "timestamp_history":
            obs[field_name]["timestamp_history"].append(v)
        elif k == "trace_lineage":
            if v not in obs[field_name]["trace_lineage"]:
                obs[field_name]["trace_lineage"].append(v)
        else:
            obs[field_name][k] = v

    return obs



from app.core.observability import TracingHelper

logger = logging.getLogger("company_intel.nodes")

# ═══════════════════════════════════════════════════════════════════════════
# WORKFLOW NODES
# ═══════════════════════════════════════════════════════════════════════════

@traceable(name="Input Processing", tags=["workflow-entry", "normalization"])
async def input_node(state: ResearchState) -> Dict[str, Any]:
    logger.info(" [Node: Input Node] Starting Session Initialization ")

    # Inject Production Metadata
    TracingHelper.set_standard_metadata(
        company=state.get("company_name"),
        session_id=state.get("session_id"),
        stage="Input-Normalization",
        extra={"industry": state.get("industry")}
    )
    TracingHelper.add_tags(["company-research", "production"])

    workflow_start_time = time.time()
    company = (state.get("company_name") or "").strip()
    industry = (state.get("industry") or "Technology").strip()
    custom_q = (state.get("custom_query") or "").strip()

    # Normalize input
    normalized_company = company.title()
    logger.info(f"Normalized company name to: '{normalized_company}' in industry: '{industry}'")

    # Register/Update session in Supabase DB
    session_id = state.get("session_id")
    try:
        if not session_id:
            session_row = await run_in_executor(
                db_service.create_session,
                company_name=normalized_company,
                industry=industry,
                custom_query=custom_q
            )
            session_id = session_row["id"]
            logger.info(f"Registered new Supabase research session with ID: {session_id}")
        else:
            await run_in_executor(db_service.update_session, session_id, {"status": "researching"})
            logger.info(f"Resumed research session: {session_id}")
    except Exception as e:
        logger.error(f"Failed to record session in Supabase: {e}")
        if not session_id:
            session_id = "temp-local-session-id"

    #  PHASE 8: DOMAIN PARAMETER ALLOCATION
    # Extract parameters ONLY from the FIRST ROW of staging_company
    logger.info("[PHASE 8] Executing standardized domain parameter allocation...")

    # 1. Fetch the first row from staging_company to establish schema and potential data
    all_companies = await run_in_executor(db_service.get_all_companies)
    if not all_companies:
        logger.error("[PHASE 8] Critical Failure: No data in staging_company. Schema consistency cannot be verified.")
        raise ValueError("Database Initialization Error: staging_company is empty.")

    first_row = all_companies[0]

    # 2. Check for specific company record
    company_row = await run_in_executor(db_service.get_company_by_name, normalized_company)
    target_row = company_row if company_row else {}

    # 3. REUSE SAME parameter extraction and domain bifurcation logic
    # Extract parameters ONLY from the FIRST ROW of staging_company
    domain_allocation = get_domain_allocation(first_row)

    # 4. LOG Domain Allocations in required JSON format
    for domain_name, data in domain_allocation.items():
        logger.info(f"[DOMAIN ALLOCATION LOG] {json.dumps({'domain': domain_name, 'allocated_parameters': list(data['parameters'].keys())})}")

    # 5. PRE-ORCHESTRATION VALIDATION
    validation_errors = []
    extracted_params = list(first_row.keys())

    # verify extracted parameters & no orphan parameters
    orphan_params = [p for p in extracted_params if p not in MASTER_PARAMETERS and p not in ["staging_id", "company_id", "id", "created_at", "updated_at", "name", "short_name", "inserted_at", "processed_at", "processing_status", "error_message", "category"]]
    if orphan_params:
        logger.warning(f"[VALIDATION] Orphan parameters detected in staging_company: {orphan_params}")

    # verify domain allocations (handled by get_domain_allocation mapping to all 6 domains)
    # verify no duplicate mappings (handled by dict keys)

    # verify schema consistency
    missing_from_db = [p for p in MASTER_PARAMETERS.keys() if p not in extracted_params and p != "company_name"]
    if missing_from_db:
        logger.warning(f"[VALIDATION] Parameters missing from staging_company schema: {missing_from_db}")

    # 6. Populate Consolidated Profile using EXACT parameter names (No Aliases)
    consolidated_profile = {p: None for p in MASTER_PARAMETERS}
    already_researched = False

    # If we found a specific company record, check if it's "complete"
    if company_row:
        # Extract values using EXACT names
        extracted_values = {p: target_row.get(p) for p in MASTER_PARAMETERS if is_valid_value(target_row.get(p))}

        # Handle field mapping: 'name' (DB) -> 'company_name' (MASTER)
        if is_valid_value(target_row.get("name")) and not extracted_values.get("company_name"):
            extracted_values["company_name"] = target_row.get("name")

        consolidated_profile.update(extracted_values)

        # Determine if already researched based on critical field coverage
        # Ensure exact MASTER_PARAMETERS keys
        critical_fields = ["founder_or_ceo", "headquarters_city", "approximate_headcount", "total_capital_raised"]
        valid_critical = [p for p in critical_fields if is_valid_value(consolidated_profile.get(p))]

        if len(valid_critical) == len(critical_fields):
            logger.info(f"[PHASE 8] Found existing complete record for '{normalized_company}' in staging_company. Bypassing agents.")
            already_researched = True
        else:
            logger.info(f"[PHASE 8] Existing record for '{normalized_company}' in staging_company is incomplete. Triggering research.")

    return {
        "session_id": session_id,
        "company_name": normalized_company,
        "regeneration_attempts": 0,
        "max_attempts": state.get("max_attempts", 3),
        "confidence_threshold": state.get("confidence_threshold", 0.85),
        "agent_data": {},
        "agent_status": {agent: ("completed" if already_researched else "pending") for agent in DOMAIN_MAPPING.keys()},
        "validation_history": [],
        "token_usage": {
            "total": {"prompt": 0, "completion": 0, "total": 0, "cost": 0.0},
            "by_node": {},
            "by_model": {},
            "by_retry": {}
        },
        "errors": [],
        "already_researched": already_researched,
        "consolidated_profile": consolidated_profile,
        "validation_passed": already_researched,
        "confidence_score": 1.0 if already_researched else 0.0,
        "conflicting_parameters": [],
        "missing_parameters": [],
        "field_observability": {
            param: {
                "generated_value": None,
                "source_llm": None,
                "validation_status": "passed" if already_researched else "pending",
                "retry_count": 0,
                "confidence_score": 1.0 if already_researched else 0.0,
                "final_consolidated_value": consolidated_profile.get(param) if already_researched else None,
                "validation_failure_reason": None,
                "repair_attempts": 0,
                "timestamp_history": [get_safe_loop().time()] if already_researched else [],
                "trace_lineage": ["database"] if already_researched else []
            } for param in MASTER_PARAMETERS
        },
        "performance_metrics": {
            "workflow_start_time": workflow_start_time,
            "node_latencies": {},
            "slowest_llm_responses": []
        },
        "error_observability": {
            "validation_failures": [],
            "retry_triggers": [],
            "api_failures": [],
            "timeout_issues": [],
            "schema_mismatches": missing_from_db,
            "parameter_mapping_failures": orphan_params,
            "consolidation_conflicts": [],
            "hallucinated_outputs": []
        }
    }


#
# 2. PARALLEL RESEARCH AGENTS NODE
#
@traceable(name="Parallel Research Orchestrator", tags=["parallel-execution", "multi-agent"])
async def research_agents_node(state: ResearchState, config: RunnableConfig) -> Dict[str, Any]:
    logger.info(" [Node: Parallel Research Agents] Executing Concurrent Agents ")

    # Inject Production Metadata
    TracingHelper.set_standard_metadata(
        company=state.get("company_name"),
        session_id=state.get("session_id"),
        stage="Parallel-Research",
        extra={"agent_count": 6}
    )
    TracingHelper.add_tags(["company-research", "agent-orchestration"])
    if state.get("already_researched"):
        logger.info("[Switch-to-Live] Bypassing concurrent research agents execution.")
        return {}
    session_id = state["session_id"]
    company = state["company_name"]
    custom_q = state.get("custom_query") or ""

    node_start_time = time.time()
    perf_metrics = state.get("performance_metrics", {})
    err_obs = state.get("error_observability", {})

    if "node_latencies" not in perf_metrics:
        perf_metrics["node_latencies"] = {}
    if "agent_latencies" not in perf_metrics["node_latencies"]:
        perf_metrics["node_latencies"]["agent_latencies"] = {}

    # Initialize agents
    agents = {
        "website": WebsiteResearchAgent(),
        "linkedin": LinkedInResearchAgent(),
        "news": NewsResearchAgent(),
        "funding": FundingInvestorAgent(),
        "product": ProductResearchAgent(),
        "social": SocialMediaAgent()
    }

    # Determine which agents should run
    # If this is a regeneration loop, we only re-run agents associated with failed fields
    failed_fields = state.get("failed_fields", [])
    regeneration_mode = state.get("regeneration_attempts", 0) > 0

    agents_to_run = list(agents.keys())
    if regeneration_mode and failed_fields:
        # Determine mapping: which failed fields belong to which agents
        agents_to_run_set = set()
        for field in failed_fields:
            if field in MASTER_PARAMETERS:
                agents_to_run_set.add(MASTER_PARAMETERS[field]["agent"])
        agents_to_run = list(agents_to_run_set)

        # If mapping is empty for some reason, run all
        if not agents_to_run:
            agents_to_run = list(agents.keys())

        logger.info(f"Regeneration Mode enabled. Re-triggering subset of agents: {agents_to_run}")

    # Build execution status list and local accumulators
    updated_status = dict(state.get("agent_status", {}))
    for a in agents_to_run:
        updated_status[a] = "running"

    accumulated_data = dict(state.get("agent_data", {}))
    # Structured token tracking
    current_tokens = dict(state.get("token_usage", {}))

    # Publish initial running statuses
    try:
        from app.services.workflow_service import publish_event
        publish_event(session_id, "agent_status_updated", {
            "agent_status": updated_status,
            "token_usage": {
                "input_tokens": current_tokens.get("total", {}).get("prompt", 0),
                "output_tokens": current_tokens.get("total", {}).get("completion", 0),
                "total_tokens": current_tokens.get("total", {}).get("total", 0)
            }
        })
    except Exception as e:
        logger.error(f"Error publishing initial agent statuses: {e}")

    async def run_agent_worker(agent_name: str, agent_obj: Any) -> Dict[str, Any]:
        # Requirement: Explicitly reference nonlocal state to avoid UnboundLocalError
        nonlocal current_tokens, accumulated_data, updated_status

        logger.info(f"Launching Agent Task: [{agent_name}]")
        agent_start_time = time.time()
        # Run inside thread pool to avoid blocking the main async loop on LLM/scrapers
        loop = get_safe_loop()
        # Prepare a custom config to pass retry_count down to agents
        agent_config = dict(config) if config else {}
        agent_config["retry_count"] = state.get("regeneration_attempts", 0)

        try:
            result = await run_in_executor(
                agent_obj.research_company, company, custom_q, config=agent_config
            )
            # Store in Supabase asynchronously in thread pool
            try:
                await run_in_executor(
                    db_service.upsert_agent_output,
                    session_id=session_id,
                    agent_name=agent_name,
                    status="completed",
                    raw_json=result["data"],
                    token_usage=result["tokens"]["total_tokens"]
                )
            except Exception as e:
                logger.error(f"Error saving {agent_name} output to Supabase: {e}")

            # Update accumulators
            accumulated_data[agent_name] = result["data"]
            agent_duration = time.time() - agent_start_time
            perf_metrics["node_latencies"]["agent_latencies"][agent_name] = agent_duration

            # Update structured token state
            current_tokens = update_token_metadata(
                state={"token_usage": current_tokens},
                node_name="research_agents",
                metrics=result.get("metrics", {}),
                retry_count=state.get("regeneration_attempts", 0)
            )
            updated_status[agent_name] = "completed"

            # --- Field-Level Observability ---
            timestamp = time.time()
            metrics = result.get("metrics", {})
            source_llm = metrics.get("model_name", "unknown")

            obs = state.get("field_observability", {})
            for field, value in result["data"].items():
                if field in MASTER_PARAMETERS:
                    update_field_observability(state, field, {
                        "generated_value": value,
                        "source_llm": source_llm,
                        "timestamp_history": timestamp,
                        "trace_lineage": agent_name,
                        "retry_count": state.get("regeneration_attempts", 0)
                    })

            # Publish real-time completed status & accumulated tokens
            try:
                from app.services.workflow_service import publish_event
                publish_event(session_id, "agent_status_updated", {
                    "agent_status": updated_status,
                    "token_usage": {
                        "input_tokens": current_tokens.get("total", {}).get("prompt", 0),
                        "output_tokens": current_tokens.get("total", {}).get("completion", 0),
                        "total_tokens": current_tokens.get("total", {}).get("total", 0)
                    }
                })
            except Exception as e:
                logger.error(f"Error publishing progress for completed {agent_name}: {e}")

            # Log detailed token usage for analytics
            try:
                metrics = result.get("metrics", {})
                await run_in_executor(
                    db_service.insert_token_log,
                    {
                        "session_id": session_id,
                        "company_name": company,
                        "workflow_name": "Research Pipeline",
                        "domain_name": agent_name,
                        "model_name": metrics.get("model_name", "unknown"),
                        "prompt_tokens": metrics.get("prompt_tokens", 0),
                        "completion_tokens": metrics.get("completion_tokens", 0),
                        "total_tokens": metrics.get("total_tokens", 0),
                        "estimated_cost": metrics.get("estimated_cost", 0.0),
                        "execution_time_ms": metrics.get("execution_time_ms", 0)
                    }
                )
            except Exception as e:
                logger.error(f"Error logging detailed token usage for {agent_name}: {e}")

            return {"name": agent_name, "status": "completed", "data": result["data"], "tokens": result["tokens"]}
        except TimeoutError as exc:
            logger.error(f"Agent Task Timeout: [{agent_name}] due to: {exc}")
            if "timeout_issues" not in err_obs: err_obs["timeout_issues"] = []
            err_obs["timeout_issues"].append({"agent": agent_name, "error": str(exc)})
            try:
                await run_in_executor(
                    db_service.upsert_agent_output,
                    session_id=session_id,
                    agent_name=agent_name,
                    status="failed",
                    raw_json={"error": "TimeoutError: " + str(exc)},
                    token_usage=0
                )
            except Exception:
                pass
            updated_status[agent_name] = "failed"
            return {"name": agent_name, "status": "failed", "data": {}, "tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
        except Exception as exc:
            logger.error(f"Agent Task Failed: [{agent_name}] due to: {exc}")
            if "api_failures" not in err_obs: err_obs["api_failures"] = []
            err_obs["api_failures"].append({"agent": agent_name, "error": str(exc)})
            try:
                await run_in_executor(
                    db_service.upsert_agent_output,
                    session_id=session_id,
                    agent_name=agent_name,
                    status="failed",
                    raw_json={"error": str(exc)},
                    token_usage=0
                )
            except Exception:
                pass

            updated_status[agent_name] = "failed"
            try:
                from app.services.workflow_service import publish_event
                publish_event(session_id, "agent_status_updated", {
                    "agent_status": updated_status,
                    "token_usage": {
                        "input_tokens": current_tokens.get("total", {}).get("prompt", 0),
                        "output_tokens": current_tokens.get("total", {}).get("completion", 0),
                        "total_tokens": current_tokens.get("total", {}).get("total", 0)
                    }
                })
            except Exception as e:
                logger.error(f"Error publishing progress for failed {agent_name}: {e}")

            return {"name": agent_name, "status": "failed", "data": {}, "tokens": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}

    # Schedule concurrent execution
    tasks = [run_agent_worker(name, agents[name]) for name in agents_to_run]
    await asyncio.gather(*tasks)

    node_duration = time.time() - node_start_time
    perf_metrics["node_latencies"]["research_agents_node"] = node_duration

    # Calculate slowest LLM/agent
    agent_lats = perf_metrics["node_latencies"].get("agent_latencies", {})
    if agent_lats:
        slowest = max(agent_lats.items(), key=lambda x: x[1])
        if "slowest_llm_responses" not in perf_metrics:
            perf_metrics["slowest_llm_responses"] = []
        perf_metrics["slowest_llm_responses"].append({
            "agent": slowest[0],
            "duration": slowest[1],
            "retry_count": state.get("regeneration_attempts", 0)
        })

    # Push to LangSmith
    try:
        ls.set_run_metadata(**{
            "node_duration_ms": node_duration * 1000,
            "slowest_agent": perf_metrics["slowest_llm_responses"][-1] if perf_metrics["slowest_llm_responses"] else None,
            "api_failures": err_obs.get("api_failures", []),
            "timeout_issues": err_obs.get("timeout_issues", [])
        })
    except Exception:
        pass

    return {
        "agent_data": accumulated_data,
        "agent_status": updated_status,
        "token_usage": current_tokens,
        "performance_metrics": perf_metrics,
        "error_observability": err_obs
    }


#
# 3. CONSOLIDATION NODE
#
@traceable(name="Schema Consolidation Engine", tags=["consolidation", "conflict-resolution"])
async def consolidation_node(state: ResearchState) -> Dict[str, Any]:
    logger.info(" [Node: Consolidation Node] Merging Source Streams ")
    node_start_time = time.time()

    # Inject Production Metadata
    token_summary = state.get("token_usage", {}).get("total", {"total": 0})
    TracingHelper.set_standard_metadata(
        company=state.get("company_name"),
        session_id=state.get("session_id"),
        stage="Consolidation",
        extra={
            "retry_count": state.get("regeneration_attempts", 0),
            "cumulative_tokens": token_summary.get("total", 0)
        }
    )
    TracingHelper.add_tags(["company-research", "consolidation"])

    if state.get("already_researched"):
        logger.info("[Switch-to-Live] Bypassing consolidation execution.")
        return {}
    session_id = state["session_id"]
    company = state["company_name"]
    agent_data = state.get("agent_data") or {}

    try:
        await run_in_executor(db_service.update_session, session_id, {"status": "consolidating"})
    except Exception:
        pass

    # Standard profile merging logic
    # We combine all fields into a unified draft profile

    # 1. Initialize all 163 master parameters to None to guarantee 100% schema retention
    consolidated = {param_name: None for param_name in MASTER_PARAMETERS}

    # 2. Dynamic lookup: Retrieve values for all keys in MASTER_PARAMETERS from mapped agents
    # Add alias translation map for flexible and resilient resolution
    alias_map = {
        "total_capital_raised": ["total_funding_usd", "total_funding", "capital_raised"],
        "company_valuation": ["approximate_valuation_usd", "valuation", "valuation_usd"],
        "implied_valuation": ["approximate_valuation_usd"],
        "employee_size": ["approximate_headcount"],
        "approximate_headcount": ["employee_size"],
        "office_locations": ["office_locations"],
        "headquarters_city": ["headquarters_city", "hq_city"],
        "headquarters_address": ["headquarters_address", "hq_address"]
    }

    for param, meta in MASTER_PARAMETERS.items():
        agent_name = meta["agent"]
        # Look in the mapped agent first, but fallback to any other agent if necessary
        # We search both standard key and aliases
        candidates = [param] + alias_map.get(param, [])
        
        val = None
        # Try mapped agent first
        agent_dict = agent_data.get(agent_name, {})
        if isinstance(agent_dict, dict):
            for cand in candidates:
                if cand in agent_dict and agent_dict[cand] is not None:
                    val = agent_dict[cand]
                    break
        
        # If not found in mapped agent, search other agents to maximize schema density!
        if val is None:
            for other_agent, other_dict in agent_data.items():
                if other_agent == agent_name or not isinstance(other_dict, dict):
                    continue
                for cand in candidates:
                    if cand in other_dict and other_dict[cand] is not None:
                        val = other_dict[cand]
                        break
                if val is not None:
                    break

        if val is not None:
            consolidated[param] = val

    # 3. Ensure company_name is populated if missed
    if not consolidated.get("company_name"):
        consolidated["company_name"] = company


    logger.info(f"Consolidated draft profile constructed for {company} with {len(consolidated)} keys (100% schema retention).")

    # --- Field-Level Observability: Conflict Detection ---
    obs = state.get("field_observability", {})
    conflicting_parameters = []
    for field in MASTER_PARAMETERS:
        values_found = {}
        for agent_name, agent_dict in agent_data.items():
            if isinstance(agent_dict, dict) and agent_dict.get(field):
                values_found[agent_name] = agent_dict[field]

        if len(values_found) > 1:
            unique_values = set(str(v).strip().lower() for v in values_found.values())
            if len(unique_values) > 1:
                logger.warning(f"Conflict detected for field '{field}': {values_found}")
                conflicting_parameters.append({
                    "field": field,
                    "agents": list(values_found.keys()),
                    "values": values_found
                })
                if field in obs:
                    obs[field]["validation_failure_reason"] = f"Conflict: Multiple agents provided different values: {values_found}"
                    obs[field]["validation_status"] = "failed"
                    obs[field]["confidence_score"] = 0.4

    # Log conflicts in metadata
    if conflicting_parameters:
        try:
            ls.set_run_metadata(**{"conflicting_parameters": conflicting_parameters})
        except Exception:
            pass

    # --- Field-Level Observability: Consolidation Tracking ---
    for field, value in consolidated.items():
        if field in obs:
            obs[field]["final_consolidated_value"] = value

    err_obs = state.get("error_observability", {})
    if conflicting_parameters:
        err_obs["consolidation_conflicts"] = conflicting_parameters

    perf_metrics = state.get("performance_metrics", {})
    if "node_latencies" not in perf_metrics: perf_metrics["node_latencies"] = {}
    perf_metrics["node_latencies"]["consolidation_node"] = time.time() - node_start_time

    return {
        "consolidated_profile": consolidated,
        "field_observability": obs,
        "conflicting_parameters": conflicting_parameters,
        "performance_metrics": perf_metrics,
        "error_observability": err_obs
    }


#
# 4. VALIDATION NODE
#
@traceable(name="Quality Assurance Auditor", tags=["validation", "remediation"])
async def validation_node(state: ResearchState, config: RunnableConfig) -> Dict[str, Any]:
    logger.info(" [Node: Validation Node] Executing Quality Audit ")
    node_start_time = time.time()

    # Inject Production Metadata
    TracingHelper.set_standard_metadata(
        company=state.get("company_name"),
        session_id=state.get("session_id"),
        stage="Quality-Audit",
        extra={
            "retry_count": state.get("regeneration_attempts", 0),
            "conflicting_parameters": state.get("conflicting_parameters", [])
        }
    )
    TracingHelper.add_tags(["company-research", "validation"])

    session_id = state["session_id"]
    profile = state.get("consolidated_profile") or {}
    attempt = state.get("regeneration_attempts", 0) + 1

    try:
        await run_in_executor(db_service.update_session, session_id, {"status": "validating"})
    except Exception:
        pass

    if state.get("already_researched"):
        logger.info("[Switch-to-Live] Bypassing quality audit for already researched company.")
        history = list(state.get("validation_history", []))
        history.append({
            "attempt": attempt,
            "overall_confidence": 1.0,
            "failed_fields": [],
            "passed": True
        })
        return {
            "validation_passed": True,
            "confidence_score": 1.0,
            "failed_fields": [],
            "validation_history": history
        }

    # Audit checks
    rules_checked = []
    failed_fields = []
    missing_parameters = []
    confidence_score = 1.0

    # 1. Missing fields check
    critical_fields = {
        "company_overview": "Overview and description",
        "headquarters_city": "Headquarters city location",
        "approximate_headcount": "Employee headcount estimates",
        "total_capital_raised": "Venture funding status",
        "founder_or_ceo": "CEO or leadership identity",
        "technological_stack": "Core software stack details"
    }

    for field, desc in critical_fields.items():
        val = profile.get(field)
        passed = True
        msg = f"Valid information extracted for '{field}'."

        if not is_valid_value(val):
            passed = False
            msg = f"Missing critical information for: '{desc}'."
            failed_fields.append(field)
            missing_parameters.append({"field": field, "description": desc})
            confidence_score -= 0.10  # Deduct 10 points for critical gaps
        rules_checked.append({
            "rule_name": f"VAL-CRIT-{field.upper()}",
            "field": field,
            "passed": passed,
            "message": msg
        })

        # --- Field-Level Observability: Validation Status ---
        update_field_observability(state, field, {
            "validation_status": "passed" if passed else "failed",
            "validation_failure_reason": msg if not passed else None,
            "confidence_score": 1.0 if passed else 0.5
        })

    # 2. Conflicting information check (CEO name or headquarters consistency)
    execs = profile.get("key_executives", [])
    founder_ceo = profile.get("founder_or_ceo", "")
    exec_passed = True
    exec_msg = "CEO identity matches executive records."

    if execs and founder_ceo:
        exec_names = [e.get("name", "").lower() for e in execs if e.get("name")]
        if exec_names and not any(founder_ceo.lower() in name or name in founder_ceo.lower() for name in exec_names):
            exec_passed = False
            exec_msg = f"Conflict: CEO name '{founder_ceo}' is absent from key executive listings."
            failed_fields.append("founder_or_ceo")
            confidence_score -= 0.15  # Deduct 15 points for executive mismatch

    rules_checked.append({
        "rule_name": "VAL-CONF-CEO_ALIGNMENT",
        "field": "founder_or_ceo",
        "passed": exec_passed,
        "message": exec_msg
    })

    # Guard bounds for score
    confidence_score = max(0.0, min(1.0, round(confidence_score, 3)))

    # If, after all checks and remediation, there are still failed fields,
    # the confidence score cannot be 1.0. Deduct a small amount if it is.
    if len(failed_fields) > 0 and confidence_score == 1.0:
        confidence_score = max(0.0, confidence_score - 0.05) # Small deduction if fields still failed but score is 1.0

    threshold = state.get("confidence_threshold", 0.85)
    passed_validation = confidence_score >= threshold and len(failed_fields) == 0

    obs = state.get("field_observability") or {}

    #  AI Auto-Remediation Loop
    if not passed_validation:
        try:
            import sys
            import os
            val_suite_path = r"d:\ps_03\PlacementIntel\validation_suite"
            if val_suite_path not in sys.path:
                sys.path.append(val_suite_path)

            from remediation import RemediationEngine
            remed_engine = RemediationEngine()

            # Formulate failed checks list
            failed_checks = []
            for rc in rules_checked:
                if not rc["passed"]:
                    failed_checks.append({
                        "rule_name": rc["rule_name"],
                        "field_name": rc["field"],
                        "error_message": rc["message"]
                    })

            if failed_checks:
                logger.info(f"[Remediation] Formulated {len(failed_checks)} failed checks. Generating AI recommendations...")
                # Fetch target company id from state or profile
                company_id = state.get("company_id")
                if company_id:
                    profile["company_id"] = company_id

                remed_result = remed_engine.generate_suggestions(failed_checks, profile)
                suggestions = remed_result.get("suggestions", [])
                remed_metrics = remed_result.get("metrics", {})

                # Track validation token usage
                if remed_metrics:
                    # We need to calculate cost for remediation metrics
                    from app.agents.base_agent import BaseResearchAgent
                    temp_agent = BaseResearchAgent("Remediation_Tracker")
                    remed_metrics["estimated_cost"] = temp_agent.calculate_cost(
                        remed_metrics.get("prompt_tokens", 0),
                        remed_metrics.get("completion_tokens", 0),
                        remed_metrics.get("model_name")
                    )
                    state["token_usage"] = update_token_metadata(
                        state=state,
                        node_name="validation_remediation",
                        metrics=remed_metrics,
                        retry_count=state.get("regeneration_attempts", 0)
                    )

                # Filter high-confidence suggestions (>= 95%) and auto-apply them
                high_conf = [s for s in suggestions if s.get("confidence", 0.0) >= 0.95]
                if high_conf:
                    logger.info(f"[Remediation] Auto-applying {len(high_conf)} high-confidence corrections directly to state profile.")
                    for s in high_conf:
                        field = s["field_name"]
                        val = s["suggested_value"]
                        # Map keys to match profile fields if necessary
                        profile[field] = val

                        # --- Field-Level Observability: Repair Tracking ---
                        update_field_observability(state, field, {
                            "repair_attempts": obs.get(field, {}).get("repair_attempts", 0) + 1,
                            "final_consolidated_value": val,
                            "trace_lineage": "RemediationEngine"
                        })

                    # Re-evaluate rules after auto-apply
                    rechecked_failed_fields = []
                    rechecked_confidence = 1.0

                    for rc in rules_checked:
                        field = rc["field"]
                        if not rc["passed"]:
                            val = profile.get(field)
                            if val and val != "Unknown" and val != "Not Disclosed" and val != "None" and not (isinstance(val, list) and len(val) == 0):
                                rc["passed"] = True
                                rc["message"] = "Valid information resolved after AI Auto-Correction."
                            else:
                                rechecked_failed_fields.append(field)
                                rechecked_confidence -= 0.10
                        else:
                            pass

                    confidence_score = max(0.0, min(1.0, round(rechecked_confidence, 3)))
                    passed_validation = confidence_score >= threshold and len(rechecked_failed_fields) == 0
                    failed_fields = rechecked_failed_fields
                    logger.info(f"[Remediation] Self-healing update complete. Confidence: {confidence_score}, Failed fields: {failed_fields}")

                # Log any pending suggestions (confidence < 0.95) to Human-in-the-Loop review queue
                pending_suggs = [s for s in suggestions if s.get("confidence", 0.0) < 0.95]
                if pending_suggs:
                    remed_engine.log_pending_suggestions(pending_suggs)

        except Exception as ex:
            logger.warning(f"Self-healing remediation loop skipped or failed: {ex}")
    #

    logger.info(f"Quality Audit Attempt #{attempt} Completed. Overall Confidence: {confidence_score} (Threshold: {threshold}). Failed fields: {failed_fields}")

    # Record validation log in Supabase
    try:
        await run_in_executor(
            db_service.insert_validation_log,
            session_id=session_id,
            attempt=attempt,
            rules_checked=rules_checked,
            confidence=confidence_score,
            failed_fields=failed_fields,
            needs_regen=not passed_validation
        )
    except Exception as e:
        logger.error(f"Error saving validation log to Supabase: {e}")

    history = list(state.get("validation_history", []))
    history.append({
        "attempt": attempt,
        "overall_confidence": confidence_score,
        "failed_fields": failed_fields,
        "passed": passed_validation
    })

    #  Confidence Debugging Trace Logging
    try:
        confidence_debugging = {
            "confidence_score": confidence_score,
            "missing_parameters": missing_parameters,
            "conflicting_parameters": state.get("conflicting_parameters", [])
        }

        # Log granular debugging data to LangSmith trace
        TracingHelper.set_standard_metadata(
            extra={
                "confidence_debugging": confidence_debugging,
                "validation_passed": passed_validation,
                "retry_trigger_visibility": not passed_validation,
                "validation_lineage": history,
                "failed_fields_count": len(failed_fields)
            }
        )

        if not passed_validation:
            logger.warning(f"Retry Triggered. Reason: Confidence {confidence_score} < Threshold {threshold} OR Failed Fields: {failed_fields}")
            TracingHelper.set_standard_metadata(
                extra={"retry_trigger_reason": f"Confidence degradation or critical field gaps. Failed: {failed_fields}"}
            )
    except Exception as e:
        logger.warning(f"Failed to log confidence debugging to LangSmith: {e}")
        TracingHelper.log_error(e, context="Confidence Debugging Metadata")
    #

    # Performance & Error Observability Updates
    perf_metrics = state.get("performance_metrics", {})
    if "node_latencies" not in perf_metrics: perf_metrics["node_latencies"] = {}
    perf_metrics["node_latencies"]["validation_node"] = time.time() - node_start_time

    err_obs = state.get("error_observability", {})
    if missing_parameters:
        err_obs["missing_parameters"] = missing_parameters
    if not passed_validation:
        err_obs["validation_failures"] = failed_fields
        # Optional: track fields that failed validation but were confidently hallucinated (low confidence, etc.)
        err_obs["hallucinated_outputs"] = [f for f in failed_fields if f not in [m["field"] for m in missing_parameters]]

    return {
        "validation_passed": passed_validation,
        "confidence_score": confidence_score,
        "failed_fields": failed_fields,
        "validation_history": history,
        "conflicting_parameters": state.get("conflicting_parameters", []),
        "missing_parameters": missing_parameters,
        "performance_metrics": perf_metrics,
        "error_observability": err_obs,
        "consolidated_profile": profile,
        "token_usage": state.get("token_usage", {}),
        "field_observability": obs
    }


#
# 5. REGENERATION LOOP NODE
#
@traceable(name="Intelligent Recovery Planner", tags=["regeneration", "retry-loop"])
async def regeneration_node(state: ResearchState) -> Dict[str, Any]:
    logger.info(" [Node: Regeneration Node] Planning Repair Search Parameters ")
    node_start_time = time.time()

    # Inject Production Metadata
    failed_fields = state.get("failed_fields", [])
    TracingHelper.set_standard_metadata(
        company=state.get("company_name"),
        session_id=state.get("session_id"),
        stage="Regeneration-Planning",
        extra={
            "retry_count": state.get("regeneration_attempts", 0),
            "retry_fields": failed_fields
        }
    )
    TracingHelper.add_tags(["company-research", "regeneration"])

    session_id = state["session_id"]
    attempts = state["regeneration_attempts"] + 1

    try:
        await run_in_executor(db_service.update_session, session_id, {"status": "regenerating"})
    except Exception:
        pass

    logger.warning(f"Validation failed (Attempt {attempts}/{state['max_attempts']}). Preparing repair filters for: {state['failed_fields']}")

    # Update field-level retry counts
    obs = state.get("field_observability", {})
    for field in state.get("failed_fields", []):
        if field in obs:
            obs[field]["retry_count"] = obs[field].get("retry_count", 0) + 1

    err_obs = state.get("error_observability", {})
    if "retry_triggers" not in err_obs: err_obs["retry_triggers"] = []
    err_obs["retry_triggers"].append({
        "attempt": attempts,
        "failed_fields": failed_fields
    })

    perf_metrics = state.get("performance_metrics", {})
    if "node_latencies" not in perf_metrics: perf_metrics["node_latencies"] = {}
    perf_metrics["node_latencies"][f"regeneration_node_{attempts}"] = time.time() - node_start_time

    # We increment attempt count and pass state back to agents
    return {
        "regeneration_attempts": attempts,
        "field_observability": obs,
        "performance_metrics": perf_metrics,
        "error_observability": err_obs
    }


#
# 6. FINAL OUTPUT NODE
#
@traceable(name="Executive Brief Compiler", tags=["reporting", "insights"])
async def final_output_node(state: ResearchState) -> Dict[str, Any]:
    logger.info(" [Node: Final Output Node] Compiling Premium Executive Brief ")
    node_start_time = time.time()

    # Inject Production Metadata
    token_summary = state.get("token_usage", {}).get("total", {"total": 0})
    TracingHelper.set_standard_metadata(
        company=state.get("company_name"),
        session_id=state.get("session_id"),
        stage="Report-Compilation",
        extra={
            "final_confidence": state.get("confidence_score", 0.0),
            "total_tokens": token_summary.get("total", 0)
        }
    )
    TracingHelper.add_tags(["company-research", "reporting"])

    session_id = state["session_id"]
    profile = state.get("consolidated_profile") or {}

    c_name = profile.get("company_name", state.get("company_name", "Unknown"))

    from app.agents.specialized_agents import DossierSynthesisAgent

    compiler = DossierSynthesisAgent()
    synthesis_res = compiler.synthesize_dossier(c_name, profile)
    final_report = synthesis_res["data"]
    synthesis_metrics = synthesis_res["metrics"]

    # Calculate compiler cost
    synthesis_metrics["estimated_cost"] = compiler.calculate_cost(
        synthesis_metrics.get("prompt_tokens", 0),
        synthesis_metrics.get("completion_tokens", 0),
        synthesis_metrics.get("model_name")
    )

    # Accumulate compilation tokens
    state["token_usage"] = update_token_metadata(
        state=state,
        node_name="final_dossier_compilation",
        metrics=synthesis_metrics,
        retry_count=state.get("regeneration_attempts", 0)
    )

    # Inject latest token summary
    final_report["token_usage_summary"] = state.get("token_usage", {}).get("total", {
        "prompt": 0,
        "completion": 0,
        "total": 0,
        "cost": 0.0
    })

    logger.info(f"Executive brief successfully compiled for {c_name}.")

    perf_metrics = state.get("performance_metrics", {})
    if "node_latencies" not in perf_metrics: perf_metrics["node_latencies"] = {}
    perf_metrics["node_latencies"]["final_output_node"] = time.time() - node_start_time

    workflow_start = perf_metrics.get("workflow_start_time", node_start_time)
    workflow_duration = time.time() - workflow_start
    perf_metrics["workflow_duration"] = workflow_duration

    total_tokens = state.get("token_usage", {}).get("total", {}).get("total", 0)
    throughput = (total_tokens / workflow_duration) if workflow_duration > 0 else 0
    perf_metrics["throughput_metrics"] = {"tokens_per_second": throughput}

    err_obs = state.get("error_observability", {})

    TracingHelper.set_standard_metadata(
        extra={
            "workflow_duration_ms": workflow_duration * 1000,
            "throughput_tokens_per_sec": throughput,
            "performance_metrics": perf_metrics,
            "error_observability": err_obs
        }
    )

    return {
        "final_report": final_report,
        "field_observability": state.get("field_observability", {}),
        "performance_metrics": perf_metrics,
        "error_observability": err_obs
    }


#
# 7. SUPABASE STORAGE NODE
#
@traceable(name="Cloud Persistence Engine", tags=["database", "supabase"])
async def supabase_storage_node(state: ResearchState) -> Dict[str, Any]:
    logger.info(" [Node: Supabase Storage Node] Writing Final Deliverables ")
    session_id = state["session_id"]
    report = state.get("final_report") or {}
    company = state["company_name"]
    score = state["confidence_score"]
    profile = state.get("consolidated_profile") or {}

    try:
        # 1. Update research session with confidence and completion status
        await run_in_executor(
            db_service.update_session,
            session_id,
            {
                "status": "completed",
                "confidence_score": score
            }
        )
        logger.info(f"Updated Supabase session status to 'completed' with confidence {score}.")

        # 2. Write finalized structured dossier report
        await run_in_executor(
            db_service.upsert_final_report,
            session_id=session_id,
            company_name=company,
            summary=report["summary"],
            market_analysis=report["market_analysis"],
            competitor_insights=report["competitor_insights"],
            tech_stack=report["technology_stack"],
            funding_status=report["funding_status"],
            risk_analysis=report["risk_opportunity_analysis"],
            tokens=state.get("token_usage", {}), # Pass full structured tokens
            field_observability=state.get("field_observability", {})
        )
        logger.info("Dossier written to final_reports table.")

        # 3. If a fresh crawl was run (not Switch-to-Live), upsert the compiled parameters to the 'staging_company' table
        if not state.get("already_researched"):
            logger.info("Writing newly compiled company parameters back to Supabase 'staging_company' table...")
            from datetime import datetime
            companies_payload = {
                "name": profile.get("company_name", company),
                "short_name": profile.get("short_name", company),
                "category": profile.get("software_category", "Technology"),
                "incorporation_year": str(profile.get("incorporation_year")) if profile.get("incorporation_year") else None,
                "nature_of_company": profile.get("nature_of_company", "Private"),
                "headquarters_address": profile.get("headquarters_address", "Unknown"),
                "office_count": profile.get("office_count") or (len(profile.get("office_locations", [])) if profile.get("office_locations") else None),
                "employee_size": profile.get("approximate_headcount") or profile.get("employee_size", "Unknown"),
                "website_url": profile.get("website_url", ""),
                "linkedin_url": profile.get("linkedin_url", ""),
                "twitter_handle": profile.get("twitter_handle", ""),
                "facebook_url": profile.get("facebook_url", ""),
                "instagram_url": profile.get("instagram_url", ""),
                "primary_contact_email": profile.get("general_contact_email") or profile.get("primary_contact_email", ""),
                "primary_phone_number": profile.get("contact_phone_number") or profile.get("primary_phone_number", ""),
                "overview_text": profile.get("company_overview", ""),
                "vision_statement": profile.get("vision_statement") or profile.get("mission_statement", ""),
                "mission_statement": profile.get("mission_statement", ""),
                "legal_issues": profile.get("legal_issues") or profile.get("known_controversies", "None"),
                "carbon_footprint": profile.get("carbon_footprint") or "Unknown",
                "processing_status": "completed",
                "processed_at": datetime.utcnow(),
                # Preserve full consolidated 163-key profile in JSON column for downstream analysis
                "allocated_parameters": profile
            }
            await run_in_executor(db_service.upsert_company, companies_payload)
            logger.info("[OK] Upserted company data directly into Supabase 'staging_company' table.")

    except Exception as e:
        logger.error(f"Error persisting final deliverables in Supabase: {e}")

    logger.info(" Pipeline Execution Completed Successfully ")
    return {}


#
# 8. LOCAL JSON EXPORT NODE
#
@traceable(name="Local Export Engine", tags=["file-system", "export"])
async def local_export_node(state: ResearchState) -> Dict[str, Any]:
    logger.info(" [Node: Local JSON Export Node] Displaying and Saving Dossier ")

    report = state.get("final_report") or {}
    company_name = state.get("company_name") or report.get("company_name") or "unknown_company"

    # 1. Console Display: Pretty-print the compiled Business Intelligence Dossier
    print("\n" + "="*80)
    print(f"  PRETTY-PRINTED BUSINESS INTELLIGENCE DOSSIER FOR: {company_name}")
    print("="*80)
    print(json.dumps(report, indent=4))
    print("="*80 + "\n")

    # 2. JSON Storage: Save both the final brief report and the 163-key raw profile
    try:
        # Slugify the company name to avoid issues with spaces or special characters in filenames
        slugified_company = re.sub(r'\W+', '_', company_name.lower()).strip('_')

        # Save final report
        filename = f"{slugified_company}_report.json"
        filepath = os.path.join(os.getcwd(), filename)
        logger.info(f"Attempting to write local JSON report to: {filepath}")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        logger.info(f"[OK] Successfully wrote dynamic JSON report to '{filename}' in current directory.")
        print(f"  [OK] JSON report saved to: {filename}")

        # Save raw 163-key consolidated profile
        raw_profile = state.get("consolidated_profile") or {}
        raw_filename = f"{slugified_company}_raw_profile.json"
        raw_filepath = os.path.join(os.getcwd(), raw_filename)
        logger.info(f"Attempting to write local raw 163-key profile to: {raw_filepath}")
        with open(raw_filepath, "w", encoding="utf-8") as f:
            json.dump(raw_profile, f, indent=4, ensure_ascii=False)
        logger.info(f"[OK] Successfully wrote raw 163-key profile to '{raw_filename}' in current directory.")
        print(f"  [OK] Raw 163-key profile saved to: {raw_filename}\n")

    except Exception as exc:
        logger.error(f"[X] Failed to save JSON exports locally due to a file/permission error: {exc}")
        print(f"  [X] JSON exports skipped/failed (Safe Recovery): {exc}\n")

    return {}

