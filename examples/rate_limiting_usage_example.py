"""
Rate Limiting Usage Examples

This module demonstrates how to use the rate limiting features in API connectors,
including automatic backoff when approaching rate limits.

Examples:
1. Basic rate limiting with default settings
2. Custom backoff threshold configuration
3. Monitoring rate limiter statistics
4. Handling rate limit warnings
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from tools.api_connectors import RateLimiter, BaseAPIConnector
from utils.logger import get_tool_logger


logger = get_tool_logger("rate_limiting_examples")


def example_basic_rate_limiting():
    """
    Example 1: Basic rate limiting with default settings.
    
    Demonstrates:
    - Creating a rate limiter with default backoff threshold (20%)
    - Making requests that trigger automatic backoff
    - Viewing rate limiter statistics
    """
    print("\n" + "="*60)
    print("Example 1: Basic Rate Limiting")
    print("="*60)
    
    # Create rate limiter: 10 requests per second
    limiter = RateLimiter(requests_per_second=10.0)
    
    print(f"Rate limiter initialized:")
    print(f"  - Rate: {limiter.requests_per_second} req/s")
    print(f"  - Burst size: {limiter.burst_size}")
    print(f"  - Backoff threshold: {limiter.backoff_threshold:.0%}")
    print(f"  - Initial tokens: {limiter.tokens}")
    
    # Make several requests
    print("\nMaking 15 requests...")
    for i in range(15):
        wait_time = limiter.acquire()
        if wait_time > 0:
            print(f"  Request {i+1}: waited {wait_time:.3f}s")
        else:
            print(f"  Request {i+1}: no wait")
    
    # View statistics
    stats = limiter.get_statistics()
    print("\nRate limiter statistics:")
    print(f"  - Total requests: {stats['total_requests']}")
    print(f"  - Total wait time: {stats['total_wait_time']:.3f}s")
    print(f"  - Backoff count: {stats['backoff_count']}")
    print(f"  - Current tokens: {stats['current_tokens']:.2f}")
    print(f"  - Token percentage: {stats['token_percentage']:.1%}")


def example_custom_backoff_threshold():
    """
    Example 2: Custom backoff threshold configuration.
    
    Demonstrates:
    - Setting a custom backoff threshold (30% instead of default 20%)
    - Observing earlier backoff activation
    - Comparing behavior with different thresholds
    """
    print("\n" + "="*60)
    print("Example 2: Custom Backoff Threshold")
    print("="*60)
    
    # Create two rate limiters with different backoff thresholds
    limiter_aggressive = RateLimiter(
        requests_per_second=10.0,
        backoff_threshold=0.5,  # Backoff at 50% tokens
        enable_backoff_warnings=False
    )
    
    limiter_conservative = RateLimiter(
        requests_per_second=10.0,
        backoff_threshold=0.1,  # Backoff at 10% tokens
        enable_backoff_warnings=False
    )
    
    print("Testing aggressive backoff (50% threshold)...")
    for i in range(10):
        limiter_aggressive.acquire()
    
    stats_aggressive = limiter_aggressive.get_statistics()
    print(f"  - Backoff count: {stats_aggressive['backoff_count']}")
    print(f"  - Total wait time: {stats_aggressive['total_wait_time']:.3f}s")
    
    print("\nTesting conservative backoff (10% threshold)...")
    for i in range(10):
        limiter_conservative.acquire()
    
    stats_conservative = limiter_conservative.get_statistics()
    print(f"  - Backoff count: {stats_conservative['backoff_count']}")
    print(f"  - Total wait time: {stats_conservative['total_wait_time']:.3f}s")
    
    print("\nComparison:")
    print(f"  Aggressive backoff triggered {stats_aggressive['backoff_count']} times")
    print(f"  Conservative backoff triggered {stats_conservative['backoff_count']} times")


def example_monitoring_statistics():
    """
    Example 3: Monitoring rate limiter statistics.
    
    Demonstrates:
    - Tracking request patterns over time
    - Identifying when rate limits are being approached
    - Using statistics for performance optimization
    """
    print("\n" + "="*60)
    print("Example 3: Monitoring Rate Limiter Statistics")
    print("="*60)
    
    limiter = RateLimiter(
        requests_per_second=5.0,
        burst_size=10,
        backoff_threshold=0.3,
        enable_backoff_warnings=False
    )
    
    print("Simulating burst traffic pattern...")
    
    # Burst phase: rapid requests
    print("\nPhase 1: Burst (10 rapid requests)")
    burst_start = time.time()
    for i in range(10):
        limiter.acquire()
    burst_duration = time.time() - burst_start
    
    stats_after_burst = limiter.get_statistics()
    print(f"  - Duration: {burst_duration:.3f}s")
    print(f"  - Backoff count: {stats_after_burst['backoff_count']}")
    print(f"  - Tokens remaining: {stats_after_burst['current_tokens']:.2f}")
    
    # Recovery phase: wait for tokens to refill
    print("\nPhase 2: Recovery (waiting 2 seconds)")
    time.sleep(2.0)
    
    # Steady phase: moderate requests
    print("\nPhase 3: Steady (5 requests with spacing)")
    for i in range(5):
        wait_time = limiter.acquire()
        print(f"  Request {i+1}: waited {wait_time:.3f}s")
        time.sleep(0.3)  # Space out requests
    
    # Final statistics
    final_stats = limiter.get_statistics()
    print("\nFinal statistics:")
    print(f"  - Total requests: {final_stats['total_requests']}")
    print(f"  - Total wait time: {final_stats['total_wait_time']:.3f}s")
    print(f"  - Average wait per request: {final_stats['total_wait_time'] / final_stats['total_requests']:.3f}s")
    print(f"  - Backoff count: {final_stats['backoff_count']}")
    print(f"  - Current tokens: {final_stats['current_tokens']:.2f}")


def example_connector_with_rate_limiting():
    """
    Example 4: Using rate limiting in API connectors.
    
    Demonstrates:
    - Configuring rate limiting in BaseAPIConnector
    - Accessing rate limiter statistics through connector
    - Customizing backoff behavior per API
    """
    print("\n" + "="*60)
    print("Example 4: Rate Limiting in API Connectors")
    print("="*60)
    
    # Note: This is a conceptual example showing how to configure connectors
    # In practice, you would use actual connector classes like ClockifyConnector
    
    print("Clockify Connector Configuration:")
    print("  - Rate limit: 10 req/s")
    print("  - Burst size: 10 (default)")
    print("  - Backoff threshold: 0.2 (20%)")
    print("  - Backoff warnings: Enabled")
    
    print("\nYou.com Agent API Configuration:")
    print("  - Rate limit: 10 req/min (0.167 req/s)")
    print("  - Per-endpoint limits via YouComRateLimiter")
    print("  - Automatic backoff when approaching limits")
    
    print("\nUnified.to Connector Configuration:")
    print("  - Rate limit: 5 req/s (conservative)")
    print("  - Burst size: 5 (default)")
    print("  - Backoff threshold: 0.2 (20%)")
    
    print("\nBest Practices:")
    print("  1. Set rate limits slightly below API provider limits")
    print("  2. Use burst_size for handling traffic spikes")
    print("  3. Monitor backoff_count to identify bottlenecks")
    print("  4. Adjust backoff_threshold based on traffic patterns")
    print("  5. Enable warnings in development, disable in production")


def example_rate_limit_warnings():
    """
    Example 5: Handling rate limit warnings.
    
    Demonstrates:
    - Enabling/disabling backoff warnings
    - Understanding warning messages
    - Using warnings for debugging
    """
    print("\n" + "="*60)
    print("Example 5: Rate Limit Warnings")
    print("="*60)
    
    print("Creating rate limiter with warnings enabled...")
    limiter_with_warnings = RateLimiter(
        requests_per_second=10.0,
        backoff_threshold=0.3,
        enable_backoff_warnings=True  # Enable warnings
    )
    
    print("\nMaking requests that will trigger warnings...")
    print("(Watch for WARNING logs about approaching rate limits)")
    
    # Make enough requests to trigger backoff
    for i in range(12):
        limiter_with_warnings.acquire()
        if i == 7:
            print(f"\n  After {i+1} requests, tokens are low...")
    
    print("\n\nCreating rate limiter with warnings disabled...")
    limiter_without_warnings = RateLimiter(
        requests_per_second=10.0,
        backoff_threshold=0.3,
        enable_backoff_warnings=False  # Disable warnings
    )
    
    print("Making requests (no warnings will be logged)...")
    for i in range(12):
        limiter_without_warnings.acquire()
    
    print("\nNote: Warnings are useful for:")
    print("  - Development and debugging")
    print("  - Identifying rate limit bottlenecks")
    print("  - Tuning backoff thresholds")
    print("  - Understanding traffic patterns")
    print("\nDisable warnings in production to reduce log noise.")


if __name__ == "__main__":
    """Run all examples."""
    print("\n" + "="*60)
    print("RATE LIMITING USAGE EXAMPLES")
    print("="*60)
    
    try:
        example_basic_rate_limiting()
        example_custom_backoff_threshold()
        example_monitoring_statistics()
        example_connector_with_rate_limiting()
        example_rate_limit_warnings()
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        print(f"\nError: {e}")
