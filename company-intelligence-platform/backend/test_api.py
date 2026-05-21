import sys; sys.path.append('d:/ps_03/company-intelligence-platform/backend');
from fastapi.testclient import TestClient;
from app.main import app;
client = TestClient(app)
response = client.get('/api/session/test_session/parameters')
if response.status_code == 200:
    data = response.json()
    domains = data.get('domains', {})
    for d, d_data in domains.items():
        meta = d_data['meta']
        print(f"{d}: {meta['parameters_count']} params")
    import json
    first_domain = list(domains.values())[0]
    print('Sample Param:', json.dumps(first_domain['parameters'].get('name', {}), indent=2))
else:
    print('Error:', response.status_code, response.text)
