"""
Entity Verification Tests (TC_4.1)
Tests for verifying entities exist in trusted external sources using centralized validators.
"""

import pytest
from validators import (
    validate_company_name,
    validate_ceo_name,
    validate_entity_existence,
    validate_placeholder_prevention,
    validate_revenue,
    validate_enum_case_insensitive
)

class TestEntityVerification:
    """TC_4.1: Entity verification tests"""
    
    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_4_1_01_fake_entity(self):
        """TC_4.1_01: Flag entities not found in authoritative sources"""
        known_db = ["Real CEO", "Real Investor"]
        is_valid, _ = validate_entity_existence(["John Xyzzabc"], known_db, "CEO Name")
        assert not is_valid

    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_4_1_07_self_competitor(self):
        """TC_4.1_07: Detect self-listed competitor"""
        # Logic: company_name == competitor_name
        from validators.dependency_validator import validate_name_consistency
        # Reusing name consistency or similar
        is_valid, _ = validate_name_consistency("ABC Tech Pvt Ltd", "ABC Tech Pvt Ltd")
        assert not is_valid

    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_4_1_10_fake_certifications(self):
        """TC_4.1_10: Reject non-existent certifications"""
        valid_compliance = ["SOC2", "ISO27001", "GDPR", "HIPAA", "PCI DSS"]
        is_valid, _ = validate_enum_case_insensitive("SOC5", valid_compliance)
        assert not is_valid

    @pytest.mark.datasource
    @pytest.mark.invalid
    def test_tc_4_1_09_placeholder_text(self):
        """TC_4.1_09: Detect synthetic or placeholder text patterns"""
        is_valid, _ = validate_placeholder_prevention("Lorem ipsum dolor sit amet...", "Overview")
        # We need to add Lorem Ipsum to the placeholder list
        assert not is_valid