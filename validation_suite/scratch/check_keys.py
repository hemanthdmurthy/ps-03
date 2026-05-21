from fetchData import fetch_all_companies
companies = fetch_all_companies()
if companies:
    print(f"Keys: {list(companies[0].keys())}")
else:
    print("No companies found")
