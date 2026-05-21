# get_supabase_openapi.py
import httpx
import json

SUPABASE_URL = "https://hkwessehtaonqaakzyvj.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhrd2Vzc2VodGFvbnFhYWt6eXZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYzMTEwMzksImV4cCI6MjA5MTg4NzAzOX0.4w-K12jyYlGT3dDXNa6ypRyhzheM2FkG5VLmmeB7GN8"

headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
}

def get_schema():
    # Attempt to fetch schema with anon key
    url = f"{SUPABASE_URL}/rest/v1/"
    resp = httpx.get(url, headers=headers)
    print("Status code:", resp.status_code)
    if resp.status_code == 200:
        schema = resp.json()
        print("Successfully fetched schema!")
        # Write schema to a local file
        with open("scratch/supabase_schema.json", "w") as f:
            json.dump(schema, f, indent=2)
        print("Saved schema to scratch/supabase_schema.json")
        
        # Print table names and their columns
        definitions = schema.get("definitions", {})
        print("\nTables found in schema:")
        for table, defs in definitions.items():
            cols = list(defs.get("properties", {}).keys())
            print(f"- {table}: {cols}")
    else:
        print("Response text:", resp.text)

if __name__ == "__main__":
    get_schema()
