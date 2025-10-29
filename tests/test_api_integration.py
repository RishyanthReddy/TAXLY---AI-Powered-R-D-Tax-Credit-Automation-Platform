"""
Integration tests for all API connectors.

These tests make REAL API calls to verify end-to-end functionality.
They require valid API keys configured in the .env file.

To run these tests:
1. Set all required API keys in your .env file:
   - CLOCKIFY_API_KEY
   - CLOCKIFY_WORKSPACE_ID
   - UNIFIED_TO_API_KEY
   - UNIFIED_TO_WORKSPACE_ID
   - YOUCOM_API_KEY
   - OPENROUTER_API_KEY
2. Run: pytest tests/test_api_integration.py -v -s

Note: These tests consume API quota and may take longer to execute.
"""

import pytest
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from tools.api_connectors import ClockifyConnector, UnifiedToConnector
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.exceptions import APIConnectionError


# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Check which API keys are available
CLOCKIFY_API_KEY = os.getenv("CLOCKIFY_API_KEY")
CLOCKIFY_WORKSPACE_ID = os.getenv("CLOCKIFY_WORKSPACE_ID")
UNIFIED_TO_API_KEY = os.getenv("UNIFIED_TO_API_KEY")
UNIFIED_TO_WORKSPACE_ID = os.getenv("UNIFIED_TO_WORKSPACE_ID")
YOUCOM_API_KEY = os.getenv("YOUCOM_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Determine which tests to skip
SKIP_CLOCKIFY = not CLOCKIFY_API_KEY or CLOCKIFY_API_KEY == "your_clockify_api_key_here"
SKIP_UNIFIED_TO = not UNIFIED_TO_API_KEY or UNIFIED_TO_API_KEY == "your_unified_to_api_key_here"
SKIP_YOUCOM = not YOUCOM_API_KEY or YOUCOM_API_KEY == "your_youcom_api_key_here"
SKIP_OPENROUTER = not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here"


class TestClockifyConnectorIntegration:
    """Integration tests for Clockify API connector."""
    
    @pytest.mark.skipif(SKIP_CLOCKIFY, reason="Clockify API key not configured")
    def test_clockify_authentication(self):
        """Test Clockify authentication with real API."""
        print("\n=== Testing Clockify Authentication ===")
        
        connector = ClockifyConnector(
            api_key=CLOCKIFY_API_KEY,
            workspace_id=CLOCKIFY_WORKSPACE_ID
        )
        
        try:
            user_info = connector.test_authentication()
            
            print(f"✓ Authentication successful")
            print(f"  User ID: {user_info.get('id', 'N/A')}")
            print(f"  Email: {user_info.get('email', 'N/A')}")
            print(f"  Name: {user_info.get('name', 'N/A')}")
            
            assert user_info is not None
            assert 'id' in user_info
            assert 'email' in user_info
            
        except APIConnectionError as e:
            pytest.fail(f"Clockify authentication failed: {e}")
    
    @pytest.mark.skipif(SKIP_CLOCKIFY, reason="Clockify API key not configured")
    def test_clockify_fetch_time_entries(self):
        """Test fetching time entries from Clockify."""
        print("\n=== Testing Clockify Time Entry Fetching ===")
        
        connector = ClockifyConnector(
            api_key=CLOCKIFY_API_KEY,
            workspace_id=CLOCKIFY_WORKSPACE_ID
        )
        
        # Fetch entries from last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        try:
            entries = connector.fetch_time_entries(
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"✓ Fetched {len(entries)} time entries")
            
            if entries:
                first_entry = entries[0]
                print(f"  Sample entry:")
                print(f"    ID: {first_entry.get('id', 'N/A')}")
                print(f"    User: {first_entry.get('userId', 'N/A')}")
                print(f"    Project: {first_entry.get('projectName', 'N/A')}")
                print(f"    Duration: {first_entry.get('duration', 'N/A')}")
            else:
                print("  No entries found in the date range")
            
            assert isinstance(entries, list)
            
    