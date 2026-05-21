# check_ather_fixed.py
import sys
import os
import json

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from app.db import db_service

def check():
    print("Checking Ather Energy Limited in Supabase 'companies' table...")
    company = db_service.get_company_by_name("Ather Energy Limited")
    if company:
        print("Ather Energy Limited found!")
        # Print keys and some sample fields to not truncate
        print(f"Columns available: {list(company.keys())}")
        print(f"Company ID: {company.get('company_id')}")
        print(f"Name: {company.get('name')}")
        print(f"Headquarters: {company.get('headquarters_address')}")
    else:
        print("Ather Energy Limited NOT found in Supabase 'companies' table.")

if __name__ == "__main__":
    check()
