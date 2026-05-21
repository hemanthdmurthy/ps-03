"""
Basic Validation Tests (TC-1.1)
Tests for valid standard inputs.
"""

import pytest
from validators.string_validator import (
    validate_company_name,
    validate_short_name,
    validate_ceo_name,
    validate_contact_name
)


class TestBasicValidation:
    """TC-1.1: Valid Standard Input tests"""
    
    @pytest.mark.valid
    @pytest.mark.parametrize("company_name", [
        "Microsoft Corporation",
        "AT&T Inc.",
        "L'Oréal S.A.",
    ])
    def test_tc_1_1_01_company_name_valid(self, company_name):
        """
        TC-1.1-01: Valid Standard Input
        Verify the field accepts well-formatted legal names including 
        allowed special characters (&, ., ,).
        """
        is_valid, result = validate_company_name(company_name)
        assert is_valid, f"Expected valid for {company_name}, got: {result}"
        assert "Validated" in result or result == "Valid"
    
    @pytest.mark.valid
    @pytest.mark.parametrize("short_name", [
        "AWS",
        "J&J",
        "OpenAI",
    ])
    def test_tc_1_1_02_short_name_valid(self, short_name):
        """
        TC-1.1-02: Valid Standard Input
        Verify abbreviated brand names are accepted within length constraints.
        """
        is_valid, result = validate_short_name(short_name)
        assert is_valid, f"Expected valid for {short_name}, got: {result}"
        # Verify Title Case conversion
        assert result == result.title() or result == "Valid"
        # Verify length constraint
        assert len(short_name) <= 100, f"Short name exceeds 100 chars: {short_name}"
    
    @pytest.mark.valid
    @pytest.mark.parametrize("ceo_name", [
        "Satya Nadella",
        "Jean-Pascal Tricoire",
    ])
    def test_tc_1_1_03_ceo_name_valid(self, ceo_name):
        """
        TC-1.1-03: Valid Standard Input
        Ensure executive names accept standard alphabetic characters and hyphens.
        """
        is_valid, result = validate_ceo_name(ceo_name)
        assert is_valid, f"Expected valid for {ceo_name}, got: {result}"
        # Verify no digits present
        assert not any(char.isdigit() for char in ceo_name)
    
    @pytest.mark.valid
    def test_tc_1_1_04_contact_name_valid(self):
        """
        TC-1.1-04: Valid Standard Input
        Validate capture of point-of-contact name for CRM integration.
        """
        contact_name = "Nandan M. Naik"
        is_valid, result = validate_contact_name(contact_name)
        assert is_valid, f"Expected valid for {contact_name}, got: {result}"
        assert "Valid" in result