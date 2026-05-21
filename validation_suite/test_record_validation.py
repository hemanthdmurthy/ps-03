"""
Record Validation Tests (TC-1.2, 11.2 - 11.5, 8.1)
Tests for invalid inputs, entity inheritance, regional deduplication, and data types.
"""

import pytest
from validators.string_validator import (
    validate_company_name,
    validate_not_null,
    validate_min_length
)
from validators.numeric_validator import validate_year
from validators.url_validator import validate_https_url
from validators.dependency_validator import (
    validate_category,
    validate_remote_policy,
    validate_inheritance_logic
)
from validators.financial_validator import (
    validate_revenue,
    validate_sales_motion
)
from validators.record_validator import (
    validate_null_density,
    validate_regional_uniqueness,
    validate_canonical_unification,
    validate_data_type
)


class TestRecordValidation:
    """Record-level validation tests"""
    
    @pytest.mark.invalid
    @pytest.mark.parametrize("company_name", [None, "", " "])
    def test_tc_1_2_001_company_name_null(self, company_name):
        """
        TC-1.2-001: Invalid/Empty Input
        Verify rejection of null or whitespace names for mandatory legal entities.
        """
        is_valid, result = validate_company_name(company_name if company_name else "")
        assert not is_valid, f"Expected failure for {company_name}, got: {result}"
    
    @pytest.mark.invalid
    def test_tc_1_2_004_category_empty(self):
        """
        TC-1.2-004: Invalid/Empty Input
        Ensure classification cannot be bypassed with empty strings.
        """
        is_valid, result = validate_category("")
        assert not is_valid, f"Expected failure for empty category, got: {result}"
    
    @pytest.mark.invalid
    @pytest.mark.parametrize("year", [None, "NULL"])
    def test_tc_1_2_005_year_null(self, year):
        """
        TC-1.2-005: Invalid/Empty Input
        Validate that a numeric year is present.
        """
        is_valid, result = validate_year(year)
        assert not is_valid, f"Expected failure for {year}, got: {result}"
    
    @pytest.mark.invalid
    def test_tc_1_2_006_overview_min_length(self):
        """
        TC-1.2-006: Invalid/Empty Input
        Check minimum length constraint against empty/short text.
        """
        overview = "Short text"
        is_valid, result = validate_min_length(overview, 50, "Overview")
        assert not is_valid, f"Expected failure for short overview, got: {result}"
    
    @pytest.mark.invalid
    def test_tc_1_2_032_website_url_empty(self):
        """
        TC-1.2-032: Invalid/Empty Input
        Ensure core tracking domain is not empty.
        """
        is_valid, result = validate_https_url("")
        assert not is_valid, f"Expected failure for empty URL, got: {result}"

    @pytest.mark.record_level
    @pytest.mark.invalid
    def test_tc_014_006_excessive_nulls(self):
        """TC_014_006: Validate excessive NULL values in entity"""
        record = {
            "Company Name": "ABC Corp",
            "CEO Name": None,
            "Website URL": None,
            "Category": None
        }
        is_valid, result = validate_null_density(record, threshold=3)
        assert not is_valid, f"Expected failure for excessive NULLs, got: {result}"

    @pytest.mark.record_level
    @pytest.mark.invalid
    def test_tc_11_2_012_inheritance_error(self):
        """TC-11.2-012: Parent employee count assigned to subsidiary"""
        parent_size = 50000 # Alphabet
        subsidiary_size = 50000 # Google (incorrectly copied)
        is_valid, result = validate_inheritance_logic(parent_size, subsidiary_size, "Employee Size")
        assert not is_valid, f"Expected failure for inherited parent metrics"

    @pytest.mark.record_level
    @pytest.mark.invalid
    def test_tc_11_3_002_regional_merge_error(self):
        """TC-11.3-002: Different regional entities merged as same record"""
        entities = [
            {"name": "Unilever", "region": "UK"},
            {"name": "Unilever", "region": "UK"} # Duplicate entry
        ]
        is_valid, result = validate_regional_uniqueness(entities)
        assert not is_valid, f"Expected failure for duplicate regional record"

    @pytest.mark.record_level
    @pytest.mark.invalid
    def test_tc_11_4_001_acronym_duplication(self):
        """TC-11.4-001: IBM vs International Business Machines fragmentation"""
        mapping_db = {"IBM": "ID_101", "INTERNATIONAL BUSINESS MACHINES": "ID_102"}
        is_valid, result = validate_canonical_unification("IBM", "International Business Machines", mapping_db)
        assert not is_valid, f"Expected failure for fragmented entity naming"

    @pytest.mark.record_level
    @pytest.mark.invalid
    def test_tc_11_5_002_legal_vs_common_duplication(self):
        """TC-11.5-002: Meta Platforms, Inc. vs Meta duplication"""
        mapping_db = {"META": "ID_201", "META PLATFORMS, INC.": "ID_202"}
        is_valid, result = validate_canonical_unification("Meta", "Meta Platforms, Inc.", mapping_db)
        assert not is_valid, f"Expected failure for legal vs common name duplication"

    @pytest.mark.record_level
    @pytest.mark.invalid
    def test_tc_8_1_1_company_name_data_type(self):
        """TC_8.1_1: Validate Company Name is stored as string"""
        is_valid, result = validate_data_type(12345, str, "Company Name")
        assert not is_valid, "Should reject integer for company name"

    @pytest.mark.record_level
    @pytest.mark.invalid
    def test_tc_8_1_5_year_data_type(self):
        """TC_8.1_5: Validate Year is integer"""
        is_valid, result = validate_data_type("2020", int, "Year")
        assert not is_valid, "Should reject string for year"


class TestQualityScoring:
    """Section 15.5: Aggregate Scoring model"""

    @pytest.mark.record_level
    @pytest.mark.invalid
    def test_tc_15_5_001_completeness_threshold(self):
        """TC_15.5_001: Validate overall completeness score below threshold"""
        from validators.record_validator import calculate_quality_scores
        metrics = {"accuracy": 90, "completeness": 50, "recency": 80}
        scores = calculate_quality_scores(metrics)
        assert scores["overall"] < 80, "Overall score should reflect low completeness"

    @pytest.mark.record_level
    @pytest.mark.valid
    def test_tc_15_5_010_assign_quality_grade(self):
        """TC_15.5_010: Assign final quality grade (A–F)"""
        from validators.record_validator import assign_quality_grade
        assert assign_quality_grade(92) == "A"
        assert assign_quality_grade(50) == "F"