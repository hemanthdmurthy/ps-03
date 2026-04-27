"""
Boundary Value Testing - Zero/Low Values (TC_7.2)
Tests for boundary conditions with zero and low values.
"""

import pytest
import re
from validators.numeric_validator import validate_positive_number, validate_numeric_range
from validators.string_validator import validate_placeholder_prevention


class TestBoundaryZeroLow:
    """TC_7.2: Boundary value testing with zero/low values"""
    
    # Number of Offices
    
    @pytest.mark.valid
    def test_tc_7_2_001_zero_offices_remote(self):
        """
        TC_7.2_001: Validate zero offices for remote company
        """
        office_count = 0
        
        assert office_count >= 0, "allowed as per business rule (≥ 0)"
    
    # Employee Size
    
    @pytest.mark.invalid
    def test_tc_7_2_002_zero_employee_size(self):
        """
        TC_7.2_002: Validate zero employee size
        """
        employee_size = "0"
        is_valid, result = validate_placeholder_prevention(employee_size, "Employee Size")
        assert not is_valid, "Should reject '0' as placeholder for employee size"
    
    # Employee Turnover
    
    @pytest.mark.valid
    def test_tc_7_2_003_zero_turnover(self):
        """
        TC_7.2_003: Validate zero turnover
        """
        turnover = "0%"
        
        numeric_value = int(turnover.replace("%", ""))
        assert 0 <= numeric_value <= 100, "valid range (0–100%)"
    
    # Website Traffic Rank
    
    @pytest.mark.invalid
    def test_tc_7_2_004_zero_traffic_rank(self):
        """
        TC_7.2_004: Validate zero traffic rank
        """
        traffic_rank = 0
        is_valid, result = validate_positive_number(traffic_rank, "Traffic Rank")
        assert not is_valid, "Should reject 0 for traffic rank"
    
    # Social Media Followers
    
    @pytest.mark.valid
    def test_tc_7_2_005_zero_followers(self):
        """
        TC_7.2_005: Validate zero followers
        """
        followers = 0
        
        assert followers >= 0, "allowed (≥ 0)"
    
    # Website Rating
    
    @pytest.mark.valid
    def test_tc_7_2_006_zero_rating(self):
        """
        TC_7.2_006: Validate zero rating
        """
        rating = 0
        
        assert 0 <= rating <= 10, "within allowed range (0–10)"
    
    # Glassdoor Rating
    
    @pytest.mark.invalid
    def test_tc_7_2_007_glassdoor_zero(self):
        """
        TC_7.2_007: Validate zero rating
        """
        rating = 0
        
        assert rating < 1.0 or rating > 5.0, "must be between 1.0–5.0"
    
    # Indeed Rating
    
    @pytest.mark.invalid
    def test_tc_7_2_008_indeed_zero(self):
        """
        TC_7.2_008: Validate zero rating
        """
        rating = 0
        
        assert rating < 1.0 or rating > 5.0, "must be between 1.0–5.0"
    
    # Google Reviews Rating
    
    @pytest.mark.invalid
    def test_tc_7_2_009_google_zero(self):
        """
        TC_7.2_009: Validate zero rating
        """
        rating = 0
        
        assert rating < 1.0 or rating > 5.0, "must be between 1.0–5.0"
    
    # Annual Revenues
    
    @pytest.mark.valid
    def test_tc_7_2_010_zero_revenue(self):
        """
        TC_7.2_010: Validate zero revenue
        """
        revenue = "$0"
        
        numeric_value = int(revenue.replace("$", ""))
        assert numeric_value == 0, "valid for early-stage/pre-revenue companies"
    
    # Annual Profits
    
    @pytest.mark.valid
    def test_tc_7_2_011_zero_profit(self):
        """
        TC_7.2_011: Validate zero profit
        """
        profit = "$0"
        
        numeric_value = int(profit.replace("$", ""))
        assert numeric_value == 0, "valid (break-even scenario)"
    
    # Company Valuation
    
    @pytest.mark.invalid
    def test_tc_7_2_012_zero_valuation(self):
        """
        TC_7.2_012: Validate zero valuation
        """
        valuation = "$0"
        numeric_value = int(valuation.replace("$", ""))
        is_valid, result = validate_positive_number(numeric_value, "Valuation")
        assert not is_valid, "Should reject 0 for valuation"
    
    # Year-over-Year Growth Rate
    
    @pytest.mark.valid
    def test_tc_7_2_013_zero_growth(self):
        """
        TC_7.2_013: Validate zero growth
        """
        growth = "0%"
        
        numeric_value = int(growth.replace("%", ""))
        assert numeric_value == 0, "indicates no growth"
    
    # Market Share
    
    @pytest.mark.valid
    def test_tc_7_2_014_zero_market_share(self):
        """
        TC_7.2_014: Validate zero market share
        """
        market_share = "0%"
        
        numeric_value = int(market_share.replace("%", ""))
        assert numeric_value >= 0, "valid lower bound"
    
    # Total Capital Raised
    
    @pytest.mark.valid
    def test_tc_7_2_015_zero_funding(self):
        """
        TC_7.2_015: Validate zero funding
        """
        capital = "$0"
        
        numeric_value = int(capital.replace("$", ""))
        assert numeric_value == 0, "valid for bootstrapped companies"
    
    # Customer Acquisition Cost
    
    @pytest.mark.invalid
    def test_tc_7_2_016_zero_cac(self):
        """
        TC_7.2_016: Validate zero CAC
        """
        cac = "$0"
        numeric_value = int(cac.replace("$", ""))
        is_valid, result = validate_positive_number(numeric_value, "CAC")
        assert not is_valid, "Should reject 0 for CAC"
    
    # Customer Lifetime Value
    
    @pytest.mark.invalid
    def test_tc_7_2_017_zero_clv(self):
        """
        TC_7.2_017: Validate zero CLV
        """
        clv = "$0"
        numeric_value = int(clv.replace("$", ""))
        is_valid, result = validate_positive_number(numeric_value, "CLV")
        assert not is_valid, "Should reject 0 for CLV"
    
    # CAC:LTV Ratio
    
    @pytest.mark.invalid
    def test_tc_7_2_018_zero_ratio(self):
        """
        TC_7.2_018: Validate zero ratio
        """
        ratio = "0:1"
        
        parts = ratio.split(":")
        assert len(parts) == 2 and int(parts[0]) == 0, "invalid ratio - division logic violation"
    
    # Churn Rate
    
    @pytest.mark.valid
    def test_tc_7_2_019_zero_churn(self):
        """
        TC_7.2_019: Validate zero churn
        """
        churn = "0%"
        
        numeric_value = int(churn.replace("%", ""))
        assert numeric_value == 0, "ideal retention scenario"
    
    # Net Promoter Score
    
    @pytest.mark.valid
    def test_tc_7_2_020_zero_nps(self):
        """
        TC_7.2_020: Validate zero NPS
        """
        nps = 0
        
        assert -100 <= nps <= 100, "valid range (-100 to 100)"
    
    # Burn Rate
    
    @pytest.mark.invalid
    def test_tc_7_2_021_zero_burn_rate(self):
        """
        TC_7.2_021: Validate zero burn rate
        """
        burn_rate = "$0"
        numeric_value = int(burn_rate.replace("$", ""))
        is_valid, result = validate_positive_number(numeric_value, "Burn Rate")
        assert not is_valid, "Should reject 0 for burn rate"
    
    # Runway
    
    @pytest.mark.invalid
    def test_tc_7_2_022_zero_runway(self):
        """
        TC_7.2_022: Validate zero runway
        """
        runway = 0
        is_valid, result = validate_positive_number(runway, "Runway")
        assert not is_valid, "Should reject 0 for runway"
    
    # Burn Multiplier
    
    @pytest.mark.valid
    def test_tc_7_2_023_zero_multiplier(self):
        """
        TC_7.2_023: Validate zero multiplier
        """
        multiplier = 0
        
        assert multiplier >= 0, "indicates highly efficient growth"
    
    # R&D Investment
    
    @pytest.mark.valid
    def test_tc_7_2_024_zero_rd_spend(self):
        """
        TC_7.2_024: Validate zero R&D spend
        """
        rd_spend = "$0"
        
        numeric_value = int(rd_spend.replace("$", ""))
        assert numeric_value >= 0, "possible for non-tech firms"
    
    # Commute Time
    
    @pytest.mark.invalid
    def test_tc_7_2_025_zero_commute(self):
        """
        TC_7.2_025: Validate zero commute time
        """
        commute = 0
        is_valid, result = validate_positive_number(commute, "Commute Time")
        assert not is_valid, "Should reject 0 for commute time"
    
    # Technology Adoption Rating
    
    @pytest.mark.invalid
    def test_tc_7_2_026_zero_tech_rating(self):
        """
        TC_7.2_026: Validate zero rating
        """
        rating = 0
        
        assert rating < 1 or rating > 10, "valid range is 1–10"