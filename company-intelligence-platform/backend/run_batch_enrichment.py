# run_batch_enrichment.py
import asyncio
import logging
import uuid
from app.workflow.graph import workflow_graph
from app.db import db_service

# Configure console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("company_intel.batch_enrichment")

async def enrich_company(company_row):
    company_name = company_row.get("name")
    industry = company_row.get("category") or "Technology"

    print("\n" + "="*80)
    print(f"  STARTING BATCH ENRICHMENT RUN FOR: {company_name.upper()} (Industry: {industry})")
    print("="*80)

    # Generate a unique session UUID for this batch enrichment run
    session_id = f"batch-session-{uuid.uuid4().hex[:8]}"

    initial_state = {
        "session_id": session_id,
        "company_name": company_name,
        "industry": industry,
        "custom_query": "Batch OSINT enrichment, entity resolution, and data reconciliation audit",
        "regeneration_attempts": 0,
        "max_attempts": 3,
        "confidence_threshold": 0.85,
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

    try:
        # Step through compiled state transitions
        async for state_update in workflow_graph.astream(initial_state, stream_mode="updates"):
            node_name = list(state_update.keys())[0]
            node_values = state_update[node_name]

            logger.info(f"Transition Completed: {node_name.upper()}")

            if node_name == "input":
                if node_values.get("already_researched"):
                    print(f"  [Switch-to-Live] Found complete cached record for '{company_name}'. Bypassing live agents.")
                else:
                    print("  [Live Recovery] Stale/Incomplete record detected. Triggering multi-agent research...")

            elif node_name == "validation":
                if node_values:
                    score = round(node_values.get("confidence_score", 0.0) * 100)
                    print(f"  - Validation passed: {node_values.get('validation_passed')} (Score: {score}%)")
                    if node_values.get("failed_fields"):
                        print(f"  - Gaps detected: {node_values.get('failed_fields')}")

            elif node_name == "regeneration":
                print(f"  - Triggering repairs & regeneration loops (Attempt #{node_values.get('regeneration_attempts')})...")

            elif node_name == "supabase_storage":
                print("  [Supabase] Richly saved complete, verified profile back to staging_company and final_reports tables.")

        print(f"  [OK] Batch run completed successfully for {company_name}.\n")

    except Exception as e:
        logger.error(f"Batch run failed for company '{company_name}': {e}", exc_info=True)

async def main():
    logger.info("Starting Batch Corporate Enrichment script...")

    # 1. Fetch all companies registered in Supabase 'staging_company' table
    companies = await asyncio.get_event_loop().run_in_executor(None, db_service.get_all_companies)
    if not companies:
        logger.warning("No companies found in Supabase 'staging_company' table or failed to connect.")
        return

    print(f"\nFetched {len(companies)} companies from Supabase staging_company table.")
    for i, c in enumerate(companies, 1):
        print(f"  {i}. {c.get('name')} (company_id: {c.get('company_id')})")

    # 2. Enrich each company sequentially to avoid API rate limits and conserve tokens
    for company in companies:
        await enrich_company(company)

    print("\n" + "="*80)
    print("  ALL COMPANIES IN SUPABASE STAGING_COMPANY PROCESSED & SYSTEMATICALLY ENRICHED")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
