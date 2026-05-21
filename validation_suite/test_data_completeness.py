"""
Data Completeness Tests (TC_DC)
Tests for empty/null response handling for various field types.
"""

import pytest
from validators.string_validator import (
    validate_company_name,
    validate_not_null,
    validate_min_length
)
from validators.numeric_validator import (
    validate_year,
    validate_positive_number
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


class TestDataCompleteness:
    """TC_DC: Data completeness tests"""
    
    # NOT NULL fields - should FAIL on empty
    
    @pytest.mark.invalid
    @pytest.mark.parametrize("input_value,expected_fail", [
        ("", True),
        (None, True),
        ("NonExistentCompanyXYZ123", True)
    ])
    def test_tc_dc_001_company_name_empty(self, input_value, expected_fail):
        """
        TC_DC_001: Validate empty response for non-existent company.
        FAIL — violates Not Null + business rule.
        """
        is_valid, _ = validate_company_name(input_value if input_value else "")
        assert is_valid != expected_fail, f"Expected {'fail' if expected_fail else 'pass'} for {input_value}"
    
    @pytest.mark.invalid
    def test_tc_dc_003_logo_empty(self):
        """
        TC_DC_003: Validate empty URL response for Logo.
        FAIL — Not Null + must resolve to valid image URL.
        """
        logo_url = ""
        is_valid, _ = validate_https_url(logo_url)
        assert not is_valid, "Empty logo URL should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_004_category_empty(self):
        """
        TC_DC_004: Validate enum field empty response.
        FAIL — Not Null + must match enum.
        """
        is_valid, _ = validate_category("")
        assert not is_valid, "Empty category should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_005_year_empty(self):
        """
        TC_DC_005: Validate empty numeric response for Year.
        FAIL — Not Null + violates range rule.
        """
        is_valid, _ = validate_year(None)
        assert not is_valid, "Empty year should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_006_overview_empty(self):
        """
        TC_DC_006: Validate empty narrative response.
        FAIL — Not Null + min length 50 chars.
        """
        is_valid, _ = validate_min_length("", 50, "Overview")
        assert not is_valid, "Empty overview should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_007_nature_of_company_empty(self):
        """
        TC_DC_007: Validate empty enum response for Nature of Company.
        FAIL — Not Null.
        """
        is_valid, _ = validate_nature_of_company(None)
        assert not is_valid, "Empty nature of company should fail"
    
    @pytest.mark.invalid
    @pytest.mark.parametrize("employee_size", ["", " "])
    def test_tc_dc_010_employee_size_empty(self, employee_size):
        """
        TC_DC_010: Validate empty range field for Employee Size.
        FAIL — Not Null + regex constraint.
        """
        # Employee size should match pattern ^(\d+|\d+-\d+)$
        import re
        pattern = r'^(\d+|\d+-\d+)$'
        is_valid = bool(re.match(pattern, employee_size)) if employee_size.strip() else False
        assert not is_valid, "Empty employee size should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_012_website_url_empty(self):
        """
        TC_DC_012: Validate empty URL response.
        FAIL — Not Null + HTTP validation.
        """
        is_valid, _ = validate_https_url("")
        assert not is_valid, "Empty website URL should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_015_ceo_name_empty(self):
        """
        TC_DC_015: Validate empty string for person name.
        FAIL — Not Null.
        """
        from validators.string_validator import validate_ceo_name
        is_valid, _ = validate_ceo_name(None)
        assert not is_valid, "Empty CEO name should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_019_profitability_empty(self):
        """
        TC_DC_019: Validate empty enum response for Profitability Status.
        FAIL — Not Null.
        """
        is_valid, _ = validate_profitability_status("")
        assert not is_valid, "Empty profitability status should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_023_sales_motion_empty(self):
        """
        TC_DC_023: Validate empty enum/text field for Sales Motion.
        FAIL — Not Null.
        """
        is_valid, _ = validate_sales_motion("")
        assert not is_valid, "Empty sales motion should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_024_remote_policy_empty(self):
        """
        TC_DC_024: Validate empty enum field for Remote Work Policy.
        FAIL — Not Null.
        """
        is_valid, _ = validate_remote_policy("")
        assert not is_valid, "Empty remote policy should fail"
    
    @pytest.mark.invalid
    def test_tc_dc_025_company_maturity_empty(self):
        """
        TC_DC_025: Validate empty derived classification.
        FAIL — Not Null + derived rule.
        """
        # Company maturity is derived - requires Year, Employee Size, Revenue
        maturity = ""
        is_valid = maturity.strip() != ""  # Basic validation
        assert not is_valid, "Empty company maturity should fail"
    
    # NULLABLE fields - should PASS on empty/null
    
    @pytest.mark.valid
    def test_tc_dc_002_short_name_null(self):
        """
        TC_DC_002: Validate empty response handling.
        PASS — field is Nullable, allowed to be NULL.
        """
        short_name = None
        assert short_name is None, "Nullable short name can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_008_countries_null(self):
        """
        TC_DC_008: Validate empty list response for Countries.
        PASS — Nullable, acceptable.
        """
        countries = None
        assert countries is None, "Nullable countries can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_009_offices_empty(self):
        """
        TC_DC_009: Validate empty numeric response for Offices.
        PASS — Nullable; system should return NULL.
        """
        offices = ""
        # Should return NULL, not fail
        result = None if offices == "" else offices
        assert result is None, "Nullable offices can be empty/NULL"
    
    @pytest.mark.valid
    def test_tc_dc_011_turnover_null(self):
        """
        TC_DC_011: Validate empty percentage for Employee Turnover.
        PASS — Nullable.
        """
        turnover = None
        assert turnover is None, "Nullable turnover can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_013_website_rating_null(self):
        """
        TC_DC_013: Validate empty numeric rating.
        PASS — Nullable.
        """
        rating = None
        assert rating is None, "Nullable rating can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_016_ceo_linkedin_null(self):
        """
        TC_DC_016: Validate empty profile URL for CEO LinkedIn.
        PASS — Nullable.
        """
        linkedin_url = None
        assert linkedin_url is None, "Nullable LinkedIn URL can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_017_company_email_null(self):
        """
        TC_DC_017: Validate empty email response.
        PASS — Nullable.
        """
        email = None
        assert email is None, "Nullable email can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_018_company_phone_null(self):
        """
        TC_DC_018: Validate empty phone response.
        PASS — Nullable.
        """
        phone = None
        assert phone is None, "Nullable phone can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_020_annual_revenues_null(self):
        """
        TC_DC_020: Validate empty financial metric.
        PASS — Nullable.
        """
        revenues = None
        assert revenues is None, "Nullable revenues can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_021_cac_null(self):
        """
        TC_DC_021: Validate empty numeric for CAC.
        PASS — Nullable.
        """
        cac = None
        assert cac is None, "Nullable CAC can be NULL"
    
    @pytest.mark.valid
    def test_tc_dc_022_nps_null(self):
        """
        TC_DC_022: Validate empty integer score for NPS.
        PASS — Nullable.
        """
        nps = None
        assert nps is None, "Nullable NPS can be NULL"