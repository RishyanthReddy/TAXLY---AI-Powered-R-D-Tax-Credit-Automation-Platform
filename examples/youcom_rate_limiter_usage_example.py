"""
Example usage of You.com Rate Limiter.

This example demonstrates how to use the You.com rate limiter with various
configurations and how to monitor rate limiting behavior.
"""

import time
from tools.you_com_client import YouComClient
from tools.youcom_rate_limiter import YouComRateLimiter, RateLimitConfig
from utils.config import get_config


def example_basic_usage():
    """Example: Basic usage with automatic rate limiting."""
    print("=" * 60)
    print("Example 1: Basic Usage with Automatic Rate Limiting")
    print("=" * 60)
    
    config = get_config()
    client = YouComClient(api_key=config.youcom_api_key)
    
    # Make multiple search requests
    # Rate limiting is automatically applied
    print("\nMaking 5 search requests...")
    for i in range(5):
        print(f"\nRequest {i+1}:")
        try:
            results = client.search(
                query=f"IRS R&D tax credit example {i+1}",
                count=3
            )
            print(f"  Retrieved {len(results)} results")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Get rate limiter statistics
    print("\n" + "-" * 60)
    print("Rate Limiter Statistics:")
    print("-" * 60)
    client.log_rate_limiter_statistics()


def example_custom_rate_limits():
    """Example: Custom rate limits per endpoint."""
    print("\n" + "=" * 60)
    print("Example 2: Custom Rate Limits")
    print("=" * 60)
    
    config = get_config()
    
    # Configure custom rate limits
    custom_limits = {
        # More restrictive for agent API (5 requests per minute)
        'agent': RateLimitConfig(requests_per_minute=5, burst_size=5),
        
        # More permissive for search API (20 requests per minute)
        'search': RateLimitConfig(requests_per_minute=20, burst_size=30),
    }
    
    client = YouComClient(
        api_key=config.youcom_api_key,
        custom_rate_limits=custom_limits
    )
    
    print("\nCustom rate limits configured:")
    print("  - Agent API: 5 requests/min (burst: 5)")
    print("  - Search API: 20 requests/min (burst: 30)")
    
    # Make multiple search requests (should be fast with higher limit)
    print("\nMaking 10 search requests with higher rate limit...")
    start_time = time.time()
    for i in range(10):
        try:
            results = client.search(
                query=f"test query {i+1}",
                count=1
            )
            print(f"  Request {i+1}: {len(results)} results")
        except Exception as e:
            print(f"  Request {i+1}: Error - {e}")
    
    elapsed = time.time() - start_time
    print(f"\nCompleted 10 requests in {elapsed:.2f}s")
    
    # Get statistics
    stats = client.get_rate_limiter_statistics()
    search_stats = stats['search']
    print(f"\nSearch API Statistics:")
    print(f"  Total requests: {search_stats['total_requests']}")
    print(f"  Total wait time: {search_stats['total_wait_time']:.2f}s")
    print(f"  Average wait: {search_stats['average_wait_time']:.3f}s")


def example_direct_rate_limiter():
    """Example: Using rate limiter directly."""
    print("\n" + "=" * 60)
    print("Example 3: Direct Rate Limiter Usage")
    print("=" * 60)
    
    # Create rate limiter
    limiter = YouComRateLimiter()
    
    print("\nMaking 15 requests to search endpoint...")
    print("(Rate limit: 10 requests/min, burst: 10)")
    
    for i in range(15):
        # Check available tokens before acquiring
        available = limiter.get_available_tokens('search')
        wait_estimate = limiter.get_wait_time('search')
        
        print(f"\nRequest {i+1}:")
        print(f"  Available tokens: {available:.1f}")
        print(f"  Estimated wait: {wait_estimate:.2f}s")
        
        # Acquire token (will wait if necessary)
        wait_time = limiter.acquire('search')
        
        if wait_time > 0:
            print(f"  Waited: {wait_time:.2f}s")
        else:
            print(f"  No wait needed")
        
        # Simulate API call
        time.sleep(0.1)
    
    # Get statistics
    print("\n" + "-" * 60)
    print("Final Statistics:")
    print("-" * 60)
    limiter.log_statistics()


def example_non_blocking_acquisition():
    """Example: Non-blocking token acquisition."""
    print("\n" + "=" * 60)
    print("Example 4: Non-Blocking Token Acquisition")
    print("=" * 60)
    
    limiter = YouComRateLimiter()
    
    print("\nAttempting to make 15 requests without blocking...")
    
    successful = 0
    rate_limited = 0
    
    for i in range(15):
        # Try to acquire without blocking
        if limiter.try_acquire('agent'):
            print(f"Request {i+1}: Success")
            successful += 1
            # Simulate API call
            time.sleep(0.1)
        else:
            print(f"Request {i+1}: Rate limited (skipped)")
            rate_limited += 1
    
    print(f"\nResults:")
    print(f"  Successful: {successful}")
    print(f"  Rate limited: {rate_limited}")
    
    # Wait a bit and try again
    print("\nWaiting 10 seconds for tokens to refill...")
    time.sleep(10)
    
    available = limiter.get_available_tokens('agent')
    print(f"Available tokens after wait: {available:.1f}")


def example_monitoring_and_statistics():
    """Example: Monitoring rate limiter behavior."""
    print("\n" + "=" * 60)
    print("Example 5: Monitoring and Statistics")
    print("=" * 60)
    
    config = get_config()
    client = YouComClient(api_key=config.youcom_api_key)
    
    # Make requests to different endpoints
    print("\nMaking requests to different endpoints...")
    
    try:
        # Search API
        print("\n1. Search API:")
        results = client.search(query="test", count=1)
        print(f"   Retrieved {len(results)} results")
        
        # News API
        print("\n2. News API:")
        news = client.news(query="test", count=1)
        print(f"   Retrieved {len(news)} news items")
        
        # Contents API
        print("\n3. Contents API:")
        content = client.fetch_content(
            url="https://example.com",
            format="markdown"
        )
        print(f"   Retrieved {content.get('word_count', 0)} words")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Get comprehensive statistics
    print("\n" + "-" * 60)
    print("Comprehensive Statistics:")
    print("-" * 60)
    
    stats = client.get_statistics()
    
    print(f"\nClient Statistics:")
    print(f"  API Name: {stats['api_name']}")
    print(f"  Total Requests: {stats['request_count']}")
    print(f"  Error Count: {stats['error_count']}")
    print(f"  Error Rate: {stats['error_rate']:.2%}")
    
    print(f"\nCache Statistics:")
    cache_stats = stats['cache']
    print(f"  Enabled: {cache_stats['enabled']}")
    print(f"  Search Cache Size: {cache_stats['search_cache_size']}")
    print(f"  Content Cache Size: {cache_stats['content_cache_size']}")
    
    print(f"\nRate Limiter Statistics:")
    rate_stats = stats['rate_limiter']
    for endpoint, endpoint_stats in rate_stats.items():
        print(f"\n  {endpoint}:")
        print(f"    Requests: {endpoint_stats['total_requests']}")
        print(f"    Total Wait: {endpoint_stats['total_wait_time']:.2f}s")
        print(f"    Avg Wait: {endpoint_stats['average_wait_time']:.3f}s")
        print(f"    Max Wait: {endpoint_stats['max_wait_time']:.2f}s")
        print(f"    Backoffs: {endpoint_stats['backoff_count']}")
        print(f"    Available: {endpoint_stats['available_tokens']:.1f} tokens")


def example_reset_rate_limiter():
    """Example: Resetting rate limiter."""
    print("\n" + "=" * 60)
    print("Example 6: Resetting Rate Limiter")
    print("=" * 60)
    
    limiter = YouComRateLimiter()
    
    # Use up some tokens
    print("\nUsing up tokens...")
    for i in range(10):
        limiter.acquire('search')
    
    available = limiter.get_available_tokens('search')
    print(f"Available tokens after 10 requests: {available:.1f}")
    
    # Reset specific endpoint
    print("\nResetting search endpoint...")
    limiter.reset('search')
    
    available = limiter.get_available_tokens('search')
    print(f"Available tokens after reset: {available:.1f}")
    
    # Use up tokens on multiple endpoints
    print("\nUsing tokens on multiple endpoints...")
    for i in range(5):
        limiter.acquire('search')
        limiter.acquire('agent')
        limiter.acquire('contents')
    
    print("\nAvailable tokens before reset:")
    for endpoint in ['search', 'agent', 'contents']:
        available = limiter.get_available_tokens(endpoint)
        print(f"  {endpoint}: {available:.1f}")
    
    # Reset all endpoints
    print("\nResetting all endpoints...")
    limiter.reset()
    
    print("\nAvailable tokens after reset:")
    for endpoint in ['search', 'agent', 'contents']:
        available = limiter.get_available_tokens(endpoint)
        print(f"  {endpoint}: {available:.1f}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("You.com Rate Limiter Usage Examples")
    print("=" * 60)
    
    try:
        # Run examples
        example_basic_usage()
        example_custom_rate_limits()
        example_direct_rate_limiter()
        example_non_blocking_acquisition()
        example_monitoring_and_statistics()
        example_reset_rate_limiter()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
