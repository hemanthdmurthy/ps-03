
import sys
import os
sys.path.append(os.getcwd())

from app.db import db_service
from app.config import settings

print(f"Supabase URL: {settings.SUPABASE_URL}")

def check_table(table_name):
    url = f"{db_service.url}/rest/v1/{table_name}?limit=1"
    try:
        resp = db_service.client.get(url)
        if resp.status_code == 200:
            print(f"Table '{table_name}' exists and is accessible. Rows: {len(resp.json())}")
        elif resp.status_code == 404:
            print(f"Table '{table_name}' does not exist (404).")
        else:
            print(f"Table '{table_name}' returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Error checking '{table_name}': {e}")

check_table("staging_company")
check_table("companies")
