import re
from datetime import datetime


# =========================
# GENERIC PRECISION VALIDATOR
# =========================
def validate_precision(value, min_val=None, max_val=None):
    if not isinstance(value, (int, float)):
        return False

    if min_val is not None and value < min_val:
        return False

    if max_val is not None and value > max_val:
        return False

    return True


# =========================
# YEAR VALIDATION
# =========================
def validate_year(year):
    current_year = datetime.now().year

    if not isinstance(year, int):
        return False, "Year must be integer"

    # 🔥 STRICT CHECK
    if year < 1800 or year > current_year:
        return False, "Year out of valid range"

    return True, "Valid"


# =========================
# MARKET SHARE
# =========================
def validate_market_share(value):
    if not isinstance(value, str) or not value.endswith("%"):
        return False

    try:
        num = float(value.replace("%", ""))
        return 0 <= num <= 100
    except:
        return False


# =========================
# NPS
# =========================
def validate_nps(value):
    return isinstance(value, int) and -100 <= value <= 100


# =========================
# REVENUE VALIDATION (FINAL FIX)
# =========================
def validate_revenue(value):
    if not isinstance(value, str):
        return False

    # ❌ Must start with $
    if not value.startswith("$"):
        return False

    # ❌ Reject negative values
    if "-" in value:
        return False

    # ❌ Reject formats like "50B" (missing $)
    # ❌ Reject plain numbers

    # ✅ Strict valid formats:
    # $50.3B
    # $50,300,000,000
    pattern = r'^\$\d{1,3}(,\d{3})*(\.\d+)?(B|M)?$'

    return bool(re.match(pattern, value))