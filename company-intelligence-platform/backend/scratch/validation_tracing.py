# backend/scratch/validation_tracing.py
import asyncio
import os
import sys
import uuid
import logging
from unittest.mock import MagicMock

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy environment variables if not present for validation
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "tracing-validation-test")
os.environ.setdefault("LANGCHAIN_API_KEY", "ls__dummy_key") # Use a dummy key if the user hasn't provided one, though it might fail actual upload

from app.config import settings
from app.observability import TracingHelper, initialize_langsmith
from app.main import run_langgraph_workflow

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validation_tracing")

async def test_tracing_pipeline():
    print("\nStarting LangSmith Tracing Validation Test...")
    
    # 1. Initialize LangSmith
    client = initialize_langsmith()
    if not client:
        print("LangSmith client not initialized. Check your environment variables.")
        # We continue to test local execution logic
    else:
        print("LangSmith Client Initialized.")

    # 2. Mock Database Service to avoid external dependencies during tracing test
    from app import main
    original_db = main.db_service
    main.db_service = MagicMock()
    main.db_service.create_session.return_value = {"id": str(uuid.uuid4())}
    main.db_service.update_session.return_value = {}
    main.db_service.test_connection.return_value = True
    main.db_service.get_all_companies.return_value = [{"name": "Mock Corp", "id": 1}]
    main.db_service.get_company_by_name.return_value = None
    
    # Mock specialized agents search to avoid API calls
    from app.agents import specialized_agents
    specialized_agents.execute_search = MagicMock(return_value=[{"title": "Mock Result", "content": "Sample content for tracing test."}])

    # 3. Run a sample research workflow
    session_id = str(uuid.uuid4())
    company_name = "Tracing Validation Corp"
    industry = "Observability"
    custom_query = "Test the new production-grade tracing implementation."
    
    print(f"Launching test workflow for {company_name} (Session: {session_id})")
    
    try:
        await run_langgraph_workflow(
            session_id=session_id,
            company_name=company_name,
            industry=industry,
            custom_query=custom_query,
            max_attempts=1,
            threshold=0.8
        )
        print("Workflow execution finished.")
    except Exception as e:
        print(f"Workflow failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nCHECK YOUR LANGSMITH DASHBOARD:")
    print(f"Project: {settings.LANGCHAIN_PROJECT}")
    print(f"Look for a run named: 'Research: {company_name}'")
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_tracing_pipeline())
