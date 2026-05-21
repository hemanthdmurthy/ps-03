import pytest
from validators import (
    validate_year,
    validate_market_share,
    validate_nps,
    validate_revenue,
    validate_revenue_mix,
    validate_churn_rate
)


class TestPrecisionValidation:

    # =========================
    # YEAR VALIDATION
    # =========================
    @pytest.mark.parametrize("year", [2001, 2020, 1999])
    def test_year_valid(self, year):
        is_valid, _ = validate_year(year)
        assert is_valid

    @pytest.mark.parametrize("year", ["~2001", "2001.0", "01", 2099])
    def test_year_invalid(self, year):
        is_valid, _ = validate_year(year)
        assert not is_valid


    # =========================
    # MARKET SHARE
    # =========================
    @pytest.mark.parametrize("share", ["15%", "15.5%", "0.5%"])
    def test_market_share_valid(self, share):
        is_valid, _ = validate_market_share(share)
        assert is_valid

    @pytest.mark.parametrize("share", ["15", "0.15", "101%", -5, 120])
    def test_market_share_invalid(self, share):
        is_valid, _ = validate_market_share(share)
        assert not is_valid


    # =========================
    # NPS
    # =========================
    @pytest.mark.parametrize("nps", [72, -30, 0, 100, -100])
    def test_nps_valid(self, nps):
        is_valid, _ = validate_nps(nps)
        assert is_valid

    @pytest.mark.parametrize("nps", [72.5, 101, -101, "72"])
    def test_nps_invalid(self, nps):
        is_valid, _ = validate_nps(nps)
        assert not is_valid


    # =========================
    # REVENUE FORMAT
    # =========================
    @pytest.mark.parametrize("revenue", ["$50.3B", "$50,300,000,000"])
    def test_revenue_valid(self, revenue):
        is_valid, _ = validate_revenue(revenue)
        assert is_valid

    @pytest.mark.parametrize("revenue", ["50300000000", "50B", "$-50M", -100, 0])
    def test_revenue_invalid(self, revenue):
        is_valid, _ = validate_revenue(revenue)
        assert not is_valid


    # =========================
    # REVENUE MIX
    # =========================
    @pytest.mark.parametrize("ratio", ["80/20", "70%/30%", "50/50"])
    def test_revenue_mix_valid(self, ratio):
        is_valid, _ = validate_revenue_mix(ratio)
        assert is_valid

    @pytest.mark.parametrize("ratio", ["80/25", "60/30", "100/10"])
    def test_revenue_mix_invalid(self, ratio):
        is_valid, _ = validate_revenue_mix(ratio)
        assert not is_valid


    # =========================
    # CHURN RATE
    # =========================
    @pytest.mark.parametrize("churn", ["15%", "0%", "100%"])
    def test_churn_valid(self, churn):
        is_valid, _ = validate_churn_rate(churn)
        assert is_valid

    @pytest.mark.parametrize("churn", ["101%", "-1%", "15", 150, -5])
    def test_churn_invalid(self, churn):
        is_valid, _ = validate_churn_rate(churn)
        assert not is_valid