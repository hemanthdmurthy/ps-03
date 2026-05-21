# d:\ps_03\company-intelligence-platform\backend\scratch\check_extra_columns.py
import httpx

SUPABASE_URL = "https://hkwessehtaonqaakzyvj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhrd2Vzc2VodGFvbnFhYWt6eXZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzMTEwMzksImV4cCI6MjA5MTg4NzAzOX0.4w-K12jyYlGT3dDXNa6ypRyhzheM2FkG5VLmmeB7GN8"

headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}

candidates = [
    "data", "profile", "report", "parameters", "raw_json", "agent_data",
    "consolidated_profile", "intel", "research", "payload", "result", "results",
    "content", "body", "company_name", "company", "domain_data"
]

def check_extra():
    with httpx.Client(headers=headers) as client:
        for col in candidates:
            url = f"{SUPABASE_URL}/rest/v1/company_intelligence?select={col}&limit=1"
            resp = client.get(url)
            if resp.status_code == 200:
                print(f"Column '{col}' EXISTS in company_intelligence!")
            elif resp.status_code == 400:
                # Column doesn't exist
                pass
            else:
                print(f"Col '{col}' returned status {resp.status_code}: {resp.text}")

if __name__ == "__main__":
    check_extra()
