# check_companies_table.py
import httpx

SUPABASE_URL = "https://hkwessehtaonqaakzyvj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhrd2Vzc2VodGFvbnFhYWt6eXZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzMTEwMzksImV4cCI6MjA5MTg4NzAzOX0.4w-K12jyYlGT3dDXNa6ypRyhzheM2FkG5VLmmeB7GN8"

headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}

def check():
    url = f"{SUPABASE_URL}/rest/v1/companies?select=*"
    resp = httpx.get(url, headers=headers)
    print("Status code:", resp.status_code)
    print("Response JSON:")
    import json
    print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    check()
