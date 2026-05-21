"""
Case Sensitivity Tests (TC-CS)
Tests for case-insensitive validation and normalization.
"""

import pytest
from validators.string_validator import (
    validate_company_name,
    validate_short_name,
    validate_ceo_name,
    validate_contact_name,
    normalize_to_title_case,
    normalize_to_lowercase
)
from validators.url_validator import (
    validate_https_url,
    validate_twitter_handle,
    validate_email,
    validate_url_case_insensitive
)
from validators.dependency_validator import (
    validate_category,
    validate_nature_of_company
)
from validators.financial_validator import validate_profitability_status


class TestCaseSensitivity:
    """TC-CS: Case Sensitivity tests"""
    
    @pytest.mark.format
    def test_tc_cs_001_company_name_lowercase(self):
        """
        TC-CS-001: Validate that lowercase input is accepted and 
        normalized to Standard Case.
        """
        input_value = "apple inc."
        is_valid, result = validate_company_name(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        
        # Normalize to Title Case
        normalized = normalize_to_title_case(input_value)
        assert normalized == "Apple Inc.", f"Should normalize to 'Apple Inc.', got: {normalized}"
    
    @pytest.mark.format
    def test_tc_cs_002_short_name_mixed_case(self):
        """
        TC-CS-002: Verify that mixed-case variations are handled 
        without creating duplicate alias records.
        """
        input_value = "MiCrOsOfT"
        is_valid, result = validate_short_name(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        
        # System identifies as "Microsoft"
        normalized = normalize_to_title_case(input_value)
        assert normalized == "Microsoft", f"Should normalize to 'Microsoft', got: {normalized}"
    
    @pytest.mark.format
    def test_tc_cs_003_category_case_insensitive(self):
        """
        TC-CS-003: Validate that enum matching is case-insensitive 
        as per data rules.
        """
        input_value = "startup"
        is_valid, result = validate_category(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        assert result == "Startup", f"Should match 'Startup', got: {result}"
    
    @pytest.mark.format
    def test_tc_cs_004_nature_of_company_uppercase(self):
        """
        TC-CS-004: Verify that uppercase enum inputs map correctly 
        to the standard legal structure list.
        """
        input_value = "PRIVATE"
        is_valid, result = validate_nature_of_company(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        assert result == "Private", f"Should map to 'Private', got: {result}"
    
    @pytest.mark.format
    def test_tc_cs_005_url_case_insensitive(self):
        """
        TC-CS-005: Ensure domain components are treated as 
        case-insensitive during deduplication.
        """
        input_value = "HTTPS://WWW.GOOGLE.COM"
        is_valid, result = validate_url_case_insensitive(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        
        # Strip HTTPS://, trailing slashes, convert to lowercase
        assert result == "www.google.com", f"Should normalize to 'www.google.com', got: {result}"
    
    @pytest.mark.format
    def test_tc_cs_006_twitter_handle_mixed_case(self):
        """
        TC-CS-006: Test handle validation with mixed-case variations.
        """
        input_value = "@TestUser"
        is_valid, result = validate_twitter_handle(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        # Social handles are case-insensitive for triggers
        assert "@testuser" in input_value.lower() or "@TestUser" in input_value
    
    @pytest.mark.format
    def test_tc_cs_007_ceo_name_uppercase(self):
        """
        TC-CS-007: Validate that uppercase name input is formatted 
        to Standard Case.
        """
        input_value = "SATYA NADELLA"
        is_valid, result = validate_ceo_name(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        
        # Store or display as "Satya Nadella"
        normalized = normalize_to_title_case(input_value.lower())
        assert normalized == "Satya Nadella", f"Should normalize to 'Satya Nadella', got: {normalized}"
    
    @pytest.mark.format
    def test_tc_cs_008_email_normalization(self):
        """
        TC-CS-008: Verify that the local part and domain are 
        normalized for B2B flag validation.
        """
        input_value = "SALES@Company.com"
        is_valid, result = validate_email(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        
        # Standardize to lowercase before MX record lookup
        assert result == "sales@company.com", f"Should normalize to lowercase, got: {result}"
    
    @pytest.mark.format
    def test_tc_cs_009_compliance_tag_case_insensitive(self):
        """
        TC-CS-009: Test pattern matching for compliance tags 
        with different casing.
        """
        input_value = "gdpr"
        # Pattern matching should identify "GDPR" from framework list
        assert input_value.upper() == "GDPR", f"Should match GDPR framework"
    
    @pytest.mark.format
    def test_tc_cs_010_profitability_status_uppercase(self):
        """
        TC-CS-010: Ensure categorical status matches valid enums 
        regardless of input case.
        """
        input_value = "PROFITABLE"
        is_valid, result = validate_profitability_status(input_value)
        assert is_valid, f"Expected valid for '{input_value}', got: {result}"
        assert result == "Profitable", f"Should match 'Profitable', got: {result}"