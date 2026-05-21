import asyncio
import os
import sys
import uuid
import logging

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "company-intelligence-platform", "backend"))

from app.services.workflow_service import run_langgraph_workflow
from app.core.config import settings

# Setup basic logging to see progress in console
logging.basicConfig(level=logging.INFO)

async def main():
    session_id = f"validation-test-{uuid.uuid4()}"
    company_name = "Perplexity AI"
    industry = "Artificial Intelligence"
    custom_query = "Focus on their latest series C funding and expansion into enterprise search."
    max_attempts = 2
    threshold = 0.95 # High threshold to potentially trigger remediation/retry

    print(f"Starting Phase 10 Validation Workflow for: {company_name}")
    print(f"Session ID: {session_id}")
    print(f"Tracing enabled: {settings.LANGCHAIN_TRACING_V2}")
    print(f"Project: {settings.LANGCHAIN_PROJECT}")

    await run_langgraph_workflow(
        session_id=session_id,
        company_name=company_name,
        industry=industry,
        custom_query=custom_query,
        max_attempts=max_attempts,
        threshold=threshold
    )

    print("\nWorkflow Execution Finished.")
    print(f"Check LangSmith for trace in project: {settings.LANGCHAIN_PROJECT}")

if __name__ == "__main__":
    asyncio.run(main())
