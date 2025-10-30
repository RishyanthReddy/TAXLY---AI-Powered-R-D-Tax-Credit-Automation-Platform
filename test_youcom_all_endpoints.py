"""
Comprehensive test script for all You.com API endpoints.

This script tests:
1. Search API - GET https://api.ydc-index.io/v1/search
2. Contents API - POST https://api.ydc-index.io/v1/contents
3. Express Agent API - POST https://api.you.com/v1/agents/runs

Tests verify that tasks 129 and 130 work correctly with You.com endpoints.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tools.you_com_client import YouComClient
from utils.config import get_config


def test_search_api():
    """Test You.com Search API."""
    print("\n" + "=" * 70)
    print("TEST 1: You.com Search API")
    print("=" * 70)
    
    try:
        config = get_config()
        client = YouComClient(api_key=config.youcom_api_key)
        
        print("\n1. Testing search for IRS R&D guidance...")
        results = client.search(
            query="IRS R&D tax credit software development",
            count=3,
            freshness="year"
        )
        
        print(f"   ✓ Search successful! Retrieved {len(results)} results")
        
        if results:
            print("\n2. Sample result:")
            result = results[0]
            print(f"   - Title: {result.get('title', 'N/A')[:80]}")
            print(f"   - URL: {result.get('url', 'N/A')[:80]}")
            print(f"   - Type: {result.get('source_type', 'N/A')}")
            if result.get('snippets'):
                print(f"   - Snippet: {result['snippets'][0][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Search API failed: {str(e)}")
        return False


def test_contents_api():
    """Test You.com Contents API."""
    print("\n" + "=" * 70)
    print("TEST 2: You.com Contents API")
    print("=" * 70)
    
    try:
        config = get_config()
        client = YouComClient(api_key=config.youcom_api_key)
        
        # Test with a simple, reliable URL
        test_url = "https://example.com"
        
        print(f"\n1. Fetching content from: {test_url}")
        print("   (This may take a few seconds...)")
        
        result = client.fetch_content(
            url=test_url,
            format="markdown"
        )
        
        print("   ✓ Content fetched successfully!")
        print(f"\n2. Response details:")
        print(f"   - URL: {result.get('url', 'N/A')}")
        print(f"   - Title: {result.get('title', 'N/A')}")
        print(f"   - Format: {result.get('format', 'N/A')}")
        print(f"   - Word count: {result.get('word_count', 0)}")
        
        # Show content preview
        content = result.get('content', '')
        if content:
            preview = content[:150]
            if len(content) > 150:
                preview += "..."
            print(f"\n3. Content preview:")
            print(f"   {preview}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Contents API failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_express_agent_api():
    """Test You.com Express Agent API."""
    print("\n" + "=" * 70)
    print("TEST 3: You.com Express Agent API")
    print("=" * 70)
    
    try:
        config = get_config()
        client = YouComClient(api_key=config.youcom_api_key)
        
        print("\n1. Running Express Agent with R&D qualification query...")
        print("   (This may take 10-30 seconds...)")
        
        # Simple test prompt for R&D qualification
        test_prompt = """
Based on IRS guidelines for R&D tax credits, analyze this project:

Project: API Performance Optimization
Description: Developed a new caching algorithm to reduce API response times by 50%.
Activities: Algorithm research, performance testing, systematic experimentation with different caching strategies.
Hours: 120 hours
Cost: $15,000

Question: What percentage of this project qualifies for R&D tax credits?
Provide a qualification percentage (0-100) and confidence score (0-1).
"""
        
        response = client.agent_run(
            prompt=test_prompt,
            agent_mode="express",
            stream=False
        )
        
        print("   ✓ Express Agent call successful!")
        
        # Extract the answer from response
        if 'output' in response and len(response['output']) > 0:
            output_item = response['output'][0]
            answer_text = output_item.get('text', '')
            
            print(f"\n2. Agent response preview:")
            preview = answer_text[:300]
            if len(answer_text) > 300:
                preview += "..."
            print(f"   {preview}")
            
            print(f"\n3. Response metadata:")
            print(f"   - Type: {output_item.get('type', 'N/A')}")
            print(f"   - Agent: {output_item.get('agent', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Express Agent API failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all You.com API tests."""
    print("\n" + "=" * 70)
    print("YOU.COM API COMPREHENSIVE TEST SUITE")
    print("Testing all endpoints for Tasks 129 & 130")
    print("=" * 70)
    
    results = {
        "Search API": test_search_api(),
        "Contents API": test_contents_api(),
        "Express Agent API": test_express_agent_api()
    }
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<50} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - You.com integration is working correctly!")
        print("  Tasks 129 & 130 are ready to use.")
    else:
        print("✗ SOME TESTS FAILED - Please review the errors above.")
        print("  Check API key and endpoint configurations.")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
