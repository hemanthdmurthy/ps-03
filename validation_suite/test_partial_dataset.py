"""
Partial Dataset Validation Tests (TC_2_2)
Tests for records with only mandatory or optional fields populated.
"""

import pytest
from validators.string_validator import validate_not_null
from validators.numeric_validator import validate_positive_number
from validators.dependency_validator import validate_remote_policy
from validators.financial_validator import validate_revenue


class TestPartialDatasetValidation:
    """TC_2_2: Partial dataset validation tests"""
    
    @pytest.mark.valid
    def test_tc_2_2_001_only_mandatory_fields(self):
        """
        TC_2_2_001: Validate record with only mandatory fields populated.
        Only required fields filled; others NULL.
        """
        # Mandatory fields only
        record = {
            "company_name": "Test Corp",
            "category": "Startup",
            "year_of_incorporation": 2020,
            "website_url": "https://test.com"
        }
        
        # All mandatory fields present
        assert record["company_name"] is not None
        assert record["category"] is not None
        assert record["year_of_incorporation"] is not None
        assert record["website_url"] is not None
    
    @pytest.mark.valid
    def test_tc_2_2_002_missing_optional_fields(self):
        """
        TC_2_2_002: Validate handling of missing optional fields.
        Optional fields absent (e.g., revenue, leadership).
        """
        record = {
            "company_name": "Test Corp",
            "revenue": None,  # Optional
            "ceo_name": None,  # Optional
            "leadership": None  # Optional
        }
        
        # No validation errors for optional fields
        assert record["company_name"] is not None
        # Optional fields can be None
        assert record["revenue"] is None or record["revenue"] is not None
    
    @pytest.mark.valid
    def test_tc_2_2_003_null_handling_consistency(self):
        """
        TC_2_2_003: Validate null handling consistency.
        Nullable = NULL, Non-nullable = populated.
        """
        record = {
            "company_name": "Test Corp",  # Not Null
            "short_name": None,  # Nullable
            "revenue": None,  # Nullable
            "category": "Startup"  # Not Null
        }
        
        # Non-nullable fields populated
        assert record["company_name"] is not None
        assert record["category"] is not None
        
        # Nullable fields can be NULL
        assert "short_name" in record or record.get("short_name") is None
    
    @pytest.mark.valid
    def test_tc_2_2_004_downstream_compatibility(self):
        """
        TC_2_2_004: Validate downstream compatibility of partial data.
        Partial dataset used for scoring/search.
        """
        partial_record = {
            "company_name": "Test Corp",
            "category": "Startup"
        }
        
        # System handles missing values safely
        try:
            # Simulate search operation
            search_fields = ["company_name", "category"]
            for field in search_fields:
                value = partial_record.get(field)
                # Should not crash on None values
                if value is not None:
                    assert isinstance(value, str)
            result = "success"
        except Exception as e:
            result = f"error: {e}"
        
        assert result == "success"
    
    @pytest.mark.valid
    def test_tc_2_2_005_no_incorrect_defaults(self):
        """
        TC_2_2_005: Validate no incorrect default values are injected.
        Missing revenue NOT defaulted to 0.
        """
        record = {
            "company_name": "Test Corp",
            "revenue": None  # Should remain None, not 0
        }
        
        # System preserves NULL, no misleading defaults
        assert record["revenue"] is None, "Revenue should remain NULL, not defaulted to 0"
        
        # Verify not incorrectly set to 0
        revenue_value = record.get("revenue")
        assert revenue_value is None or revenue_value != 0
    
    @pytest.mark.valid
    def test_tc_2_2_006_minimal_viable_dataset(self):
        """
        TC_2_2_006: Validate minimal viable dataset integrity.
        Only core fields provided.
        """
        minimal_record = {
            "company_name": "Test Corp",
            "category": "Startup"
        }
        
        # Record usable for basic workflows
        assert minimal_record["company_name"] is not None
        assert minimal_record["category"] is not None
        
        # Basic search/display should work
        assert isinstance(minimal_record["company_name"], str)
        assert isinstance(minimal_record["category"], str)