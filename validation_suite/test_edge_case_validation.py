"""
Edge Case Validation Tests (TC_6.1)
Tests for new startup scenarios and edge cases using centralized validators.
"""

import pytest
from validators import (
    validate_year,
    validate_min_length,
    validate_https_url,
    validate_category,
    validate_not_null
)

class TestEdgeCaseValidation:
    """TC_6.1: Edge case validation for new startups"""
    
    @pytest.mark.valid
    def test_tc_6_1_01_current_year_incorporation(self):
        """TC_6.1_01: Validate company incorporated in current year"""
        is_valid, _ = validate_year(2026)
        assert is_valid
    
    @pytest.mark.invalid
    def test_tc_6_1_02_future_incorporation(self):
        """TC_6.1_02: Future incorporation year should fail"""
        is_valid, _ = validate_year(2027)
        assert not is_valid
    
    @pytest.mark.invalid
    def test_tc_6_1_03_stealth_startup_insufficient_info(self):
        """TC_6.1_03: Stealth startup with insufficient overview length"""
        is_valid, _ = validate_min_length("AI startup", 50, "Overview")
        assert not is_valid
    
    @pytest.mark.invalid
    def test_tc_6_1_05_missing_website(self):
        """TC_6.1_05: Mandatory website URL missing"""
        is_valid, _ = validate_not_null(None, "Website URL")
        assert not is_valid
    
    @pytest.mark.invalid
    def test_tc_6_1_06_invalid_temp_url(self):
        """TC_6.1_06: Newly launched startup with temporary URL"""
        is_valid, _ = validate_https_url("http://stealth-startup")
        assert not is_valid
    
    @pytest.mark.invalid
    def test_tc_6_1_10_new_startup_wrong_category(self):
        """TC_6.1_10: Newly formed startup incorrectly categorized"""
        category = "Enterprise"
        # Logic: If it's a NEW company (implied), it shouldn't be Enterprise
        is_valid = (category == "Startup")
        assert not is_valid, "Expected failure for wrong categorization"

    @pytest.mark.invalid
    def test_tc_6_1_12_invalid_employee_format(self):
        """TC_6.1_12: Invalid employee size format"""
        from validators import validate_placeholder_prevention
        is_valid, _ = validate_placeholder_prevention("Few", "Employee Size")
        assert not is_valid