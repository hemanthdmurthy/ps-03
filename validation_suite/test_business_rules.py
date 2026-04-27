"""
Business Rules Validation Tests (Section 14.2 & 4.2)
Tests for entity-specific applicability and narrative consistency.
"""

import pytest
from validators.dependency_validator import (
    validate_applicability, 
    validate_entity_existence, 
    validate_leadership,
    validate_semantic_consistency
)
from validators.string_validator import validate_na_vs_not_public

class TestBusinessRules:
    """Section 14.2: Entity-specific applicability rules"""

    @pytest.mark.business_rule
    @pytest.mark.valid
    def test_tc_014_001_vc_products_na(self):
        """TC_014_001: Validate VC entity with non-applicable product field"""
        is_valid, result = validate_applicability(
            category_value="VC",
            field_value="N/A",
            category_type="Category",
            field_name="Products",
            restricted_categories=["VC"]
        )
        assert is_valid

    @pytest.mark.business_rule
    @pytest.mark.invalid
    def test_tc_014_002_vc_products_exist(self):
        """TC_014_002: Validate VC entity incorrectly having products"""
        is_valid, result = validate_applicability(
            category_value="VC",
            field_value="SaaS Platform",
            category_type="Category",
            field_name="Products",
            restricted_categories=["VC"]
        )
        assert not is_valid, f"Expected failure for VC with products, got: {result}"

    @pytest.mark.business_rule
    @pytest.mark.valid
    def test_tc_014_007_nonprofit_profit_na(self):
        """TC_014_007: Validate nonprofit entity with no profit field"""
        is_valid, result = validate_applicability(
            category_value="Non-Profit",
            field_value="N/A",
            category_type="Nature",
            field_name="Annual Profits",
            restricted_categories=["Non-Profit"]
        )
        assert is_valid

    @pytest.mark.business_rule
    @pytest.mark.invalid
    def test_tc_014_008_nonprofit_profit_exists(self):
        """TC_014_008: Validate nonprofit entity incorrectly having profit"""
        is_valid, result = validate_applicability(
            category_value="Non-Profit",
            field_value="$5M",
            category_type="Nature",
            field_name="Annual Profits",
            restricted_categories=["Non-Profit"]
        )
        assert not is_valid, f"Expected failure for Non-Profit with profits, got: {result}"

    @pytest.mark.business_rule
    @pytest.mark.invalid
    def test_tc_014_302_na_vs_not_public(self):
        """TC_014_302: Validate distinction between 'N/A' vs 'Not Public'"""
        is_valid, result = validate_na_vs_not_public("N/A", "Private")
        assert not is_valid, f"Expected failure for N/A in private company, got: {result}"
        assert "Not Public" in result

    @pytest.mark.business_rule
    @pytest.mark.valid
    def test_tc_014_015_saas_supply_chain_na(self):
        """TC_014_015: Validate SaaS company without physical supply chain"""
        is_valid, result = validate_applicability(
            category_value="SaaS",
            field_value="N/A",
            category_type="Industry",
            field_name="Supply Chain",
            restricted_categories=["SaaS"]
        )
        assert is_valid

    @pytest.mark.business_rule
    @pytest.mark.invalid
    def test_tc_4_2_01_leadership_mismatch(self):
        """TC_4.2_01: CEO mismatch (Sundar Pichai for non-Google)"""
        company = "StartupX"
        ceo = "Sundar Pichai"
        known_leadership = {"Google": "Sundar Pichai", "Microsoft": "Satya Nadella"}
        is_valid, result = validate_leadership(company, ceo, known_leadership)
        assert not is_valid, f"Expected failure for leadership mismatch, got: {result}"

    @pytest.mark.business_rule
    @pytest.mark.invalid
    def test_tc_4_2_05_fabricated_customers(self):
        """TC_4.2_05: Fabricated customer references"""
        customers = ["Microsoft", "Amazon"]
        known_customers = ["Unknown Startup Partner"] # Simulated knowledge
        is_valid, result = validate_entity_existence(customers, known_customers, "Top Customers")
        assert not is_valid, f"Expected failure for fabricated customers"

    @pytest.mark.business_rule
    @pytest.mark.invalid
    def test_tc_4_2_10_narrative_inconsistency(self):
        """TC_4.2_10: Semantic inconsistency across fields"""
        category = "AI SaaS"
        services = ["Logistics trucking services"]
        is_valid, result = validate_semantic_consistency(category, services)
        assert not is_valid, f"Expected failure for narrative inconsistency"
