"""
Data Source Validation Tests (TC_DA_SA)
Tests for data source traceability and authority validation using centralized validators.
"""

import pytest
from validators import (
    validate_source_traceability,
    validate_recency_threshold,
    validate_enum_case_insensitive
)

# Allowed data sources by category
ALLOWED_SOURCES = {
    "leadership": ["LinkedIn", "Company Website", "Press Release", "API"],
    "financial": ["SEC Filings", "Pitchbook", "Financial Reports", "Annual Report"],
}

class TestDataSourceValidation:
    """TC_DA_SA: Data source validation tests"""
    
    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_da_sa_001_null_data_source(self):
        """TC_DA_SA_001: Every field must have non-null data_source"""
        is_valid, _ = validate_source_traceability(None, "ceo_name")
        assert not is_valid
    
    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_da_sa_002_non_authoritative_source(self):
        """TC_DA_SA_002: data_source values must be authoritative"""
        is_valid, _ = validate_enum_case_insensitive("Random Blog", ALLOWED_SOURCES["leadership"])
        assert not is_valid
    
    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_da_sa_003_source_domain_mismatch(self):
        """TC_DA_SA_003: data_source must align with category"""
        is_valid, _ = validate_enum_case_insensitive("Twitter Post", ALLOWED_SOURCES["financial"])
        assert not is_valid
    
    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_da_sa_004_stale_source_timestamp(self):
        """TC_DA_SA_004: Recent fields must have recent timestamps"""
        is_valid, _ = validate_recency_threshold(2018, max_months=24)
        assert not is_valid
    
    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_da_sa_009_vague_source(self):
        """TC_DA_SA_009: Prevent vague or unverifiable sources"""
        vague_sources = ["Internet", "Various", "Unknown", "Online"]
        # If the source IS in the vague list, it should be rejected
        is_valid, _ = validate_enum_case_insensitive("Internet", ["LinkedIn", "SEC Filings"])
        assert not is_valid

    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_015_204_no_source_provided(self):
        """TC_015_204: No source provided"""
        is_valid, _ = validate_source_traceability(None, "Revenue")
        assert not is_valid