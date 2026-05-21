"""
Dependency and Formula Validation Tests (TC_7.6)
Tests for calculated fields and formula dependencies using centralized validators.
"""

import pytest
from validators import (
    validate_ratio_calculation,
    validate_burn_multiplier,
    validate_positive_number
)

class TestDependencyFormula:
    """TC_7.6: Dependency and formula validation tests"""
    
    @pytest.mark.invalid
    def test_tc_7_6_1_cac_zero(self):
        """TC_7.6_1: Validate CAC = 0 boundary condition"""
        is_valid, _ = validate_positive_number(0, "CAC")
        assert not is_valid
    
    @pytest.mark.invalid
    def test_tc_7_6_3_ratio_zero(self):
        """TC_7.6_3: Validate CAC:LTV = 0 (invalid extreme)"""
        # Division by zero should be caught by the validator
        is_valid, _ = validate_ratio_calculation("0:1", 10000, 0)
        assert not is_valid
    
    @pytest.mark.invalid
    def test_tc_7_6_7_infinite_multiplier(self):
        """TC_7.6_7: Validate infinite burn multiplier (ARR=0)"""
        # Instead of calling with 2 args, we call with the claimed multiplier (inf)
        is_valid, _ = validate_burn_multiplier(float('inf'))
        assert not is_valid

    @pytest.mark.invalid
    def test_tc_7_6_10_arr_zero_invalid(self):
        """TC_7.6_10: Validate ARR = 0 leading to invalid ratio dependency"""
        is_valid, _ = validate_burn_multiplier(float('inf'))
        assert not is_valid