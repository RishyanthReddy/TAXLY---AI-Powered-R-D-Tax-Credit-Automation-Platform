"""
API Monitor Usage Examples

This script demonstrates how to use the APIMonitor class to track
API calls, monitor performance, and analyze usage patterns.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path

from tools.api_monitor import APIMonitor, get_global_monitor


def example_basic_usage():
    """Example: Basic API monitoring."""
    print("=" * 60)
    print("Example 1: Basic API Monitoring")
    print("=" * 60)
    
    # Create monitor
    monitor = APIMonitor()
    
    # Simulate some API calls
    print("\nSimulating API calls...")
    
    # Successful Clockify call
    monitor.record_api_call(
        api_name='Clockify',
        endpoint='/time-entries',
        response_time=1.5,
        success=True,
        status_code=200
    )
    
    # Successful You.com call
    monitor.record_api_call(
        api_name='You.com',
        endpoint='search',
        response_time=2.3,
        success=True,
        status_code=200
    )
    
    # Failed call with rate limit
    monitor.record_api_call(
        api_name='You.com',
        endpoint='agent',
        response_time=0.5,
        success=False,
        status_code=429,
        error_type='RateLimitError',
        error_message='Rate limit exceeded'
    )
    
    # Cached call
    monitor.record_api_call(
        api_name='You.com',
        endpoint='search',
        response_time=0.1,
        success=True,
        status_code=200,
        cached=True
    )
    
    # Get statistics
    print("\nOverall Statistics:")
    stats = monitor.get_all_statistics()
    print(f"Total calls: {stats['total_calls']}")
    print(f"Success rate: {100 - stats['overall_error_rate']:.1f}%")
    print(f"Cache hit rate: {stats['overall_cache_hit_rate']:.1f}%")
    print(f"Average response time: {stats['average_response_time']:.2f}s")
    
    print("\n" + "=" * 60 + "\n")


def example_per_api_statistics():
    """Example: Get statistics for specific APIs."""
    print("=" * 60)
    print("Example 2: Per-API Statistics")
    print("=" * 60)
    
    monitor = APIMonitor()
    
    # Simulate multiple calls to different APIs
    print("\nSimulating API calls to multiple services...")
    
    # Clockify calls
    for i in range(5):
        monitor.record_api_call(
            api_name='Clockify',
            endpoint='/time-entries',
            response_time=1.0 + i * 0.2,
            success=True,
            status_code=200
        )
    
    # You.com calls
    for i in range(3):
        monitor.record_api_call(
            api_name='You.com',
            endpoint='agent',
            response_time=2.0 + i * 0.5,
            success=True,
            status_code=200
        )
    
    # OpenRouter calls
    for i in range(4):
        monitor.record_api_call(
            api_name='OpenRouter',
            endpoint='/chat/completions',
            response_time=3.0 + i * 0.3,
            success=True,
            status_code=200
        )
    
    # Get per-API statistics
    print("\nClockify Statistics:")
    clockify_stats = monitor.get_api_statistics('Clockify')
    print(f"  Total calls: {clockify_stats['total_calls']}")
    print(f"  Avg response time: {clockify_stats['average_response_time']:.2f}s")
    
    print("\nYou.com Statistics:")
    youcom_stats = monitor.get_api_statistics('You.com')
    print(f"  Total calls: {youcom_stats['total_calls']}")
    print(f"  Avg response time: {youcom_stats['average_response_time']:.2f}s")
    
    print("\nOpenRouter Statistics:")
    openrouter_stats = monitor.get_api_statistics('OpenRouter')
    print(f"  Total calls: {openrouter_stats['total_calls']}")
    print(f"  Avg response time: {openrouter_stats['average_response_time']:.2f}s")
    
    print("\n" + "=" * 60 + "\n")


def example_error_tracking():
    """Example: Track and analyze errors."""
    print("=" * 60)
    print("Example 3: Error Tracking")
    print("=" * 60)
    
    monitor = APIMonitor(
        failure_threshold=2,  # Alert after 2 consecutive failures
        enable_alerts=True
    )
    
    print("\nSimulating API calls with errors...")
    
    # Successful call
    monitor.record_api_call(
        api_name='You.com',
        endpoint='agent',
        response_time=2.0,
        success=True,
        status_code=200
    )
    
    # First failure
    monitor.record_api_call(
        api_name='You.com',
        endpoint='agent',
        response_time=0.5,
        success=False,
        status_code=500,
        error_type='ServerError',
        error_message='Internal server error'
    )
    
    # Second consecutive failure (should trigger alert)
    monitor.record_api_call(
        api_name='You.com',
        endpoint='agent',
        response_time=0.5,
        success=False,
        status_code=503,
        error_type='ServiceUnavailable',
        error_message='Service temporarily unavailable'
    )
    
    # Get recent errors
    print("\nRecent Errors:")
    errors = monitor.get_recent_errors('You.com', 'agent', limit=5)
    for error in errors:
        print(f"  {error['timestamp']}: {error['error_type']} - {error['error_message']}")
    
    # Get endpoint statistics
    endpoint_stats = monitor.get_endpoint_statistics('You.com', 'agent')
    print(f"\nEndpoint Statistics:")
    print(f"  Total calls: {endpoint_stats['total_calls']}")
    print(f"  Error rate: {endpoint_stats['error_rate']:.1f}%")
    print(f"  Consecutive failures: {endpoint_stats['consecutive_failures']}")
    
    print("\n" + "=" * 60 + "\n")


def example_cost_tracking():
    """Example: Track API usage for cost estimation."""
    print("=" * 60)
    print("Example 4: Cost Tracking")
    print("=" * 60)
    
    monitor = APIMonitor()
    
    print("\nSimulating API calls with caching...")
    
    # You.com calls (some cached)
    for i in range(10):
        cached = i % 3 == 0  # Every 3rd call is cached
        monitor.record_api_call(
            api_name='You.com',
            endpoint='search',
            response_time=0.1 if cached else 2.0,
            success=True,
            status_code=200,
            cached=cached
        )
    
    # OpenRouter calls (no caching)
    for i in range(15):
        monitor.record_api_call(
            api_name='OpenRouter',
            endpoint='/chat/completions',
            response_time=3.0,
            success=True,
            status_code=200
        )
    
    # Get cost estimate
    print("\nCost Estimate:")
    cost_info = monitor.get_cost_estimate()
    
    for api_name, info in cost_info.items():
        if api_name == 'summary':
            continue
        print(f"\n{api_name}:")
        print(f"  Total calls: {info['total_calls']}")
        print(f"  Cached calls: {info['cached_calls']}")
        print(f"  Billable calls: {info['billable_calls']}")
    
    print(f"\nTotal billable calls across all APIs: {cost_info['summary']['total_billable_calls']}")
    
    print("\n" + "=" * 60 + "\n")


def example_export_statistics():
    """Example: Export statistics to file."""
    print("=" * 60)
    print("Example 5: Export Statistics")
    print("=" * 60)
    
    monitor = APIMonitor()
    
    # Simulate some API calls
    print("\nSimulating API calls...")
    for i in range(20):
        api_name = 'Clockify' if i % 2 == 0 else 'You.com'
        endpoint = '/time-entries' if api_name == 'Clockify' else 'search'
        
        monitor.record_api_call(
            api_name=api_name,
            endpoint=endpoint,
            response_time=1.0 + i * 0.1,
            success=i % 5 != 0,  # Every 5th call fails
            status_code=200 if i % 5 != 0 else 500
        )
    
    # Export to file
    output_path = Path('logs/api_monitor_stats.json')
    monitor.export_statistics(output_path)
    print(f"\nStatistics exported to: {output_path}")
    
    # Log statistics to console
    print("\nLogging statistics to console:")
    monitor.log_statistics()
    
    print("\n" + "=" * 60 + "\n")


def example_global_monitor():
    """Example: Use global monitor instance."""
    print("=" * 60)
    print("Example 6: Global Monitor Instance")
    print("=" * 60)
    
    # Get global monitor
    monitor = get_global_monitor()
    
    print("\nUsing global monitor instance...")
    
    # Record some calls
    monitor.record_api_call(
        api_name='Clockify',
        endpoint='/workspaces',
        response_time=1.2,
        success=True,
        status_code=200
    )
    
    monitor.record_api_call(
        api_name='You.com',
        endpoint='agent',
        response_time=2.5,
        success=True,
        status_code=200
    )
    
    # Get statistics from anywhere in the application
    stats = get_global_monitor().get_all_statistics()
    print(f"\nGlobal monitor tracked {stats['total_calls']} calls")
    
    print("\n" + "=" * 60 + "\n")


def example_time_range_analysis():
    """Example: Analyze metrics by time range."""
    print("=" * 60)
    print("Example 7: Time Range Analysis")
    print("=" * 60)
    
    monitor = APIMonitor()
    
    print("\nSimulating API calls over time...")
    
    # Record calls with small delays
    for i in range(5):
        monitor.record_api_call(
            api_name='You.com',
            endpoint='search',
            response_time=1.5,
            success=True,
            status_code=200
        )
        time.sleep(0.1)  # Small delay between calls
    
    # Get metrics from last minute
    now = datetime.now()
    one_minute_ago = now - timedelta(minutes=1)
    
    recent_metrics = monitor.get_metrics_by_time_range(
        start_time=one_minute_ago,
        end_time=now,
        api_name='You.com'
    )
    
    print(f"\nYou.com calls in last minute: {len(recent_metrics)}")
    print(f"Average response time: {sum(m.response_time for m in recent_metrics) / len(recent_metrics):.2f}s")
    
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # Run all examples
    example_basic_usage()
    example_per_api_statistics()
    example_error_tracking()
    example_cost_tracking()
    example_export_statistics()
    example_global_monitor()
    example_time_range_analysis()
    
    print("All examples completed!")
