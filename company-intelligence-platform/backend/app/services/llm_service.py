import os
import logging
from typing import Optional, Dict, Any, List
from langchain_core.language_models.chat_models import BaseChatModel, SimpleChatModel
from langchain_core.messages import BaseMessage, AIMessage
from app.core.config import settings

logger = logging.getLogger("company_intel.services.llm")

class FakePlacementChatModel(SimpleChatModel):
    """
    Custom mock chat model that dynamically returns high-fidelity,
    agent-tailored JSON responses in testing mode, avoiding external API calls.
    """
    
    @property
    def _llm_type(self) -> str:
        return "fake-placement-chat-model"

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        prompt_text = "".join([getattr(m, "content", str(m)) for m in messages]).lower()
        
        # 1. Resume Agent Mock Response
        if "resume" in prompt_text or "cv" in prompt_text or "skills" in prompt_text:
            return """{
                "candidate_summary": "Highly motivated Python backend developer with extensive FastAPI experience.",
                "resume_score_out_of_100": 88,
                "primary_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "profile_gaps": ["No production AWS experience", "Limited frontend experience"],
                "actionable_improvements": [
                    "Complete a cloud certification or build an AWS-hosted project.",
                    "Enhance frontend exposure with basic React integrations."
                ]
            }"""
            
        # 2. Recommendation Agent Mock Response
        elif "recommend" in prompt_text or "match" in prompt_text or "company" in prompt_text:
            return """{
                "recommended_matches": [
                    {
                        "company_name": "Google",
                        "fit_score_out_of_100": 92,
                        "role_suitability": "Exceptional fit for Backend Infrastructure",
                        "matching_factors": ["Advanced Python skills", "Strong API design expertise"],
                        "gap_factors": ["No experience with large-scale distributed consensus protocols"],
                        "customized_pitch": "I am a high-performing backend engineer with deep expertise in API scalability and asynchronous frameworks, ready to drive value."
                    }
                ],
                "general_career_advice": "Focus on system design fundamentals and scaling strategies."
            }"""
            
        # 3. Interview Agent Mock Response
        elif "interview" in prompt_text or "prep" in prompt_text or "question" in prompt_text:
            return """{
                "target_role": "Backend Engineer",
                "company": "Google",
                "technical_questions": [
                    {
                        "question": "Explain the difference between threading and multiprocessing in Python.",
                        "answer_outline": "GIL limitations mean threads don't run in parallel; use multiprocessing for CPU-bound tasks."
                    }
                ],
                "behavioral_questions": [
                    {
                        "question": "Tell me about a time you resolved a major production crash.",
                        "guidance": "Focus on your immediate triage, logging audits, and post-mortem actions using the STAR method."
                    }
                ],
                "company_specific_culture_tips": [
                    "Highlight Google's core value of 'Googlyness' - thrive in ambiguity and care for users."
                ],
                "prep_checklist": [
                    "Review major data structures.",
                    "Practice talking through code solutions out loud."
                ]
            }"""
            
        # Default fallback response
        return "Hello! I am your AI placement assistant. How can I help you today?"

    async def _acall(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        # Native async path returns immediately on main event loop
        return self._call(messages, stop, run_manager, **kwargs)

class LLMService:
    """
    Centralized LLM management service for Placement Intel Portal backend.
    Supports Google Gemini, OpenAI, and graceful mock/fallback strategies.
    Ensures proper configuration of retries, timeouts, and API key validation.
    """
    def __init__(self):
        self.provider = settings.MODEL_PROVIDER.lower()
        self.model_name = settings.MODEL_NAME
        self.temperature = settings.TEMPERATURE
        self.timeout = 30.0
        self.max_retries = 3
        
        # Validate API Keys
        self._validate_api_keys()

    def _validate_api_keys(self):
        """Validates key configuration and warns if required keys are missing or invalid."""
        google_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY
        openai_key = settings.OPENAI_API_KEY
        
        logger.info(f"[LLMService] Initializing. Selected Provider: {self.provider}, Model: {self.model_name}")

        if self.provider == "google":
            if not google_key or google_key.startswith("YOUR_") or len(google_key) < 10:
                logger.error("[LLMService] Google API Key is missing or invalid in environment.")
            else:
                logger.info("[LLMService] Google API Key format validated successfully.")
        elif self.provider == "openai":
            if not openai_key or openai_key.startswith("sk-YOUR") or len(openai_key) < 10:
                logger.error("[LLMService] OpenAI API Key is missing or invalid in environment.")
            else:
                logger.info("[LLMService] OpenAI API Key format validated successfully.")
        else:
            logger.warning(f"[LLMService] Unknown or unrecognized model provider: {self.provider}. Will attempt default initialization.")

    def get_llm(self, custom_provider: Optional[str] = None, custom_model: Optional[str] = None, temperature: Optional[float] = None) -> BaseChatModel:
        """
        Instantiates and returns the configured LangChain Chat Model.
        Implements fallback logic if the requested provider/key is not available.
        """
        if settings.ENVIRONMENT == "testing":
            logger.info("[LLMService] Testing environment active. Forcing custom FakePlacementChatModel.")
            return FakePlacementChatModel()

        provider = (custom_provider or self.provider).lower()
        model = custom_model or self.model_name
        temp = temperature if temperature is not None else self.temperature
        
        google_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY
        openai_key = settings.OPENAI_API_KEY

        # Check for Google Gemini initialization
        if provider == "google" or (provider == "default" and google_key):
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                api_key = google_key
                if not api_key:
                    raise ValueError("Google API key is not configured.")
                
                # Resiliently handle model transition
                target_model = model
                if target_model in ["gemini-1.5-flash-latest", "gemini-1.5-flash"]:
                    target_model = "gemini-2.0-flash"
                
                logger.info(f"[LLMService] Constructing ChatGoogleGenerativeAI (Model: {target_model}, Temp: {temp})")
                try:
                    return ChatGoogleGenerativeAI(
                        model=target_model,
                        google_api_key=api_key,
                        temperature=temp,
                        max_retries=self.max_retries,
                        timeout=self.timeout,
                    )
                except Exception as inner_e:
                    logger.warning(f"[LLMService] Failed to initialize {target_model}, falling back to gemini-1.5-flash: {inner_e}")
                    return ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash",
                        google_api_key=api_key,
                        temperature=temp,
                        max_retries=self.max_retries,
                        timeout=self.timeout,
                    )
            except Exception as e:
                logger.error(f"[LLMService] Failed to initialize Google Chat Model: {e}. Attempting OpenAI fallback...")
                # Fall through to OpenAI if key is present

        # Check for OpenAI initialization
        if provider == "openai" or openai_key:
            try:
                from langchain_openai import ChatOpenAI
                api_key = openai_key
                if not api_key:
                    raise ValueError("OpenAI API key is not configured.")

                logger.info(f"[LLMService] Constructing ChatOpenAI (Model: {model}, Temp: {temp})")
                return ChatOpenAI(
                    model=model,
                    openai_api_key=api_key,
                    temperature=temp,
                    max_retries=self.max_retries,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.error(f"[LLMService] Failed to initialize OpenAI Chat Model: {e}.")

        # If both fail, or no keys are configured, use a fallback mock model
        logger.warning("[LLMService] API Keys are missing or invalid. Initializing fallback mock LLM layer.")
        return FakePlacementChatModel()

# Initialize singleton LLM Service instance
llm_service = LLMService()
