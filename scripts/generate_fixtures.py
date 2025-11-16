"""
Script to generate test fixtures using real API calls.
This script fetches data from Clockify, Unified.to, and OpenRouter APIs
and saves them as JSON fixtures for testing.
"""

import requests
import json
from pathlib import Path
from openai import OpenAI
import sys

# API Configuration
CLOCKIFY_API_KEY = ""
CLOCKIFY_BASE_URL = "https://api.clockify.me/api/v1"

UNIFIED_AUTH = ""
UNIFIED_WORKSPACE_ID = ""

OPENROUTER_API_KEY = ""

# Output directory
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def fetch_clockify_workspace_id():
    """Fetch the Clockify workspace ID."""
    print("Fetching Clockify workspace ID...")
    headers = {'X-Api-Key': CLOCKIFY_API_KEY}
    url = f"{CLOCKIFY_BASE_URL}/workspaces"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        workspaces = response.json()
        
        if workspaces:
            workspace_id = workspaces[0]['id']
            workspace_name = workspaces[0]['name']
            print(f"✓ Found workspace: {workspace_name} (ID: {workspace_id})")
            return workspace_id
        else:
            print("✗ No workspaces found")
            return None
    except Exception as e:
        print(f"✗ Error fetching workspace ID: {e}")
        return None


def fetch_clockify_data(workspace_id):
    """Fetch data from Clockify API."""
    print("\nFetching Clockify data...")
    headers = {'X-Api-Key': CLOCKIFY_API_KEY}
    
    fixtures = {
        "workspace": None,
        "users": None,
        "projects": None,
        "time_entries": None
    }
    
    # Get workspace details
    try:
        url = f"{CLOCKIFY_BASE_URL}/workspaces/{workspace_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        fixtures["workspace"] = response.json()
        print(f"✓ Fetched workspace details")
    except Exception as e:
        print(f"✗ Error fetching workspace: {e}")
    
    # Get users
    try:
        url = f"{CLOCKIFY_BASE_URL}/workspaces/{workspace_id}/users"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        fixtures["users"] = response.json()
        print(f"✓ Fetched {len(fixtures['users'])} users")
    except Exception as e:
        print(f"✗ Error fetching users: {e}")
    
    # Get projects
    try:
        url = f"{CLOCKIFY_BASE_URL}/workspaces/{workspace_id}/projects"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        fixtures["projects"] = response.json()
        print(f"✓ Fetched {len(fixtures['projects'])} projects")
    except Exception as e:
        print(f"✗ Error fetching projects: {e}")
    
    # Get time entries (for the first user if available)
    if fixtures["users"]:
        try:
            user_id = fixtures["users"][0]['id']
            url = f"{CLOCKIFY_BASE_URL}/workspaces/{workspace_id}/user/{user_id}/time-entries"
            params = {"page-size": 10}  # Limit to 10 entries
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            fixtures["time_entries"] = response.json()
            print(f"✓ Fetched {len(fixtures['time_entries'])} time entries")
        except Exception as e:
            print(f"✗ Error fetching time entries: {e}")
    
    # Save to file
    output_file = FIXTURES_DIR / "clockify_responses.json"
    with open(output_file, "w") as f:
        json.dump(fixtures, f, indent=2)
    print(f"✓ Saved Clockify fixtures to {output_file}")
    
    return fixtures


def fetch_unified_to_data():
    """Fetch data from Unified.to API."""
    print("\nFetching Unified.to data...")
    headers = {
        "accept": "application/json",
        "authorization": UNIFIED_AUTH
    }
    
    fixtures = {
        "candidates": None,
        "employees": None,
        "payslips": None
    }
    
    # Get candidates
    try:
        url = f"https://api.unified.to/ats/{UNIFIED_WORKSPACE_ID}/candidate"
        params = {"limit": 5}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        fixtures["candidates"] = response.json()
        print(f"✓ Fetched candidates data")
    except Exception as e:
        print(f"✗ Error fetching candidates: {e}")
    
    # Get employees (HRIS)
    try:
        url = f"https://api.unified.to/hris/{UNIFIED_WORKSPACE_ID}/employee"
        params = {"limit": 5}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        fixtures["employees"] = response.json()
        print(f"✓ Fetched employees data")
    except Exception as e:
        print(f"✗ Error fetching employees: {e}")
    
    # Get payslips
    try:
        url = f"https://api.unified.to/hris/{UNIFIED_WORKSPACE_ID}/payslip"
        params = {"limit": 5}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        fixtures["payslips"] = response.json()
        print(f"✓ Fetched payslips data")
    except Exception as e:
        print(f"✗ Error fetching payslips: {e}")
    
    # Save to file
    output_file = FIXTURES_DIR / "unified_to_responses.json"
    with open(output_file, "w") as f:
        json.dump(fixtures, f, indent=2)
    print(f"✓ Saved Unified.to fixtures to {output_file}")
    
    return fixtures


def fetch_openrouter_data():
    """Fetch sample responses from OpenRouter API."""
    print("\nFetching OpenRouter data...")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    
    fixtures = {
        "qualification_analysis": None,
        "audit_trail_summary": None,
        "compliance_check": None
    }
    
    # Generate qualification analysis
    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            extra_headers={
                "HTTP-Referer": "https://rd-tax-credit-agent.local",
                "X-Title": "R&D Tax Credit Automation Agent"
            },
            messages=[{
                "role": "user",
                "content": "Generate a sample R&D tax credit qualification analysis for a software development project involving machine learning model development. Include confidence score and reasoning."
            }]
        )
        fixtures["qualification_analysis"] = {
            "model": completion.model,
            "response": completion.choices[0].message.content,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens
            }
        }
        print(f"✓ Generated qualification analysis")
    except Exception as e:
        print(f"✗ Error generating qualification analysis: {e}")
    
    # Generate audit trail summary
    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            extra_headers={
                "HTTP-Referer": "https://rd-tax-credit-agent.local",
                "X-Title": "R&D Tax Credit Automation Agent"
            },
            messages=[{
                "role": "user",
                "content": "Generate a sample audit trail summary for R&D tax credit compliance. Include employee time entries, project descriptions, and qualified research activities."
            }]
        )
        fixtures["audit_trail_summary"] = {
            "model": completion.model,
            "response": completion.choices[0].message.content,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens
            }
        }
        print(f"✓ Generated audit trail summary")
    except Exception as e:
        print(f"✗ Error generating audit trail summary: {e}")
    
    # Generate compliance check
    try:
        completion = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            extra_headers={
                "HTTP-Referer": "https://rd-tax-credit-agent.local",
                "X-Title": "R&D Tax Credit Automation Agent"
            },
            messages=[{
                "role": "user",
                "content": "Generate a sample IRS Form 6765 compliance check result for R&D tax credit. Include validation of qualified research expenses and four-part test criteria."
            }]
        )
        fixtures["compliance_check"] = {
            "model": completion.model,
            "response": completion.choices[0].message.content,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "total_tokens": completion.usage.total_tokens
            }
        }
        print(f"✓ Generated compliance check")
    except Exception as e:
        print(f"✗ Error generating compliance check: {e}")
    
    # Save to file
    output_file = FIXTURES_DIR / "openrouter_responses.json"
    with open(output_file, "w") as f:
        json.dump(fixtures, f, indent=2)
    print(f"✓ Saved OpenRouter fixtures to {output_file}")
    
    return fixtures


def main():
    """Main function to generate all fixtures."""
    print("=" * 60)
    print("Generating Test Fixtures from Real API Calls")
    print("=" * 60)
    
    # Fetch Clockify workspace ID first
    workspace_id = fetch_clockify_workspace_id()
    
    if workspace_id:
        # Fetch Clockify data
        clockify_data = fetch_clockify_data(workspace_id)
    else:
        print("\n⚠ Skipping Clockify data fetch due to missing workspace ID")
    
    # Fetch Unified.to data
    unified_data = fetch_unified_to_data()
    
    # Fetch OpenRouter data
    openrouter_data = fetch_openrouter_data()
    
    print("\n" + "=" * 60)
    print("✓ All fixtures generated successfully!")
    print(f"✓ Fixtures saved to: {FIXTURES_DIR}")
    print("=" * 60)
    
    # Automatically enrich fixtures with sample data
    print("\n" + "=" * 60)
    print("Enriching fixtures with sample data...")
    print("=" * 60)
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "enrich_fixtures.py")],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"⚠ Enrichment completed with warnings:\n{result.stderr}")
    except Exception as e:
        print(f"⚠ Could not run enrichment script: {e}")
        print("You can manually run: python scripts/enrich_fixtures.py")


if __name__ == "__main__":
    main()
