# print_ather_values.py
import sys
import os
import json

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from app.db import db_service

def check():
    company = db_service.get_company_by_name("Ather Energy Limited")
    if company:
        print("Ather Energy Limited current column values:")
        for col, val in company.items():
            print(f"- {col}: {val}")
    else:
        print("Ather Energy Limited not found!")

if __name__ == "__main__":
    check()
