"""
Unit tests for the cache module.

Tests cover:
- Basic cache operations (get, set, delete, clear)
- TTL expiration behavior
- Cache key generation
- Thread safety
- Cache statistics
- Decorator functionality
"""

import pytest
import time
import threading
from datetime import datetime, timedelta

from tools.cache import SimpleCache, cached, time_entry_cache, payroll_cache


class TestSimpleCache:
    """Test cases for SimpleCache class."""
    
    def test_cache_initialization(self):
        """Test cache initialization with default and custom TTL."""
        # Default TTL
        cache1 = SimpleCache()
        assert cache1.default_ttl == 3600
        assert cache1.size() == 0
        
        # Custom TTL
        cache2 = SimpleCache(default_ttl=1800)
        assert cache2.default_ttl == 1800
        assert cache2.size() == 0
    
    def test_generate_key(self):
        """Test cache key generation from parameters."""
        cache = SimpleCache()
        
        # Same parameters should generate same key
        key1 = cache.generate_key("test", param1="value1", param2="value2")
        key2 = cache.generate_key("test", param1="value1", param2="value2")
        assert key1 == key2
        
        # Different parameter order should generate same key
        key3 = cache.generate_key("test", param2="value2", param1="value1")
        assert key1 == key3
        
        # Different parameters should generate different key
        key4 = cache.generate_key("test", param1="value1", param2="different")
        assert key1 != key4
        
        # Different prefix should generate different key
        key5 = cache.generate_key("other", param1="value1", param2="value2")
        assert key1 != key5
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = SimpleCache()
        
        # Set and get a value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Set and get different types
        cache.set("key2", {"data": "dict"})
        assert cache.get("key2") == {"data": "dict"}
        
        cache.set("key3", [1, 2, 3])
        assert cache.get("key3") == [1, 2, 3]
        
        cache.set("key4", 42)
        assert cache.get("key4") == 42
    
    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = SimpleCache()
        assert cache.get("nonexistent") is None
    
    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = SimpleCache(default_ttl=1)  # 1 second TTL
        
        # Set a value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should be expired now
        assert cache.get("key1") is None
        
        # Cache should have removed the expired entry
        assert cache.size() == 0
    
    def test_custom_ttl(self):
        """Test setting custom TTL for individual entries."""
        cache = SimpleCache(default_ttl=3600)
        
        # Set with custom short TTL
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should be expired
        assert cache.get("key1") is None
    
    def test_delete(self):
        """Test deleting cache entries."""
        cache = SimpleCache()
        
        # Set a value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Delete it
        deleted = cache.delete("key1")
        assert deleted is True
        assert cache.get("key1") is None
        
        # Try to delete non-existent key
        deleted = cache.delete("nonexistent")
        assert deleted is False
    
    def test_clear(self):
        """Test clearing all cache entries."""
        cache = SimpleCache()
        
        # Add multiple entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size() == 3
        
        # Clear cache
        count = cache.clear()
        assert count == 3
        assert cache.size() == 0
        assert cache.get("key1") is None
    
    def test_size(self):
        """Test getting cache size."""
        cache = SimpleCache()
        
        assert cache.size() == 0
        
        cache.set("key1", "value1")
        assert cache.size() == 1
        
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.delete("key1")
        assert cache.size() == 1
        
        cache.clear()
        assert cache.size() == 0
    
    def test_cleanup_expired(self):
        """Test cleaning up expired entries."""
        cache = SimpleCache(default_ttl=1)
        
        # Add entries with different TTLs
        cache.set("key1", "value1", ttl=1)  # Will expire
        cache.set("key2", "value2", ttl=10)  # Won't expire
        cache.set("key3", "value3", ttl=1)  # Will expire
        
        assert cache.size() == 3
        
        # Wait for some to expire
        time.sleep(1.5)
        
        # Cleanup expired entries
        removed = cache.cleanup_expired()
        assert removed == 2
        assert cache.size() == 1
        assert cache.get("key2") == "value2"
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        cache = SimpleCache(default_ttl=10)
        
        # Empty cache
        stats = cache.get_stats()
        assert stats['total_entries'] == 0
        assert stats['valid_entries'] == 0
        assert stats['expired_entries'] == 0
        
        # Add some entries
        cache.set("key1", "value1", ttl=1)  # Will expire soon
        cache.set("key2", "value2", ttl=10)  # Won't expire
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 2
        assert stats['valid_entries'] == 2
        assert stats['expired_entries'] == 0
        
        # Wait for one to expire
        time.sleep(1.5)
        
        stats = cache.get_stats()
        assert stats['total_entries'] == 2
        assert stats['valid_entries'] == 1
        assert stats['expired_entries'] == 1
    
    def test_thread_safety(self):
        """Test that cache operations are thread-safe."""
        cache = SimpleCache()
        errors = []
        
        def set_values(thread_id):
            try:
                for i in range(100):
                    cache.set(f"key_{thread_id}_{i}", f"value_{thread_id}_{i}")
            except Exception as e:
                errors.append(e)
        
        def get_values(thread_id):
            try:
                for i in range(100):
                    cache.get(f"key_{thread_id}_{i}")
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t1 = threading.Thread(target=set_values, args=(i,))
            t2 = threading.Thread(target=get_values, args=(i,))
            threads.extend([t1, t2])
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # Should have entries from all threads
        assert cache.size() > 0


class TestCachedDecorator:
    """Test cases for the @cached decorator."""
    
    def test_basic_caching(self):
        """Test basic function caching."""
        cache = SimpleCache()
        call_count = [0]
        
        @cached(cache)
        def expensive_function(x, y):
            call_count[0] += 1
            return x + y
        
        # First call - should execute function
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count[0] == 1
        
        # Second call with same args - should use cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count[0] == 1  # Not incremented
        
        # Call with different args - should execute function
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count[0] == 2
    
    def test_caching_with_kwargs(self):
        """Test caching with keyword arguments."""
        cache = SimpleCache()
        call_count = [0]
        
        @cached(cache)
        def function_with_kwargs(x, y=10):
            call_count[0] += 1
            return x + y
        
        # Call with positional args
        result1 = function_with_kwargs(5, 10)
        assert result1 == 15
        assert call_count[0] == 1
        
        # Call with keyword args - should use cache
        result2 = function_with_kwargs(5, y=10)
        assert result2 == 15
        assert call_count[0] == 1
        
        # Call with different kwargs - should execute
        result3 = function_with_kwargs(5, y=20)
        assert result3 == 25
        assert call_count[0] == 2
    
    def test_caching_with_custom_ttl(self):
        """Test caching with custom TTL."""
        cache = SimpleCache()
        call_count = [0]
        
        @cached(cache, ttl=1)
        def function_with_ttl(x):
            call_count[0] += 1
            return x * 2
        
        # First call
        result1 = function_with_ttl(5)
        assert result1 == 10
        assert call_count[0] == 1
        
        # Second call - should use cache
        result2 = function_with_ttl(5)
        assert result2 == 10
        assert call_count[0] == 1
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Third call - cache expired, should execute
        result3 = function_with_ttl(5)
        assert result3 == 10
        assert call_count[0] == 2
    
    def test_caching_with_key_params(self):
        """Test caching with specific key parameters."""
        cache = SimpleCache()
        call_count = [0]
        
        @cached(cache, key_params=['user_id'])
        def fetch_user_data(user_id, debug=False):
            call_count[0] += 1
            return {"user": user_id, "debug": debug}
        
        # First call
        result1 = fetch_user_data("user123", debug=True)
        assert result1 == {"user": "user123", "debug": True}
        assert call_count[0] == 1
        
        # Second call with different debug flag - should use cache
        # because debug is not in key_params
        result2 = fetch_user_data("user123", debug=False)
        assert result2 == {"user": "user123", "debug": True}  # Cached result
        assert call_count[0] == 1
        
        # Call with different user_id - should execute
        result3 = fetch_user_data("user456", debug=True)
        assert result3 == {"user": "user456", "debug": True}
        assert call_count[0] == 2
    
    def test_caching_with_custom_prefix(self):
        """Test caching with custom key prefix."""
        cache = SimpleCache()
        call_count = [0]
        
        @cached(cache, key_prefix="custom_prefix")
        def my_function(x):
            call_count[0] += 1
            return x * 2
        
        # First call
        result1 = my_function(5)
        assert result1 == 10
        assert call_count[0] == 1
        
        # Second call - should use cache
        result2 = my_function(5)
        assert result2 == 10
        assert call_count[0] == 1
    
    def test_caching_method(self):
        """Test caching instance methods."""
        cache = SimpleCache()
        
        class MyClass:
            def __init__(self):
                self.call_count = 0
            
            @cached(cache)
            def my_method(self, x, y):
                self.call_count += 1
                return x + y
        
        obj = MyClass()
        
        # First call
        result1 = obj.my_method(1, 2)
        assert result1 == 3
        assert obj.call_count == 1
        
        # Second call - should use cache
        result2 = obj.my_method(1, 2)
        assert result2 == 3
        assert obj.call_count == 1


class TestGlobalCacheInstances:
    """Test global cache instances."""
    
    def test_global_caches_exist(self):
        """Test that global cache instances are created."""
        assert time_entry_cache is not None
        assert payroll_cache is not None
        assert isinstance(time_entry_cache, SimpleCache)
        assert isinstance(payroll_cache, SimpleCache)
    
    def test_global_cache_ttls(self):
        """Test that global caches have correct TTLs."""
        # Time entry cache: 1 hour
        assert time_entry_cache.default_ttl == 3600
        
        # Payroll cache: 1 hour
        assert payroll_cache.default_ttl == 3600
    
    def test_global_caches_are_independent(self):
        """Test that global caches don't interfere with each other."""
        # Clear both caches
        time_entry_cache.clear()
        payroll_cache.clear()
        
        # Add to time_entry_cache
        time_entry_cache.set("key1", "value1")
        assert time_entry_cache.size() == 1
        assert payroll_cache.size() == 0
        
        # Add to payroll_cache
        payroll_cache.set("key2", "value2")
        assert time_entry_cache.size() == 1
        assert payroll_cache.size() == 1
        
        # Values should be independent
        assert time_entry_cache.get("key1") == "value1"
        assert time_entry_cache.get("key2") is None
        assert payroll_cache.get("key2") == "value2"
        assert payroll_cache.get("key1") is None


class TestCacheIntegration:
    """Integration tests for cache usage patterns."""
    
    def test_api_response_caching_pattern(self):
        """Test typical API response caching pattern."""
        cache = SimpleCache(default_ttl=3600)
        
        def fetch_api_data(endpoint, params):
            """Simulate API call."""
            # Generate cache key
            cache_key = cache.generate_key(endpoint, **params)
            
            # Check cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Simulate API call
            result = {"endpoint": endpoint, "params": params, "data": "..."}
            
            # Store in cache
            cache.set(cache_key, result)
            
            return result
        
        # First call - cache miss
        result1 = fetch_api_data("time_entries", {"date": "2024-01-01"})
        assert result1["endpoint"] == "time_entries"
        
        # Second call - cache hit
        result2 = fetch_api_data("time_entries", {"date": "2024-01-01"})
        assert result2 == result1
        
        # Different params - cache miss
        result3 = fetch_api_data("time_entries", {"date": "2024-01-02"})
        assert result3 != result1
    
    def test_cache_invalidation_pattern(self):
        """Test cache invalidation after data update."""
        cache = SimpleCache()
        
        # Cache some data
        cache.set("user_123", {"name": "John", "age": 30})
        assert cache.get("user_123")["name"] == "John"
        
        # Simulate data update - invalidate cache
        cache.delete("user_123")
        
        # Cache should be empty
        assert cache.get("user_123") is None
        
        # Re-cache with updated data
        cache.set("user_123", {"name": "John", "age": 31})
        assert cache.get("user_123")["age"] == 31
