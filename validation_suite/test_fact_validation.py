"""
Fact Validation Tests (TC-FACT-3.1)
Tests for temporal accuracy and fact-checking using centralized validators.
"""

import pytest
from validators import (
    validate_year,
    validate_recency_threshold,
    validate_future_event,
    validate_hiring_consistency,
    validate_positive_number,
    validate_revenue
)

class TestTemporalAccuracy:
    """TC_TA: Temporal accuracy tests"""
    
    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_ta_001_outdated_ceo(self):
        """TC_TA_001: Validate CEO is current"""
        ceo = "Sundar Pichai (Former CEO)"
        # We'll use a generic placeholder check or specific 'former' check
        from validators import validate_placeholder_prevention
        is_valid, _ = validate_placeholder_prevention(ceo, "CEO Name")
        # Need to add 'former' to placeholders or similar
        assert not is_valid
    
    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_ta_003_outdated_funding(self):
        """TC_TA_003: Validate funding round recency"""
        is_valid, _ = validate_recency_threshold("2010-05-01", max_months=24)
        assert not is_valid
    
    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_ta_005_outdated_news(self):
        """TC_TA_005: Validate news recency"""
        is_valid, _ = validate_recency_threshold("2018-01-01", max_months=24)
        assert not is_valid
    
    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_ta_007_future_year(self):
        """TC_TA_007: Validate year is not in future"""
        is_valid, _ = validate_year(2030)
        assert not is_valid
    
    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_ta_009_past_roadmap(self):
        """TC_TA_009: Roadmap must be in future"""
        is_valid, _ = validate_future_event("2022-01-01")
        assert not is_valid
    
    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_ta_011_past_projection(self):
        """TC_TA_011: Projections must be future-oriented"""
        is_valid, _ = validate_future_event("2022 - Revenue Growth 20%")
        assert not is_valid
    
    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_ta_013_negative_runway(self):
        """TC_TA_013: Negative runway should fail"""
        is_valid, _ = validate_positive_number("-5", "Runway")
        assert not is_valid
    
    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_ta_015_inconsistent_hiring(self):
        """TC_TA_015: Scaling rapidly vs 0 roles"""
        is_valid, _ = validate_hiring_consistency("0 roles (but company scaling rapidly)")
        assert not is_valid