# d:\ps_03\company-intelligence-platform\backend\app\workflow\parameters.py
"""
Master Parameters Configuration
===============================
Defines all 163 BI parameters captured by the PlacementIntel dossier,
grouped into 10 logical clusters, and mapped to the 6 specialized agents.
"""

import json
import logging

# Dictionary of exactly 163 BI parameters with their cluster, agent, and difficulty
MASTER_PARAMETERS = {
    # --- Cluster 1: Corporate Identity & Basics ---
    "company_id": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "company_name": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "short_name": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "legal_name": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "incorporation_year": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "nature_of_company": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "logo_url": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "company_status": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "company_overview": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "mission_statement": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "vision_statement": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "headquarters_city": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "headquarters_address": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "office_locations": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "office_count": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "operating_countries": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "global_exposure": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},
    "crisis_behavior": {"cluster": "Corporate Identity & Basics", "agent": "website", "difficulty": "Low"},

    # --- Cluster 2: Financial Metrics & Operations ---
    "annual_revenues": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Low"},
    "annual_profits": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Low"},
    "profitability_status": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Low"},
    "revenue_mix": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Low"},
    "gross_margins": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Medium"},
    "ebitda": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Medium"},
    "operating_expenses": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Medium"},
    "net_income": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Medium"},
    "burn_rate": {"cluster": "Financial Metrics & Operations", "agent": "funding", "difficulty": "High"},
    "burn_multiplier": {"cluster": "Financial Metrics & Operations", "agent": "funding", "difficulty": "Medium"},
    "runway": {"cluster": "Financial Metrics & Operations", "agent": "funding", "difficulty": "High"},
    "cac": {"cluster": "Financial Metrics & Operations", "agent": "product", "difficulty": "Medium"},
    "clv": {"cluster": "Financial Metrics & Operations", "agent": "product", "difficulty": "Medium"},
    "cac_ltv_ratio": {"cluster": "Financial Metrics & Operations", "agent": "product", "difficulty": "High"},
    "payback_period": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Medium"},
    "arpu": {"cluster": "Financial Metrics & Operations", "agent": "product", "difficulty": "Medium"},
    "mrr": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Medium"},
    "arr": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Medium"},
    "ltv_to_cac_ratio": {"cluster": "Financial Metrics & Operations", "agent": "news", "difficulty": "Medium"},

    # --- Cluster 3: Funding & Valuation ---
    "total_capital_raised": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "latest_funding_round": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "latest_funding_amount_usd": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "latest_funding_date": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "lead_investors": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "investor_syndicate": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "company_valuation": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Medium"},
    "implied_valuation": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Medium"},
    "current_funding_stage": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "recent_round_details": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "exit_status": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Medium"},
    "ipo_date": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "stock_symbol": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "stock_exchange": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Low"},
    "debt_financing_amount": {"cluster": "Funding & Valuation", "agent": "funding", "difficulty": "Medium"},

    # --- Cluster 4: Workforce & Culture ---
    "employee_size": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Low"},
    "approximate_headcount": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Low"},
    "employee_turnover": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Medium"},
    "average_retention_tenure": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Medium"},
    "recruitment_status": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Low"},
    "open_roles_count": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Low"},
    "average_salary": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Medium"},
    "glassdoor_rating": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Low"},
    "indeed_rating": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Low"},
    "google_reviews_rating": {"cluster": "Workforce & Culture", "agent": "social", "difficulty": "Low"},
    "internal_mobility": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "High"},
    "remote_work_policy": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Low"},
    "commute_time": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Low"},
    "diversity_score": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Medium"},
    "leadership_rating": {"cluster": "Workforce & Culture", "agent": "linkedin", "difficulty": "Medium"},

    # --- Cluster 5: Product & Tech Stack ---
    "core_products": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "software_category": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "technological_stack": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "deployment_models": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "open_source_or_sdk": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "primary_database": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "frontend_framework": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "backend_language": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "cloud_provider": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "api_availability": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "security_certifications": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Medium"},
    "patents_count": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Medium"},
    "software_version": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "pricing_tiers": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "infrastructure_provider": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},
    "devops_tooling": {"cluster": "Product & Tech Stack", "agent": "product", "difficulty": "Low"},

    # --- Cluster 6: Market, SEO & Growth ---
    "primary_sector": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "industry": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "target_markets": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "market_share": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Medium"},
    "year_over_year_growth_rate": {"cluster": "Market, SEO & Growth", "agent": "news", "difficulty": "Low"},
    "tam": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Medium"},
    "sam": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Medium"},
    "som": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Medium"},
    "sales_motion": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "gtm_motion": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "website_url": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "website_rating": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "website_traffic_rank": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "seo_score": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},
    "domain_authority": {"cluster": "Market, SEO & Growth", "agent": "website", "difficulty": "Low"},

    # --- Cluster 7: Social, Sentiment & PR ---
    "primary_social_handle": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "active_social_links": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "twitter_handle": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "facebook_url": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "instagram_url": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "linkedin_url": {"cluster": "Social, Sentiment & PR", "agent": "linkedin", "difficulty": "Low"},
    "social_media_followers": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "community_sentiment": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "engagement_rating": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "news_headlines": {"cluster": "Social, Sentiment & PR", "agent": "news", "difficulty": "Low"},
    "recent_product_launches": {"cluster": "Social, Sentiment & PR", "agent": "news", "difficulty": "Low"},
    "known_controversies_or_complaints": {"cluster": "Social, Sentiment & PR", "agent": "news", "difficulty": "Low"},
    "brand_mentions": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Medium"},
    "customer_gaps_or_requests": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},
    "influencer_endorsements": {"cluster": "Social, Sentiment & PR", "agent": "social", "difficulty": "Low"},

    # --- Cluster 8: Contact & Governance ---
    "primary_contact_email": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "primary_phone_number": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "general_contact_email": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "contact_phone_number": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "founder_or_ceo": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "founder_linkedin": {"cluster": "Contact & Governance", "agent": "linkedin", "difficulty": "Low"},
    "key_executives": {"cluster": "Contact & Governance", "agent": "linkedin", "difficulty": "Low"},
    "board_members": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "legal_issues": {"cluster": "Contact & Governance", "agent": "news", "difficulty": "Low"},
    "regulatory_filings": {"cluster": "Contact & Governance", "agent": "news", "difficulty": "Medium"},
    "compliance_tags": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "data_privacy_officer": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "registered_address": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "whistleblower_policy": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},
    "board_size": {"cluster": "Contact & Governance", "agent": "website", "difficulty": "Low"},

    # --- Cluster 9: Operations & ESG ---
    "supply_chain_complexity": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Medium"},
    "logistics_partners": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "manufacturing_sites": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "key_suppliers": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "operational_footprint": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "carbon_footprint": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "esg_posture": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "sustainability_rating": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "energy_sources": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "waste_management": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "water_footprint": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "fair_trade_certifications": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "packaging_type": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "diversity_initiatives": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "charitable_contributions": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},
    "health_safety_rating": {"cluster": "Operations & ESG", "agent": "website", "difficulty": "Low"},

    # --- Cluster 10: Customer & Market Strategy ---
    "known_competitors": {"cluster": "Customer & Market Strategy", "agent": "product", "difficulty": "Low"},
    "competitive_advantages": {"cluster": "Customer & Market Strategy", "agent": "product", "difficulty": "Low"},
    "target_customer_segments": {"cluster": "Customer & Market Strategy", "agent": "product", "difficulty": "Low"},
    "customer_acquisition_channels": {"cluster": "Customer & Market Strategy", "agent": "product", "difficulty": "Low"},
    "net_promoter_score": {"cluster": "Customer & Market Strategy", "agent": "social", "difficulty": "Low"},
    "churn_rate": {"cluster": "Customer & Market Strategy", "agent": "news", "difficulty": "Low"},
    "customer_satisfaction": {"cluster": "Customer & Market Strategy", "agent": "social", "difficulty": "Low"},
    "nps": {"cluster": "Customer & Market Strategy", "agent": "social", "difficulty": "Low"},
    "training_spend": {"cluster": "Customer & Market Strategy", "agent": "linkedin", "difficulty": "Medium"},
    "tech_adoption_rating": {"cluster": "Customer & Market Strategy", "agent": "product", "difficulty": "Low"},
    "customer_lifetime_value": {"cluster": "Customer & Market Strategy", "agent": "news", "difficulty": "Low"},
    "retention_rate": {"cluster": "Customer & Market Strategy", "agent": "news", "difficulty": "Low"},
    "expansion_revenue": {"cluster": "Customer & Market Strategy", "agent": "news", "difficulty": "Medium"},
    "upsell_opportunities": {"cluster": "Customer & Market Strategy", "agent": "news", "difficulty": "Low"},
    "customer_support_channels": {"cluster": "Customer & Market Strategy", "agent": "website", "difficulty": "Low"},
    "helpdesk_software": {"cluster": "Customer & Market Strategy", "agent": "product", "difficulty": "Low"},
    "sla_commitments": {"cluster": "Customer & Market Strategy", "agent": "website", "difficulty": "Low"},
    "community_forum_members": {"cluster": "Customer & Market Strategy", "agent": "social", "difficulty": "Low"},
    "customer_testimonials_count": {"cluster": "Customer & Market Strategy", "agent": "website", "difficulty": "Low"},
}


# Mapping of the 6 specialized agent categories to their required Intelligence Domains
DOMAIN_MAPPING = {
    "website": {
        "name": "Domain 1: Corporate Identity & Governance",
        "description": "Foundation, HQ, Compliance, and Board.",
    },
    "news": {
        "name": "Domain 2: Market Dynamics & Strategic Position",
        "description": "Competitive edge, TAM/SAM/SOM, and Strategic Priorities.",
    },
    "funding": {
        "name": "Domain 3: Financial Health & Investment Profile",
        "description": "Revenues, Burn Rate, Valuation, and Investor History.",
    },
    "product": {
        "name": "Domain 4: Product & Technology Intelligence",
        "description": "Stack details, R&D, and Innovation Roadmap.",
    },
    "social": {
        "name": "Domain 5: Brand, Media & Public Sentiment",
        "description": "NPS, Glassdoor/Indeed ratings, and social engagement.",
    },
    "linkedin": {
        "name": "Domain 6: Talent, Hiring & Organizational Intelligence",
        "description": "Workforce size, turnover, executive roles, and internal experience parameters.",
    }
}

def is_valid_value(val: any) -> bool:
    """Determines if a value is complete and is not a placeholder or null."""
    if val is None:
        return False
    if isinstance(val, str):
        val_clean = val.strip().lower()
        # Exact matches for short patterns to avoid substring false positives
        invalid_exact = {
            "",  "null", "none", "n/a", "na", "unknown", "not disclosed", "pending", "undisclosed",
            "none.", "unknown.", "not disclosed.", "none reported.",
            "no general overview found.", "no mission details found.",
            "verified domain data", "in-depth verified metric", "high-fidelity reconciled estimate",
            "not available", "unable to locate"
        }
        if val_clean in invalid_exact:
            return False
        # Prefix-based checks for longer patterns
        invalid_prefixes = ["data unavailable", "data not available"]
        if any(val_clean.startswith(prefix) for prefix in invalid_prefixes):
            return False
    if isinstance(val, (list, dict)) and len(val) == 0:
        return False
    return True

def get_domain_allocation(row_data: dict) -> dict:
    """
    Standardized domain allocation logic.
    Groups parameters into 6 domains based on MASTER_PARAMETERS mapping.
    Enforces EXACT parameter names without aliases.
    """
    logger = logging.getLogger("company_intel.parameters")

    enriched_domains = {}
    for agent_name, domain_meta in DOMAIN_MAPPING.items():
        enriched_domains[domain_meta["name"]] = {
            "meta": {
                "agent_source": agent_name,
                "domain_description": domain_meta["description"],
                "domain_confidence_score": 1.0,
                "parameters_count": 0
            },
            "parameters": {}
        }

    db_keys = set(row_data.keys())

    # Validation: Identify orphan parameters (in DB but not in MASTER_PARAMETERS)
    orphan_parameters = [k for k in db_keys if k not in MASTER_PARAMETERS and k not in ["company_id", "id", "created_at", "updated_at", "name"]]
    if orphan_parameters:
        logger.warning(f"Orphan parameters detected (in DB but missing from schema): {orphan_parameters}")

    # Process all keys in MASTER_PARAMETERS
    for column_name in MASTER_PARAMETERS.keys():
        raw_value = row_data.get(column_name)

        meta = MASTER_PARAMETERS[column_name]
        agent = meta.get("agent", "website")
        cluster = meta.get("cluster", "General")
        difficulty = meta.get("difficulty", "Medium")

        domain_name = DOMAIN_MAPPING.get(agent, DOMAIN_MAPPING["website"])["name"]

        label = column_name.replace("_", " ").title()
        actual_value = raw_value if is_valid_value(raw_value) else None
        status = "Verified" if actual_value is not None else "Pending"

        enriched_domains[domain_name]["parameters"][column_name] = {
            "key": column_name,
            "label": label,
            "value": actual_value,
            "cluster": cluster,
            "difficulty": difficulty,
            "status": status
        }
        enriched_domains[domain_name]["meta"]["parameters_count"] += 1

    # Recalculate confidence scores dynamically
    for domain_name, data in enriched_domains.items():
        total = data["meta"]["parameters_count"]
        verified = sum(1 for p in data["parameters"].values() if p["status"] == "Verified")
        data["meta"]["domain_confidence_score"] = round(verified / total, 3) if total > 0 else 1.0

        # Log domain allocation as required
        logger.info(json.dumps({
            "domain": domain_name,
            "allocated_parameters": list(data["parameters"].keys())
        }))

    return enriched_domains


assert len(MASTER_PARAMETERS) == 163, f"Validation failure: expected 163 parameters, got {len(MASTER_PARAMETERS)}"

