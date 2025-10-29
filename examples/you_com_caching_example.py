"""
Example usage of You.com API client caching functionality.

This example demonstrates:
1. Enabling/disabling cache
2. Configuring cache TTLs
3. Using cached search results
4. Using cached content/templates
5. Cache invalidation
6. Cache statistics
"""

import os
import time
from dotenv import load_dotenv

from tools.you_com_client import YouComClient


def main():
    """Demonstrate You.com API caching functionality."""
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("YOUCOM_API_KEY")
    
    if not api_key:
        print("Error: YOUCOM_API_KEY not found in environment variables")
        return
    
    print("=" * 80)
    print("You.com API Client - Caching Example")
    print("=" * 80)
    
    # Example 1: Initialize client with caching enabled (default)
    print("\n1. Initialize client with caching enabled")
    print("-" * 80)
    
    client = YouComClient(
        api_key=api_key,
        enable_cache=True,
        search_cache_ttl=3600,  # 1 hour for search results
        content_cache_ttl=86400  # 24 hours for content/templates
    )
    
    print("✓ Client initialized with caching enabled")
    print(f"  - Search cache TTL: 3600s (1 hour)")
    print(f"  - Content cache TTL: 86400s (24 hours)")
    
    # Example 2: Make a search request (will be cached)
    print("\n2. Make a search request (first call - will be cached)")
    print("-" * 80)
    
    query = "IRS R&D tax credit software development"
    
    start_time = time.time()
    results = client.search(query=query, count=5)
    elapsed_time = time.time() - start_time
    
    print(f"✓ Search completed in {elapsed_time:.2f}s")
    print(f"  - Found {len(results)} results")
    print(f"  - First result: {results[0]['title'][:60]}...")
    
    # Example 3: Make the same search request again (will use cache)
    print("\n3. Make the same search request again (will use cache)")
    print("-" * 80)
    
    start_time = time.time()
    cached_results = client.search(query=query, count=5)
    elapsed_time = time.time() - start_time
    
    print(f"✓ Search completed in {elapsed_time:.2f}s (much faster!)")
    print(f"  - Found {len(cached_results)} results (from cache)")
    print(f"  - Results match: {results == cached_results}")
    
    # Example 4: Fetch content (will be cached)
    print("\n4. Fetch content from URL (first call - will be cached)")
    print("-" * 80)
    
    # Use a sample URL (replace with actual URL in production)
    url = "https://www.irs.gov/businesses/small-businesses-self-employed/research-credit"
    
    try:
        start_time = time.time()
        content = client.fetch_content(url=url, format="markdown")
        elapsed_time = time.time() - start_time
        
        print(f"✓ Content fetched in {elapsed_time:.2f}s")
        print(f"  - Word count: {content['word_count']}")
        print(f"  - Title: {content.get('title', 'N/A')}")
        
        # Example 5: Fetch the same content again (will use cache)
        print("\n5. Fetch the same content again (will use cache)")
        print("-" * 80)
        
        start_time = time.time()
        cached_content = client.fetch_content(url=url, format="markdown")
        elapsed_time = time.time() - start_time
        
        print(f"✓ Content fetched in {elapsed_time:.2f}s (much faster!)")
        print(f"  - Word count: {cached_content['word_count']} (from cache)")
        print(f"  - Content matches: {content == cached_content}")
        
    except Exception as e:
        print(f"⚠ Content fetch failed (this is expected if URL is not accessible): {e}")
        print("  Continuing with other examples...")
    
    # Example 6: Get cache statistics
    print("\n6. Get cache statistics")
    print("-" * 80)
    
    cache_stats = client.get_cache_statistics()
    
    print("✓ Cache statistics:")
    print(f"  - Cache enabled: {cache_stats['enabled']}")
    print(f"  - Search cache size: {cache_stats['search_cache_size']} entries")
    print(f"  - Content cache size: {cache_stats['content_cache_size']} entries")
    print(f"  - Total cache size: {cache_stats['total_cache_size']} entries")
    print(f"  - Search TTL: {cache_stats['search_ttl']}s")
    print(f"  - Content TTL: {cache_stats['content_ttl']}s")
    
    # Example 7: Get full client statistics (includes cache)
    print("\n7. Get full client statistics")
    print("-" * 80)
    
    stats = client.get_statistics()
    
    print("✓ Client statistics:")
    print(f"  - API name: {stats['api_name']}")
    print(f"  - Request count: {stats['request_count']}")
    print(f"  - Error count: {stats['error_count']}")
    print(f"  - Rate limit: {stats['rate_limit']}")
    print(f"  - Cache entries: {stats['cache']['total_cache_size']}")
    
    # Example 8: Clear search cache
    print("\n8. Clear search cache")
    print("-" * 80)
    
    cleared = client.clear_search_cache()
    
    print(f"✓ Cleared {cleared} search cache entries")
    
    # Verify cache is cleared
    cache_stats = client.get_cache_statistics()
    print(f"  - Search cache size after clear: {cache_stats['search_cache_size']}")
    
    # Example 9: Clear all caches
    print("\n9. Clear all caches")
    print("-" * 80)
    
    cleared = client.clear_all_caches()
    
    print(f"✓ Cleared all caches:")
    print(f"  - Search entries cleared: {cleared['search']}")
    print(f"  - Content entries cleared: {cleared['content']}")
    print(f"  - Total entries cleared: {cleared['total']}")
    
    # Example 10: Agent API is NOT cached (always fresh reasoning)
    print("\n10. Agent API is NOT cached (always fresh reasoning)")
    print("-" * 80)
    
    print("✓ Agent API and Express Agent API are NOT cached")
    print("  - Each agent run provides fresh reasoning")
    print("  - This ensures qualification decisions are always current")
    print("  - Only Search and Contents APIs use caching")
    
    # Example 11: Initialize client with caching disabled
    print("\n11. Initialize client with caching disabled")
    print("-" * 80)
    
    client_no_cache = YouComClient(
        api_key=api_key,
        enable_cache=False
    )
    
    print("✓ Client initialized with caching disabled")
    print("  - All requests will hit the API directly")
    print("  - Useful for testing or when fresh data is critical")
    
    cache_stats = client_no_cache.get_cache_statistics()
    print(f"  - Cache enabled: {cache_stats['enabled']}")
    
    print("\n" + "=" * 80)
    print("Caching example completed successfully!")
    print("=" * 80)
    
    print("\nKey Takeaways:")
    print("1. Search API results are cached for 1 hour (configurable)")
    print("2. Content/template fetches are cached for 24 hours (configurable)")
    print("3. Agent API is NOT cached (always fresh reasoning)")
    print("4. Cache can be cleared selectively or entirely")
    print("5. Cache statistics help monitor performance")
    print("6. Caching significantly improves response times for repeated requests")


if __name__ == "__main__":
    main()
