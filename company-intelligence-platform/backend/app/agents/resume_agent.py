import logging
import time
import json
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.llm_service import llm_service
from app.core.observability import TracingHelper

logger = logging.getLogger("company_intel.agents.resume")

class ResumeAgent:
    """
    Agent responsible for analyzing student resumes, extracting structured skills,
    identifying profile gaps, and recommending tailored improvements for placements.
    """
    def __init__(self, model_provider: Optional[str] = None, model_name: Optional[str] = None):
        self.name = "ResumeAgent"
        self.llm = llm_service.get_llm(custom_provider=model_provider, custom_model=model_name)
        
    async def analyze_resume_async(self, resume_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Asynchronously parses and evaluates a resume against industry placement standards.
        """
        start_time = time.time()
        logger.info(f"[{self.name}] Beginning async resume analysis.")

        system_prompt = """
        You are an expert Talent Acquisition Agent and Resume Screener.
        Analyze the student resume text below to extract key skills, career profile, and areas of improvement.
        Your response MUST be a highly professional, valid, and structured JSON with the following EXACT keys:
        - 'candidate_summary': A concise summary of their professional background.
        - 'primary_skills': A list of key technical skills, languages, or tools they excel in.
        - 'secondary_skills': A list of auxiliary skills, soft skills, or domain knowledge.
        - 'resume_score_out_of_100': An integer score evaluating the quality and impact of the resume.
        - 'profile_gaps': A list of missing skills or experiences for current market standards.
        - 'actionable_improvements': A list of concrete suggestions to improve the resume.
        Do not add any other keys or write any markdown text outside the JSON.
        """

        human_prompt = f"Resume Content:\n{resume_text}"
        if context:
            human_prompt += f"\nAdditional Context (Target Roles/Interests): {context}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        try:
            # Async invocation of the model
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()

            # Clean JSON markdown blocks if present
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)

            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[{self.name}] Async resume analysis completed in {execution_time_ms}ms.")

            # Hook for token usage monitoring
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
            logger.error(f"[{self.name}] JSON parsing error: {je}. Raw: {response.content}")
            return {
                "success": False,
                "agent": self.name,
                "error": "Failed to parse resume analysis response as JSON.",
                "raw_response": response.content if 'response' in locals() else None
            }
        except Exception as e:
            logger.error(f"[{self.name}] Failed to analyze resume: {e}")
            return {
                "success": False,
                "agent": self.name,
                "error": str(e)
            }
