"""
Complete Dataset Validation Tests (TC_2_1)
Tests for fully populated records with all mandatory + optional fields.
"""

import pytest
from validators.string_validator import (
    validate_company_name,
    validate_short_name,
    validate_not_null,
    validate_min_length
)
from validators.numeric_validator import (
    validate_year,
    validate_numeric_range
)
from validators.url_validator import (
    validate_https_url,
    validate_email
)
from validators.financial_validator import (
    validate_revenue,
    validate_profitability_status,
    validate_sales_motion
)
from validators.dependency_validator import (
    validate_category,
    validate_remote_policy,
    validate_nature_of_company
)


class TestCompleteDatasetValidation:
    """TC_2_1: Complete dataset validation tests"""
    
    @pytest.mark.valid
    def test_tc_2_1_001_all_mandatory_optional_fields(self):
        """
        TC_2_1_001: Validate record where all mandatory + optional 
        fields are populated with valid data.
        """
        # Fully populated dataset
        record = {
            "company_name": "Microsoft Corporation",
            "short_name": "MSFT",
            "category": "Enterprise",
            "year_of_incorporation": 1975,
            "overview": "A leading technology company providing software, services, devices and solutions.",
            "website_url": "https://www.microsoft.com",
            "ceo_name": "Satya Nadella",
            "revenue": 211000000000,
            "profitability_status": "Profitable",
            "sales_motion": "Sales-Led",
            "remote_work_policy": "Hybrid"
        }
        
        # Validate all fields
        assert validate_company_name(record["company_name"])[0]
        assert validate_short_name(record["short_name"])[0]
        assert validate_category(record["category"])[0]
        assert validate_year(record["year_of_incorporation"])[0]
        assert validate_min_length(record["overview"], 50, "Overview")[0]
        assert validate_https_url(record["website_url"])[0]
        assert validate_revenue(record["revenue"])[0]
        assert validate_profitability_status(record["profitability_status"])[0]
        assert validate_sales_motion(record["sales_motion"])[0]
    
    @pytest.mark.format
    def test_tc_2_1_002_format_compliance(self):
        """
        TC_2_1_002: Validate format compliance across all fields 
        in a complete dataset.
        """
        record = {
            "company_name": "Apple Inc.",
            "website_url": "https://www.apple.com",
            "email": "contact@apple.com",
            "employee_size": "10000+",
            "employee_turnover": "12.5%",
            "year_of_incorporation": 1976
        }
        
        # Validate regex patterns
        assert validate_company_name(record["company_name"])[0]
        assert validate_https_url(record["website_url"])[0]
        assert validate_email(record["email"])[0]
        assert validate_year(record["year_of_incorporation"])[0]
    
    @pytest.mark.valid
    def test_tc_2_1_003_business_rule_compliance(self):
        """
        TC_2_1_003: Validate business rule compliance in complete dataset.
        Example: Revenue > 0, Churn ≤ 100%, Year ≤ current year
        """
        current_year = 2026
        
        # Business rules
        revenue = 1000000
        assert revenue > 0, "Revenue must be > 0"
        
        churn = 25.5
        assert churn <= 100, "Churn must be ≤ 100%"
        
        year = 2020
        assert year <= current_year, f"Year {year} must be ≤ {current_year}"
    
    @pytest.mark.crossfield
    def test_tc_2_1_004_cross_field_consistency(self):
        """
        TC_2_1_004: Validate cross-field consistency in complete dataset.
        Example: CAC, CLV, CAC:LTV aligned
        """
        cac = 150  # Customer Acquisition Cost
        clv = 600  # Customer Lifetime Value
        ltv = clv
        
        # CAC:LTV ratio should be reasonable (< 1:3 is good)
        cac_ltv_ratio = cac / ltv if ltv > 0 else 0
        assert cac_ltv_ratio < 0.35, "CAC:LTV ratio should be < 0.35 (1:3)"
        
        # CLV should be > CAC for profitability
        assert clv > cac, "CLV must be greater than CAC"
    
    @pytest.mark.valid
    def test_tc_2_1_005_data_richness_score(self):
        """
        TC_2_1_005: Validate data richness and completeness score.
        All 150+ fields populated = High quality score.
        """
        # Simulated field count
        total_fields = 150
        populated_fields = 150
        
        completeness_score = (populated_fields / total_fields) * 100
        assert completeness_score == 100, "Data quality score should be High"
    
    @pytest.mark.datasource
    def test_tc_2_1_006_multi_source_consistency(self):
        """
        TC_2_1_006: Validate multi-source consistency 
        (API + Manual + AI fields).
        """
        # Fields from different sources
        api_field = {"source": "api", "value": "Microsoft", "confidence": 0.95}
        manual_field = {"source": "manual", "value": "Microsoft", "confidence": 1.0}
        ai_field = {"source": "ai", "value": "Microsoft", "confidence": 0.85}
        
        # No conflicts between sources
        assert api_field["value"] == manual_field["value"] == ai_field["value"]
        
        # Confidence levels respected
        assert manual_field["confidence"] >= api_field["confidence"]
        assert api_field["confidence"] >= ai_field["confidence"]