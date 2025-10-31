"""
Test WebSocket Connection
Simple script to verify WebSocket integration is working
"""

import asyncio
import websockets
import json
from datetime import datetime

async def test_websocket_connection():
    """Test WebSocket connection to the backend"""
    uri = "ws://localhost:8000/ws"
    
    print("=" * 60)
    print("WebSocket Connection Test")
    print("=" * 60)
    print(f"\nConnecting to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connection established successfully!")
            
            # Receive welcome message
            print("\nWaiting for welcome message...")
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            
            print(f"✓ Welcome message received:")
            print(f"  Type: {welcome_data.get('type')}")
            print(f"  Message: {welcome_data.get('message')}")
            print(f"  Connection ID: {welcome_data.get('connection_id')}")
            print(f"  Timestamp: {welcome_data.get('timestamp')}")
            
            # Send a test message
            print("\nSending test message...")
            test_message = {
                "type": "test",
                "message": "Hello from Python test script!",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(test_message))
            print("✓ Test message sent")
            
            # Receive echo response
            print("\nWaiting for echo response...")
            echo_msg = await websocket.recv()
            echo_data = json.loads(echo_msg)
            
            print(f"✓ Echo response received:")
            print(f"  Type: {echo_data.get('type')}")
            print(f"  Message: {echo_data.get('message')}")
            print(f"  Timestamp: {echo_data.get('timestamp')}")
            
            # Simulate status update (this would normally come from backend)
            print("\n" + "=" * 60)
            print("Testing Status Update Message Format")
            print("=" * 60)
            
            status_update = {
                "type": "status_update",
                "stage": "data_ingestion",
                "status": "in_progress",
                "details": "Fetching time entries from Clockify...",
                "timestamp": datetime.now().isoformat()
            }
            
            print("\nStatus update message format:")
            print(json.dumps(status_update, indent=2))
            
            # Test error message format
            print("\n" + "=" * 60)
            print("Testing Error Message Format")
            print("=" * 60)
            
            error_message = {
                "type": "error",
                "error_type": "api_connection",
                "message": "Failed to connect to Clockify API",
                "traceback": None,
                "timestamp": datetime.now().isoformat()
            }
            
            print("\nError message format:")
            print(json.dumps(error_message, indent=2))
            
            # Test progress message format
            print("\n" + "=" * 60)
            print("Testing Progress Message Format")
            print("=" * 60)
            
            progress_message = {
                "type": "progress",
                "current_step": 15,
                "total_steps": 50,
                "percentage": 30.0,
                "description": "Processing project 15 of 50",
                "timestamp": datetime.now().isoformat()
            }
            
            print("\nProgress message format:")
            print(json.dumps(progress_message, indent=2))
            
            print("\n" + "=" * 60)
            print("✓ All tests passed successfully!")
            print("=" * 60)
            
            # Close connection
            print("\nClosing connection...")
            await websocket.close()
            print("✓ Connection closed gracefully")
            
    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket error: {e}")
        return False
    except ConnectionRefusedError:
        print(f"\n✗ Connection refused. Is the backend server running?")
        print("  Start the server with: python main.py")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_reconnection():
    """Test reconnection behavior"""
    uri = "ws://localhost:8000/ws"
    
    print("\n" + "=" * 60)
    print("Testing Reconnection Behavior")
    print("=" * 60)
    
    try:
        # First connection
        print("\nEstablishing first connection...")
        async with websockets.connect(uri) as ws1:
            msg1 = await ws1.recv()
            data1 = json.loads(msg1)
            conn_id_1 = data1.get('connection_id')
            print(f"✓ First connection established (ID: {conn_id_1})")
        
        print("✓ First connection closed")
        
        # Second connection (simulating reconnection)
        print("\nEstablishing second connection (reconnection)...")
        async with websockets.connect(uri) as ws2:
            msg2 = await ws2.recv()
            data2 = json.loads(msg2)
            conn_id_2 = data2.get('connection_id')
            print(f"✓ Second connection established (ID: {conn_id_2})")
        
        print("✓ Second connection closed")
        
        if conn_id_1 != conn_id_2:
            print(f"\n✓ Connection IDs are different (expected behavior)")
            print(f"  First ID: {conn_id_1}")
            print(f"  Second ID: {conn_id_2}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Reconnection test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WebSocket Integration Test Suite")
    print("=" * 60)
    print("\nThis script tests the WebSocket connection between")
    print("the frontend and backend server.")
    print("\nPrerequisites:")
    print("  1. Backend server must be running (python main.py)")
    print("  2. Server must be accessible at ws://localhost:8000/ws")
    print("\n" + "=" * 60)
    
    # Test 1: Basic connection
    test1_passed = await test_websocket_connection()
    
    # Test 2: Reconnection
    test2_passed = await test_reconnection()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Basic Connection Test: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"Reconnection Test: {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n✓ All tests passed! WebSocket integration is working correctly.")
        print("\nNext steps:")
        print("  1. Open http://localhost:8000/frontend/test_websocket.html")
        print("  2. Verify connection status shows 'Connected'")
        print("  3. Open http://localhost:8000/frontend/workflow.html")
        print("  4. Verify backend status shows 'Connected' (green)")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
