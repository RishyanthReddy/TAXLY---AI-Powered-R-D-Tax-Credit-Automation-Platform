"""
Usage example for You.com API client.

This example demonstrates how to:
1. Initialize the You.com client
2. Test authentication
3. Search for IRS guidance using the Search API
4. Parse and display search results
5. Get client statistics
6. Use the client as a context manager
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.you_com_client import YouComClient
from utils.config import get_config


def main():
    """Demonstrate You.com client usage."""
    
    # Load configuration
    config = get_config()
    
    print("=" * 60)
    print("You.com API Client Usage Example")
    print("=" * 60)
    
    # Example 1: Basic initialization
    print("\n1. Initializing You.com client...")
    client = YouComClient(api_key=config.youcom_api_key)
    print(f"   ✓ Client initialized: {client.api_name}")
    print(f"   ✓ Base URL: {client._get_base_url()}")
    print(f"   ✓ Timeout: {client.timeout}s")
    print(f"   ✓ Max retries: {client.max_retries}")
    
    # Example 2: Test authentication
    print("\n2. Testing authentication...")
    is_authenticated = client.test_authentication()
    if is_authenticated:
        print("   ✓ Authentication successful!")
    else:
        print("   ✗ Authentication failed!")
        return
    
    # Example 3: Search for IRS R&D guidance
    print("\n3. Searching for IRS R&D tax credit guidance...")
    try:
        results = client.search(
            query="IRS R&D tax credit software development 2025",
            count=5,
            freshness="year"
        )
        
        print(f"   ✓ Found {len(results)} results")
        
        # Display results
        for i, result in enumerate(results, 1):
            print(f"\n   Result {i}:")
            print(f"   Title: {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Type: {result['source_type']}")
            print(f"   Description: {result['description'][:100]}...")
            
            if result.get('snippets'):
                print(f"   Snippets: {len(result['snippets'])} found")
                for snippet in result['snippets'][:2]:  # Show first 2 snippets
                    print(f"     - {snippet[:80]}...")
            
            if result.get('page_age'):
                print(f"   Published: {result['page_age']}")
    
    except Exception as e:
        print(f"   ✗ Search failed: {e}")
    
    # Example 4: Search with specific site filter
    print("\n4. Searching IRS.gov specifically...")
    try:
        results = client.search(
            query='site:irs.gov "research credit" "qualified research"',
            count=3
        )
        
        print(f"   ✓ Found {len(results)} results from IRS.gov")
        
        for i, result in enumerate(results, 1):
            print(f"\n   Result {i}:")
            print(f"   Title: {result['title']}")
            print(f"   URL: {result['url']}")
    
    except Exception as e:
        print(f"   ✗ Search failed: {e}")
    
    # Example 5: Get statistics
    print("\n5. Getting client statistics...")
    stats = client.get_statistics()
    print(f"   ✓ API Name: {stats['api_name']}")
    print(f"   ✓ Request Count: {stats['request_count']}")
    print(f"   ✓ Error Count: {stats['error_count']}")
    print(f"   ✓ Error Rate: {stats['error_rate']:.2%}")
    print(f"   ✓ Rate Limit: {stats['rate_limit']}")
    
    # Example 6: Fetch R&D narrative template using Contents API
    print("\n6. Fetching R&D narrative template...")
    try:
        # Example URL - replace with actual template URL
        template_url = "https://example.com/rd-narrative-template"
        
        result = client.fetch_content(
            url=template_url,
            format="markdown"
        )
        
        print(f"   ✓ Content fetched successfully")
        print(f"   ✓ URL: {result['url']}")
        print(f"   ✓ Format: {result['format']}")
        print(f"   ✓ Word count: {result['word_count']}")
        
        if 'title' in result:
            print(f"   ✓ Title: {result['title']}")
        
        if 'description' in result:
            print(f"   ✓ Description: {result['description'][:80]}...")
        
        # Show first 200 characters of content
        if result['content']:
            print(f"\n   Content preview:")
            print(f"   {result['content'][:200]}...")
    
    except Exception as e:
        print(f"   ✗ Content fetch failed: {e}")
    
    # Example 7: Using as context manager
    print("\n7. Using client as context manager...")
    with YouComClient(api_key=config.youcom_api_key) as ctx_client:
        print(f"   ✓ Client created in context")
        print(f"   ✓ API Name: {ctx_client.api_name}")
        
        # Quick search in context
        try:
            results = ctx_client.search(query="IRS Form 6765", count=2)
            print(f"   ✓ Found {len(results)} results for Form 6765")
        except Exception as e:
            print(f"   ✗ Search failed: {e}")
    
    print("   ✓ Client automatically closed on exit")
    
    # Clean up
    client.close()
    print("\n✓ Client closed successfully")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
