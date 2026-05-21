# d:\ps_03\company-intelligence-platform\backend\scratch\test_all_possible_columns.py
import sys
import os
import httpx

# Add backend directory to path to import MASTER_PARAMETERS
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workflow.parameters import MASTER_PARAMETERS

SUPABASE_URL = "https://hkwessehtaonqaakzyvj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhrd2Vzc2VodGFvbnFhYWt6eXZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzMTEwMzksImV4cCI6MjA5MTg4NzAzOX0.4w-K12jyYlGT3dDXNa6ypRyhzheM2FkG5VLmmeB7GN8"

headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}

# Collect all potential columns from MASTER_PARAMETERS keys and the user prompt headers
candidates = list(MASTER_PARAMETERS.keys())

# Let's add extra candidate columns based on the user prompt domains and splitting
prompt_headers = [
    # Domain 1
    "nameshort_name", "name", "short_name", "logo_url", "category", "incorporation_year", "overview_text", 
    "nature_of_company", "headquarters_address", "operating_countries", "office_count", "office_locations", 
    "vision_statement", "mission_statement", "core_values", "website_url", "website_quality", "website_rating", 
    "website_traffic_rank", "regulatory_status", "legal_issues", "board_members", "company_maturity",
    
    # Domain 2
    "focus_sectors", "competitive_advantages", "weaknesses_gaps", "key_challenges_needs", "key_competitors", 
    "brand_sentiment_score", "event_participation", "market_share_percentage", "benchmark_vs_peers", 
    "future_projections", "strategic_priorities", "industry_associations", "case_studies", 
    "go_to_market_strategy", "innovation_roadmap", "product_pipeline", "tam", "sam", "som", 
    "tech_adoption_rating", "external_recognition",
    
    # Domain 3
    "annual_revenue", "annual_profit", "revenue_mix", "valuation", "yoy_growth_rate", "profitability_status", 
    "key_investors", "recent_funding_rounds", "total_capital_raised", "sales_motion", "customer_acquisition_cost", 
    "customer_lifetime_value", "cac_ltv_ratio", "churn_rate", "burn_rate", "runway_months", "burn_multiplier", 
    "exit_strategy_history",
    
    # Domain 4
    "offerings_description", "top_customers", "core_value_proposition", "unique_differentiators", 
    "technology_partners", "ai_ml_adoption_level", "intellectual_property", "r_and_d_investment", 
    "tech_stack", "cybersecurity_postures", "automation_level", "tools_access", "supply_chain_dependencies", 
    "geopolitical_risks", "macro_risks",
    
    # Domain 5
    "employee_size", "hiring_velocity", "employee_turnover", "avg_retention_tenure", "remote_policy_details", 
    "diversity_metrics", "work_culture_summary", "manager_quality", "psychological_safety", "feedback_culture", 
    "diversity_inclusion_score", "ethical_standards", "typical_hours", "overtime_expectations", "weekend_work", 
    "flexibility_level", "leave_policy", "burnout_risk", "onboarding_quality", "learning_culture", 
    "exposure_quality", "mentorship_availability", "internal_mobility", "promotion_clarity", "role_clarity", 
    "early_ownership", "work_impact", "execution_thinking_balance", "cross_functional_exposure",
    
    # Domain 6
    "social_media_followers", "glassdoor_rating", "indeed_rating", "google_rating", "linkedin_url", 
    "twitter_handle", "facebook_url", "instagram_url", "ceo_name", "ceo_linkedin_url", "key_leaders", 
    "warm_intro_pathways", "decision_maker_access", "primary_contact_email", "primary_phone_number", 
    "contact_person_name", "contact_person_title", "contact_person_email", "contact_person_phone"
]

for col in prompt_headers:
    if col not in candidates:
        candidates.append(col)

# Extra common database audit and key columns
extra_cols = ["id", "company_id", "created_at", "updated_at", "staging_id", "research_notes", "company_name", "status"]
for col in extra_cols:
    if col not in candidates:
        candidates.append(col)

def test_columns():
    valid = []
    invalid = []
    
    print(f"Testing {len(candidates)} columns on table 'company_intelligence'...")
    with httpx.Client(headers=headers) as client:
        for col in candidates:
            url = f"{SUPABASE_URL}/rest/v1/company_intelligence?select={col}&limit=1"
            try:
                resp = client.get(url)
                if resp.status_code == 200:
                    valid.append(col)
                elif resp.status_code == 400:
                    invalid.append(col)
                else:
                    print(f"Unexpected status for '{col}': {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"Error testing '{col}': {e}")
                
    print("\nRESULTS FOR table 'company_intelligence':")
    print(f"Total valid columns: {len(valid)}")
    print("Valid columns:")
    print(valid)
    
    # Write results to file
    with open("scratch/valid_columns.json", "w") as f:
        import json
        json.dump(valid, f, indent=2)
    print("Saved valid columns list to scratch/valid_columns.json")

if __name__ == "__main__":
    test_columns()
