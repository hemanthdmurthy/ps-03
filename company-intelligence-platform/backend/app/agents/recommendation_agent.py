import logging
import time
import json
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.llm_service import llm_service

logger = logging.getLogger("company_intel.agents.recommendation")

class RecommendationAgent:
    """
    Agent responsible for matching student skills, preferences, and projects
    against target companies, generating personalized company recommendations and fit scores.
    """
    def __init__(self, model_provider: Optional[str] = None, model_name: Optional[str] = None):
        self.name = "RecommendationAgent"
        self.llm = llm_service.get_llm(custom_provider=model_provider, custom_model=model_name)

    async def recommend_companies_async(self, student_profile: Dict[str, Any], companies_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Asynchronously computes suitability match of a student across multiple company profiles.
        """
        start_time = time.time()
        logger.info(f"[{self.name}] Initiating async matchmaking recommendation.")

        system_prompt = """
        You are a corporate Placement Matchmaking and Recommendation Agent.
        Analyze the student profile and the list of available target companies to recommend the best matches.
        Your response MUST be valid JSON conforming to the following structure:
        {
          "recommended_matches": [
            {
              "company_name": "Name of Company",
              "fit_score_out_of_100": 85,
              "matching_factors": ["List of skills or experiences that align"],
              "gap_factors": ["List of requirements they are missing"],
              "role_suitability": "E.g. Full Stack Developer, Data Analyst",
              "customized_pitch": "Brief 2-sentence guidance on how the student should present themselves to this company."
            }
          ],
          "general_career_advice": "A short summary of general career path recommendations based on their profile."
        }
        Do not add any other keys or markdown fences. Ensure valid JSON return.
        """

        human_prompt = f"Student Profile:\n{student_profile}\n\nTarget Companies Available:\n{companies_list}"

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
            logger.info(f"[{self.name}] Async company matching completed in {execution_time_ms}ms.")

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
            logger.error(f"[{self.name}] JSON parsing error: {je}. Content: {response.content}")
            return {
                "success": False,
                "agent": self.name,
                "error": "Failed to parse recommendation output as JSON.",
                "raw_response": response.content if 'response' in locals() else None
            }
        except Exception as e:
            logger.error(f"[{self.name}] Failed to generate recommendations: {e}")
            return {
                "success": False,
                "agent": self.name,
                "error": str(e)
            }
