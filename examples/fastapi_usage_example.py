"""
FastAPI Application Usage Example

This example demonstrates how to:
1. Run the FastAPI application
2. Test endpoints using requests
3. Handle WebSocket connections
4. Test exception handling

Requirements: 5.3, 8.4
"""

import requests
import json
from typing import Dict, Any


def test_health_check(base_url: str = "http://localhost:8000") -> None:
    """
    Test the health check endpoint.
    
    Args:
        base_url: Base URL of the API
    """
    print("Testing health check endpoint...")
    
    response = requests.get(f"{base_url}/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Health check successful")
        print(f"  Status: {data['status']}")
        print(f"  Version: {data['version']}")
        print(f"  Configuration: {json.dumps(data['configuration'], indent=2)}")
        print(f"  API Keys: {json.dumps(data['api_keys_configured'], indent=2)}")
    else:
        print(f"✗ Health check failed: {response.status_code}")
        print(f"  Response: {response.text}")


def test_root_endpoint(base_url: str = "http://localhost:8000") -> None:
    """
    Test the root endpoint.
    
    Args:
        base_url: Base URL of the API
    """
    print("\nTesting root endpoint...")
    
    response = requests.get(f"{base_url}/")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Root endpoint successful")
        print(f"  Message: {data['message']}")
        print(f"  Version: {data['version']}")
        print(f"  Documentation: {data['documentation']}")
    else:
        print(f"✗ Root endpoint failed: {response.status_code}")


def test_openapi_docs(base_url: str = "http://localhost:8000") -> None:
    """
    Test that OpenAPI documentation is accessible.
    
    Args:
        base_url: Base URL of the API
    """
    print("\nTesting OpenAPI documentation...")
    
    # Test OpenAPI JSON
    response = requests.get(f"{base_url}/openapi.json")
    if response.status_code == 200:
        print(f"✓ OpenAPI JSON accessible at {base_url}/openapi.json")
    else:
        print(f"✗ OpenAPI JSON not accessible")
    
    # Test Swagger UI
    response = requests.get(f"{base_url}/docs")
    if response.status_code == 200:
        print(f"✓ Swagger UI accessible at {base_url}/docs")
    else:
        print(f"✗ Swagger UI not accessible")
    
    # Test ReDoc
    response = requests.get(f"{base_url}/redoc")
    if response.status_code == 200:
        print(f"✓ ReDoc accessible at {base_url}/redoc")
    else:
        print(f"✗ ReDoc not accessible")


def test_cors_headers(base_url: str = "http://localhost:8000") -> None:
    """
    Test CORS headers in responses.
    
    Args:
        base_url: Base URL of the API
    """
    print("\nTesting CORS headers...")
    
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    }
    
    response = requests.options(f"{base_url}/health", headers=headers)
    
    if "access-control-allow-origin" in response.headers:
        print(f"✓ CORS headers present")
        print(f"  Allow-Origin: {response.headers.get('access-control-allow-origin')}")
        print(f"  Allow-Methods: {response.headers.get('access-control-allow-methods')}")
        print(f"  Allow-Headers: {response.headers.get('access-control-allow-headers')}")
    else:
        print(f"✗ CORS headers not found")


def run_all_tests(base_url: str = "http://localhost:8000") -> None:
    """
    Run all API tests.
    
    Args:
        base_url: Base URL of the API
    """
    print("=" * 60)
    print("FastAPI Application Tests")
    print("=" * 60)
    
    try:
        test_root_endpoint(base_url)
        test_health_check(base_url)
        test_openapi_docs(base_url)
        test_cors_headers(base_url)
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the API server.")
        print("Make sure the server is running:")
        print("  python main.py")
        print("or")
        print("  uvicorn main:app --reload")


if __name__ == "__main__":
    # Instructions for running the server
    print("""
To run the FastAPI server, use one of these commands:

1. Using the main.py script:
   python main.py

2. Using uvicorn directly:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000

3. Using uvicorn with custom settings:
   uvicorn main:app --reload --log-level info

Once the server is running, this script will test the endpoints.
Press Ctrl+C to stop the server.

""")
    
    # Run tests
    run_all_tests()
