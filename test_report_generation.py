"""
Quick test for report generation endpoint
"""
import requests
import json

# Load sample data
with open('tests/fixtures/sample_qualified_projects.json', 'r') as f:
    qualified_projects = json.load(f)

# Use only 2 projects for faster testing
test_data = {
    "qualified_projects": qualified_projects[:2],
    "tax_year": 2024,
    "company_name": "Test Corporation"
}

print("Testing report generation endpoint...")
print(f"Sending {len(test_data['qualified_projects'])} projects")

try:
    response = requests.post(
        'http://localhost:8000/api/generate-report',
        json=test_data,
        timeout=120
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success!")
        print(f"Report ID: {result.get('report_id')}")
        print(f"PDF Path: {result.get('pdf_path')}")
        print(f"Execution Time: {result.get('execution_time_seconds')}s")
    else:
        print(f"✗ Failed")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"✗ Error: {e}")
