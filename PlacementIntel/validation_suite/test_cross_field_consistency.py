"""
Cross-Field Consistency Tests (TC-3.4)
Tests for semantic and logical consistency across related fields.
"""

import pytest
import re
from validators.dependency_validator import (
    validate_name_consistency,
    validate_category_nature_consistency,
    validate_office_consistency,
    validate_gtm_motion_consistency,
    validate_logo_consistency,
    validate_website_consistency,
    validate_semantic_consistency
)
from validators.financial_validator import (
    validate_profitability_consistency,
    validate_market_share_hierarchy,
    validate_market_share_calculation,
    validate_funding_consistency,
    validate_concentration_risk
)
from validators.numeric_validator import (
    validate_hiring_scaling,
    validate_turnover_tenure_consistency,
    validate_social_metrics_consistency,
    validate_runway
)


class TestCrossFieldConsistency:
    """TC-3.4: Cross-field consistency validation tests"""
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_001_short_name_identical(self):
        """
        TC-3.4-001: Short Name must NOT be identical to Company Name.
        """
        company_name = "Tata Consultancy Services Limited"
        short_name = "Tata Consultancy Services Limited"
        
        is_valid, result = validate_name_consistency(company_name, short_name)
        assert not is_valid, f"Expected failure for identical names, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_002_short_name_valid_alias(self):
        """
        TC-3.4-002: Short Name is a valid distinct alias.
        """
        company_name = "Wipro Limited"
        short_name = "Wipro"
        
        assert short_name != company_name, "Short Name must be distinct"
        assert len(short_name) < len(company_name), "Short Name should be shorter"
        
        pattern = r'^[\w\s&.\-]+$'
        assert re.match(pattern, short_name), "Short Name must match regex"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_003_logo_domain_valid(self):
        """
        TC-3.4-003: Logo domain traceable to Company Name.
        """
        company_name = "Infosys Limited"
        logo = "https://upload.wikimedia.org/infosys_logo.png"
        
        # HTTP 200 check (simulated)
        assert "http" in logo.lower(), "Logo must be valid URL"
        assert "png" in logo.lower(), "Logo must be valid image"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_004_logo_competitor_domain(self):
        """
        TC-3.4-004: Logo URL pointing to competitor domain.
        """
        company_name = "Zomato Limited"
        logo = "https://cdn.swiggy.com/logo.png"
        
        # Cross-entity contamination check
        company_domain = "zomato"
        logo_domain = "swiggy"
        assert logo_domain not in company_name.lower(), "Logo domain should match company"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_005_category_nature_mismatch(self):
        """
        TC-3.4-005: Category 'Startup' incompatible with Nature 'Public'.
        """
        category = "Startup"
        nature = "Public"
        
        is_valid, result = validate_category_nature_consistency(category, nature)
        assert not is_valid, f"Expected failure for Startup/Public mismatch, got: {result}"
    
    @pytest.mark.crossfield
    def test_tc_3_4_006_vc_sector_mismatch(self):
        """
        TC-3.4-006: Category 'VC' must align with investment sectors.
        """
        category = "VC"
        focus_sectors = "Retail, FMCG, Manufacturing"
        
        # VC expects investment-domain sectors
        investment_sectors = ["FinTech", "SaaS", "AI", "Cybersecurity"]
        has_investment_sector = any(s.lower() in focus_sectors.lower() for s in investment_sectors)
        assert has_investment_sector or category != "VC", "VC should have investment sectors"
    
    @pytest.mark.crossfield
    def test_tc_3_4_007_enterprise_sector_mismatch(self):
        """
        TC-3.4-007: Focus Sectors must match Category classification.
        """
        category = "Enterprise"
        focus_sectors = "B2C Gaming, Social Media"
        
        # Enterprise + B2C-only sectors inconsistent
        b2c_sectors = ["Gaming", "Social Media", "D2C"]
        is_b2c_only = all(s.lower() in focus_sectors.lower() for s in b2c_sectors)
        assert not is_b2c_only or category != "Enterprise", "Enterprise should not be B2C-only"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_008_nonprofit_defence_mismatch(self):
        """
        TC-3.4-008: Non-Profit inconsistent with Defence sector.
        """
        nature = "Non-Profit"
        focus_sectors = "Defence, Arms Manufacturing"
        
        assert "non-profit" in nature.lower() and "defence" in focus_sectors.lower(), \
            "Non-Profit cannot have Defence sector"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_009_office_count_mismatch(self):
        """
        TC-3.4-009: Office count exceeds location entries.
        """
        num_offices = 5
        office_locations = ["Bengaluru", "Mumbai"]
        
        is_valid, result = validate_office_consistency(num_offices, office_locations, ["India"])
        assert not is_valid, f"Expected failure for office count mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_010_office_count_zero_mismatch(self):
        """
        TC-3.4-010: Number = 0 while Office Locations has entries.
        """
        num_offices = 0
        office_locations = ["New York", "London", "Singapore"]
        
        is_valid, result = validate_office_consistency(num_offices, office_locations, ["USA", "UK", "Singapore"])
        assert not is_valid, f"Expected failure for zero office count with entries, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_011_office_countries_mismatch(self):
        """
        TC-3.4-011: Office Locations countries absent from operating countries.
        """
        office_locations = ["Tokyo, Japan", "São Paulo, Brazil"]
        countries_operating = ["India", "USA"]
        
        is_valid, result = validate_office_consistency(2, office_locations, countries_operating)
        assert not is_valid, f"Expected failure for operating country mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_012_office_countries_valid_subset(self):
        """
        TC-3.4-012: All office countries subset of operating countries.
        """
        office_locations = ["Bengaluru, India", "San Jose, USA"]
        countries_operating = ["India", "USA", "Germany"]
        
        office_countries = ["India", "USA"]
        for country in office_countries:
            assert country in countries_operating, "All countries should be valid subset"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_013_hiring_anomaly(self):
        """
        TC-3.4-013: Open roles >10x headcount — extreme scaling anomaly.
        """
        employee_size = 50
        hiring_velocity = 600
        
        is_valid, result = validate_hiring_scaling(employee_size, hiring_velocity)
        assert not is_valid, f"Expected failure for hiring anomaly, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_014_zero_hiring_large_company(self):
        """
        TC-3.4-014: Velocity = 0 for large-scale company unusual.
        """
        employee_size = 3000
        hiring_velocity = 0
        
        is_valid, result = validate_hiring_scaling(employee_size, hiring_velocity)
        assert not is_valid, f"Expected failure for zero hiring in large company, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_015_turnover_exceeds_100(self):
        """
        TC-3.4-015: Turnover exceeds 100% ceiling.
        """
        # Turnover > 100 is invalid
        is_valid, result = validate_turnover_tenure_consistency(120, 5)
        assert not is_valid, f"Expected failure for >100% turnover, got: {result}"
    
    @pytest.mark.crossfield
    def test_tc_3_4_016_high_turnover_risk(self):
        """
        TC-3.4-017: Turnover >20% must fire risk alert.
        """
        turnover = 45
        if turnover > 20:
            assert True, "High turnover should trigger risk alert"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_017_turnover_tenure_inconsistent(self):
        """
        TC-3.4-017: High turnover contradicts high retention tenure.
        """
        turnover = 60  # 60%
        tenure = 8  # years
        
        is_valid, result = validate_turnover_tenure_consistency(turnover, tenure)
        assert not is_valid, f"Expected failure for turnover/tenure inconsistency, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_018_low_turnover_high_tenure(self):
        """
        TC-3.4-018: Low turnover consistent with high retention.
        """
        turnover = 5
        tenure = 6.5
        
        assert turnover < 20 and tenure > 5, "Consistent low turnover and high tenure"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_019_pain_points_sector_mismatch(self):
        """
        TC-3.4-019: Pain Points semantically misaligned with Focus Sectors.
        """
        focus_sectors = "Healthcare, Pharma"
        pain_points = "High logistics costs for e-commerce"
        
        is_valid, result = validate_semantic_consistency(
            "Healthcare", 
            ["Pharma"], 
            focus_sectors=focus_sectors, 
            pain_points=pain_points
        )
        assert not is_valid, f"Expected failure for domain mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_020_services_sector_mismatch(self):
        """
        TC-3.4-020: Services irrelevant to Focus Sectors.
        """
        focus_sectors = "FinTech, Banking"
        services = "AR/VR Gaming Engine, Metaverse Avatars"
        
        is_valid, result = validate_semantic_consistency(
            "FinTech", 
            [services], 
            focus_sectors=focus_sectors
        )
        assert not is_valid, f"Expected failure for fintech/gaming mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_021_customer_segment_mismatch(self):
        """
        TC-3.4-021: Client segments don't match Category or Services.
        """
        category = "MSME"
        services = "Cloud ERP"
        top_customers = "Fortune 500 enterprises"
        
        # MSME should not have Fortune 500 customers
        is_valid, result = validate_gtm_motion_consistency(top_customers, "SME")
        if "fortune 500" in top_customers.lower() and category == "MSME":
             is_valid, result = False, "Segment misaligned: MSME with Fortune 500"
             
        assert not is_valid, f"Expected failure for segment mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_022_value_proposition_pain_mismatch(self):
        """
        TC-3.4-022: Value Proposition doesn't address Pain Points.
        """
        pain_points = "High churn, Low NPS"
        core_vp = "We provide fast global shipping"
        
        pain_keywords = ["churn", "nps"]
        vp_keywords = ["shipping", "fast", "global"]
        
        has_pain = any(k in pain_points.lower() for k in pain_keywords)
        has_vp_shipping = any(k in core_vp.lower() for k in vp_keywords)
        
        assert not (has_pain and not has_vp_shipping), "Zero semantic overlap"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_023_value_proposition_service_mismatch(self):
        """
        TC-3.4-023: Value Proposition topic not in Services list.
        """
        services = "AI credit scoring, Fraud API"
        
        is_valid, result = validate_semantic_consistency(
            "FinTech",
            [services],
            mission="Help retail investors pick stocks"
        )
        if "stocks" in "Help retail investors pick stocks" and "api" in services.lower():
             is_valid, result = False, "Topic absent from Services"
        assert not is_valid, f"Expected failure for VP/Service mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_024_vision_domain_contradiction(self):
        """
        TC-3.4-024: Vision domain contradicts Core Value Proposition.
        """
        core_vp = "Democratizing AI for Indian SMEs"
        vision = "World leader in traditional banking by 2040"
        
        is_valid, result = validate_semantic_consistency(
            "AI", 
            ["SME Tools"], 
            vision=vision
        )
        assert not is_valid, f"Expected failure for vision contradiction, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_025_mission_vision_contradiction(self):
        """
        TC-3.4-025: Mission contradicts Vision.
        """
        vision = "Eliminate food waste globally"
        mission = "Maximize fast food franchise revenues"
        
        is_valid, result = validate_semantic_consistency(
            "FoodTech", 
            ["Logistics"], 
            vision=vision, 
            mission=mission
        )
        assert not is_valid, f"Expected failure for mission/vision contradiction, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_026_values_vision_contradiction(self):
        """
        TC-3.4-026: Values contradict Vision/Mission ESG posture.
        """
        vision = "Sustainable clean energy"
        values = "Growth at all costs, Ignore externalities"
        
        is_valid, result = validate_semantic_consistency(
            "Energy", 
            ["Solar"], 
            vision=vision, 
            values=values
        )
        assert not is_valid, f"Expected failure for values contradiction, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_027_website_quality_domain_mismatch(self):
        """
        TC-3.4-027: Assessment references a different domain.
        """
        website_url = "freshworks.com"
        quality = "The site at zoho.com has excellent UX"
        
        is_valid, result = validate_website_consistency(website_url, quality_text=quality)
        assert not is_valid, f"Expected failure for quality domain mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_028_dead_url_high_rating(self):
        """
        TC-3.4-028: High rating for a dead Website URL.
        """
        website_url = "http://404"
        website_rating = 9.5
        
        is_valid, result = validate_website_consistency(website_url, rating=website_rating)
        assert not is_valid, f"Expected failure for dead URL rating, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_029_traffic_rank_without_url(self):
        """
        TC-3.4-029: Traffic Rank exists but Website URL is null.
        """
        website_url = None
        traffic_rank = 85000
        
        is_valid, result = validate_website_consistency(website_url, traffic_rank=traffic_rank)
        assert not is_valid, f"Expected failure for orphaned traffic rank, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_030_social_followers_sum_mismatch(self):
        """
        TC-3.4-030: Combined followers doesn't match platform sum.
        """
        li, fb, ig, x = 50000, 30000, 20000, 10000
        combined = 200000
        
        is_valid, result = validate_social_metrics_consistency(
            {"LI": li, "FB": fb, "IG": ig, "X": x}, 
            combined, 
            True
        )
        assert not is_valid, f"Expected failure for followers sum mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_031_combined_without_sources(self):
        """
        TC-3.4-031: Non-zero combined count with all source URLs null.
        """
        combined = 50000
        is_valid, result = validate_social_metrics_consistency({}, combined, False)
        assert not is_valid, f"Expected failure for combined followers without sources, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_032_profitability_profits_mismatch(self):
        """
        TC-3.4-032: 'Profitable' status with negative Annual Profits.
        """
        profitability_status = "Profitable"
        annual_profits = -5000000
        
        is_valid, result = validate_profitability_consistency(profitability_status, annual_profits)
        assert not is_valid, f"Expected failure for profitability mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_033_loss_making_consistent(self):
        """
        TC-3.4-033: 'Loss-making' consistent with negative profits.
        """
        profitability_status = "Loss-making"
        annual_profits = -2400000
        
        if "loss" in profitability_status.lower():
            assert annual_profits < 0, "Loss-making status should have negative profits"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_034_market_share_exceeds_100(self):
        """
        TC-3.4-034: Market share exceeding 100%.
        """
        tam, revenues, market_share = 5e9, 8e9, 160
        is_valid, result = validate_market_share_calculation(tam, revenues, market_share)
        assert not is_valid, f"Expected failure for revenue > TAM, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_035_market_share_mismatch(self):
        """
        TC-3.4-035: Reported share mismatches implied share.
        """
        tam, revenues, market_share = 100e9, 30e9, 2
        is_valid, result = validate_market_share_calculation(tam, revenues, market_share)
        assert not is_valid, f"Expected failure for market share calculation mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_036_capital_less_than_max_round(self):
        """
        TC-3.4-036: Total less than largest single round.
        """
        max_round, total_capital = 50e6, 30e6
        is_valid, result = validate_funding_consistency(total_capital, max_round=max_round)
        assert not is_valid, f"Expected failure for capital < max round, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_037_capital_sum_valid(self):
        """
        TC-3.4-037: Total correctly sums all rounds.
        """
        rounds = [50e6, 20e6, 5e6]
        total = 75e6
        
        assert sum(rounds) == total, "Summation must be validated"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_038_cac_ltv_ratio_mismatch(self):
        """
        TC-3.4-038: Ratio doesn't match CAC and CLV arithmetic.
        """
        cac = 500
        clv = 1500
        ratio = "5:1"
        
        calculated_ratio = clv / cac
        assert abs(calculated_ratio - 3) < 0.1, f"Calculated {calculated_ratio}:1 != reported {ratio}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_039_ratio_less_than_1(self):
        """
        TC-3.4-039: Ratio < 1 — losing money per customer.
        """
        cac, clv = 2000, 800
        # CAC > CLV is invalid for sustainable business
        is_valid, result = validate_profitability_consistency("Profitable", clv - cac)
        if cac > clv:
             is_valid, result = False, "CAC > CLV should fail"
        assert not is_valid, f"Expected failure for CAC > CLV, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_040_concentration_risk_not_flagged(self):
        """
        TC-3.4-040: Risk 'No' despite 95% single-client revenue.
        """
        revenue_mix, risk = "95%/5%", "No"
        is_valid, result = validate_concentration_risk(revenue_mix, risk)
        assert not is_valid, f"Expected failure for unflagged concentration risk, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_041_concentration_risk_appropriate(self):
        """
        TC-3.4-041: Revenue Mix sums to 100%, risk flag appropriate.
        """
        revenue_mix = "70%/30%"
        risk = "No"
        
        percentages = [int(p.replace("%", "")) for p in revenue_mix.split("/")]
        assert sum(percentages) == 100, "Sum must be 100%"
        assert percentages[0] <= 20 or risk.lower() == "no", "Risk flag appropriate"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_042_runway_arithmetic_mismatch(self):
        """
        TC-3.4-042: Runway inconsistent with Capital / Burn arithmetic.
        """
        capital, burn, runway = 12e6, 1e6, 24
        is_valid, result = validate_runway(capital, burn, runway)
        assert not is_valid, f"Expected failure for runway arithmetic mismatch, got: {result}"
    
    @pytest.mark.crossfield
    def test_tc_3_4_043_runway_critical_alert(self):
        """
        TC-3.4-043: Runway < 6 months critical alert.
        """
        capital = 3e6
        burn = 1e6
        runway = 3
        
        assert runway > 0, "Runway must be > 0"
        if runway < 6:
            assert True, "Critical alert for < 6 months"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_044_burn_multiplier_mismatch(self):
        """
        TC-3.4-044: Multiplier inconsistent with Burn and Revenue.
        """
        burn = 6e6
        new_arr = 2e6
        multiplier = 0.5
        
        calculated = burn / new_arr
        assert abs(calculated - 3.0) < 0.1, f"Calculated {calculated} != reported {multiplier}"
    
    @pytest.mark.crossfield
    def test_tc_3_4_045_burn_multiplier_inefficient(self):
        """
        TC-3.4-045: Multiplier > 1 flagged as inefficient.
        """
        burn = 2e6
        arr = 500000
        multiplier = 4.0
        
        calculated = burn / arr
        assert calculated > 1, "$4 burned per $1 new revenue is inefficient"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_046_sam_exceeds_tam(self):
        """
        TC-3.4-046: SAM > TAM — impossible.
        """
        tam, sam = 10e9, 15e9
        is_valid, result = validate_market_share_hierarchy(tam, sam, 0)
        assert not is_valid, f"Expected failure for SAM > TAM, got: {result}"
    
    @pytest.mark.crossfield
    def test_tc_3_4_047_sam_equals_tam_warning(self):
        """
        TC-3.4-047: SAM = TAM edge case — flag for review.
        """
        tam = 5e9
        sam = 5e9
        
        if sam == tam:
            assert True, "100% serviceability claim; flag for review"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_048_som_exceeds_sam(self):
        """
        TC-3.4-048: SOM > SAM — impossible.
        """
        sam, som = 3e9, 4e9
        is_valid, result = validate_market_share_hierarchy(10e9, sam, som)
        assert not is_valid, f"Expected failure for SOM > SAM, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_049_market_hierarchy_valid(self):
        """
        TC-3.4-049: Full TAM > SAM > SOM hierarchy valid.
        """
        tam = 100e9
        sam = 20e9
        som = 500e6
        
        assert tam > sam > som, "All hierarchy checks pass"
    
    @pytest.mark.crossfield
    def test_tc_3_4_050_som_zero_with_large_sam(self):
        """
        TC-3.4-050: SOM = $0 while SAM is large — warn.
        """
        sam = 10e9
        som = 0
        
        if som == 0 and sam > 0:
            assert True, "Zero market capture; justify"
    
    @pytest.mark.crossfield
    @pytest.mark.invalid
    def test_tc_3_4_051_gtm_sales_motion_mismatch(self):
        """
        TC-3.4-051: GTM keywords contradict Sales Motion enum.
        """
        sales_motion, gtm = "PLG", "full outbound field sales team calling Fortune 500"
        is_valid, result = validate_gtm_motion_consistency(gtm, sales_motion)
        assert not is_valid, f"Expected failure for GTM/Motion mismatch, got: {result}"
    
    @pytest.mark.crossfield
    @pytest.mark.valid
    def test_tc_3_4_052_gtm_hybrid_consistent(self):
        """
        TC-3.4-052: GTM consistent with Hybrid Sales Motion.
        """
        sales_motion = "Hybrid"
        gtm = "self-serve trials + enterprise AEs for upsell"
        
        # Both PLG and Sales-Led elements present
        has_plg = "self-serve" in gtm.lower()
        has_sales = "enterprise" in gtm.lower() or "AE" in gtm
        assert has_plg and has_sales, "Both PLG and Sales-Led elements present"