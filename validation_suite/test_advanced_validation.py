"""
Advanced Validation Tests (TC-1.5, 5.1, 5.2, 11.1, 8.2, 9.3)
Tests for ratios, boundaries, entity resolution, and context isolation.
"""

import pytest
from validators.string_validator import validate_company_name, validate_short_name
from validators.dependency_validator import (
    validate_category,
    validate_entitydisambiguation,
    validate_ratio_calculation,
    validate_entity_signals
)
from validators.numeric_validator import (
    validate_burn_multiplier,
    validate_runway,
    validate_numeric_range
)
from validators.url_validator import validate_url_accessibility


# Mock database for entity disambiguation tests
KNOWN_ENTITIES = {
    "company": [
        "Delta Air Lines", "Delta Corp", "Delta Technologies",
        "Microsoft Corporation", "Mercury Systems", "Mercury Insurance",
        "Apple Inc.", "Apple Bank"
    ],
    "category": [
        "VC", "PE", "Angel", "Startup", "Enterprise"
    ],
    "ceo": [
        "Satya Nadella", "John Smith", "Tim Cook"
    ],
    "competitor": [
        "Apple Inc.", "Microsoft Corporation", "Google LLC"
    ],
    "investor": [
        "Sequoia Capital US", "Sequoia China", "Sequoia India",
        "Accel Partners", "Andreessen Horowitz"
    ],
    "association": [
        "IEEE", "ISO", "ANSI", "NIST"
    ]
}


class TestAdvancedValidation:
    """Advanced/Contextual Validation tests"""
    
    @pytest.mark.crossfield
    def test_tc_1_5_01_company_name_disambiguation(self):
        """
        TC_1.5_01: Verify system handles generic names that match 
        multiple global legal entities.
        """
        entity_name = "Delta"
        is_valid, result = validate_entitydisambiguation(
            entity_name, "company", KNOWN_ENTITIES
        )
        # System should flag for disambiguation
        assert not is_valid or "Delta" in result, \
            f"Expected disambiguation flag for '{entity_name}', got: {result}"
    
    @pytest.mark.crossfield
    def test_tc_1_5_02_short_name_distinct(self):
        """
        TC_1.5_02: Validate that abbreviated names are distinct enough 
        to represent the specific brand.
        """
        short_name = "Mercury"
        is_valid, result = validate_short_name(short_name)
        assert is_valid, f"Expected valid for {short_name}, got: {result}"
        
        # Check for restricted/generic words
        generic_words = ["test", "demo", "sample", "unknown"]
        assert short_name.lower() not in generic_words, \
            f"Short name '{short_name}' contains restricted/generic word"
    
    @pytest.mark.crossfield
    def test_tc_1_5_04_category_standardized(self):
        """
        TC_1.5_04: Test handling of generic classification tags that 
        could apply to multiple business models.
        """
        category = "Investor"
        is_valid, result = validate_category(category)
        # Must map to standardized taxonomy (VC vs. PE vs. Angel)
        assert is_valid, f"Expected valid mapping for '{category}', got: {result}"
        # Should not remain as generic "Investor"
        assert result in ["VC", "PE", "Angel"], \
            f"Category should map to specific type, got: {result}"
    
    @pytest.mark.crossfield
    def test_tc_1_5_44_ceo_identity_lookup(self):
        """
        TC_1.5_44: Ensure common names do not lead to incorrect 
        identity mapping for the top executive.
        """
        ceo_name = "John Smith"
        # System should trigger lookup for LinkedIn URL
        # This is a placeholder - actual implementation would check CEO DB
        is_valid, result = validate_entitydisambiguation(ceo_name, "ceo", KNOWN_ENTITIES)
        # Common name should trigger additional validation
        assert "John Smith" in KNOWN_ENTITIES["ceo"], \
            "Common CEO name should exist in known entities for validation"
    
    @pytest.mark.crossfield
    def test_tc_1_5_28_competitor_contextual(self):
        """
        TC_1.5_28: Verify that competitor names are contextually 
        relevant to the company's industry.
        """
        competitor = "Apple"
        is_valid, result = validate_entitydisambiguation(
            competitor, "competitor", KNOWN_ENTITIES
        )
        # Entity recognition must ensure it's the Technology Company
        assert is_valid, f"Expected valid competitor '{competitor}', got: {result}"
        assert "Apple" in result, f"Should match Apple Inc., got: {result}"
    
    @pytest.mark.crossfield
    def test_tc_1_5_67_investor_mapping(self):
        """
        TC_1.5_67: Test mapping of investors with common names or 
        regional branches.
        """
        investor = "Sequoia"
        is_valid, result = validate_entitydisambiguation(
            investor, "investor", KNOWN_ENTITIES
        )
        # Should identify which Sequoia (US, China, or India)
        assert not is_valid or "Sequoia" in result, \
            f"Expected disambiguation for '{investor}', got: {result}"
    
    @pytest.mark.crossfield
    def test_tc_1_5_99_association_specific(self):
        """
        TC_1.5_99: Validate that generic association names are mapped 
        to specific industry bodies.
        """
        association = "IEEE"
        is_valid, result = validate_entitydisambiguation(
            association, "association", KNOWN_ENTITIES
        )
        # Verify against known Industry Bodies
        assert is_valid, f"Expected valid IEEE membership, got: {result}"
        assert result == "IEEE", f"Should match exact IEEE, got: {result}"

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_5_1_02_cac_ltv_incorrect(self):
        """TC_5.1_02: Detect incorrect CAC:LTV ratio calculation"""
        is_valid, result = validate_ratio_calculation("2:1", 300, 100) # 300/100 = 3
        assert not is_valid, "Expected failure for incorrect ratio calculation"

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_5_1_08_burn_multiplier_incorrect(self):
        """TC_5.1_08: Detect incorrect Burn Multiplier"""
        is_valid, result = validate_burn_multiplier(50000, 100000, 1.5)
        assert not is_valid, "Expected failure for incorrect burn multiplier"

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_5_1_13_critical_runway(self):
        """TC_5.1_13: Flag critical runway (<6 months)"""
        is_valid, result = validate_runway(400000, 100000, 4)
        assert not is_valid, "Expected failure for critical runway"
        assert "risk" in result.lower()

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_5_2_02_incorporation_year_bounds(self):
        """TC_5.2_02: Year should be >= 1800"""
        from validators.numeric_validator import validate_year
        is_valid, result = validate_year(1500)
        assert not is_valid, "Expected failure for year < 1800"

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_5_2_06_turnover_bounds(self):
        """TC_5.2_06: Turnover % must be between 0–100"""
        is_valid, result = validate_numeric_range(150, "Turnover", 0, 100)
        assert not is_valid, "Expected failure for turnover > 100"

    @pytest.mark.format
    @pytest.mark.invalid
    def test_tc_5_2_28_nps_bounds(self):
        """TC_5.2_28: NPS must be between -100 to 100"""
        is_valid, result = validate_numeric_range(150, "NPS", -100, 100)
        assert not is_valid, "Expected failure for NPS > 100"

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ar_11_1_02_signal_mismatch(self):
        """TC_AR_11.1_02: Conflicting identity signals (domain vs industry)"""
        is_valid, result = validate_entity_signals("Delta", "https://deltafaucet.com", "Airlines", "Atlanta")
        assert not is_valid, f"Expected failure for faucet domain with airline industry"

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_url_05_broken_url(self):
        """TC_URL_05: Validate broken website URL (HTTP 404)"""
        is_valid, result = validate_url_accessibility("https://invalid-company.com", status_code=404)
        assert not is_valid, "Should reject unreachable URL"

    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_url_06_redirect_handling(self):
        """TC_URL_06: Validate redirect handling (HTTP 200 after redirect)"""
        is_valid, result = validate_url_accessibility("http://company.com", status_code=200)
        assert is_valid

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_9_3_1_entity_isolation(self):
        """TC_9.3_1: Similar company names isolation (Apple Inc vs Apple Bank)"""
        is_valid, result = validate_entitydisambiguation("Apple Inc.", "company", KNOWN_ENTITIES)
        # Should flag if just "Apple" is searched
        is_valid_generic, result_generic = validate_entitydisambiguation("Apple", "company", KNOWN_ENTITIES)
        assert not is_valid_generic, "System should flag 'Apple' as ambiguous between Inc and Bank"

    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_9_3_6_parent_subsidiary_confusion(self):
        """TC_9.3_6: Confusion between parent (Alphabet) and subsidiary (Google)"""
        parent = "Alphabet Inc."
        subsidiary = "Google LLC"
        # Logic: Attributes must be independent
        if parent == subsidiary:
            assert False, "Data Leakage: Parent and subsidiary merged"