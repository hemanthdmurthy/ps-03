import logging
import time
import json
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.llm_service import llm_service

logger = logging.getLogger("company_intel.agents.interview")

class InterviewAgent:
    """
    Agent responsible for generating mock interview questions, assessing candidate answers,
    providing behavioral advice, and designing customizable technical screening scenarios.
    """
    def __init__(self, model_provider: Optional[str] = None, model_name: Optional[str] = None):
        self.name = "InterviewAgent"
        self.llm = llm_service.get_llm(custom_provider=model_provider, custom_model=model_name)

    async def generate_prep_kit_async(self, role: str, company_name: str, skills: list) -> Dict[str, Any]:
        """
        Asynchronously designs a comprehensive role/company-specific mock interview prep kit.
        """
        start_time = time.time()
        logger.info(f"[{self.name}] Initiating async interview prep kit generation.")

        system_prompt = """
        You are an advanced corporate Interview Preparation Coach and Technical Interviewer.
        Generate a comprehensive interview preparation kit for the specified role and target company.
        Your response MUST be a highly structured JSON document with the following exact keys:
        - 'target_role': The role being prepared for.
        - 'company': The target company.
        - 'technical_questions': A list of 3-4 specific technical questions, with answer outlines and key points.
        - 'behavioral_questions': A list of 2-3 behavioral questions based on Star method with guidance.
        - 'company_specific_culture_tips': A list of insights about this company's hiring values and culture.
        - 'prep_checklist': A step-by-step checklist of things to review or prepare before the interview.
        Do not add any other keys or surrounding markdown code blocks other than json.
        """

        human_prompt = f"Role: {role}\nCompany: {company_name}\nCandidate Core Skills: {skills}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()

            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[{self.name}] Async interview prep kit completed in {execution_time_ms}ms.")

            token_usage = {}
            if hasattr(response, "response_metadata"):
                token_usage = response.response_metadata.get("token_usage", {})

            return {
                "success": True,
                "agent": self.name,
                "data": data,
                "token_usage": token_usage,
                "metrics": {
                    "execution_time_ms": execution_time_ms
                }
            }
        except json.JSONDecodeError as je:
            logger.error(f"[{self.name}] JSON parsing error: {je}. Raw output: {response.content}")
            return {
                "success": False,
                "agent": self.name,
                "error": "Failed to parse interview prep kit output as JSON.",
                "raw_response": response.content if 'response' in locals() else None
            }
        except Exception as e:
            logger.error(f"[{self.name}] Failed to generate interview prep kit: {e}")
            return {
                "success": False,
                "agent": self.name,
                "error": str(e)
            }
