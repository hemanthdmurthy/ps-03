import pytest
from validators import (
    validate_implied_presence, 
    validate_derived_null,
    validate_ratio_calculation,
    validate_structural_propagation,
    validate_chronological_order,
    validate_precision,
    validate_tone_neutrality,
    validate_profitability_consistency,
    validate_employee_revenue_ratio,
    validate_office_scale_consistency,
    validate_nps_churn_consistency,
    validate_market_share_calculation,
    validate_acquisition_competitor_consistency
)

class TestCrossFieldValidation:
    """Cross-field validation logic"""

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_014_004_market_share_implies_revenue(self):
        """TC_014_004: Market share implies revenue exists"""
        market_share = "15%"
        revenue = None
        is_valid, _ = validate_implied_presence(
            market_share, revenue, "Market Share (%)", "Annual Revenues"
        )
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_014_011_valuation_implies_funding(self):
        """TC_014_011: Missing funding data when valuation exists"""
        valuation = "$2B"
        funding = None
        is_valid, _ = validate_implied_presence(
            valuation, funding, "Company Valuation", "Recent Funding Rounds"
        )
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_014_501_revenue_null_yoy_null(self):
        """TC_014_501: Revenue null -> YoY null"""
        revenue = None
        yoy_growth = "10%"
        is_valid, _ = validate_derived_null(
            revenue, yoy_growth, "Annual Revenues", "YoY Growth"
        )
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_014_502_cac_null_ratio_null(self):
        """TC_014_502: CAC null -> ratio null"""
        cac = None
        ratio = "1:5"
        is_valid, _ = validate_derived_null(
            cac, ratio, "CAC", "CAC:LTV Ratio"
        )
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_014_505_burn_rate_null_runway_null(self):
        """TC_014_505: Burn rate null -> runway null"""
        burn_rate = None
        runway = "12"
        is_valid, _ = validate_derived_null(
            burn_rate, runway, "Burn Rate", "Runway"
        )
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_4_3_02_over_precision(self):
        """TC_4.3_02: Identify overly precise fabricated data"""
        is_valid, _ = validate_precision("17.348%")
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_4_3_03_authoritative_tone(self):
        """TC_4.3_03: Detect authoritative tone in estimated fields"""
        is_valid, _ = validate_tone_neutrality("$2.3B (confirmed)")
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_4_3_04_profit_logic_contradiction(self):
        """TC_4.3_04: Logical contradiction (Profitable vs negative profits)"""
        is_valid, _ = validate_profitability_consistency("Profitable", -5000000)
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_4_3_06_unrealistic_combination(self):
        """TC_4.3_06: Unrealistic combo (Low employees, High revenue)"""
        is_valid, _ = validate_employee_revenue_ratio("10-20", 5000000000)
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_4_3_10_ratio_mismatch(self):
        """TC_4.3_10: Validate consistency between ratio and base fields"""
        is_valid, _ = validate_ratio_calculation("5:1", 500, 1000)
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_5_5_02_scale_consistency(self):
        """TC_5.5_02: Large headcount with 1 office inconsistency"""
        is_valid, _ = validate_office_scale_consistency(50000, 1)
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_5_5_03_nps_churn_consistency(self):
        """TC_5.5_03: High NPS with high churn inconsistency"""
        is_valid, _ = validate_nps_churn_consistency(85, 45)
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_5_5_04_market_share_consistency(self):
        """TC_5.5_04: Revenue vs TAM vs Market Share inconsistency"""
        is_valid, _ = validate_market_share_calculation(1000000000, 500000000, 2)
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_struct_04_unpropagated_subsidiary(self):
        """TC_STRUCT_04: Detect unpropagated subsidiary Mentioned in News"""
        is_valid, _ = validate_structural_propagation("2025 - Launched ABC Subsidiary", None, "ABC Corp")
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_struct_08_stale_competitors(self):
        """TC_STRUCT_08: Detect stale competitors after acquisition"""
        is_valid, _ = validate_acquisition_competitor_consistency("TargetCorp", "2025 - Acquired TargetCorp")
        assert not is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_struct_12_contradictory_structure(self):
        """TC_STRUCT_12: Detect contradictory structure (Created vs Divested)"""
        is_valid, _ = validate_chronological_order(2025, 2024, "Created", "Divested")
        assert not is_valid
