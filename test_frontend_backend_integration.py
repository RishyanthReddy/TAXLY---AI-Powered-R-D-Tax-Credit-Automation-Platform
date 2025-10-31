"""
Automated Frontend-Backend Integration Test

This script tests the complete integration between frontend and backend
by simulating what happens when a user clicks the "Generate Report" button.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
import requests
import websockets

# Test configuration
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/ws"
TIMEOUT = 180  # 3 minutes max for pipeline


class IntegrationTestResult:
    def __init__(self):
        self.tests_passed = []
        self.tests_failed = []
        self.websocket_messages = []
        self.pipeline_result = None
        self.pdf_downloaded = False
        self.start_time = None
        self.end_time = None
        
    def add_pass(self, test_name):
        self.tests_passed.append(test_name)
        print(f"✓ {test_name}")
        
    def add_fail(self, test_name, error):
        self.tests_failed.append((test_name, str(error)))
        print(f"✗ {test_name}: {error}")
        
    def print_summary(self):
        print("\n" + "=" * 80)
        print("FRONTEND-BACKEND INTEGRATION TEST SUMMARY")
        print("=" * 80)
        
        total_duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        print(f"\nTotal Test Duration: {total_duration:.2f} seconds")
        
        print(f"\nTests Passed: {len(self.tests_passed)}")
        for test in self.tests_passed:
            print(f"  ✓ {test}")
            
        if self.tests_failed:
            print(f"\nTests Failed: {len(self.tests_failed)}")
            for test, error in self.tests_failed:
                print(f"  ✗ {test}: {error}")
        
        if self.websocket_messages:
            print(f"\nWebSocket Messages Received: {len(self.websocket_messages)}")
            for msg in self.websocket_messages[:5]:  # Show first 5
                print(f"  - {msg.get('stage', 'unknown')}: {msg.get('status', 'unknown')}")
            if len(self.websocket_messages) > 5:
                print(f"  ... and {len(self.websocket_messages) - 5} more")
        
        if self.pipeline_result:
            print("\nPipeline Result:")
            print(f"  Report ID: {self.pipeline_result.get('report_id')}")
            print(f"  Projects: {self.pipeline_result.get('project_count')}")
            print(f"  Total Hours: {self.pipeline_result.get('total_qualified_hours'):.1f}")
            print(f"  Estimated Credit: ${self.pipeline_result.get('estimated_credit'):,.2f}")
            print(f"  Execution Time: {self.pipeline_result.get('execution_time_seconds'):.1f}s")
        
        print("\n" + "=" * 80)
        success_rate = len(self.tests_passed) / (len(self.tests_passed) + len(self.tests_failed)) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        
        if len(self.tests_failed) == 0:
            print("✓✓✓ ALL TESTS PASSED ✓✓✓")
            return True
        else:
            print("✗✗✗ SOME TESTS FAILED ✗✗✗")
            return False


async def test_websocket_connection(result):
    """Test WebSocket connection and message reception"""
    print("\n" + "-" * 80)
    print("TEST 1: WebSocket Connection")
    print("-" * 80)
    
    try:
        async with websockets.connect(WEBSOCKET_URL, timeout=10) as websocket:
            result.add_pass("WebSocket connection established")
            
            # Wait for a message (with timeout)
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(message)
                result.websocket_messages.append(data)
                result.add_pass("WebSocket message received")
            except asyncio.TimeoutError:
                result.add_pass("WebSocket connected (no immediate message)")
                
    except Exception as e:
        result.add_fail("WebSocket connection", e)


def test_backend_health(result):
    """Test backend health endpoint"""
    print("\n" + "-" * 80)
    print("TEST 2: Backend Health Check")
    print("-" * 80)
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        
        if response.status_code == 200:
            result.add_pass("Backend health check")
            
            data = response.json()
            if data.get('status') == 'healthy':
                result.add_pass("Backend status is healthy")
            else:
                result.add_fail("Backend status", f"Status: {data.get('status')}")
                
            # Check API keys
            api_keys = data.get('api_keys_configured', {})
            if api_keys.get('youcom'):
                result.add_pass("You.com API key configured")
            else:
                result.add_fail("You.com API key", "Not configured")
                
            if api_keys.get('openrouter'):
                result.add_pass("OpenRouter API key configured")
            else:
                result.add_fail("OpenRouter API key", "Not configured")
        else:
            result.add_fail("Backend health check", f"Status code: {response.status_code}")
            
    except Exception as e:
        result.add_fail("Backend health check", e)


async def test_pipeline_execution(result):
    """Test complete pipeline execution (simulates frontend button click)"""
    print("\n" + "-" * 80)
    print("TEST 3: Pipeline Execution (Frontend Button Click Simulation)")
    print("-" * 80)
    
    # Start WebSocket listener in background
    websocket_task = asyncio.create_task(listen_to_websocket(result))
    
    # Give WebSocket time to connect
    await asyncio.sleep(1)
    
    try:
        print("Sending POST request to /api/run-pipeline...")
        
        # This simulates what the frontend does when user clicks "Generate Report"
        response = requests.post(
            f"{BACKEND_URL}/api/run-pipeline",
            json={
                "use_sample_data": True,
                "tax_year": 2024,
                "company_name": "Test Company E2E"
            },
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result.add_pass("Pipeline API call successful")
            
            data = response.json()
            result.pipeline_result = data
            
            # Validate response structure
            if 'report_id' in data:
                result.add_pass("Response contains report_id")
            else:
                result.add_fail("Response structure", "Missing report_id")
                
            if 'pdf_path' in data:
                result.add_pass("Response contains pdf_path")
            else:
                result.add_fail("Response structure", "Missing pdf_path")
                
            # Validate metrics
            if data.get('project_count') == 5:
                result.add_pass("Correct project count (5)")
            else:
                result.add_fail("Project count", f"Expected 5, got {data.get('project_count')}")
                
            if 60 < data.get('total_qualified_hours', 0) < 80:
                result.add_pass("Total hours in expected range")
            else:
                result.add_fail("Total hours", f"Got {data.get('total_qualified_hours')}")
                
            if 1000 < data.get('estimated_credit', 0) < 1500:
                result.add_pass("Estimated credit in expected range")
            else:
                result.add_fail("Estimated credit", f"Got {data.get('estimated_credit')}")
                
            if data.get('execution_time_seconds', 0) < TIMEOUT:
                result.add_pass(f"Execution time acceptable ({data.get('execution_time_seconds'):.1f}s)")
            else:
                result.add_fail("Execution time", f"Took {data.get('execution_time_seconds')}s")
                
        else:
            result.add_fail("Pipeline API call", f"Status code: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                pass
                
    except requests.Timeout:
        result.add_fail("Pipeline execution", f"Timeout after {TIMEOUT}s")
    except Exception as e:
        result.add_fail("Pipeline execution", e)
    finally:
        # Cancel WebSocket listener
        websocket_task.cancel()
        try:
            await websocket_task
        except asyncio.CancelledError:
            pass


async def listen_to_websocket(result):
    """Listen to WebSocket messages during pipeline execution"""
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                result.websocket_messages.append(data)
                
                # Print real-time updates
                if data.get('type') == 'status_update':
                    stage = data.get('stage', 'unknown')
                    status = data.get('status', 'unknown')
                    details = data.get('details', '')
                    print(f"  [{stage}] {status}: {details}")
                    
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"WebSocket listener error: {e}")


def test_pdf_download(result):
    """Test PDF download endpoint"""
    print("\n" + "-" * 80)
    print("TEST 4: PDF Download")
    print("-" * 80)
    
    if not result.pipeline_result:
        result.add_fail("PDF download", "No pipeline result available")
        return
        
    report_id = result.pipeline_result.get('report_id')
    if not report_id:
        result.add_fail("PDF download", "No report_id in pipeline result")
        return
        
    try:
        print(f"Downloading report: {report_id}")
        
        response = requests.get(
            f"{BACKEND_URL}/api/download/report/{report_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            result.add_pass("PDF download successful")
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' in content_type.lower():
                result.add_pass("Correct content type (PDF)")
            else:
                result.add_fail("Content type", f"Got: {content_type}")
                
            # Check file size
            file_size = len(response.content)
            if 60000 < file_size < 100000:  # 60-100 KB
                result.add_pass(f"PDF file size acceptable ({file_size/1024:.1f} KB)")
                result.pdf_downloaded = True
            else:
                result.add_fail("PDF file size", f"Got {file_size/1024:.1f} KB")
                
        else:
            result.add_fail("PDF download", f"Status code: {response.status_code}")
            
    except Exception as e:
        result.add_fail("PDF download", e)


async def run_all_tests():
    """Run all integration tests"""
    result = IntegrationTestResult()
    result.start_time = time.time()
    
    print("=" * 80)
    print("FRONTEND-BACKEND INTEGRATION TEST")
    print("=" * 80)
    print("\nThis test simulates a user clicking 'Generate Report' in the frontend")
    print("and verifies the complete integration with the backend.\n")
    
    # Test 1: WebSocket
    await test_websocket_connection(result)
    
    # Test 2: Backend Health
    test_backend_health(result)
    
    # Test 3: Pipeline Execution (main test)
    await test_pipeline_execution(result)
    
    # Test 4: PDF Download
    test_pdf_download(result)
    
    result.end_time = time.time()
    
    # Print summary
    success = result.print_summary()
    
    return 0 if success else 1


def main():
    """Main entry point"""
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
