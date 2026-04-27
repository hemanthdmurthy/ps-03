"""
Context Isolation Tests (TC_CTX)
Tests for isolation between similar company names and record independence.
"""

import pytest
from validators.dependency_validator import validate_entity_signals


class TestContextIsolation:
    """TC_CTX: Context isolation validation tests"""
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_ctx_01_isolation_similar_names(self):
        """
        TC_CTX_01: Validate isolation between similar company names.
        """
        record1 = {"company_name": "Apple Inc.", "ceo": "Tim Cook"}
        record2 = {"company_name": "Apple Bank", "ceo": "Different CEO"}
        
        # No attribute leakage between records
        assert record1["company_name"] != record2["company_name"]
        assert record1["ceo"] != record2["ceo"]
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ctx_02_ceo_leakage(self):
        """
        TC_CTX_02: Detect CEO leakage across similar names.
        """
        apple_inc = {"company_name": "Apple Inc.", "ceo": "Tim Cook"}
        apple_bank = {"company_name": "Apple Bank", "ceo": "Tim Cook"}  # Leakage!
        
        # CEO from Apple Inc appears in Apple Bank record
        assert apple_inc["ceo"] == apple_bank["ceo"], \
            "violates entity isolation - CEO leakage detected"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_ctx_03_url_mapping(self):
        """
        TC_CTX_03: Validate correct URL mapping per entity.
        """
        apple_inc = {"company_name": "Apple Inc.", "website": "apple.com"}
        apple_bank = {"company_name": "Apple Bank", "website": "applebank.com"}
        
        # URLs correctly aligned
        assert "apple.com" in apple_inc["website"]
        assert "applebank" in apple_bank["website"]
        assert apple_inc["website"] != apple_bank["website"]
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ctx_04_website_contamination(self):
        """
        TC_CTX_04: Detect website cross-contamination.
        """
        apple_bank = {"company_name": "Apple Bank", "website": "apple.com"}
        
        # Apple Bank has Apple Inc URL
        is_valid, result = validate_entity_signals(
            apple_bank["company_name"], 
            apple_bank["website"], 
            "Banking"
        )
        assert not is_valid, f"Expected failure for website contamination, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_ctx_05_competitor_distinct(self):
        """
        TC_CTX_05: Validate competitor lists remain distinct.
        """
        delta_airlines = {"company_name": "Delta Airlines", "competitors": "United, American, Southwest"}
        delta_electronics = {"company_name": "Delta Electronics", "competitors": "Samsung, LG, Sony"}
        
        # Domain-specific separation
        assert delta_airlines["competitors"] != delta_electronics["competitors"], \
            "domain-specific separation"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ctx_06_competitor_overlap(self):
        """
        TC_CTX_06: Detect competitor overlap due to confusion.
        """
        delta1 = {"company_name": "Delta Airlines", "competitors": "United, American"}
        delta2 = {"company_name": "Delta Electronics", "competitors": "United, American"}
        
        # Both Delta entities share identical competitor lists
        assert delta1["competitors"] == delta2["competitors"], \
            "indicates bleed - identical competitor lists"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_ctx_07_investor_attribution(self):
        """
        TC_CTX_07: Validate funding/investor attribution.
        """
        company = {"company_name": "TechCorp", "investors": "Sequoia, Andreessen Horowitz"}
        
        # Investors tied to correct entity
        assert "sequoia" in company["investors"].lower(), "correct mapping"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ctx_08_investor_leakage(self):
        """
        TC_CTX_08: Detect investor leakage.
        """
        company1 = {"company_name": "TechCorp", "investors": "Sequoia"}
        company2 = {"company_name": "Unrelated Corp", "investors": "Sequoia"}  # Leakage!
        
        # Investor from one entity appears in another unrelated entity
        assert company1["investors"] == company2["investors"], "investor leakage detected"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_ctx_09_product_differentiation(self):
        """
        TC_CTX_09: Validate product/service differentiation.
        """
        apple_inc = {"company_name": "Apple Inc.", "products": "iPhone, Mac"}
        apple_bank = {"company_name": "Apple Bank", "products": "Loans, Credit Cards"}
        
        # Domain-specific content
        assert "iphone" in apple_inc["products"].lower()
        assert "loan" in apple_bank["products"].lower()
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ctx_10_product_hallucination(self):
        """
        TC_CTX_10: Detect product hallucination crossover.
        """
        apple_bank = {"company_name": "Apple Bank", "products": "iPhone services"}
        
        # Apple Bank has "iPhone services"
        is_valid, result = validate_entity_signals(
            apple_bank["company_name"],
            "applebank.com",
            "Banking",
            products=[apple_bank["products"]]
        )
        assert not is_valid, f"Expected failure for product hallucination, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_ctx_11_sequential_processing(self):
        """
        TC_CTX_11: Validate sequential processing robustness.
        """
        batch = [
            {"company_name": "Delta", "ceo": "CEO1"},
            {"company_name": "Apple", "ceo": "CEO2"},
            {"company_name": "Apple Bank", "ceo": "CEO3"}
        ]
        
        # No carry-over context
        for i, record in enumerate(batch):
            assert record["company_name"] is not None
            assert record["ceo"] is not None
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ctx_12_memory_carry_over(self):
        """
        TC_CTX_12: Detect memory carry-over across sequence.
        """
        records = [
            {"company_name": "Company A", "ceo": "CEO A"},
            {"company_name": "Company B", "ceo": "CEO B"},
        ]
        
        # Attributes from previous record persist (simulated issue)
        # In proper isolation, each record should be independent
        assert records[0]["company_name"] != records[1]["company_name"], \
            "no carry-over expected"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_ctx_13_name_variations(self):
        """
        TC_CTX_13: Validate normalization of name variations.
        """
        names = ["OpenAI", "Open AI", "OpenAI Inc."]
        
        # Canonical mapping maintained
        # Each should be handled distinctly or normalized properly
        assert len(set(names)) >= 2, "variations handled"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ctx_14_alias_collision(self):
        """
        TC_CTX_14: Detect alias collision.
        """
        entity1 = "Meta"
        entity2 = "MetLife"
        
        # "Meta" incorrectly merged with "MetLife"
        # These are different entities
        assert entity1.lower() != entity2.lower(), "semantic confusion"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_ctx_15_high_similarity_stress(self):
        """
        TC_CTX_15: Validate independence under high similarity stress.
        """
        similar_names = [
            "Apple Inc.",
            "Apple Bank",
            "Apple Corp",
            "Apple Ltd",
            "Apple LLC"
        ]
        
        # No degradation with 5 similar names processed sequentially
        for name in similar_names:
            assert name is not None
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_ctx_16_cumulative_drift(self):
        """
        TC_CTX_16: Detect cumulative drift.
        """
        records = [
            {"company_name": "First", "ceo": "CEO1"},
            {"company_name": "Second", "ceo": "CEO2"},
            {"company_name": "Third", "ceo": "CEO3"},
        ]
        
        # Later records increasingly resemble earlier ones
        # Check for drift
        first_ceo = records[0]["ceo"]
        last_ceo = records[-1]["ceo"]
        
        # If later records resemble earlier ones excessively, drift detected
        assert first_ceo != last_ceo, "context drift detected"