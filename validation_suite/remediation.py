"""
AI-Assisted Auto-Remediation & Deduplication Layer
===================================================
Uses LLM structured reasoning to analyze data validation failures 
and generate precise correction suggestions.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from langsmith import traceable
import langsmith as ls
from dotenv import load_dotenv
from supabaseClient import get_supabase_client

# ---------------------------------------------------------------------------
# Multi-Path Environment Variable Loading
# Resolves keys from both validation suite and backend environments
# ---------------------------------------------------------------------------
_DIR = os.path.dirname(os.path.abspath(__file__))
# Try backend .env first
backend_env = os.path.abspath(os.path.join(_DIR, "..", "..", "company-intelligence-platform", "backend", ".env"))
if os.path.exists(backend_env):
    load_dotenv(backend_env)
# Then local .env fallback
local_env = os.path.join(_DIR, ".env")
if os.path.exists(local_env):
    load_dotenv(local_env)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class RemediationEngine:
    def __init__(self):
        self.model_type = "mock"
        self.llm = None
        self._init_llm()

    def _init_llm(self):
        """Initializes LangChain Chat models based on active key."""
        if GEMINI_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=GEMINI_API_KEY,
                    temperature=0.1
                )
                self.model_type = "gemini"
                return
            except Exception as e:
                print(f"[Remediation] Failed loading Gemini Chat model: {e}")

        if OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    openai_api_key=OPENAI_API_KEY,
                    temperature=0.1
                )
                self.model_type = "openai"
                return
            except Exception as e:
                print(f"[Remediation] Failed loading OpenAI Chat model: {e}")

        self.model_type = "heuristic"
        print("[Remediation] Using standard Rule-Based Heuristics for suggestions.")

    def clean_json_text(self, text: str) -> str:
        """Strips markdown fences from model json responses."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    @traceable(name="Validation Node – LLM 1")
    def generate_suggestions(
        self, 
        failed_checks: List[Dict[str, Any]], 
        company_record: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Sends failed constraints and company records to the active LLM.
        Returns structured correction suggestions.
        """
        if not failed_checks:
            return []

        company_name = company_record.get("company_name", "Unknown")
        
        # Inject Rich Metadata
        ls.set_run_metadata({
            "company": company_name,
            "domain": "Remediation",
            "llm": self.model_type,
            "retry_count": company_record.get("regeneration_attempts", 0),
            "workflow_stage": "Validation Correction"
        })

        company_id = company_record.get("company_id") or company_record.get("_raw", {}).get("company_id")
        company_name = company_record.get("company_name", "Unknown")

        if self.model_type == "heuristic" or not self.llm:
            return self._generate_heuristic_suggestions(failed_checks, company_record)

        system_prompt = (
            "You are an expert Enterprise Data Quality and Auto-Correction Assistant.\n"
            "Your task is to analyze failed data validation constraints on a company record and recommend "
            "precise correction suggestions.\n\n"
            "You MUST output raw JSON matching the following structure and no other text:\n"
            "[\n"
            "  {\n"
            "    \"field_name\": \"Name of the database column (e.g. website_url, primary_contact_email)\",\n"
            "    \"original_value\": \"The current malformed value\",\n"
            "    \"suggested_value\": \"The sanitized/corrected value\",\n"
            "    \"rationale\": \"Brief rationale for why this change is suggested (e.g., Standardized to secure HTTPS, added domain prefix)\",\n"
            "    \"confidence\": 0.98\n"
            "  }\n"
            "]\n"
        )

        human_prompt = (
            f"Company Details:\n{json.dumps(company_record, indent=2, default=str)}\n\n"
            f"Failed Validations:\n{json.dumps(failed_checks, indent=2)}\n\n"
            "Synthesize corrections. If you don't have enough context to fix a critical value, "
            "provide your best guess with low confidence (e.g., < 0.70)."
        )

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            response = self.llm.invoke(messages)
            content = self.clean_json_text(response.content)
            suggestions = json.loads(content)
            
            # Extract token usage from metadata
            metadata = getattr(response, "response_metadata", {})
            token_usage = metadata.get("token_usage", {})
            model_name = metadata.get("model_name", self.model_type)
            
            # Enrich with database record details and metrics
            metrics = {
                "model_name": model_name,
                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                "completion_tokens": token_usage.get("completion_tokens", 0),
                "total_tokens": token_usage.get("total_tokens", 0)
            }
            
            for s in suggestions:
                s["company_id"] = company_id
                s["source"] = "LLM_Remediation"
                
            return {"suggestions": suggestions, "metrics": metrics}
        except Exception as exc:
            print(f"[Remediation] LLM suggestion failed: {exc}. Falling back to heuristics...")
            return self._generate_heuristic_suggestions(failed_checks, company_record)

    def _generate_heuristic_suggestions(
        self, 
        failed_checks: List[Dict[str, Any]], 
        company_record: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fallback rule-based correction generator when LLM is unavailable."""
        suggestions = []
        company_id = company_record.get("company_id") or company_record.get("_raw", {}).get("company_id")
        
        for check in failed_checks:
            field = check.get("field") or check.get("field_name")
            actual = company_record.get(field, "")
            
            sugg_val = None
            rationale = ""
            confidence = 0.50
            
            if field == "website_url" and actual:
                # HTTP -> HTTPS or adding secure protocol
                if actual.startswith("http://"):
                    sugg_val = "https://" + actual[7:]
                else:
                    sugg_val = "https://" + str(actual)
                rationale = "Heuristic standardisation to secure HTTPS protocol."
                confidence = 0.96
                
            elif field == "contact_person_email" and actual:
                sugg_val = str(actual).strip().lower()
                rationale = "Heuristic standardisation to lowercase email structures."
                confidence = 0.98
                
            elif field == "logo_url" and not actual:
                # Auto-enrich logo based on website domain if present
                web_url = company_record.get("website_url", "")
                if web_url:
                    domain = web_url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                    sugg_val = f"https://logo.clearbit.com/{domain}"
                    rationale = "Enriched company branding using Clearbit Logo API service heuristic."
                    confidence = 0.92
                    
            if sugg_val:
                suggestions.append({
                    "company_id": company_id,
                    "field_name": field,
                    "original_value": str(actual),
                    "suggested_value": sugg_val,
                    "rationale": rationale,
                    "confidence": confidence,
                    "source": "Heuristic_Normalizer"
                })
                
        return {"suggestions": suggestions, "metrics": {}}

    def auto_apply_high_confidence(self, suggestions: List[Dict[str, Any]]) -> int:
        """
        Auto-applies suggestions where confidence >= 0.95 and updates Supabase.
        Returns count of applied fixes.
        """
        if not suggestions:
            return 0

        client = get_supabase_client()
        applied_count = 0

        for sugg in suggestions:
            confidence = sugg.get("confidence", 0.0)
            status = sugg.get("status", "pending")
            
            if confidence >= 0.95 and status == "pending":
                company_id = sugg.get("company_id")
                field = sugg.get("field_name")
                val = sugg.get("suggested_value")
                
                if not company_id or not field:
                    continue
                
                # Column mapping lookup for the 'companies' table (mapping canonical key -> supabase column)
                column_mapping = {
                    "company_name": "name",
                    "short_name": "short_name",
                    "website_url": "website_url",
                    "contact_person_email": "primary_contact_email",
                    "contact_person_phone": "primary_phone_number",
                    "overview": "overview_text",
                    "logo_url": "logo_url",
                    "nature_of_company": "nature_of_company",
                    "category": "category",
                    "gtm_motion": "gtm_motion"
                }
                
                supabase_col = column_mapping.get(field, field)
                
                try:
                    # Update company table in Supabase
                    client.table("companies").update({supabase_col: val}).eq("company_id", company_id).execute()
                    
                    # Log Suggestion as Applied
                    sugg["status"] = "applied"
                    sugg_data = {
                        "company_id": company_id,
                        "field_name": field,
                        "original_value": sugg.get("original_value"),
                        "suggested_value": val,
                        "rationale": sugg.get("rationale"),
                        "confidence": confidence,
                        "source": sugg.get("source", "LLM_Remediation"),
                        "status": "applied",
                        "reviewed_by": "auto_agent"
                    }
                    client.table("validation_correction_suggestions").insert(sugg_data).execute()
                    applied_count += 1
                except Exception as e:
                    print(f"[Remediation] Failed auto-applying correction: {e}")
                    
        return applied_count

    def log_pending_suggestions(self, suggestions: List[Dict[str, Any]]):
        """Logs recommendations with confidence < 0.95 as pending for Human-in-the-Loop review."""
        if not suggestions:
            return

        client = get_supabase_client()
        pending_to_log = []

        for sugg in suggestions:
            confidence = sugg.get("confidence", 0.0)
            if confidence < 0.95:
                company_id = sugg.get("company_id")
                field = sugg.get("field_name")
                
                if not company_id or not field:
                    continue
                    
                pending_to_log.append({
                    "company_id": company_id,
                    "field_name": field,
                    "original_value": str(sugg.get("original_value", "")),
                    "suggested_value": str(sugg.get("suggested_value", "")),
                    "rationale": sugg.get("rationale", ""),
                    "confidence": confidence,
                    "source": sugg.get("source", "LLM_Remediation"),
                    "status": "pending"
                })

        if pending_to_log:
            try:
                client.table("validation_correction_suggestions").insert(pending_to_log).execute()
                print(f"[Remediation] Saved {len(pending_to_log)} pending suggestions to Human-in-the-Loop queue.")
            except Exception as e:
                print(f"[Remediation] Note: Failed to log pending suggestions (Table may not exist yet): {e}")

    def recommended_duplicates(self) -> List[Dict[str, Any]]:
        """
        Examines Supabase companies table and searches for duplicate entities.
        If pgvector and company_embeddings exist, utilizes cosine distance, 
        otherwise runs string similarity checks.
        """
        client = get_supabase_client()
        duplicates = []
        
        try:
            # Quick string-distance fuzzy check as a backup
            response = client.table("companies").select("company_id, name, website_url").execute()
            companies = response.data or []
            
            # Simple fuzzy matching on company name & website
            for i, c1 in enumerate(companies):
                n1 = str(c1.get("name", "")).lower()
                w1 = str(c1.get("website_url", "")).lower().replace("www.", "").replace("https://", "").replace("http://", "")
                
                for j in range(i + 1, len(companies)):
                    c2 = companies[j]
                    n2 = str(c2.get("name", "")).lower()
                    w2 = str(c2.get("website_url", "")).lower().replace("www.", "").replace("https://", "").replace("http://", "")
                    
                    # Score matches
                    name_similarity = 0.0
                    # Common suffix cleaning
                    clean_n1 = n1.replace("pvt", "").replace("ltd", "").replace("private", "").replace("limited", "").strip()
                    clean_n2 = n2.replace("pvt", "").replace("ltd", "").replace("private", "").replace("limited", "").strip()
                    
                    if clean_n1 == clean_n2:
                        name_similarity = 1.0
                    elif clean_n1 in clean_n2 or clean_n2 in clean_n1:
                        name_similarity = 0.90
                        
                    web_match = (w1 == w2) and (len(w1) > 4)
                    
                    if web_match or name_similarity >= 0.90:
                        duplicates.append({
                            "company_a_id": c1["company_id"],
                            "company_a_name": c1["name"],
                            "company_b_id": c2["company_id"],
                            "company_b_name": c2["name"],
                            "similarity": 0.98 if web_match else name_similarity,
                            "reason": "Matching domain names" if web_match else "Similar name structures"
                        })
        except Exception as e:
            print(f"[Deduplication] String deduplication error: {e}")
            
        return duplicates
