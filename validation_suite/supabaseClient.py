"""
Supabase Client Module
======================
Provides a singleton Supabase client for the validation pipeline.
Reads credentials from environment variables (via .env file).

Usage:
    from supabaseClient import get_supabase_client
    client = get_supabase_client()
"""

import os
import sys
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from .env file in the same directory
# ---------------------------------------------------------------------------
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# ---------------------------------------------------------------------------
# Validate that credentials are present
# ---------------------------------------------------------------------------
if not SUPABASE_URL:
    raise EnvironmentError(
        "Missing SUPABASE_URL. Add it to validation_suite/.env and restart."
    )
if not SUPABASE_ANON_KEY:
    raise EnvironmentError(
        "Missing SUPABASE_ANON_KEY. Add it to validation_suite/.env and restart."
    )

# ---------------------------------------------------------------------------
# Singleton client instance
# ---------------------------------------------------------------------------
_client = None


def get_supabase_client():
    """
    Returns a singleton Supabase client instance.
    Lazily initialised on first call to avoid import-time side effects.
    """
    global _client
    if _client is None:
        try:
            from supabase import create_client
            _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            print(f"[SupabaseClient] Connected to {SUPABASE_URL}")
        except Exception as exc:
            print(f"[SupabaseClient] ERROR — Failed to create client: {exc}")
            raise
    return _client


def health_check() -> bool:
    """
    Quick connectivity check — fetches 1 row from the company table.
    Returns True if the connection is alive, False otherwise.
    """
    try:
        client = get_supabase_client()
        response = client.table("companies").select("company_id").limit(1).execute()
        if response.data is not None:
            print("[SupabaseClient] Health check PASSED ✓")
            return True
        print("[SupabaseClient] Health check FAILED — no data returned")
        return False
    except Exception as exc:
        print(f"[SupabaseClient] Health check FAILED — {exc}")
        return False


# ---------------------------------------------------------------------------
# Self-test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Running Supabase client self-test...")
    ok = health_check()
    sys.exit(0 if ok else 1)
