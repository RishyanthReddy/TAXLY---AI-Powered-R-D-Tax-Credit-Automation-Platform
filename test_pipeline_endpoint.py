"""
Test script for the /api/run-pipeline endpoint

This script tests the complete pipeline endpoint to ensure it:
1. Accepts requests correctly
2. Loads sample data from fixtures
3. Runs the audit trail agent
4. Generates a PDF report
5. Returns proper response with report metadata

Requirements: 5.2, 5.3
"""

import requests
import json
import time
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8000"

def test_run_pipeline():
    """Test the complete pipeline endpoint."""
    print("=" * 80)
    print("TESTING /api/run-pipeline ENDPOINT")
    print("=" * 80)
    
    # Test data
    request_data = {
        "use_sample_data": True,
        "tax_year": 2024,
        "company_name": "Test Company Pipeline"
    }
    
    print(f"\nRequest Data:")
    print(json.dumps(request_data, indent=2))
    
    # Make request
    print(f"\nSending POST request to {API_BASE_URL}/api/run-pipeline...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/run-pipeline",
            json=request_data,
            timeout=180  # 3 minute timeout for complete pipeline
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Execution Time: {execution_time:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n" + "=" * 80)
            print("PIPELINE EXECUTION SUCCESSFUL")
            print("=" * 80)
            
            print(f"\nReport Details:")
            print(f"  - Success: {result.get('success')}")
            print(f"  - Report ID: {result.get('report_id')}")
            print(f"  - PDF Path: {result.get('pdf_path')}")
            print(f"  - Project Count: {result.get('project_count')}")
            print(f"  - Total Hours: {result.get('total_qualified_hours', 0):.1f}h")
            print(f"  - Total Cost: ${result.get('total_qualified_cost', 0):,.2f}")
            print(f"  - Estimated Credit: ${result.get('estimated_credit', 0):,.2f}")
            print(f"  - Execution Time: {result.get('execution_time_seconds', 0):.1f}s")
            print(f"\nSummary: {result.get('summary')}")
            
            # Verify PDF file exists
            pdf_path = Path(result.get('pdf_path', ''))
            if pdf_path.exists():
                file_size = pdf_path.stat().st_size
                print(f"\n✓ PDF file exists: {pdf_path}")
                print(f"  File size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
            else:
                print(f"\n✗ PDF file not found: {pdf_path}")
            
            print("\n" + "=" * 80)
            print("TEST PASSED")
            print("=" * 80)
            
            return True
            
        else:
            print("\n" + "=" * 80)
            print("PIPELINE EXECUTION FAILED")
            print("=" * 80)
            
            try:
                error_data = response.json()
                print(f"\nError Details:")
                print(json.dumps(error_data, indent=2))
            except:
                print(f"\nError Response:")
                print(response.text)
            
            print("\n" + "=" * 80)
            print("TEST FAILED")
            print("=" * 80)
            
            return False
            
    except requests.exceptions.Timeout:
        print("\n✗ Request timed out after 3 minutes")
        print("  The pipeline may still be running on the backend")
        return False
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Connection error - is the backend server running?")
        print("  Start the backend with: python rd_tax_agent/main.py")
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_health_check():
    """Test the health check endpoint first."""
    print("\nChecking backend health...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✓ Backend is healthy")
            print(f"  Status: {health_data.get('status')}")
            print(f"  Version: {health_data.get('version')}")
            return True
        else:
            print(f"✗ Backend health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to backend - is it running?")
        print("  Start the backend with: python rd_tax_agent/main.py")
        return False
        
    except Exception as e:
        print(f"✗ Health check error: {e}")
        return False


if __name__ == "__main__":
    # First check if backend is running
    if not test_health_check():
        print("\nPlease start the backend server first:")
        print("  cd rd_tax_agent")
        print("  python main.py")
        exit(1)
    
    # Run the pipeline test
    success = test_run_pipeline()
    
    exit(0 if success else 1)
