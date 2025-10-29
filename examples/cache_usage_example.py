"""
Usage examples for the cache module.

This file demonstrates how to use the SimpleCache class and @cached decorator
for API response caching and performance optimization.
"""

import time
from tools.cache import SimpleCache, cached, time_entry_cache, payroll_cache


def example_basic_cache_usage():
    """Example: Basic cache operations."""
    print("\n=== Basic Cache Usage ===")
    
    # Create a cache with 1 hour default TTL
    cache = SimpleCache(default_ttl=3600)
    
    # Store a value
    cache.set("user_123", {"name": "John Doe", "email": "john@example.com"})
    print("Stored user data in cache")
    
    # Retrieve the value
    user_data = cache.get("user_123")
    print(f"Retrieved from cache: {user_data}")
    
    # Check cache size
    print(f"Cache size: {cache.size()} entries")
    
    # Delete a specific entry
    cache.delete("user_123")
    print("Deleted user_123 from cache")
    
    # Clear all entries
    cache.clear()
    print("Cleared all cache entries")


def example_ttl_expiration():
    """Example: TTL-based expiration."""
    print("\n=== TTL Expiration ===")
    
    # Create cache with short TTL for demonstration
    cache = SimpleCache(default_ttl=2)  # 2 seconds
    
    # Store a value
    cache.set("temp_data", "This will expire soon")
    print("Stored temp_data with 2 second TTL")
    
    # Retrieve immediately - should work
    result = cache.get("temp_data")
    print(f"Retrieved immediately: {result}")
    
    # Wait for expiration
    print("Waiting 3 seconds for expiration...")
    time.sleep(3)
    
    # Try to retrieve - should be None
    result = cache.get("temp_data")
    print(f"After expiration: {result}")


def example_custom_ttl():
    """Example: Custom TTL per entry."""
    print("\n=== Custom TTL ===")
    
    cache = SimpleCache(default_ttl=3600)
    
    # Store with default TTL (1 hour)
    cache.set("long_lived", "This lasts 1 hour")
    
    # Store with custom short TTL (5 seconds)
    cache.set("short_lived", "This expires in 5 seconds", ttl=5)
    
    print("Stored two entries with different TTLs")
    print(f"Cache size: {cache.size()}")
    
    # Wait 6 seconds
    print("Waiting 6 seconds...")
    time.sleep(6)
    
    # Check what's still in cache
    print(f"long_lived: {cache.get('long_lived')}")
    print(f"short_lived: {cache.get('short_lived')}")


def example_cache_key_generation():
    """Example: Generating cache keys from parameters."""
    print("\n=== Cache Key Generation ===")
    
    cache = SimpleCache()
    
    # Generate keys from parameters
    key1 = cache.generate_key("api_call", endpoint="users", user_id="123")
    key2 = cache.generate_key("api_call", endpoint="users", user_id="123")
    key3 = cache.generate_key("api_call", endpoint="users", user_id="456")
    
    print(f"Key 1: {key1}")
    print(f"Key 2: {key2}")
    print(f"Key 3: {key3}")
    print(f"Key 1 == Key 2: {key1 == key2}")
    print(f"Key 1 == Key 3: {key1 == key3}")
    
    # Use generated keys for caching
    cache.set(key1, {"user_id": "123", "name": "John"})
    cache.set(key3, {"user_id": "456", "name": "Jane"})
    
    # Retrieve using generated keys
    user1 = cache.get(key1)
    user3 = cache.get(key3)
    print(f"User 123: {user1}")
    print(f"User 456: {user3}")


def example_api_response_caching():
    """Example: Caching API responses."""
    print("\n=== API Response Caching ===")
    
    cache = SimpleCache(default_ttl=3600)
    call_count = [0]
    
    def fetch_time_entries(workspace_id: str, date: str):
        """Simulate API call with caching."""
        # Generate cache key
        cache_key = cache.generate_key(
            "clockify_time_entries",
            workspace_id=workspace_id,
            date=date
        )
        
        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            print(f"  Cache HIT for {workspace_id}/{date}")
            return cached_result
        
        # Cache miss - make API call
        print(f"  Cache MISS for {workspace_id}/{date} - fetching from API...")
        call_count[0] += 1
        time.sleep(0.5)  # Simulate API latency
        
        result = {
            "workspace_id": workspace_id,
            "date": date,
            "entries": [
                {"employee": "John", "hours": 8},
                {"employee": "Jane", "hours": 7}
            ]
        }
        
        # Store in cache
        cache.set(cache_key, result)
        
        return result
    
    # First call - cache miss
    print("First call:")
    result1 = fetch_time_entries("ws_123", "2024-01-01")
    print(f"  Result: {len(result1['entries'])} entries")
    
    # Second call with same params - cache hit
    print("\nSecond call (same params):")
    result2 = fetch_time_entries("ws_123", "2024-01-01")
    print(f"  Result: {len(result2['entries'])} entries")
    
    # Third call with different params - cache miss
    print("\nThird call (different params):")
    result3 = fetch_time_entries("ws_123", "2024-01-02")
    print(f"  Result: {len(result3['entries'])} entries")
    
    print(f"\nTotal API calls made: {call_count[0]}")


def example_cached_decorator():
    """Example: Using @cached decorator."""
    print("\n=== @cached Decorator ===")
    
    cache = SimpleCache(default_ttl=3600)
    call_count = [0]
    
    @cached(cache, ttl=1800)  # 30 minute TTL
    def expensive_calculation(x: int, y: int) -> int:
        """Simulate expensive calculation."""
        print(f"  Executing expensive_calculation({x}, {y})...")
        call_count[0] += 1
        time.sleep(0.5)  # Simulate processing time
        return x * y + x + y
    
    # First call - executes function
    print("First call:")
    result1 = expensive_calculation(10, 20)
    print(f"  Result: {result1}")
    
    # Second call with same args - uses cache
    print("\nSecond call (same args):")
    result2 = expensive_calculation(10, 20)
    print(f"  Result: {result2}")
    
    # Third call with different args - executes function
    print("\nThird call (different args):")
    result3 = expensive_calculation(5, 15)
    print(f"  Result: {result3}")
    
    print(f"\nFunction executed {call_count[0]} times")


def example_cached_with_key_params():
    """Example: Using @cached with specific key parameters."""
    print("\n=== @cached with key_params ===")
    
    cache = SimpleCache()
    call_count = [0]
    
    @cached(cache, key_params=['user_id', 'date'])
    def fetch_user_activity(user_id: str, date: str, include_details: bool = False):
        """Fetch user activity, cache by user_id and date only."""
        print(f"  Fetching activity for {user_id} on {date} (details={include_details})...")
        call_count[0] += 1
        time.sleep(0.3)
        return {
            "user_id": user_id,
            "date": date,
            "activities": ["login", "edit", "logout"],
            "details": "Full details" if include_details else "Summary"
        }
    
    # First call
    print("First call:")
    result1 = fetch_user_activity("user123", "2024-01-01", include_details=True)
    print(f"  Details: {result1['details']}")
    
    # Second call with different include_details - uses cache
    # because include_details is not in key_params
    print("\nSecond call (different include_details):")
    result2 = fetch_user_activity("user123", "2024-01-01", include_details=False)
    print(f"  Details: {result2['details']}")  # Still "Full details" from cache
    
    # Third call with different date - executes function
    print("\nThird call (different date):")
    result3 = fetch_user_activity("user123", "2024-01-02", include_details=False)
    print(f"  Details: {result3['details']}")
    
    print(f"\nFunction executed {call_count[0]} times")


def example_cache_statistics():
    """Example: Getting cache statistics."""
    print("\n=== Cache Statistics ===")
    
    cache = SimpleCache(default_ttl=10)
    
    # Add some entries
    cache.set("key1", "value1", ttl=2)  # Will expire soon
    cache.set("key2", "value2", ttl=10)
    cache.set("key3", "value3", ttl=10)
    
    # Get initial stats
    stats = cache.get_stats()
    print(f"Initial stats:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Valid entries: {stats['valid_entries']}")
    print(f"  Expired entries: {stats['expired_entries']}")
    
    # Wait for one to expire
    print("\nWaiting 3 seconds...")
    time.sleep(3)
    
    # Get updated stats
    stats = cache.get_stats()
    print(f"After expiration:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Valid entries: {stats['valid_entries']}")
    print(f"  Expired entries: {stats['expired_entries']}")
    
    # Cleanup expired entries
    removed = cache.cleanup_expired()
    print(f"\nCleaned up {removed} expired entries")
    print(f"Cache size after cleanup: {cache.size()}")


def example_global_cache_instances():
    """Example: Using global cache instances."""
    print("\n=== Global Cache Instances ===")
    
    # Use global time_entry_cache
    time_entry_cache.set("entry_123", {
        "employee": "John",
        "hours": 8,
        "project": "Project Alpha"
    })
    
    # Use global payroll_cache
    payroll_cache.set("payroll_456", {
        "employee": "John",
        "salary": 75000,
        "hourly_rate": 36.06
    })
    
    print(f"Time entry cache size: {time_entry_cache.size()}")
    print(f"Payroll cache size: {payroll_cache.size()}")
    
    # Retrieve from caches
    entry = time_entry_cache.get("entry_123")
    payroll = payroll_cache.get("payroll_456")
    
    print(f"Time entry: {entry}")
    print(f"Payroll: {payroll}")
    
    # Clear specific cache
    time_entry_cache.clear()
    print(f"\nAfter clearing time_entry_cache:")
    print(f"Time entry cache size: {time_entry_cache.size()}")
    print(f"Payroll cache size: {payroll_cache.size()}")


def example_cache_invalidation():
    """Example: Cache invalidation patterns."""
    print("\n=== Cache Invalidation ===")
    
    cache = SimpleCache()
    
    # Cache some user data
    user_id = "user_123"
    cache_key = cache.generate_key("user", user_id=user_id)
    
    cache.set(cache_key, {"name": "John", "age": 30})
    print(f"Cached user data: {cache.get(cache_key)}")
    
    # Simulate user update - invalidate cache
    print("\nUser data updated - invalidating cache...")
    cache.delete(cache_key)
    
    # Re-cache with updated data
    cache.set(cache_key, {"name": "John", "age": 31})
    print(f"Updated cache: {cache.get(cache_key)}")
    
    # Alternative: Clear all user-related caches
    print("\nClearing all caches...")
    cache.clear()
    print(f"Cache size: {cache.size()}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Cache Module Usage Examples")
    print("=" * 60)
    
    example_basic_cache_usage()
    example_ttl_expiration()
    example_custom_ttl()
    example_cache_key_generation()
    example_api_response_caching()
    example_cached_decorator()
    example_cached_with_key_params()
    example_cache_statistics()
    example_global_cache_instances()
    example_cache_invalidation()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
