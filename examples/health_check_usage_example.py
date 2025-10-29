"""
Health Check Usage Examples

This module demonstrates how to use the health check functionality to verify
API connectivity and authentication for all external services.
"""

import asyncio
from tools.health_check import (
    check_api_health,
    check_all_apis,
    check_all_apis_async,
    startup_health_check,
    print_health_report,
    get_overall_health_status,
    HealthStatus
)


def example_check_single_api():
    """Example: Check health of a single API."""
    print("=" * 60)
    print("Example 1: Check Single API Health")
    print("=" * 60)
    
    # Check Clockify
    print("\nChecking Clockify...")
    result = check_api_health('clockify')
    print(f"Status: {result.status}")
    print(f"Response Time: {result.response_time:.2f}s")
    print(f"Message: {result.message}")
    
    if result.details:
        print(f"Details: {result.details}")
    
    # Check You.com
    print("\nChecking You.com...")
    result = check_api_health('youcom')
    print(f"Status: {result.status}")
    print(f"Response Time: {result.response_time:.2f}s")
    print(f"Message: {result.message}")


def example_check_all_apis():
    """Example: Check health of all APIs."""
    print("\n" + "=" * 60)
    print("Example 2: Check All APIs")
    print("=" * 60)
    
    # Check all APIs in parallel
    results = check_all_apis(parallel=True)
    
    # Print formatted report
    print_health_report(results)
    
    # Get overall status
    overall = get_overall_health_status(results)
    print(f"\nOverall Health: {overall}")
    
    # Check individual results
    for api_name, result in results.items():
        if result.status != HealthStatus.HEALTHY:
            print(f"\n⚠ {api_name} Issue:")
            print(f"  Status: {result.status}")
            print(f"  Message: {result.message}")
            if result.error:
                print(f"  Error: {result.error}")


def example_check_specific_apis():
    """Example: Check health of specific APIs only."""
    print("\n" + "=" * 60)
    print("Example 3: Check Specific APIs")
    print("=" * 60)
    
    # Check only Clockify and You.com
    apis_to_check = ['clockify', 'youcom']
    print(f"\nChecking: {', '.join(apis_to_check)}")
    
    results = check_all_apis(include_apis=apis_to_check)
    
    for api_name, result in results.items():
        print(f"\n{api_name}:")
        print(f"  Status: {result.status}")
        print(f"  Response Time: {result.response_time * 1000:.0f}ms")
        print(f"  Message: {result.message}")


async def example_async_health_check():
    """Example: Async health check for better performance."""
    print("\n" + "=" * 60)
    print("Example 4: Async Health Check")
    print("=" * 60)
    
    print("\nRunning async health checks...")
    
    # Run checks asynchronously
    results = await check_all_apis_async(parallel=True)
    
    print(f"\nCompleted {len(results)} health checks")
    
    for api_name, result in results.items():
        symbol = "✓" if result.status == HealthStatus.HEALTHY else "✗"
        print(f"{symbol} {api_name}: {result.status} ({result.response_time * 1000:.0f}ms)")


def example_startup_check():
    """Example: Startup health check for application initialization."""
    print("\n" + "=" * 60)
    print("Example 5: Startup Health Check")
    print("=" * 60)
    
    print("\nPerforming startup health check...")
    
    # Check required APIs on startup
    required_apis = ['clockify', 'youcom', 'glm']
    
    try:
        all_healthy = startup_health_check(
            required_apis=required_apis,
            fail_on_error=False  # Don't fail, just warn
        )
        
        if all_healthy:
            print("\n✓ All required APIs are healthy. Starting application...")
        else:
            print("\n⚠ Some APIs are not healthy. Application may have limited functionality.")
    
    except RuntimeError as e:
        print(f"\n✗ Startup failed: {e}")


def example_custom_timeout():
    """Example: Health check with custom timeout."""
    print("\n" + "=" * 60)
    print("Example 6: Custom Timeout")
    print("=" * 60)
    
    # Check with shorter timeout for faster failure detection
    print("\nChecking with 5 second timeout...")
    result = check_api_health('youcom', timeout=5.0)
    
    print(f"Status: {result.status}")
    print(f"Response Time: {result.response_time:.2f}s")
    print(f"Message: {result.message}")


def example_result_to_dict():
    """Example: Convert health check results to dictionary."""
    print("\n" + "=" * 60)
    print("Example 7: Export Results as Dictionary")
    print("=" * 60)
    
    # Check APIs
    results = check_all_apis()
    
    # Convert to dictionary format (useful for JSON serialization)
    results_dict = {
        api_name: result.to_dict()
        for api_name, result in results.items()
    }
    
    print("\nResults as dictionary:")
    import json
    print(json.dumps(results_dict, indent=2, default=str))


def example_conditional_startup():
    """Example: Conditional startup based on health check."""
    print("\n" + "=" * 60)
    print("Example 8: Conditional Startup")
    print("=" * 60)
    
    print("\nChecking critical APIs...")
    
    # Check critical APIs
    critical_apis = ['clockify', 'youcom']
    results = check_all_apis(include_apis=critical_apis)
    
    # Determine if we can start
    critical_healthy = all(
        result.status == HealthStatus.HEALTHY
        for result in results.values()
    )
    
    if critical_healthy:
        print("\n✓ All critical APIs are healthy")
        print("Starting application in full mode...")
    else:
        print("\n⚠ Some critical APIs are down")
        print("Starting application in limited mode...")
        
        # Show which APIs are down
        for api_name, result in results.items():
            if result.status != HealthStatus.HEALTHY:
                print(f"  - {api_name}: {result.message}")


def example_monitoring_loop():
    """Example: Continuous health monitoring."""
    print("\n" + "=" * 60)
    print("Example 9: Continuous Monitoring")
    print("=" * 60)
    
    import time
    
    print("\nMonitoring API health (3 iterations)...")
    
    for i in range(3):
        print(f"\n--- Check #{i+1} ---")
        
        results = check_all_apis()
        overall = get_overall_health_status(results)
        
        print(f"Overall Status: {overall}")
        
        # Show any issues
        issues = [
            (name, result)
            for name, result in results.items()
            if result.status != HealthStatus.HEALTHY
        ]
        
        if issues:
            print("Issues detected:")
            for name, result in issues:
                print(f"  - {name}: {result.message}")
        else:
            print("All systems operational")
        
        if i < 2:  # Don't sleep after last iteration
            time.sleep(2)


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("API Health Check Examples")
    print("=" * 60)
    
    try:
        # Synchronous examples
        example_check_single_api()
        example_check_all_apis()
        example_check_specific_apis()
        example_startup_check()
        example_custom_timeout()
        example_result_to_dict()
        example_conditional_startup()
        example_monitoring_loop()
        
        # Async example
        print("\n" + "=" * 60)
        print("Running Async Example")
        print("=" * 60)
        asyncio.run(example_async_health_check())
        
        print("\n" + "=" * 60)
        print("All Examples Completed")
        print("=" * 60)
    
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
