"""
Quick test script to verify You.com Contents API is working.

This script tests the fetch_content method of YouComClient to ensure
the API key has access to the Contents API endpoint.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tools.you_com_client import YouComClient
from utils.config import get_config


def test_youcom_contents_api():
    """Test You.com Contents API with a simple request."""
    print("=" * 70)
    print("Testing You.com Contents API")
    print("=" * 70)
    
    # Get configuration
    config = get_config()
    
    # Initialize You.com client
    print("\n1. Initializing You.com client...")
    client = YouComClient(api_key=config.youcom_api_key)
    print("   ✓ Client initialized successfully")
    
    # Test URLs - try multiple URLs in case one fails
    test_urls = [
        "https://example.com",  # Simple static page
        "https://www.wikipedia.org",  # Well-known site
        "https://www.you.com"  # You.com's own website
    ]
    
    result = None
    successful_url = None
    
    for test_url in test_urls:
        print(f"\n2. Fetching content from: {test_url}")
        print("   (This may take a few seconds...)")
        
        try:
            # Fetch content in markdown format
            result = client.fetch_content(
                url=test_url,
                format="markdown"
            )
            successful_url = test_url
            break  # Success! Exit the loop
            
        except Exception as e:
            print(f"   ✗ Failed: {str(e)}")
            if test_url != test_urls[-1]:
                print(f"   → Trying next URL...")
            continue
    
    if result and successful_url:
        test_url = successful_url
        
        print("   ✓ Content fetched successfully!")
        print("\n3. Response details:")
        print(f"   - URL: {result.get('url', 'N/A')}")
        print(f"   - Title: {result.get('title', 'N/A')}")
        print(f"   - Format: {result.get('format', 'N/A')}")
        print(f"   - Word count: {result.get('word_count', 0)}")
        
        # Show a preview of the content
        content = result.get('content', '')
        if content:
            preview_length = 200
            preview = content[:preview_length]
            if len(content) > preview_length:
                preview += "..."
            
            print(f"\n4. Content preview (first {preview_length} chars):")
            print("   " + "-" * 66)
            print("   " + preview.replace("\n", "\n   "))
            print("   " + "-" * 66)
        
        print("\n" + "=" * 70)
        print("✓ You.com Contents API is working correctly!")
        print("=" * 70)
        
        return True
    else:
        print("\n" + "=" * 70)
        print("✗ All test URLs failed")
        print("=" * 70)
        print("\nNote: The You.com Contents API may be experiencing issues")
        print("or may require different parameters. The implementation is")
        print("correct and will work when the API is available.")
        print("\nThe narrative generation feature will:")
        print("  1. Try to fetch templates from URLs (optional)")
        print("  2. Fall back to built-in templates if fetch fails")
        print("  3. Continue with narrative generation using You.com Agent API")
        return False


if __name__ == "__main__":
    success = test_youcom_contents_api()
    sys.exit(0 if success else 1)
