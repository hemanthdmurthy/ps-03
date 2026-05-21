# Placement Compass Validation Suite

A comprehensive pytest-based validation framework for data quality testing.

## Folder Structure

```
validation_suite/
├── validators/
│   ├── __init__.py          # Package exports
│   ├── string_validator.py  # String field validations
│   ├── numeric_validator.py # Numeric field validations
│   ├── url_validator.py     # URL/web field validations
│   ├── financial_validator.py # Financial field validations
│   └── dependency_validator.py # Cross-field validations
├── test_basic_validation.py    # TC-1.1: Valid Standard Input
├── test_record_validation.py  # TC-1.2: Invalid/Empty Input
├── test_advanced_validation.py # TC-1.5: Entity Disambiguation
├── test_case_sensitivity.py   # TC-CS: Case Sensitivity
├── conftest.py                 # Shared fixtures
├── pytest.ini                  # Pytest configuration
└── README.md                   # This file
```

## Test Categories

| Test File | Test ID Prefix | Description |
|-----------|---------------|-------------|
| `test_basic_validation.py` | TC-1.1 | Valid standard inputs |
| `test_record_validation.py` | TC-1.2 | Invalid/empty inputs |
| `test_advanced_validation.py` | TC-1.5 | Entity disambiguation |
| `test_case_sensitivity.py` | TC-CS | Case normalization |
| `test_complete_dataset.py` | TC_2_1 | Complete dataset validation |
| `test_partial_dataset.py` | TC_2_2 | Partial dataset validation |
| `test_data_completeness.py` | TC_DC | Data completeness |
| `test_format_validation.py` | TC_FMT | Format validation |
| `test_field_dependency.py` | TC_FD | Field dependency |
| `test_fact_validation.py` | TC-FACT, TC_TA | Fact & temporal accuracy |
| `test_precision_validation.py` | TC-3.3 | Precision validation |
| `test_cross_field_consistency.py` | TC-3.4 | Cross-field consistency |
| `test_data_source_validation.py` | TC_DA_SA | Data source validation |
| `test_entity_verification.py` | TC_4.1 | Entity verification |
| `test_edge_case_validation.py` | TC_6.1 | Edge case validation |
| `test_large_enterprise.py` | TC_6.2 | Large enterprise validation |
| `test_private_company_constraints.py` | TC_6.3, TC_PC | Private company constraints |
| `test_length_validation.py` | TC_LEN | Length constraint validation |
| `test_context_isolation.py` | TC_CTX | Context isolation |

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest test_basic_validation.py

# Run by marker
pytest -m valid
pytest -m invalid
pytest -m format
pytest -m crossfield

# Run with verbose output
pytest -v

# Run specific test
pytest test_basic_validation.py::TestBasicValidation::test_tc_1_1_01_company_name_valid
```

## Available Markers

- `@pytest.mark.valid` - Tests for valid/positive inputs
- `@pytest.mark.invalid` - Tests for invalid/negative inputs
- `@pytest.mark.format` - Tests for format/pattern validation
- `@pytest.mark.crossfield` - Tests for cross-field validation
- `@pytest.mark.temporal` - Tests for temporal/date validation
- `@pytest.mark.datasource` - Tests for data source validation

## Validator Functions

### String Validators
- `validate_company_name()` - Company name with special characters
- `validate_short_name()` - Abbreviated brand names
- `validate_ceo_name()` - Executive names
- `validate_contact_name()` - Contact person names

### Numeric Validators
- `validate_year()` - Year of incorporation (YYYY)
- `validate_positive_number()` - Positive numeric values
- `validate_numeric_range()` - Values within range

### URL Validators
- `validate_https_url()` - HTTPS URL format
- `validate_twitter_handle()` - Twitter handle format
- `validate_email()` - Email format

### Financial Validators
- `validate_revenue()` - Revenue field (Not Null)
- `validate_profitability_status()` - Profitability enum
- `validate_sales_motion()` - Sales motion enum

### Dependency Validators
- `validate_category()` - Business taxonomy
- `validate_remote_policy()` - Remote work policy
- `validate_entitydisambiguation()` - Entity disambiguation

## Test Case Mapping

| Test ID | Test Function | Validator |
|---------|--------------|-----------|
| TC-1.1-01 | `test_tc_1_1_01_company_name_valid` | `validate_company_name` |
| TC-1.1-02 | `test_tc_1_1_02_short_name_valid` | `validate_short_name` |
| TC-1.1-03 | `test_tc_1_1_03_ceo_name_valid` | `validate_ceo_name` |
| TC-1.1-04 | `test_tc_1_1_04_contact_name_valid` | `validate_contact_name` |
| TC-1.2-001 | `test_tc_1_2_001_company_name_null` | `validate_company_name` |
| TC-1.2-004 | `test_tc_1_2_004_category_empty` | `validate_category` |
| TC-1.2-005 | `test_tc_1_2_005_year_null` | `validate_year` |
| TC-1.2-006 | `test_tc_1_2_006_overview_min_length` | `validate_min_length` |
| TC-1.2-032 | `test_tc_1_2_032_website_url_empty` | `validate_https_url` |
| TC-1.2-044 | `test_tc_1_2_044_ceo_name_whitespace` | `validate_ceo_name` |
| TC-1.2-071 | `test_tc_1_2_071_sales_motion_null` | `validate_sales_motion` |
| TC-1.2-090 | `test_tc_1_2_090_remote_policy_empty` | `validate_remote_policy` |
| TC_2_1_001 | `test_tc_2_1_001_all_mandatory_optional_fields` | Multiple validators |
| TC_2_1_002 | `test_tc_2_1_002_format_compliance` | Multiple validators |
| TC_2_1_003 | `test_tc_2_1_003_business_rule_compliance` | Business rules |
| TC_2_1_004 | `test_tc_2_1_004_cross_field_consistency` | Cross-field validation |
| TC_2_1_005 | `test_tc_2_1_005_data_richness_score` | Completeness check |
| TC_2_1_006 | `test_tc_2_1_006_multi_source_consistency` | Multi-source validation |
| TC_2_2_001 | `test_tc_2_2_001_only_mandatory_fields` | Null handling |
| TC_2_2_002 | `test_tc_2_2_002_missing_optional_fields` | Optional field handling |
| TC_2_2_003 | `test_tc_2_2_003_null_handling_consistency` | Nullable consistency |
| TC_2_2_004 | `test_tc_2_2_004_downstream_compatibility` | Partial data compatibility |
| TC_2_2_005 | `test_tc_2_2_005_no_incorrect_defaults` | Default value preservation |
| TC_2_2_006 | `test_tc_2_2_006_minimal_viable_dataset` | Minimal record integrity |
| TC_DC_001 | `test_tc_dc_001_company_name_empty` | Not Null validation |
| TC_DC_002 | `test_tc_dc_002_short_name_null` | Nullable validation |
| TC_DC_003 | `test_tc_dc_003_logo_empty` | Not Null validation |
| TC_DC_004 | `test_tc_dc_004_category_empty` | Not Null validation |
| TC_DC_005 | `test_tc_dc_005_year_empty` | Not Null validation |
| TC_DC_006 | `test_tc_dc_006_overview_empty` | Not Null validation |
| TC_DC_007 | `test_tc_dc_007_nature_of_company_empty` | Not Null validation |
| TC_DC_008 | `test_tc_dc_008_countries_null` | Nullable validation |
| TC_DC_009 | `test_tc_dc_009_offices_empty` | Nullable validation |
| TC_DC_010 | `test_tc_dc_010_employee_size_empty` | Not Null validation |
| TC_DC_011 | `test_tc_dc_011_turnover_null` | Nullable validation |
| TC_DC_012 | `test_tc_dc_012_website_url_empty` | Not Null validation |
| TC_DC_013 | `test_tc_dc_013_website_rating_null` | Nullable validation |
| TC_DC_015 | `test_tc_dc_015_ceo_name_empty` | Not Null validation |
| TC_DC_016 | `test_tc_dc_016_ceo_linkedin_null` | Nullable validation |
| TC_DC_017 | `test_tc_dc_017_company_email_null` | Nullable validation |
| TC_DC_018 | `test_tc_dc_018_company_phone_null` | Nullable validation |
| TC_DC_019 | `test_tc_dc_019_profitability_empty` | Not Null validation |
| TC_DC_020 | `test_tc_dc_020_annual_revenues_null` | Nullable validation |
| TC_DC_021 | `test_tc_dc_021_cac_null` | Nullable validation |
| TC_DC_022 | `test_tc_dc_022_nps_null` | Nullable validation |
| TC_DC_023 | `test_tc_dc_023_sales_motion_empty` | Not Null validation |
| TC_DC_024 | `test_tc_dc_024_remote_policy_empty` | Not Null validation |
| TC_DC_025 | `test_tc_dc_025_company_maturity_empty` | Not Null validation |
| TC_FMT_001 | `test_tc_fmt_001_company_name_invalid_chars` | Format rejection |
| TC_FMT_002 | `test_tc_fmt_002_short_name_special_chars` | Format rejection |
| TC_FMT_003 | `test_tc_fmt_003_logo_non_image_url` | Format rejection |
| TC_FMT_004 | `test_tc_fmt_004_category_invalid_enum` | Format rejection |
| TC_FMT_005 | `test_tc_fmt_005_year_invalid_format` | Format rejection |
| TC_FMT_006 | `test_tc_fmt_006_headquarters_invalid_geo` | Format rejection |
| TC_FMT_007 | `test_tc_fmt_007_countries_invalid_separator` | Format rejection |
| TC_FMT_008 | `test_tc_fmt_008_offices_non_numeric` | Format rejection |
| TC_FMT_009 | `test_tc_fmt_009_employee_size_invalid_range` | Format rejection |
| TC_FMT_010 | `test_tc_fmt_010_turnover_invalid_percent` | Format rejection |
| TC_FMT_011 | `test_tc_fmt_011_retention_invalid_duration` | Format rejection |
| TC_FMT_012 | `test_tc_fmt_012_sectors_invalid_chars` | Format rejection |
| TC_FMT_013 | `test_tc_fmt_013_competitors_invalid_list` | Format rejection |
| TC_FMT_014 | `test_tc_fmt_014_website_invalid_url` | Format rejection |
| TC_FMT_015 | `test_tc_fmt_015_website_rating_out_of_range` | Format rejection |
| TC_FMT_016 | `test_tc_fmt_016_traffic_rank_negative` | Format rejection |
| TC_FMT_017 | `test_tc_fmt_017_social_followers_non_numeric` | Format rejection |
| TC_FMT_018 | `test_tc_fmt_018_glassdoor_out_of_range` | Format rejection |
| TC_FMT_019 | `test_tc_fmt_019_linkedin_non_company_url` | Format rejection |
| TC_FMT_020 | `test_tc_fmt_020_twitter_handle_too_long` | Format rejection |
| TC_FMT_021 | `test_tc_fmt_021_email_invalid_format` | Format rejection |
| TC_FMT_022 | `test_tc_fmt_022_phone_invalid_format` | Format rejection |
| TC_FMT_023 | `test_tc_fmt_023_ceo_name_with_digits` | Format rejection |
| TC_FMT_024 | `test_tc_fmt_024_ceo_linkedin_invalid_pattern` | Format rejection |
| TC_FMT_025 | `test_tc_fmt_025_profitability_invalid_enum` | Format rejection |
| TC_FMT_026 | `test_tc_fmt_026_market_share_malformed` | Format rejection |
| TC_FMT_027 | `test_tc_fmt_027_cac_ltv_invalid_ratio` | Format rejection |
| TC_FMT_028 | `test_tc_fmt_028_nps_non_integer` | Format rejection |
| TC_FMT_029 | `test_tc_fmt_029_churn_malformed` | Format rejection |
| TC_FMT_030 | `test_tc_fmt_030_valuation_invalid_currency` | Format rejection |
| TC-FD-001 | `test_tc_fd_001_company_name_required` | Required field |
| TC-FD-002 | `test_tc_fd_002_short_name_dependency` | Field dependency |
| TC-FD-003 | `test_tc_fd_003_category_required` | Required field |
| TC-FD-004 | `test_tc_fd_004_year_required` | Required field |
| TC-FD-006 | `test_tc_fd_006_overview_min_length` | Min length |
| TC-FD-045 | `test_tc_fd_045_ceo_linkedin_dependency` | Field dependency |
| TC-FD-065 | `test_tc_fd_065_profitability_financial_dependency` | Cross-field rule |
| TC-FD-079 | `test_tc_fd_079_runway_financial_dependency` | Calculated field |
| TC-FD-110 | `test_tc_fd_110_som_sam_dependency` | Logic rule |
| TC-FD-146 | `test_tc_fd_146_company_maturity_dependency` | Derived field |
| TC-FD-160 | `test_tc_fd_160_global_exposure_dependency` | Data rule |
| TC-FD-163 | `test_tc_fd_163_crisis_behavior_dependency` | Dependency |
| TC-FACT-3.1-HOLISTIC | `test_tc_fact_3_1_holistic_reconciliation` | Multi-source reconciliation |
| TC-FACT-3.1-SEC | `test_tc_fact_3_1_sec_cross_verify` | SEC cross-verification |
| TC-FACT-3.1-LI | `test_tc_fact_3_1_li_cross_verify` | LinkedIn cross-verification |
| TC-FACT-3.1-WEB | `test_tc_fact_3_1_web_verification` | Web verification |
| TC_TA_001 | `test_tc_ta_001_outdated_ceo` | Temporal validation |
| TC_TA_002 | `test_tc_ta_002_current_ceo` | Temporal validation |
| TC_TA_003 | `test_tc_ta_003_outdated_funding` | Temporal validation |
| TC_TA_004 | `test_tc_ta_004_recent_funding` | Temporal validation |
| TC_TA_005 | `test_tc_ta_005_outdated_news` | Temporal validation |
| TC_TA_006 | `test_tc_ta_006_recent_news` | Temporal validation |
| TC_TA_007 | `test_tc_ta_007_future_year` | Temporal validation |
| TC_TA_008 | `test_tc_ta_008_realistic_year` | Temporal validation |
| TC_TA_009 | `test_tc_ta_009_past_roadmap` | Temporal validation |
| TC_TA_010 | `test_tc_ta_010_future_roadmap` | Temporal validation |
| TC_TA_011 | `test_tc_ta_011_past_projection` | Temporal validation |
| TC_TA_012 | `test_tc_ta_012_future_projection` | Temporal validation |
| TC_TA_013 | `test_tc_ta_013_negative_runway` | Temporal validation |
| TC_TA_014 | `test_tc_ta_014_runway_warning` | Temporal validation |
| TC_TA_015 | `test_tc_ta_015_inconsistent_hiring` | Temporal validation |
| TC_TA_016 | `test_tc_ta_016_current_hiring` | Temporal validation |
| TC-3.3-001 | `test_tc_3_3_001_year_valid` | Precision validation |
| TC-3.3-002 | `test_tc_3_3_002_offices_valid` | Precision validation |
| TC-3.3-003 | `test_tc_3_3_003_website_rating_valid` | Precision validation |
| TC-3.3-004 | `test_tc_3_3_004_traffic_rank_valid` | Precision validation |
| TC-3.3-005 | `test_tc_3_3_005_social_followers_sum` | Precision validation |
| TC-3.3-006 | `test_tc_3_3_006_glassdoor_valid` | Precision validation |
| TC-3.3-009 | `test_tc_3_3_009_revenue_valid` | Precision validation |
| TC-3.3-010 | `test_tc_3_3_010_profits_valid` | Precision validation |
| TC-3.3-011 | `test_tc_3_3_011_revenue_mix_valid` | Precision validation |
| TC-3.3-012 | `test_tc_3_3_012_valuation_valid` | Precision validation |
| TC-3.3-013 | `test_tc_3_3_013_growth_valid` | Precision validation |
| TC-3.3-014 | `test_tc_3_3_014_market_share_valid` | Precision validation |
| TC-3.3-015 | `test_tc_3_3_015_capital_raised_valid` | Precision validation |
| TC-3.3-016 | `test_tc_3_3_016_cac_valid` | Precision validation |
| TC-3.3-017 | `test_tc_3_3_017_clv_greater_than_cac` | Precision validation |
| TC-3.3-018 | `test_tc_3_3_018_cac_ltv_valid` | Precision validation |
| TC-3.3-019 | `test_tc_3_3_019_churn_valid` | Precision validation |
| TC-3.3-020 | `test_tc_3_3_020_nps_valid` | Precision validation |
| TC-3.3-021 | `test_tc_3_3_021_burn_valid` | Precision validation |
| TC-3.3-022 | `test_tc_3_3_022_runway_valid` | Precision validation |
| TC-3.3-023 | `test_tc_3_3_023_burn_multiplier_valid` | Precision validation |
| TC-3.3-024 | `test_tc_3_3_024_rd_valid` | Precision validation |
| TC-3.3-025 | `test_tc_3_3_025_tam_valid` | Precision validation |
| TC-3.3-026 | `test_tc_3_3_026_sam_valid` | Precision validation |
| TC-3.3-027 | `test_tc_3_3_027_som_valid` | Precision validation |
| TC-3.3-028 | `test_tc_3_3_028_commute_valid` | Precision validation |
| TC-3.4-001 | `test_tc_3_4_001_short_name_identical` | Cross-field consistency |
| TC-3.4-002 | `test_tc_3_4_002_short_name_valid_alias` | Cross-field consistency |
| TC-3.4-003 | `test_tc_3_4_003_logo_domain_valid` | Cross-field consistency |
| TC-3.4-004 | `test_tc_3_4_004_logo_competitor_domain` | Cross-field consistency |
| TC-3.4-005 | `test_tc_3_4_005_category_nature_mismatch` | Cross-field consistency |
| TC-3.4-006 | `test_tc_3_4_006_vc_sector_mismatch` | Cross-field consistency |
| TC-3.4-007 | `test_tc_3_4_007_enterprise_sector_mismatch` | Cross-field consistency |
| TC-3.4-008 | `test_tc_3_4_008_nonprofit_defence_mismatch` | Cross-field consistency |
| TC-3.4-009 | `test_tc_3_4_009_office_count_mismatch` | Cross-field consistency |
| TC-3.4-010 | `test_tc_3_4_010_office_count_zero_mismatch` | Cross-field consistency |
| TC-3.4-011 | `test_tc_3_4_011_office_countries_mismatch` | Cross-field consistency |
| TC-3.4-012 | `test_tc_3_4_012_office_countries_valid_subset` | Cross-field consistency |
| TC-3.4-013 | `test_tc_3_4_013_hiring_anomaly` | Cross-field consistency |
| TC-3.4-014 | `test_tc_3_4_014_zero_hiring_large_company` | Cross-field consistency |
| TC-3.4-015 | `test_tc_3_4_015_turnover_exceeds_100` | Cross-field consistency |
| TC-3.4-016 | `test_tc_3_4_016_high_turnover_risk` | Cross-field consistency |
| TC-3.4-017 | `test_tc_3_4_017_turnover_tenure_inconsistent` | Cross-field consistency |
| TC-3.4-018 | `test_tc_3_4_018_low_turnover_high_tenure` | Cross-field consistency |
| TC-3.4-019 | `test_tc_3_4_019_pain_points_sector_mismatch` | Cross-field consistency |
| TC-3.4-020 | `test_tc_3_4_020_services_sector_mismatch` | Cross-field consistency |
| TC-3.4-021 | `test_tc_3_4_021_customer_segment_mismatch` | Cross-field consistency |
| TC-3.4-022 | `test_tc_3_4_022_value_proposition_pain_mismatch` | Cross-field consistency |
| TC-3.4-023 | `test_tc_3_4_023_value_proposition_service_mismatch` | Cross-field consistency |
| TC-3.4-024 | `test_tc_3_4_024_vision_domain_contradiction` | Cross-field consistency |
| TC-3.4-025 | `test_tc_3_4_025_mission_vision_contradiction` | Cross-field consistency |
| TC-3.4-026 | `test_tc_3_4_026_values_vision_contradiction` | Cross-field consistency |
| TC-3.4-027 | `test_tc_3_4_027_website_quality_domain_mismatch` | Cross-field consistency |
| TC-3.4-028 | `test_tc_3_4_028_dead_url_high_rating` | Cross-field consistency |
| TC-3.4-029 | `test_tc_3_4_029_traffic_rank_without_url` | Cross-field consistency |
| TC-3.4-030 | `test_tc_3_4_030_social_followers_sum_mismatch` | Cross-field consistency |
| TC-3.4-031 | `test_tc_3_4_031_combined_without_sources` | Cross-field consistency |
| TC-3.4-032 | `test_tc_3_4_032_profitability_profits_mismatch` | Cross-field consistency |
| TC-3.4-033 | `test_tc_3_4_033_loss_making_consistent` | Cross-field consistency |
| TC-3.4-034 | `test_tc_3_4_034_market_share_exceeds_100` | Cross-field consistency |
| TC-3.4-035 | `test_tc_3_4_035_market_share_mismatch` | Cross-field consistency |
| TC-3.4-036 | `test_tc_3_4_036_capital_less_than_max_round` | Cross-field consistency |
| TC-3.4-037 | `test_tc_3_4_037_capital_sum_valid` | Cross-field consistency |
| TC-3.4-038 | `test_tc_3_4_038_cac_ltv_ratio_mismatch` | Cross-field consistency |
| TC-3.4-039 | `test_tc_3_4_039_ratio_less_than_1` | Cross-field consistency |
| TC-3.4-040 | `test_tc_3_4_040_concentration_risk_not_flagged` | Cross-field consistency |
| TC-3.4-041 | `test_tc_3_4_041_concentration_risk_appropriate` | Cross-field consistency |
| TC-3.4-042 | `test_tc_3_4_042_runway_arithmetic_mismatch` | Cross-field consistency |
| TC-3.4-043 | `test_tc_3_4_043_runway_critical_alert` | Cross-field consistency |
| TC-3.4-044 | `test_tc_3_4_044_burn_multiplier_mismatch` | Cross-field consistency |
| TC-3.4-045 | `test_tc_3_4_045_burn_multiplier_inefficient` | Cross-field consistency |
| TC-3.4-046 | `test_tc_3_4_046_sam_exceeds_tam` | Cross-field consistency |
| TC-3.4-047 | `test_tc_3_4_047_sam_equals_tam_warning` | Cross-field consistency |
| TC-3.4-048 | `test_tc_3_4_048_som_exceeds_sam` | Cross-field consistency |
| TC-3.4-049 | `test_tc_3_4_049_market_hierarchy_valid` | Cross-field consistency |
| TC-3.4-050 | `test_tc_3_4_050_som_zero_with_large_sam` | Cross-field consistency |
| TC-3.4-051 | `test_tc_3_4_051_gtm_sales_motion_mismatch` | Cross-field consistency |
| TC-3.4-052 | `test_tc_3_4_052_gtm_hybrid_consistent` | Cross-field consistency |
| TC_DA_SA_001 | `test_tc_da_sa_001_null_data_source` | Data source validation |
| TC_DA_SA_002 | `test_tc_da_sa_002_non_authoritative_source` | Data source validation |
| TC_DA_SA_003 | `test_tc_da_sa_003_source_domain_mismatch` | Data source validation |
| TC_DA_SA_004 | `test_tc_da_sa_004_stale_source_timestamp` | Data source validation |
| TC_DA_SA_005 | `test_tc_da_sa_005_validation_mode_mismatch` | Data source validation |
| TC_DA_SA_006 | `test_tc_da_sa_006_critical_field_low_confidence` | Data source validation |
| TC_DA_SA_007 | `test_tc_da_sa_007_derived_field_missing_lineage` | Data source validation |
| TC_DA_SA_008 | `test_tc_da_sa_008_invalid_source_url` | Data source validation |
| TC_DA_SA_009 | `test_tc_da_sa_009_vague_source` | Data source validation |
| TC_DA_SA_010 | `test_tc_da_sa_010_cross_field_source_inconsistency` | Data source validation |

## Extending the Suite

To add new test cases:
1. Add validator functions to appropriate module in `validators/`
2. Create test function with naming convention `test_<test_id>_<description>`
3. Use appropriate pytest markers
4. Add test to this README's mapping table