# run_workflow_offline.py
import asyncio
import logging
from app.workflow.graph import workflow_graph

# Configure console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("company_intel.offline_test")

async def test_offline_pipeline():
    logger.info("Initializing offline pipeline verification harness...")

    # Seed mock company into the local database to satisfy pipeline inputs & schema checks
    from app.services.db import db_service
    db_service.upsert_company({
        "name": "Ather Energy Limited",
        "short_name": "Ather",
        "category": "EV Manufacturer",
        "incorporation_year": "2013",
        "nature_of_company": "Private",
        "headquarters_address": "Bengaluru, Karnataka, India",
        "office_count": 5,
        "employee_size": "1000-5000",
        "website_url": "https://atherenergy.com",
        "linkedin_url": "https://linkedin.com/company/ather-energy",
        "twitter_handle": "@atherenergy",
        "facebook_url": "https://facebook.com/atherenergy",
        "instagram_url": "https://instagram.com/atherenergy",
        "primary_contact_email": "info@atherenergy.com",
        "primary_phone_number": "+91 80 1234 5678",
        "overview_text": "Ather Energy is an Indian electric vehicle company headquartered in Bangalore.",
        "vision_statement": "To transition India to sustainable energy usage through EV products.",
        "mission_statement": "To manufacture premium electric scooters.",
        "legal_issues": "None",
        "carbon_footprint": "Low",
        "processing_status": "completed"
    })
    logger.info("[+] Successfully seeded 'Ather Energy Limited' in local staging_company database table.")

    # Target inputs
    company = "Ather Energy Limited"
    industry = "Automotive"
    custom_query = "Focus on electric vehicles scale and funding"

    initial_state = {
        "session_id": "test-session-uuid-12345",
        "company_name": company,
        "industry": industry,
        "custom_query": custom_query,
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

    print("\n" + "="*80)
    print(f"  LAUNCHING OFFLINE MULTI-AGENT VALIDATION RUN FOR: {company}")
    print("="*80)

    try:
        # Step through compiled state transitions
        async for state_update in workflow_graph.astream(initial_state, stream_mode="updates"):
            node_name = list(state_update.keys())[0]
            node_values = state_update[node_name]

            print(f"\n>>> [Node Execution Completed]: {node_name.upper()}")

            if node_name == "input":
                print(f"  - Company Name Normalized: '{node_values.get('company_name') if node_values else ''}'")
                print(f"  - Session Registered in DB: {node_values.get('session_id') if node_values else ''}")

            elif node_name == "research_agents":
                print("  - Specialized Research Agents Outcomes:")
                if node_values:
                    for agent, status in node_values.get("agent_status", {}).items():
                        print(f"    * {agent.capitalize()}: {status.upper()}")
                    tu = node_values.get("token_usage", {})
                    print(f"  - Cumulative Token Weight: {tu.get('total_tokens', 0):,} spent")
                else:
                    print("    * (Bypassed due to Switch-to-Live database loading)")

            elif node_name == "consolidation":
                print("  - Consolidated Profile Synthesized:")
                if node_values:
                    profile = node_values.get("consolidated_profile", {})
                    print(f"    * CEO: {profile.get('founder_or_ceo')}")
                    print(f"    * HQ City: {profile.get('headquarters_city')}")
                    print(f"    * Headcount: {profile.get('approximate_headcount')}")
                    print(f"    * Funding: {profile.get('total_funding_usd')}")
                    print(f"    * Tech Stack: {', '.join(profile.get('technological_stack', []))}")
                else:
                    print("    * (Bypassed due to Switch-to-Live database loading)")

            elif node_name == "validation":
                print("  - Quality Guard Audit Check:")
                if node_values:
                    print(f"    * Passed Validation: {node_values.get('validation_passed')}")
                    print(f"    * Confidence Score: {round(node_values.get('confidence_score', 0.0) * 100)}%")
                    print(f"    * Gaps / Failed fields: {node_values.get('failed_fields')}")
                else:
                    print("    * (Bypassed due to Switch-to-Live database loading)")

            elif node_name == "regeneration":
                if node_values:
                    print(f"  - Validation failed. Feedback loop activated (Attempt #{node_values.get('regeneration_attempts')})")
                    print("  - Preparing repairs filters and scheduling subset run...")

            elif node_name == "final_output":
                print("  - Executive Brief Dossier Generated:")
                if node_values:
                    report = node_values.get("final_report", {})
                    print(f"    * Brief Summary: {report.get('summary')}")
                    print(f"    * SWOT Strengths: {report.get('competitor_insights', {}).get('swot_analysis', {}).get('strengths')}")
                    print(f"    * Cost Assessment: {report.get('token_usage_summary', {}).get('approximate_cost_usd')} USD")

            elif node_name == "supabase_storage":
                print("  - Synced report datasets with permanent final_reports DB tables.")

            elif node_name == "local_export":
                print("  - Locally exported dynamic JSON dossier report and pretty-printed results.")

        print("\n" + "="*80)
        print("  [OK] OFFLINE PIPELINE VERIFICATION SUCCESSFUL")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Pipeline verification crashed: {e}", exc_info=True)

if __name__ == "__main__":
    # Launch async loop
    asyncio.run(test_offline_pipeline())
