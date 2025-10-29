"""
Generic API response caching utility with TTL support.

This module provides a simple in-memory cache with time-to-live (TTL) support
for API responses. It includes:
- TTL-based expiration
- Cache key generation from parameters
- Cache invalidation methods
- Decorator for easy integration with API methods
- Thread-safe operations

The cache is designed to reduce API calls and improve performance by storing
frequently accessed data temporarily.
"""

import time
import hashlib
import json
import functools
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import logging

from utils.logger import get_tool_logger


# Get logger for cache
logger = get_tool_logger("cache")


class SimpleCache:
    """
    Simple in-memory cache with TTL (Time-To-Live) support.
    
    This cache stores key-value pairs with expiration times. Expired entries
    are automatically removed when accessed. The cache is thread-safe for
    concurrent access.
    
    Attributes:
        default_ttl: Default time-to-live in seconds for cache entries
        _cache: Internal dictionary storing cache entries
        _lock: Thread lock for thread-safe operations
    
    Example:
        >>> cache = SimpleCache(default_ttl=3600)  # 1 hour default TTL
        >>> cache.set("key1", {"data": "value"}, ttl=1800)  # 30 minutes
        >>> result = cache.get("key1")
        >>> if result is not None:
        ...     print("Cache hit!")
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize the cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        logger.info(f"Initialized SimpleCache with default TTL: {default_ttl}s")
    
    def generate_key(self, prefix: str, **params) -> str:
        """
        Generate a unique cache key from parameters.
        
        Creates an MD5 hash of the parameters to use as a cache key.
        This ensures consistent keys for the same parameters regardless
        of parameter order.
        
        Args:
            prefix: Cache key prefix (e.g., "api_name", "endpoint")
            **params: Parameters to include in the cache key
        
        Returns:
            MD5 hash string to use as cache key
        
        Example:
            >>> cache = SimpleCache()
            >>> key = cache.generate_key("clockify", workspace_id="123", date="2024-01-01")
            >>> print(key)  # e.g., "a1b2c3d4e5f6..."
        """
        # Create a dictionary with all parameters
        cache_params = {"prefix": prefix}
        cache_params.update(params)
        
        # Generate hash from sorted JSON representation
        params_str = json.dumps(cache_params, sort_keys=True, default=str)
        cache_key = hashlib.md5(params_str.encode()).hexdigest()
        
        return cache_key
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Returns None if the key doesn't exist or if the entry has expired.
        Expired entries are automatically removed from the cache.
        
        Args:
            key: Cache key to retrieve
        
        Returns:
            Cached value if available and not expired, None otherwise
        
        Example:
            >>> cache = SimpleCache()
            >>> cache.set("key1", {"data": "value"})
            >>> result = cache.get("key1")
            >>> if result:
            ...     print("Found:", result)
        """
        with self._lock:
            if key not in self._cache:
                logger.debug(f"Cache miss: key not found")
                return None
            
            entry = self._cache[key]
            cached_time = entry['timestamp']
            cached_value = entry['value']
            ttl = entry['ttl']
            
            # Check if entry has expired
            age = (datetime.now() - cached_time).total_seconds()
            if age > ttl:
                # Remove expired entry
                del self._cache[key]
                logger.debug(f"Cache miss: entry expired (age: {age:.1f}s, ttl: {ttl}s)")
                return None
            
            logger.debug(f"Cache hit! (age: {age:.1f}s, ttl: {ttl}s)")
            return cached_value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key to store under
            value: Value to cache (can be any Python object)
            ttl: Time-to-live in seconds (uses default_ttl if not specified)
        
        Example:
            >>> cache = SimpleCache(default_ttl=3600)
            >>> cache.set("key1", {"data": "value"})  # Uses default 1 hour TTL
            >>> cache.set("key2", {"data": "value"}, ttl=1800)  # Custom 30 min TTL
        """
        if ttl is None:
            ttl = self.default_ttl
        
        with self._lock:
            self._cache[key] = {
                'value': value,
                'timestamp': datetime.now(),
                'ttl': ttl
            }
            
            logger.debug(f"Stored value in cache (ttl: {ttl}s)")
    
    def delete(self, key: str) -> bool:
        """
        Delete a specific cache entry.
        
        Args:
            key: Cache key to delete
        
        Returns:
            True if the key was found and deleted, False otherwise
        
        Example:
            >>> cache = SimpleCache()
            >>> cache.set("key1", "value")
            >>> deleted = cache.delete("key1")
            >>> print(deleted)  # True
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted cache entry")
                return True
            return False
    
    def clear(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        
        Example:
            >>> cache = SimpleCache()
            >>> cache.set("key1", "value1")
            >>> cache.set("key2", "value2")
            >>> count = cache.clear()
            >>> print(f"Cleared {count} entries")  # Cleared 2 entries
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} cache entries")
            return count
    
    def size(self) -> int:
        """
        Get the current number of cache entries.
        
        Returns:
            Number of entries in the cache
        
        Example:
            >>> cache = SimpleCache()
            >>> cache.set("key1", "value1")
            >>> cache.set("key2", "value2")
            >>> print(cache.size())  # 2
        """
        with self._lock:
            return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.
        
        This method scans all cache entries and removes those that have
        exceeded their TTL. This is useful for periodic cleanup to free
        memory.
        
        Returns:
            Number of expired entries removed
        
        Example:
            >>> cache = SimpleCache()
            >>> # ... after some time ...
            >>> removed = cache.cleanup_expired()
            >>> print(f"Removed {removed} expired entries")
        """
        with self._lock:
            now = datetime.now()
            expired_keys = []
            
            for key, entry in self._cache.items():
                age = (now - entry['timestamp']).total_seconds()
                if age > entry['ttl']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing:
                - total_entries: Total number of cache entries
                - expired_entries: Number of expired entries
                - valid_entries: Number of valid (non-expired) entries
                - oldest_entry_age: Age of oldest entry in seconds
                - newest_entry_age: Age of newest entry in seconds
        
        Example:
            >>> cache = SimpleCache()
            >>> cache.set("key1", "value1")
            >>> stats = cache.get_stats()
            >>> print(f"Cache has {stats['valid_entries']} valid entries")
        """
        with self._lock:
            now = datetime.now()
            total = len(self._cache)
            expired = 0
            ages = []
            
            for entry in self._cache.values():
                age = (now - entry['timestamp']).total_seconds()
                ages.append(age)
                if age > entry['ttl']:
                    expired += 1
            
            stats = {
                'total_entries': total,
                'expired_entries': expired,
                'valid_entries': total - expired,
                'oldest_entry_age': max(ages) if ages else 0,
                'newest_entry_age': min(ages) if ages else 0
            }
            
            return stats


def cached(
    cache_instance: SimpleCache,
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    key_params: Optional[list] = None
) -> Callable:
    """
    Decorator to cache function results.
    
    This decorator automatically caches the return value of a function based
    on its arguments. The cache key is generated from the function name and
    specified parameters.
    
    Args:
        cache_instance: SimpleCache instance to use for caching
        ttl: Time-to-live in seconds (uses cache's default if not specified)
        key_prefix: Custom prefix for cache key (uses function name if not specified)
        key_params: List of parameter names to include in cache key
                   (uses all parameters if not specified)
    
    Returns:
        Decorated function with caching behavior
    
    Example:
        >>> cache = SimpleCache(default_ttl=3600)
        >>> 
        >>> @cached(cache, ttl=1800, key_params=['user_id', 'date'])
        >>> def fetch_user_data(user_id: str, date: str, debug: bool = False):
        ...     # Expensive API call
        ...     return {"user": user_id, "data": "..."}
        >>> 
        >>> # First call - cache miss, executes function
        >>> result1 = fetch_user_data("user123", "2024-01-01")
        >>> 
        >>> # Second call with same params - cache hit, returns cached result
        >>> result2 = fetch_user_data("user123", "2024-01-01")
    
    Note:
        - Only works with functions that have hashable arguments
        - The 'self' parameter is automatically excluded for methods
        - Keyword arguments are supported
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            func_name = key_prefix or func.__name__
            
            # Build parameters dict for cache key
            cache_params = {}
            
            # Get function signature to map args to param names
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Map positional args to param names (skip 'self' for methods)
            start_idx = 1 if param_names and param_names[0] == 'self' else 0
            for i, arg in enumerate(args[start_idx:], start=start_idx):
                if i < len(param_names):
                    param_name = param_names[i]
                    # Only include if in key_params or if key_params not specified
                    if key_params is None or param_name in key_params:
                        cache_params[param_name] = arg
            
            # Add keyword arguments
            for key, value in kwargs.items():
                if key_params is None or key in key_params:
                    cache_params[key] = value
            
            # Generate cache key
            cache_key = cache_instance.generate_key(func_name, **cache_params)
            
            # Try to get from cache
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func_name}")
                return cached_result
            
            # Cache miss - execute function
            logger.debug(f"Cache miss for {func_name}, executing function")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_instance.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


# Global cache instances for common use cases
# These can be imported and used directly

# Cache for time entry data (1 hour TTL)
time_entry_cache = SimpleCache(default_ttl=3600)

# Cache for payroll data (1 hour TTL)
payroll_cache = SimpleCache(default_ttl=3600)

# Cache for search results (1 hour TTL)
search_cache = SimpleCache(default_ttl=3600)

# Cache for content/templates (24 hours TTL)
content_cache = SimpleCache(default_ttl=86400)


logger.info("Initialized global cache instances (time_entry, payroll, search, content)")
