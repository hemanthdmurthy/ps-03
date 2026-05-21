import httpx

SUPABASE_URL = "https://hkwessehtaonqaakzyvj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhrd2Vzc2VodGFvbnFhYWt6eXZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzMTEwMzksImV4cCI6MjA5MTg4NzAzOX0.4w-K12jyYlGT3dDXNa6ypRyhzheM2FkG5VLmmeB7GN8"

headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
}

tables_to_check = [
    "users",
    "students",
    "student_profiles",
    "profiles",
    "skills",
    "student_skills",
    "resumes",
    "student_resumes",
    "user_profiles",
    "company",
    "companies",
    "staging_company"
]

def check():
    print("Checking Supabase tables...")
    for table in tables_to_check:
        url = f"{SUPABASE_URL}/rest/v1/{table}?limit=1"
        try:
            resp = httpx.get(url, headers=headers)
            if resp.status_code == 200:
                print(f"[+] Table '{table}' exists! Status: 200")
            elif resp.status_code == 404:
                print(f"[-] Table '{table}' does not exist. Status: 404")
            else:
                print(f"[?] Table '{table}' status {resp.status_code}")
        except Exception as e:
            print(f"Error checking '{table}': {e}")

if __name__ == "__main__":
    check()
