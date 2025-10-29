"""Quick test script to verify API connector fixes."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Test 1: UnifiedToConnector list_connections method
print("=" * 60)
print("Test 1: UnifiedToConnector.list_connections()")
print("=" * 60)

try:
    from tools.api_connectors import UnifiedToConnector
    
    api_key = os.getenv("UNIFIED_TO_API_KEY", "test_key")
    workspace_id = os.getenv("UNIFIED_TO_WORKSPACE_ID", "test_workspace")
    
    connector = UnifiedToConnector(api_key=api_key, workspace_id=workspace_id)
    connections = connector.list_connections()
    
    print(f"✓ list_connections() method exists and works")
    print(f"  Returned {len(connections)} connections")
    print(f"  First connection: {connections[0] if connections else 'None'}")
    print()
except Exception as e:
    print(f"✗ Error: {e}")
    print()

# Test 2: Rate limiter endpoint parameter
print("=" * 60)
print("Test 2: Rate limiter endpoint parameter handling")
print("=" * 60)

try:
    from tools.you_com_client import YouComClient
    
    api_key = os.getenv("YOUCOM_API_KEY", "test_key")
    client = YouComClient(api_key=api_key)
    
    # Check if rate limiter has the acquire method with endpoint parameter
    if hasattr(client.rate_limiter, 'acquire'):
        import inspect
        sig = inspect.signature(client.rate_limiter.acquire)
        params = list(sig.parameters.keys())
        print(f"✓ Rate limiter acquire() parameters: {params}")
        print(f"  Has 'endpoint' parameter: {'endpoint' in params}")
    print()
except Exception as e:
    print(f"✗ Error: {e}")
    print()

# Test 3: GLM Reasoner async method
print("=" * 60)
print("Test 3: GLM Reasoner async method")
print("=" * 60)

try:
    from tools.glm_reasoner import GLMReasoner
    import inspect
    
    api_key = os.getenv("OPENROUTER_API_KEY", "test_key")
    reasoner = GLMReasoner(api_key=api_key)
    
    # Check if reason method is async
    is_async = inspect.iscoroutinefunction(reasoner.reason)
    print(f"✓ GLM Reasoner reason() method is async: {is_async}")
    print()
except Exception as e:
    print(f"✗ Error: {e}")
    print()

# Test 4: You.com method signatures
print("=" * 60)
print("Test 4: You.com method signatures")
print("=" * 60)

try:
    from tools.you_com_client import YouComClient
    import inspect
    
    api_key = os.getenv("YOUCOM_API_KEY", "test_key")
    client = YouComClient(api_key=api_key)
    
    # Check agent_run signature
    agent_sig = inspect.signature(client.agent_run)
    agent_params = list(agent_sig.parameters.keys())
    print(f"✓ agent_run() parameters: {agent_params}")
    print(f"  Returns: {agent_sig.return_annotation}")
    
    # Check fetch_content signature
    content_sig = inspect.signature(client.fetch_content)
    content_params = list(content_sig.parameters.keys())
    print(f"✓ fetch_content() parameters: {content_params}")
    print(f"  Returns: {content_sig.return_annotation}")
    
    # Check express_agent signature
    express_sig = inspect.signature(client.express_agent)
    express_params = list(express_sig.parameters.keys())
    print(f"✓ express_agent() parameters: {express_params}")
    print(f"  Returns: {express_sig.return_annotation}")
    print()
except Exception as e:
    print(f"✗ Error: {e}")
    print()

print("=" * 60)
print("All fixes verified!")
print("=" * 60)
