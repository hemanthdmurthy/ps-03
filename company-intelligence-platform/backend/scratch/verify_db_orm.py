# scratch/verify_db_orm.py
import sys
import os
import uuid

# Ensure backend directory is in Python module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db import db_service, get_db_session
from app.models import ResearchSession, AgentOutput, ValidationLog, FinalReport

def main():
    print("==========================================================")
    print("  RUNNING DATABASE ORM & CASCADE INTEGRITY SANITY TEST")
    print("==========================================================")

    # 1. Connectivity Check
    print("\n[1] Testing Database Connection...")
    connected = db_service.test_connection()
    if not connected:
        print("[-] [FAILED] Database is not reachable.")
        sys.exit(1)
    print("[+] [SUCCESS] Database is reachable.")

    # 2. CRUD: Create Session
    company_name = f"TestCorp_{uuid.uuid4().hex[:6]}"
    print(f"\n[2] Creating Research Session for: {company_name}...")
    session_data = db_service.create_session(
        company_name=company_name,
        industry="Automotive & Robotics",
        custom_query="Analyze EV self-healing charging systems."
    )
    session_id = session_data["id"]
    print(f"[+] [SUCCESS] Created session with ID: {session_id}")

    # 3. Create Agent Outputs
    print("\n[3] Adding intermediate agent outputs...")
    db_service.upsert_agent_output(
        session_id=session_id,
        agent_name="website_agent",
        status="completed",
        raw_json={"urls": ["https://testcorp.com"], "sentiment": "high"},
        token_usage=1250
    )
    db_service.upsert_agent_output(
        session_id=session_id,
        agent_name="linkedin_agent",
        status="completed",
        raw_json={"employees": 450, "executives": ["CEO Jane Doe"]},
        token_usage=850
    )
    print("[+] [SUCCESS] Added website and linkedin agent outputs.")

    # 4. Insert Validation Logs
    print("\n[4] Adding Validation Logs...")
    db_service.insert_validation_log(
        session_id=session_id,
        attempt=1,
        rules_checked=[{"rule": "has_ceo", "passed": True}],
        confidence=0.98,
        failed_fields=[],
        needs_regen=False
    )
    print("[+] [SUCCESS] Added validation log row.")

    # 5. Create Final Brief Report
    print("\n[5] Adding Premium Final Report...")
    db_service.upsert_final_report(
        session_id=session_id,
        company_name=company_name,
        summary="A premium tech enterprise pushing bounds in EV space.",
        market_analysis={"market_size": "$4.5B", "growth_rate": "15%"},
        competitor_insights={"competitors": ["Tesla", "Rivian"]},
        tech_stack=["Python", "PyTorch", "Rust"],
        funding_status={"valuation": "$100M", "series": "Series A"},
        risk_analysis={"gaps": "None"},
        tokens={"prompt": 5000, "completion": 3000, "total": 8000, "cost": 0.024}
    )
    print("[+] [SUCCESS] Final report upserted.")

    # 6. Eager Loading Verification
    print("\n[6] Fetching Aggregated Session Data (Eager Loading)...")
    full_data = db_service.get_full_session_data(session_id)
    
    # Assertions
    session = full_data["session"]
    agent_outputs = full_data["agent_outputs"]
    validation_history = full_data["validation_history"]
    final_report = full_data["final_report"]

    assert session["company_name"] == company_name, "Company name mismatch!"
    assert "website_agent" in agent_outputs, "Website agent output missing!"
    assert len(validation_history) == 1, "Validation history mismatch!"
    assert final_report["summary"] is not None, "Final report summary missing!"

    print("[+] [SUCCESS] Verified full eager load retrieval matches inserted parameters!")
    print(f"    - Agent Outputs Found: {list(agent_outputs.keys())}")
    print(f"    - Final Report Summary: '{final_report['summary']}'")

    # 7. Cascade Deletion Integrity Check
    print("\n[7] Testing Cascade Deletion Integrity...")
    with get_db_session() as db:
        # Verify children exist in the DB first
        outputs_count = db.query(AgentOutput).filter(AgentOutput.session_id == session_id).count()
        reports_count = db.query(FinalReport).filter(FinalReport.session_id == session_id).count()
        logs_count = db.query(ValidationLog).filter(ValidationLog.session_id == session_id).count()
        
        print(f"    - Linked Agent Outputs Count (Before): {outputs_count}")
        print(f"    - Linked Final Reports Count (Before): {reports_count}")
        print(f"    - Linked Validation Logs Count (Before): {logs_count}")
        
        assert outputs_count == 2
        assert reports_count == 1
        assert logs_count == 1

        # Delete the main parent ResearchSession
        print(f"    - Deleting Parent Session ID: {session_id}...")
        session_to_delete = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
        db.delete(session_to_delete)
        db.flush()

        # Check if child tables are cleanly swept via SQL cascade constraints
        outputs_count_after = db.query(AgentOutput).filter(AgentOutput.session_id == session_id).count()
        reports_count_after = db.query(FinalReport).filter(FinalReport.session_id == session_id).count()
        logs_count_after = db.query(ValidationLog).filter(ValidationLog.session_id == session_id).count()

        print(f"    - Linked Agent Outputs Count (After): {outputs_count_after}")
        print(f"    - Linked Final Reports Count (After): {reports_count_after}")
        print(f"    - Linked Validation Logs Count (After): {logs_count_after}")

        assert outputs_count_after == 0, "Cascade failed for AgentOutput!"
        assert reports_count_after == 0, "Cascade failed for FinalReport!"
        assert logs_count_after == 0, "Cascade failed for ValidationLog!"

    print("[+] [SUCCESS] Cascade delete constraints are fully operational and verified!")
    print("\n==========================================================")
    print("  ALL DATABASE ORM AND CASCADE SANITY TESTS PASSED! [OK]")
    print("==========================================================")

if __name__ == "__main__":
    main()
