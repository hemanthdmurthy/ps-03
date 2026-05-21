# graph.py
from typing import Literal
from langgraph.graph import StateGraph, START, END
from app.workflow.state import ResearchState
from app.workflow.nodes import (
    input_node,
    research_agents_node,
    consolidation_node,
    validation_node,
    regeneration_node,
    final_output_node,
    supabase_storage_node,
    local_export_node
)

def validation_router(state: ResearchState) -> Literal["regeneration", "final_output"]:
    """
    Evaluates whether to enter the regeneration cycle or proceed to finalization.
    Forces proceeding to final_output if max attempts have been exceeded.
    
    Key Fix: **Regeneration is triggered only when BOTH conditions are true:**
    1. validation_passed is False (confidence < threshold OR failed_fields exist)
    2. regeneration_attempts < max_attempts (still have retries left)
    
    If validation_passed is True, proceed directly to final_output regardless of confidence score.
    """
    if state.get("validation_passed", False):
        print(f"[Router] Validation passed. Proceeding to final_output.")
        return "final_output"

    attempts = state.get("regeneration_attempts", 0)
    max_att = state.get("max_attempts", 3)

    if attempts >= max_att:
        print(f"[Router] Forced Finalization: Validation failed, but maximum attempts reached ({attempts}/{max_att}).")
        return "final_output"

    print(f"[Router] Routing to Regeneration Loop (Attempt {attempts + 1}/{max_att}).")
    return "regeneration"

def build_workflow_graph():
    """
    Assembles, configures, and compiles the Research Pipeline state graph.
    """
    # 1. Initialize Graph with state schema
    builder = StateGraph(ResearchState)

    # 2. Add structural nodes
    builder.add_node("input", input_node)
    builder.add_node("research_agents", research_agents_node)
    builder.add_node("consolidation", consolidation_node)
    builder.add_node("validation", validation_node)
    builder.add_node("regeneration", regeneration_node)
    builder.add_node("final_output", final_output_node)
    builder.add_node("supabase_storage", supabase_storage_node)
    builder.add_node("local_export", local_export_node)

    # 3. Add static transitions
    builder.add_edge(START, "input")
    builder.add_edge("input", "research_agents")
    builder.add_edge("research_agents", "consolidation")
    builder.add_edge("consolidation", "validation")

    # 4. Add quality validation conditional router
    builder.add_conditional_edges(
        "validation",
        validation_router,
        {
            "regeneration": "regeneration",
            "final_output": "final_output"
        }
    )

    # Loop back from regeneration to research agents
    builder.add_edge("regeneration", "research_agents")

    # Finalize and exit
    builder.add_edge("final_output", "supabase_storage")
    builder.add_edge("supabase_storage", "local_export")
    builder.add_edge("local_export", END)

    # Compile graph with checkpoints (MemorySaver can be integrated if needed)
    graph = builder.compile()
    return graph

# ExportCompiled graph singleton
workflow_graph = build_workflow_graph()
