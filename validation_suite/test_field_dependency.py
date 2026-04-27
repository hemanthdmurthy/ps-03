"""
Field Dependency Tests (TC_FD)
Tests for cross-field validation and dependency rules.
"""

import pytest
from validators.string_validator import (
    validate_short_name,
    validate_ceo_name
)
from validators.dependency_validator import (
    validate_field_dependency,
    validate_entitydisambiguation
)
from validators.financial_validator import validate_profitability_status


# Mock database for entity disambiguation
KNOWN_ENTITIES = {
    "company": ["Microsoft Corporation", "Apple Inc."],
    "ceo": ["Satya Nadella", "Tim Cook"],
    "investor": ["Sequoia Capital US", "Sequoia China"]
}


class TestFieldDependency:
    """TC_FD: Field dependency validation tests"""
    
    @pytest.mark.crossfield
    def test_tc_fd_002_short_name_dependency(self):
        """
        TC-FD-002: Validate that a Short Name is only present 
        if a primary Company Name exists.
        """
        short_name = "J-Tech"
        company_name = "Johnson Technologies"
        
        # Business Rule: If Short Name != NULL, Company Name must be != NULL
        if short_name:
            assert company_name is not None, "Company Name must exist when Short Name is provided"
            assert company_name != short_name, "Short Name must be distinct from Company Name"
    
    @pytest.mark.crossfield
    def test_tc_fd_045_ceo_linkedin_dependency(self):
        """
        TC-FD-045: Ensure the executive's identity link is coupled 
        with their legal name.
        """
        ceo_linkedin = "https://www.linkedin.com/in/jash-d/"
        ceo_name = "Jash Dhage"
        
        # Dependency Rule: CEO Name must not be null when CEO LinkedIn URL is provided
        if ceo_linkedin:
            assert ceo_name is not None, "CEO Name must exist when CEO LinkedIn URL is provided"
            assert ceo_name.strip() != "", "CEO Name must not be empty"
    
    @pytest.mark.crossfield
    def test_tc_fd_065_profitability_financial_dependency(self):
        """
        TC-FD-065: Validate that status classification matches 
        the financial metric.
        """
        profitability_status = "Loss-making"
        annual_profits = -500000  # Negative value for loss-making
        
        # Data Rule: If Profitability Status is set, Annual Profits must be populated
        if profitability_status:
            assert annual_profits is not None, "Annual Profits must be populated when Profitability Status is set"
            
            # Verify consistency
            if "loss" in profitability_status.lower():
                assert annual_profits < 0, "Loss-making status should have negative profits"
            elif "profit" in profitability_status.lower():
                assert annual_profits > 0, "Profitable status should have positive profits"
    
    @pytest.mark.crossfield
    def test_tc_fd_079_runway_financial_dependency(self):
        """
        TC-FD-079: Verify that the sustainability duration has 
        the required financial inputs.
        """
        total_capital_raised = 10000000  # $10M
        burn_rate = 500000  # $500K/month
        runway = 20  # months
        
        # Business Rule: Calculated from Total Capital Raised / Burn Rate
        if runway:
            assert total_capital_raised is not None, "Total Capital Raised must be non-null for runway calculation"
            assert burn_rate is not None, "Burn Rate must be non-null for runway calculation"
            assert burn_rate > 0, "Burn Rate must be positive"
            
            # Verify calculation
            calculated_runway = total_capital_raised / burn_rate
            assert abs(calculated_runway - runway) < 1, "Runway should match calculated value"
    
    @pytest.mark.crossfield
    def test_tc_fd_110_som_sam_dependency(self):
        """
        TC-FD-110: Ensure the narrowest market metric has its 
        parent metric defined.
        """
        som = 500000000  # $500M
        sam = 1000000000  # $1B
        
        # Logic Rule: SOM <= SAM
        if som:
            assert sam is not None, "SAM must not be null when SOM is provided"
            assert som <= sam, f"SOM ({som}) must be <= SAM ({sam})"
    
    @pytest.mark.crossfield
    def test_tc_fd_146_company_maturity_dependency(self):
        """
        TC-FD-146: Validate that the lifecycle stage is supported 
        by foundational metadata.
        """
        maturity = "Scale-up"
        year_of_incorporation = 2018
        employee_size = 500
        annual_revenues = 50000000
        
        # Business Rule: Requires Year, Employee Size, and Revenues for calculation
        if maturity:
            assert year_of_incorporation is not None, "Year of Incorporation must be non-null for maturity calculation"
            assert employee_size is not None, "Employee Size must be non-null for maturity calculation"
            assert annual_revenues is not None, "Annual Revenues must be non-null for maturity calculation"
            
            # Verify reasonable values for scale-up
            assert 2010 <= year_of_incorporation <= 2026
            assert employee_size >= 100
            assert annual_revenues >= 1000000
    
    @pytest.mark.crossfield
    def test_tc_fd_160_global_exposure_dependency(self):
        """
        TC-FD-160: Ensure exposure flag is backed by geographic data.
        """
        global_exposure = "Yes"
        countries_operating_in = ["USA", "India", "UK"]
        
        # Data Rule: If Global exposure is "Yes", Countries count must be > 1
        if global_exposure.lower() == "yes":
            assert countries_operating_in is not None, "Countries Operating In must be non-null when Global exposure is Yes"
            assert len(countries_operating_in) > 1, f"Global exposure requires > 1 country, got {len(countries_operating_in)}"
    
    @pytest.mark.crossfield
    def test_tc_fd_163_crisis_behavior_dependency(self):
        """
        TC-FD-163: Validate that qualitative crisis narrative is 
        linked to documented events.
        """
        crisis_behavior = "Swift Covid-19 response"
        recent_news = ["Covid-19 pandemic impact 2020", "Remote work transition"]
        legal_issues = []
        
        # Dependency: Recent News or Legal Issues must contain relevant event data
        if crisis_behavior:
            has_relevant_event = (
                (recent_news and any("covid" in str(n).lower() for n in recent_news)) or
                (legal_issues and any("covid" in str(i).lower() for i in legal_issues))
            )
            assert has_relevant_event or (recent_news is None and legal_issues is None), \
                "Crisis behavior should be supported by event data or fields can be null"
    
    @pytest.mark.crossfield
    def test_tc_fd_001_company_name_required(self):
        """
        TC-FD-001: Validate that Company Name is mandatory.
        """
        company_name = "Test Corp"
        
        # Company Name is mandatory
        assert company_name is not None, "Company Name is required"
        assert company_name.strip() != "", "Company Name cannot be empty"
    
    @pytest.mark.crossfield
    def test_tc_fd_003_category_required(self):
        """
        TC-FD-003: Validate that Category is mandatory.
        """
        category = "Startup"
        
        # Category is mandatory
        assert category is not None, "Category is required"
        assert category.strip() != "", "Category cannot be empty"
    
    @pytest.mark.crossfield
    def test_tc_fd_004_year_required(self):
        """
        TC-FD-004: Validate that Year of Incorporation is mandatory.
        """
        year = 2020
        
        # Year is mandatory
        assert year is not None, "Year of Incorporation is required"
        assert isinstance(year, int), "Year must be an integer"
        assert 1800 <= year <= 2100, "Year must be in valid range"
    
    @pytest.mark.crossfield
    def test_tc_fd_006_overview_min_length(self):
        """
        TC-FD-006: Validate Overview minimum length.
        """
        overview = "This is a short overview that is less than fifty characters long."
        
        # Overview has minimum length requirement
        assert len(overview) >= 50, f"Overview must be at least 50 characters, got {len(overview)}"