import json
import logging
import random
from typing import Dict, Any, List, Optional
from langsmith import traceable
import langsmith as ls
from app.agents.base_agent import BaseResearchAgent
from app.tools.search_tool import execute_search

from app.core.observability import TracingHelper

logger = logging.getLogger("company_intel.agents")

# ═══════════════════════════════════════════════════════════════════════════
# 1. WEBSITE RESEARCH AGENT
# ═══════════════════════════════════════════════════════════════════════════
class WebsiteResearchAgent(BaseResearchAgent):
    def __init__(self):
        super().__init__("WebsiteResearchAgent")

    @traceable(name="Research Node – Website")
    def research_company(self, company_name: str, custom_query: str = "", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Initiated website research for: {company_name}")

        # Production-grade metadata & tags
        TracingHelper.set_standard_metadata(
            company=company_name,
            stage="Research-Website",
            model=self.model_type,
            provider=self.provider,
            extra={"retry_count": (config or {}).get("retry_count", 0)}
        )
        TracingHelper.add_tags(["company-research", "website-audit", "production"])

        query = f"company {company_name} website, official homepage, headquarters address, email and contact phone"
        search_results = execute_search(query, company_name)

        system_prompt = """
        You are a Website Research Agent.
        Analyze search results to extract key corporate info about the target company.
        Return a structured JSON document with these EXACT keys:
        - 'company_overview': A concise 2-3 sentence description.
        - 'mission_statement': Corporate mission or vision statement.
        - 'headquarters_city': City where corporate HQ is located.
        - 'headquarters_address': Full physical mailing address of headquarters.
        - 'general_contact_email': General or customer support email.
        - 'contact_phone_number': Official telephone number.
        - 'founder_or_ceo': Name of the founder(s) or CEO.
        Do not add other keys. Ensure values are accurate.
        """

        human_prompt = f"Target Company: {company_name}\nSearch Results:\n{json.dumps(search_results, indent=2)}"
        if custom_query:
            human_prompt += f"\nCustom User Request: {custom_query}"

        res = self.invoke_llm(system_prompt, human_prompt, config=config)
        return {"data": res["json"], "tokens": res["tokens"], "metrics": res["metrics"]}


# ═══════════════════════════════════════════════════════════════════════════
# 2. LINKEDIN RESEARCH AGENT
# ═══════════════════════════════════════════════════════════════════════════
class LinkedInResearchAgent(BaseResearchAgent):
    def __init__(self):
        super().__init__("LinkedInResearchAgent")

    @traceable(name="Research Node – LinkedIn")
    def research_company(self, company_name: str, custom_query: str = "", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Initiated LinkedIn audit for: {company_name}")

        # Production-grade metadata & tags
        TracingHelper.set_standard_metadata(
            company=company_name,
            stage="Research-LinkedIn",
            model=self.model_type,
            provider=self.provider,
            extra={"retry_count": (config or {}).get("retry_count", 0)}
        )
        TracingHelper.add_tags(["company-research", "linkedin-audit", "production"])

        query = f"company {company_name} LinkedIn page, employee size, key executives list, hiring trends"
        search_results = execute_search(query, company_name)

        system_prompt = """
        You are a LinkedIn Research Agent.
        Analyze search results to retrieve social capital data.
        Return a structured JSON document with these EXACT keys:
        - 'linkedin_url': URL of the official LinkedIn company page.
        - 'approximate_headcount': Number or range representing employee size (e.g. 150-200).
        - 'key_executives': List of key executives and their roles. Format as objects: [{'name': 'X', 'role': 'CEO'}].
        - 'office_locations': List of other global physical offices.
        - 'recruitment_status': Text detailing active recruiting / hiring activity.
        Do not add other keys.
        """

        human_prompt = f"Target Company: {company_name}\nSearch Results:\n{json.dumps(search_results, indent=2)}"
        res = self.invoke_llm(system_prompt, human_prompt, config=config)
        return {"data": res["json"], "tokens": res["tokens"], "metrics": res["metrics"]}


# ═══════════════════════════════════════════════════════════════════════════
# 3. NEWS RESEARCH AGENT
# ═══════════════════════════════════════════════════════════════════════════
class NewsResearchAgent(BaseResearchAgent):
    def __init__(self):
        super().__init__("NewsResearchAgent")

    @traceable(name="Research Node – News")
    def research_company(self, company_name: str, custom_query: str = "", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Scanning recent news for: {company_name}")

        # Production-grade metadata & tags
        TracingHelper.set_standard_metadata(
            company=company_name,
            stage="Research-News",
            model=self.model_type,
            provider=self.provider,
            extra={"retry_count": (config or {}).get("retry_count", 0)}
        )
        TracingHelper.add_tags(["company-research", "news-scan", "production"])

        query = f"company {company_name} news, press releases, acquisitions, announcements, controversies last 12 months"
        search_results = execute_search(query, company_name)

        system_prompt = """
        You are a News and PR Research Agent.
        Scan latest search results to extract key milestones and brand sentiment.
        Return a structured JSON document with these EXACT keys:
        - 'news_headlines': List of 2-3 major news headlines with dates and brief context.
        - 'recent_product_launches': List of product announcements.
        - 'mergers_or_acquisitions': Text detailing mergers/acquisitions, or 'None' if not found.
        - 'known_controversies_or_complaints': Text outlining major regulatory issues, outages, or negative reviews, or 'None' if healthy.
        Do not add other keys.
        """

        human_prompt = f"Target Company: {company_name}\nSearch Results:\n{json.dumps(search_results, indent=2)}"
        res = self.invoke_llm(system_prompt, human_prompt, config=config)
        return {"data": res["json"], "tokens": res["tokens"], "metrics": res["metrics"]}


# ═══════════════════════════════════════════════════════════════════════════
# 4. FUNDING / INVESTOR RESEARCH AGENT
# ═══════════════════════════════════════════════════════════════════════════
class FundingInvestorAgent(BaseResearchAgent):
    def __init__(self):
        super().__init__("FundingInvestorAgent")

    @traceable(name="Research Node – Funding")
    def research_company(self, company_name: str, custom_query: str = "", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Initiated financial inspection for: {company_name}")

        # Production-grade metadata & tags
        TracingHelper.set_standard_metadata(
            company=company_name,
            stage="Research-Funding",
            model=self.model_type,
            provider=self.provider,
            extra={"retry_count": (config or {}).get("retry_count", 0)}
        )
        TracingHelper.add_tags(["company-research", "funding-audit", "production"])

        query = f"company {company_name} funding rounds, total capital raised, Sequoia Andreessen Crunchbase, valuation"
        search_results = execute_search(query, company_name)

        system_prompt = """
        You are a Funding & Investor Research Agent.
        Analyze search results to extract venture backing details.
        Return a structured JSON document with these EXACT keys:
        - 'total_capital_raised': Numerical valuation or string representing total venture capital raised (e.g. '$24.5M').
        - 'current_funding_stage': Stage (e.g. Seed, Series A, Series B, IPO, Bootstrap).
        - 'latest_funding_amount_usd': Amount raised in the latest round.
        - 'latest_funding_date': Date of the latest funding event.
        - 'lead_investors': List of Venture Capital firms or lead angels involved.
        - 'company_valuation': Estimated valuation or 'Not Disclosed'.
        - 'implied_valuation': Implied valuation based on latest round or 'Not Disclosed'.
        Do not add other keys.
        """

        human_prompt = f"Target Company: {company_name}\nSearch Results:\n{json.dumps(search_results, indent=2)}"
        res = self.invoke_llm(system_prompt, human_prompt, config=config)
        return {"data": res["json"], "tokens": res["tokens"], "metrics": res["metrics"]}


# ═══════════════════════════════════════════════════════════════════════════
# 5. PRODUCT / TECH STACK AGENT
# ═══════════════════════════════════════════════════════════════════════════
class ProductResearchAgent(BaseResearchAgent):
    def __init__(self):
        super().__init__("ProductResearchAgent")

    @traceable(name="Research Node – Product")
    def research_company(self, company_name: str, custom_query: str = "", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Conducting product architecture audit for: {company_name}")

        # Production-grade metadata & tags
        TracingHelper.set_standard_metadata(
            company=company_name,
            stage="Research-Product",
            model=self.model_type,
            provider=self.provider,
            extra={"retry_count": (config or {}).get("retry_count", 0)}
        )
        TracingHelper.add_tags(["company-research", "product-audit", "production"])

        query = f"company {company_name} product catalog, tech stack, software libraries, hosting provider, Github SDKs"
        search_results = execute_search(query, company_name)

        system_prompt = """
        You are a Product & Technology Stack Research Agent.
        Identify the company's products, technological skeleton, competitors, and advantages.
        Return a structured JSON document with these EXACT keys:
        - 'core_products': List of core software, products, or service offerings.
        - 'software_category': The main niche category (e.g., developer tools, AI agent SaaS, fintech database).
        - 'technological_stack': List of programming languages, libraries, platforms, databases (e.g. Python, React, FastAPI, Supabase, AWS).
        - 'deployment_models': Cloud, local container, or hybrid models.
        - 'open_source_or_sdk': Text explaining if they offer open source components or developer SDKs.
        - 'known_competitors': List of key competitor company names.
        - 'competitive_advantages': List of key competitive advantages for the target company.
        Do not add other keys.
        """

        human_prompt = f"Target Company: {company_name}\nSearch Results:\n{json.dumps(search_results, indent=2)}"
        res = self.invoke_llm(system_prompt, human_prompt, config=config)
        return {"data": res["json"], "tokens": res["tokens"], "metrics": res["metrics"]}


# ═══════════════════════════════════════════════════════════════════════════
# 6. SOCIAL MEDIA RESEARCH AGENT
# ═══════════════════════════════════════════════════════════════════════════
class SocialMediaAgent(BaseResearchAgent):
    def __init__(self):
        super().__init__("SocialMediaAgent")

    @traceable(name="Research Node – Social")
    def research_company(self, company_name: str, custom_query: str = "", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Analyzing social sentiment for: {company_name}")

        # Production-grade metadata & tags
        TracingHelper.set_standard_metadata(
            company=company_name,
            stage="Research-Social",
            model=self.model_type,
            provider=self.provider,
            extra={"retry_count": (config or {}).get("retry_count", 0)}
        )
        TracingHelper.add_tags(["company-research", "social-sentiment", "production"])

        query = f"company {company_name} Twitter account, Youtube channel, Reddit discussions, brand sentiment score, community reviews"
        search_results = execute_search(query, company_name)

        system_prompt = """
        You are a Social Media & Sentiment Research Agent.
        Inspect community channels to extract customer perception.
        Return a structured JSON document with these EXACT keys:
        - 'primary_social_handle': Official Twitter/X or main social handle (e.g. '@companyintel').
        - 'active_social_links': List of active social channel links.
        - 'community_sentiment': A rating (e.g., 'Positive', 'Highly Positive', 'Neutral', 'Mixed') with brief feedback.
        - 'customer_gaps_or_requests': Major product complaints or requests discussed in social threads, or 'None'.
        - 'engagement_rating': Scale of engagement (e.g. Low, Moderate, Active, High).
        Do not add other keys.
        """

        human_prompt = f"Target Company: {company_name}\nSearch Results:\n{json.dumps(search_results, indent=2)}"
        res = self.invoke_llm(system_prompt, human_prompt, config=config)
        return {"data": res["json"], "tokens": res["tokens"], "metrics": res["metrics"]}


# ═══════════════════════════════════════════════════════════════════════════
# 7. DOSSIER SYNTHESIS AGENT (PREMIUM COMPILER)
# ═══════════════════════════════════════════════════════════════════════════
class DossierSynthesisAgent(BaseResearchAgent):
    def __init__(self):
        super().__init__("DossierSynthesisAgent")

    @traceable(name="Dossier Synthesis Engine")
    def synthesize_dossier(self, company_name: str, consolidated_profile: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Synthesizing dynamic enterprise dossier for: {company_name}")

        TracingHelper.set_standard_metadata(
            company=company_name,
            stage="Dossier-Synthesis",
            model=self.model_type,
            provider=self.provider
        )
        TracingHelper.add_tags(["company-research", "dossier-synthesis", "production"])

        # Determine the company type and construct tailored guidelines
        # Detect type based on stock exchange, headcount, series, or keyword
        headcount = str(consolidated_profile.get("approximate_headcount") or "").lower()
        funding_stage = str(consolidated_profile.get("current_funding_stage") or "").lower()
        sector = str(consolidated_profile.get("software_category") or "Technology").strip()
        
        is_startup = any(k in funding_stage for k in ["seed", "series", "venture", "pre-ipo", "early"]) or (consolidated_profile.get("total_capital_raised") is not None and "$" in str(consolidated_profile.get("total_capital_raised")))
        is_public = consolidated_profile.get("stock_symbol") is not None and str(consolidated_profile.get("stock_symbol")).lower() not in ["none", "n/a", "unknown", ""]
        is_consulting = any(k in sector.lower() for k in ["consulting", "services", "advisor", "integrator"])
        
        company_type = "SaaS/Enterprise"
        if is_public:
            company_type = "Public Enterprise"
        elif is_startup:
            company_type = "High-Growth Startup"
        elif is_consulting:
            company_type = "Consulting/Global Services"

        system_prompt = f"""
        You are a Premium Dossier Synthesis Agent.
        Your task is to compile a highly customized, dynamic, and factual business dossier for a '{company_type}' company.
        You must synthesize the provided company's real consolidated research data and generate a professional, high-fidelity JSON document.
        
        CRITICAL RULES:
        - NEVER inject generic template placeholders (e.g. HubSpot, Salesforce, Retool) unless they are truly relevant competitors.
        - If certain metrics or funding details are unavailable, explicitly mark them as "Data unavailable from verified sources".
        - Choose sector-appropriate competitors and SWOT dimensions based on the company's real domain and size.
        
        Return a structured JSON document with these EXACT keys:
        - 'summary': A beautifully written, 2-3 sentence executive brief that summarizes the company's core value proposition, leadership, size, and current market posture.
        - 'market_analysis': A dictionary with:
            * 'primary_sector': main business sector.
            * 'global_headquarters': HQ address.
            * 'scale_assessment': business size class (e.g. 'Enterprise/Global Scale', 'Mid-Market Growth', 'Early Stage Startup').
            * 'market_demand': current demand description (1 sentence).
            * 'operational_footprint': list of key global office locations.
            * 'ceo': founder or CEO name.
            * 'telephone': contact telephone or email/phone fallback.
            * 'email': contact email or general fallback.
        - 'competitor_insights': A dictionary with:
            * 'known_competitors': list of actual competitor names based on industry segment.
            * 'competitive_advantages': list of specific competitive edges of the target company.
            * 'swot_analysis': dictionary with 'strengths' (list of 3), 'weaknesses' (list of 2), 'opportunities' (list of 2), 'threats' (list of 2).
        - 'technology_stack': list of core technologies, languages, frameworks utilized.
        - 'funding_status': A dictionary with:
            * 'total_capital_usd': total venture funding or "Data unavailable from verified sources".
            * 'current_series': funding stage (e.g., Series B, IPO, Bootstrap, Public).
            * 'recent_round_details': dictionary with 'amount', 'date', 'lead_investor'.
            * 'investor_syndicate': list of venture backers/investors.
            * 'implied_valuation': valuation string or "Data unavailable from verified sources".
        - 'risk_opportunity_analysis': A dictionary with:
            * 'overall_risk_level': risk rating (e.g., 'Low', 'Moderate', 'High').
            * 'gaps_identified': customer gaps, customer requests, or general organizational gaps.
            * 'critical_fail_safes': list of 2 key corporate risk mitigation attributes (e.g. compliance, cash runway, robust data privacy).
        """

        human_prompt = f"""
        Target Company: {company_name}
        Company Type: {company_type}
        Consolidated Research Profile:
        {json.dumps(consolidated_profile, indent=2)}
        """

        res = self.invoke_llm(system_prompt, human_prompt, config=config)
        return {"data": res["json"], "tokens": res["tokens"], "metrics": res["metrics"]}
