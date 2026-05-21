
import sys
import os
sys.path.append(os.getcwd())

from app.db import db_service
from app.config import settings

print(f"Supabase URL: {settings.SUPABASE_URL}")

try:
    companies = db_service.get_all_companies()
    print(f"Fetched {len(companies)} companies from 'staging_company'")
    if companies:
        print(f"First company: {companies[0].get('name', 'N/A')}")
        print(f"Keys: {list(companies[0].keys())[:10]}")
    else:
        print("No companies found in 'staging_company'")
except Exception as e:
    print(f"Error: {e}")
