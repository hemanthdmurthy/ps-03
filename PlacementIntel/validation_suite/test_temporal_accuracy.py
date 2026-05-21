"""
Temporal Accuracy Tests (Section 15.3, 5.3, 10.1)
Tests for data freshness and chronological sequence validation.
"""

import pytest
from datetime import datetime
from validators.dependency_validator import (
    validate_recency_threshold,
    validate_chronological_order,
    validate_future_event
)

class TestTemporalAccuracy:
    """Temporal accuracy and recency logic"""

    @pytest.mark.temporal
    @pytest.mark.valid
    def test_tc_015_301_recent_data(self):
        """TC_015_301: Recent data (<6 months)"""
        is_valid, result = validate_recency_threshold("2026-01-01", max_months=6)
        assert is_valid

    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_015_303_outdated_data(self):
        """TC_015_303: Outdated data (>12 months)"""
        is_valid, result = validate_recency_threshold("2023-01-01", max_months=12)
        assert not is_valid, f"Expected failure for stale data, got: {result}"

    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_015_304_missing_timestamp(self):
        """TC_015_304: Missing timestamp"""
        is_valid, result = validate_recency_threshold(None)
        assert not is_valid, f"Expected failure for missing timestamp"
        assert "without timestamp" in result

    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_5_3_001_funding_before_incorporation(self):
        """TC_5.3_001: Funding round must occur after incorporation year"""
        is_valid, result = validate_chronological_order(2015, 2010, "Incorporation", "Funding")
        assert not is_valid, "Expected failure for funding before incorporation"

    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_5_3_003_news_too_old(self):
        """TC_5.3_003: News must be within last 2 years"""
        # Current simulated year is 2026
        is_valid, result = validate_recency_threshold("2020-01-01", max_months=24)
        assert not is_valid, "Expected failure for news > 2 years old"

    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_5_3_007_future_layoffs(self):
        """TC_5.3_007: Layoff events must have valid past dates"""
        current_year = 2026
        layoff_year = 2028
        is_valid, result = validate_chronological_order(layoff_year, current_year, "Layoff", "Current Date")
        assert not is_valid, "Expected failure for future layoffs"

    @pytest.mark.temporal
    @pytest.mark.valid
    def test_tc_temp_01_recent_event(self):
        """TC_TEMP_01: Validate presence of recent events (post-2024)"""
        is_valid, result = validate_recency_threshold("2025-02-10", max_months=24)
        assert is_valid

    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_temp_02_outdated_cutoff(self):
        """TC_TEMP_02: Detect outdated record with no events after cutoff"""
        # Using 12 month cutoff from April 2026
        is_valid, result = validate_recency_threshold("2022-05-01", max_months=12)
        assert not is_valid, f"Expected failure for stale news, got: {result}"

    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_temp_06_hallucinated_future(self):
        """TC_TEMP_06: Detect hallucinated future event beyond current date"""
        is_valid, result = validate_future_event("2028-12-01", reject_future=True)
        assert not is_valid, f"Expected failure for future hallucination, got: {result}"

    @pytest.mark.temporal
    @pytest.mark.invalid
    def test_tc_temp_10_temporal_contradiction(self):
        """TC_TEMP_10: Detect temporal contradiction (Join vs Resign)"""
        is_valid, result = validate_chronological_order(2025, 2023, "Joined", "Resigned")
        assert not is_valid, "Expected failure for resigned before joined"
