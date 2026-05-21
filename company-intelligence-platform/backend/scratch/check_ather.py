# check_ather.py
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.db import db_service

def check():
    print("Checking Ather Energy Limited in Supabase 'companies' table...")
    company = db_service.get_company_by_name("Ather Energy Limited")
    if company:
        print("Ather Energy Limited found!")
        print(json.dumps(company, indent=2))
    else:
        print("Ather Energy Limited NOT found.")

if __name__ == "__main__":
    check()
