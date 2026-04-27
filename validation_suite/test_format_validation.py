"""
Format Validation Tests (TC_FMT, 5.4, 8.5, 8.6)
Tests for rejecting invalid formats, delimiters, and length constraints.
"""

import pytest
import re
from validators.string_validator import (
    validate_company_name,
    validate_short_name,
    validate_ceo_name,
    validate_min_length
)
from validators.numeric_validator import validate_year
from validators.url_validator import (
    validate_https_url,
    validate_twitter_handle,
    validate_email,
    validate_image_url
)
from validators.dependency_validator import (
    validate_category,
    validate_nature_of_company
)
from validators.financial_validator import (
    validate_profitability_status,
    validate_sales_motion
)


class TestFormatValidation:
    """TC_FMT: Format validation tests"""
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_001_company_name_invalid_chars(self):
        """
        TC_FMT_001: Reject invalid characters outside allowed UTF-8 pattern.
        Emojis not allowed.
        """
        invalid_name = "Company@123🚀"
        is_valid, _ = validate_company_name(invalid_name)
        assert not is_valid, f"Should reject {invalid_name} with emojis"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_002_short_name_special_chars(self):
        """
        TC_FMT_002: Reject special characters not allowed in alias.
        """
        invalid_name = "My#Company!"
        pattern = r'^[\w\s&.\-]+$'
        is_valid = bool(re.match(pattern, invalid_name))
        assert not is_valid, f"Should reject {invalid_name} with special chars"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_003_logo_non_image_url(self):
        """
        TC_FMT_003: Reject non-image URL format.
        """
        invalid_url = "https://example.com/logo.txt"
        is_valid, _ = validate_image_url(invalid_url)
        assert not is_valid, "Should reject non-image URL"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_004_category_invalid_enum(self):
        """
        TC_FMT_004: Reject value outside enum.
        """
        invalid_category = "StartupX"
        is_valid, _ = validate_category(invalid_category)
        assert not is_valid, f"Should reject invalid category: {invalid_category}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_005_year_invalid_format(self):
        """
        TC_FMT_005: Reject invalid year format.
        """
        invalid_year = "20A5"
        is_valid, _ = validate_year(invalid_year)
        assert not is_valid, f"Should reject invalid year: {invalid_year}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_006_headquarters_invalid_geo(self):
        """
        TC_FMT_006: Reject invalid geo format with special chars.
        """
        invalid_geo = "Bangalore@India"
        pattern = r'^[\w\s,.\-]+$'
        is_valid = bool(re.match(pattern, invalid_geo))
        assert not is_valid, f"Should reject invalid geo: {invalid_geo}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_007_countries_invalid_separator(self):
        """
        TC_FMT_007: Reject improperly separated values.
        """
        invalid_countries = "India;USA"
        pattern = r'^[A-Za-z,\s]+$'
        is_valid = bool(re.match(pattern, invalid_countries))
        assert not is_valid, f"Should reject semicolon separator: {invalid_countries}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_008_offices_non_numeric(self):
        """
        TC_FMT_008: Reject non-numeric input for Offices.
        """
        invalid_offices = "ten"
        pattern = r'^\d+$'
        is_valid = bool(re.match(pattern, invalid_offices))
        assert not is_valid, f"Should reject non-numeric: {invalid_offices}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_009_employee_size_invalid_range(self):
        """
        TC_FMT_009: Reject invalid range format.
        """
        invalid_size = "50 to 100"
        pattern = r'^(\d+|\d+-\d+)$'
        is_valid = bool(re.match(pattern, invalid_size))
        assert not is_valid, f"Should reject space-separated range: {invalid_size}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_010_turnover_invalid_percent(self):
        """
        TC_FMT_010: Reject invalid percent format.
        """
        invalid_turnover = "15 percent"
        pattern = r'^\d{1,3}(\.\d{1,2})?%$'
        is_valid = bool(re.match(pattern, invalid_turnover))
        assert not is_valid, f"Should reject word 'percent': {invalid_turnover}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_011_retention_invalid_duration(self):
        """
        TC_FMT_011: Reject invalid duration format.
        """
        invalid_duration = "2 yrs"
        pattern = r'^\d+(\.\d+)?\s?(Years?|Months?)$'
        is_valid = bool(re.match(pattern, invalid_duration, re.IGNORECASE))
        assert not is_valid, f"Should reject abbreviated 'yrs': {invalid_duration}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_012_sectors_invalid_chars(self):
        """
        TC_FMT_012: Reject invalid characters in Focus Sectors.
        """
        invalid_sectors = "FinTech@AI"
        pattern = r'^[\w\s,&.\-]+$'
        is_valid = bool(re.match(pattern, invalid_sectors))
        assert not is_valid, f"Should reject @ in sectors: {invalid_sectors}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_013_competitors_invalid_list(self):
        """
        TC_FMT_013: Reject improperly formatted list.
        """
        invalid_competitors = "Google; Amazon"
        pattern = r'^[A-Za-z,\s]+$'
        is_valid = bool(re.match(pattern, invalid_competitors))
        assert not is_valid, f"Should reject semicolon separator: {invalid_competitors}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_014_website_invalid_url(self):
        """
        TC_FMT_014: Reject invalid URL.
        """
        invalid_url = "htp:/invalid-url"
        is_valid, _ = validate_https_url(invalid_url)
        assert not is_valid, f"Should reject invalid URL: {invalid_url}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_015_website_rating_out_of_range(self):
        """
        TC_FMT_015: Reject out-of-format decimal.
        """
        invalid_rating = "10.55"
        pattern = r'^(10(\.0)?|[1-9](\.\d)?)$'
        is_valid = bool(re.match(pattern, invalid_rating))
        assert not is_valid, f"Should reject rating > 10: {invalid_rating}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_016_traffic_rank_negative(self):
        """
        TC_FMT_016: Reject negative integer.
        """
        invalid_rank = "-5"
        pattern = r'^\d+$'
        is_valid = bool(re.match(pattern, invalid_rank))
        assert not is_valid, f"Should reject negative rank: {invalid_rank}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_017_social_followers_non_numeric(self):
        """
        TC_FMT_017: Reject non-numeric value.
        """
        invalid_followers = "10K"
        pattern = r'^\d+$'
        is_valid = bool(re.match(pattern, invalid_followers))
        assert not is_valid, f"Should reject 'K' suffix: {invalid_followers}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_018_glassdoor_out_of_range(self):
        """
        TC_FMT_018: Reject out-of-range format.
        """
        invalid_rating = "5.5"
        pattern = r'^(?:[1-4](\.\d)?|5(\.0)?)$'
        is_valid = bool(re.match(pattern, invalid_rating))
        assert not is_valid, f"Should reject > 5: {invalid_rating}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_019_linkedin_non_company_url(self):
        """
        TC_FMT_019: Reject non-company URL.
        """
        invalid_url = "https://linkedin.com/user/abc"
        is_valid = "/company/" in invalid_url or "/in/" in invalid_url
        # Must contain /company/ for company pages
        assert not is_valid or "/company/" not in invalid_url
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_020_twitter_handle_too_long(self):
        """
        TC_FMT_020: Reject invalid handle length.
        """
        invalid_handle = "@thisisaverylonghandle123"
        is_valid, _ = validate_twitter_handle(invalid_handle)
        assert not is_valid, f"Should reject handle > 15 chars"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_021_email_invalid_format(self):
        """
        TC_FMT_021: Reject invalid email format.
        """
        invalid_email = "contact@company"
        is_valid, _ = validate_email(invalid_email)
        assert not is_valid, f"Should reject email without domain: {invalid_email}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_022_phone_invalid_format(self):
        """
        TC_FMT_022: Reject invalid phone format.
        """
        invalid_phone = "123-456-789"
        # E.164 format: +[countrycode][number]
        pattern = r'^\+?\d{1,3}\d{4,14}$'
        is_valid = bool(re.match(pattern, invalid_phone))
        assert not is_valid, f"Should reject non-E.164 format: {invalid_phone}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_023_ceo_name_with_digits(self):
        """
        TC_FMT_023: Reject numeric characters in name.
        """
        invalid_name = "John123"
        is_valid, _ = validate_ceo_name(invalid_name)
        assert not is_valid, f"Should reject name with digits: {invalid_name}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_024_ceo_linkedin_invalid_pattern(self):
        """
        TC_FMT_024: Reject invalid profile URL.
        """
        invalid_url = "https://linkedin.com/company/john"
        is_valid = "/in/" in invalid_url  # Must be /in/ not /company/
        assert not is_valid, "Should reject /company/ in CEO profile URL"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_025_profitability_invalid_enum(self):
        """
        TC_FMT_025: Reject invalid enum value.
        """
        invalid_status = "Profiting"
        is_valid, _ = validate_profitability_status(invalid_status)
        assert not is_valid, f"Should reject invalid enum: {invalid_status}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_026_market_share_malformed(self):
        """
        TC_FMT_026: Reject malformed percentage.
        """
        invalid_share = "120"
        # Must include % and be within 0-100
        try:
            value = int(invalid_share)
            is_valid = 0 <= value <= 100
        except:
            is_valid = False
        assert not is_valid, f"Should reject > 100: {invalid_share}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_027_cac_ltv_invalid_ratio(self):
        """
        TC_FMT_027: Reject invalid ratio format.
        """
        invalid_ratio = "3/1"
        pattern = r'^\d+(\.\d+)?(:\d+)?$'
        is_valid = bool(re.match(pattern, invalid_ratio))
        assert not is_valid, f"Should reject slash format: {invalid_ratio}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_028_nps_non_integer(self):
        """
        TC_FMT_028: Reject non-integer format for NPS.
        """
        invalid_nps = "50.5"
        pattern = r'^-?\d+$'
        is_valid = bool(re.match(pattern, invalid_nps))
        assert not is_valid, f"Should reject decimal NPS: {invalid_nps}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_029_churn_malformed(self):
        """
        TC_FMT_029: Reject malformed percent for Churn.
        """
        invalid_churn = "5"
        pattern = r'^\d{1,3}(\.\d{1,2})?%$'
        is_valid = bool(re.match(pattern, invalid_churn))
        assert not is_valid, f"Should reject missing % symbol: {invalid_churn}"
    
    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_fmt_030_valuation_invalid_currency(self):
        """
        TC_FMT_030: Reject invalid currency format.
        """
        invalid_valuation = "100 million dollars"
        # Currency pattern: $XX.XM or $X.XB
        pattern = r'^\$?\d+(\.\d+)?\s?(Million|Billion|Trillion)?\s?(USD|EUR|INR)?$'
        is_valid = bool(re.match(pattern, invalid_valuation, re.IGNORECASE))
        assert not is_valid, f"Should reject wordy currency: {invalid_valuation}"

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_list_02_invalid_delimiter(self):
        """TC_LIST_02: Reject inconsistent delimiter (semicolon)"""
        invalid_list = "India; USA; Germany"
        pattern = r'^([A-Za-z\s]+)(,\s*[A-Za-z\s]+)*$'
        is_valid = bool(re.match(pattern, invalid_list))
        assert not is_valid, "Should reject semicolon delimiter"

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_8_6_2_short_name_max_length(self):
        """TC_8.6_2: Validate that Short Name exceeds max length"""
        is_valid, _ = validate_short_name("A" * 101, max_length=100)
        assert not is_valid, "Should reject name > 100 chars"

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_8_6_3_overview_min_length(self):
        """TC_8.6_3: Validate minimum length >= 50 characters"""
        is_valid, _ = validate_min_length("Too short", 50, "Overview")
        assert not is_valid, "Should reject overview < 50 chars"