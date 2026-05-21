# d:\ps_03\company-intelligence-platform\backend\scratch\test_columns.py
import httpx
import json

SUPABASE_URL = "https://hkwessehtaonqaakzyvj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhrd2Vzc2VodGFvbnFhYWt6eXZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzMTEwMzksImV4cCI6MjA5MTg4NzAzOX0.4w-K12jyYlGT3dDXNa6ypRyhzheM2FkG5VLmmeB7GN8"

headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}

CANDIDATE_HEADERS = [
    # Domain 1
    "nameshort_name", "logo_url", "category", "incorporation_year", "overview_text", "nature_of_company",
    "headquarters_address", "operating_countries", "office_count", "office_locations", "vision_statement",
    "mission_statement", "core_values", "website_url", "website_quality", "website_rating",
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
    "contact_person_name", "contact_person_title", "contact_person_email", "contact_person_phone",
    
    # Extra common ones / other table indicators
    "company_id", "id", "created_at", "updated_at", "staging_id", "research_notes"
]

def check_columns(table_name):
    print(f"Testing candidate columns on table '{table_name}'...")
    valid_cols = []
    invalid_cols = []
    
    # We can test all columns in one single select statement!
    # If any column does not exist, the whole request will fail with 400 and detail which column didn't exist!
    # But to find exactly which ones DO exist, we can query individually or in a binary search.
    # Individually is fast enough for ~130 columns (uses parallel/async or sequential with keep-alive).
    # Let's do sequential with connection pooling or try to query individually:
    with httpx.Client(headers=headers) as client:
        for col in CANDIDATE_HEADERS:
            url = f"{SUPABASE_URL}/rest/v1/{table_name}?select={col}&limit=1"
            try:
                resp = client.get(url)
                if resp.status_code == 200:
                    valid_cols.append(col)
                elif resp.status_code == 400:
                    invalid_cols.append(col)
                else:
                    print(f"Unexpected status for col '{col}': {resp.status_code} ({resp.text})")
            except Exception as e:
                print(f"Error testing '{col}': {e}")
                
    print(f"\nDone! Out of {len(CANDIDATE_HEADERS)} candidate columns tested:")
    print(f"  - Valid: {len(valid_cols)}")
    print(f"  - Invalid: {len(invalid_cols)}")
    print("\nValid columns:")
    print(valid_cols)

if __name__ == "__main__":
    check_columns("company_intelligence")
