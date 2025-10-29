# Cache Module

A simple, thread-safe in-memory cache with TTL (Time-To-Live) support for API response caching and performance optimization.

## Overview

The cache module provides:
- **SimpleCache**: Thread-safe in-memory cache with TTL expiration
- **@cached decorator**: Easy function result caching
- **Global cache instances**: Pre-configured caches for common use cases
- **Cache key generation**: Automatic key generation from parameters
- **Cache statistics**: Monitor cache usage and performance

## Installation

The cache module is part of the `tools` package and has no external dependencies beyond the standard library.

```python
from tools.cache import SimpleCache, cached, time_entry_cache
```

## Quick Start

### Basic Usage

```python
from tools.cache import SimpleCache

# Create a cache with 1 hour default TTL
cache = SimpleCache(default_ttl=3600)

# Store a value
cache.set("user_123", {"name": "John", "email": "john@example.com"})

# Retrieve the value
user = cache.get("user_123")

# Delete a specific entry
cache.delete("user_123")

# Clear all entries
cache.clear()
```

### Using the @cached Decorator

```python
from tools.cache import SimpleCache, cached

cache = SimpleCache(default_ttl=3600)

@cached(cache, ttl=1800)  # 30 minute TTL
def fetch_user_data(user_id: str):
    # Expensive API call or computation
    return {"user_id": user_id, "data": "..."}

# First call - executes function
result1 = fetch_user_data("user123")

# Second call - returns cached result
result2 = fetch_user_data("user123")
```

### Using Global Cache Instances

```python
from tools.cache import time_entry_cache, payroll_cache

# Use pre-configured global caches
time_entry_cache.set("entry_123", {"hours": 8, "project": "Alpha"})
payroll_cache.set("payroll_456", {"salary": 75000})

# Retrieve from cache
entry = time_entry_cache.get("entry_123")
```

## API Reference

### SimpleCache Class

#### Constructor

```python
SimpleCache(default_ttl: int = 3600)
```

Creates a new cache instance.

**Parameters:**
- `default_ttl` (int): Default time-to-live in seconds (default: 3600 = 1 hour)

#### Methods

##### set(key, value, ttl=None)

Store a value in the cache.

```python
cache.set("key1", "value1")
cache.set("key2", "value2", ttl=1800)  # Custom 30 min TTL
```

**Parameters:**
- `key` (str): Cache key
- `value` (Any): Value to cache
- `ttl` (int, optional): Time-to-live in seconds (uses default_ttl if not specified)

##### get(key)

Retrieve a value from the cache.

```python
value = cache.get("key1")
if value is not None:
    print("Cache hit!")
```

**Parameters:**
- `key` (str): Cache key to retrieve

**Returns:**
- Cached value if available and not expired, None otherwise

##### delete(key)

Delete a specific cache entry.

```python
deleted = cache.delete("key1")
```

**Parameters:**
- `key` (str): Cache key to delete

**Returns:**
- `True` if the key was found and deleted, `False` otherwise

##### clear()

Clear all cache entries.

```python
count = cache.clear()
print(f"Cleared {count} entries")
```

**Returns:**
- Number of entries cleared

##### size()

Get the current number of cache entries.

```python
size = cache.size()
```

**Returns:**
- Number of entries in the cache

##### generate_key(prefix, **params)

Generate a unique cache key from parameters.

```python
key = cache.generate_key("api_call", user_id="123", date="2024-01-01")
```

**Parameters:**
- `prefix` (str): Cache key prefix
- `**params`: Parameters to include in the cache key

**Returns:**
- MD5 hash string to use as cache key

##### cleanup_expired()

Remove all expired entries from the cache.

```python
removed = cache.cleanup_expired()
print(f"Removed {removed} expired entries")
```

**Returns:**
- Number of expired entries removed

##### get_stats()

Get cache statistics.

```python
stats = cache.get_stats()
print(f"Valid entries: {stats['valid_entries']}")
```

**Returns:**
- Dictionary containing:
  - `total_entries`: Total number of cache entries
  - `expired_entries`: Number of expired entries
  - `valid_entries`: Number of valid (non-expired) entries
  - `oldest_entry_age`: Age of oldest entry in seconds
  - `newest_entry_age`: Age of newest entry in seconds

### @cached Decorator

```python
@cached(
    cache_instance: SimpleCache,
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    key_params: Optional[list] = None
)
```

Decorator to cache function results.

**Parameters:**
- `cache_instance` (SimpleCache): Cache instance to use
- `ttl` (int, optional): Time-to-live in seconds (uses cache's default if not specified)
- `key_prefix` (str, optional): Custom prefix for cache key (uses function name if not specified)
- `key_params` (list, optional): List of parameter names to include in cache key (uses all parameters if not specified)

**Example:**

```python
@cached(cache, ttl=1800, key_params=['user_id', 'date'])
def fetch_user_activity(user_id: str, date: str, debug: bool = False):
    # Only user_id and date are used in cache key
    # debug flag doesn't affect caching
    return {"user": user_id, "date": date}
```

### Global Cache Instances

Pre-configured cache instances for common use cases:

```python
from tools.cache import (
    time_entry_cache,    # 1 hour TTL
    payroll_cache,       # 1 hour TTL
    search_cache,        # 1 hour TTL
    content_cache        # 24 hours TTL
)
```

## Usage Patterns

### API Response Caching

```python
from tools.cache import SimpleCache

cache = SimpleCache(default_ttl=3600)

def fetch_time_entries(workspace_id: str, date: str):
    # Generate cache key
    cache_key = cache.generate_key(
        "time_entries",
        workspace_id=workspace_id,
        date=date
    )
    
    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Cache miss - make API call
    result = api_client.fetch_time_entries(workspace_id, date)
    
    # Store in cache
    cache.set(cache_key, result)
    
    return result
```

### Decorator-Based Caching

```python
from tools.cache import SimpleCache, cached

cache = SimpleCache()

@cached(cache, ttl=1800)
def expensive_calculation(x: int, y: int) -> int:
    # Expensive computation
    return x * y + x + y

# First call - executes function
result1 = expensive_calculation(10, 20)

# Second call - returns cached result
result2 = expensive_calculation(10, 20)
```

### Selective Parameter Caching

```python
@cached(cache, key_params=['user_id', 'date'])
def fetch_user_data(user_id: str, date: str, include_details: bool = False):
    # Cache key only includes user_id and date
    # Different include_details values will return same cached result
    return fetch_from_api(user_id, date, include_details)
```

### Cache Invalidation

```python
# Invalidate specific entry
cache.delete("user_123")

# Invalidate all entries
cache.clear()

# Cleanup expired entries
cache.cleanup_expired()
```

### Cache Statistics and Monitoring

```python
# Get cache statistics
stats = cache.get_stats()
print(f"Cache efficiency: {stats['valid_entries']}/{stats['total_entries']}")

# Monitor cache size
if cache.size() > 1000:
    cache.cleanup_expired()
```

## Configuration

### TTL Configuration

Configure TTL based on data volatility:

```python
# Frequently changing data - short TTL
user_cache = SimpleCache(default_ttl=300)  # 5 minutes

# Stable data - long TTL
config_cache = SimpleCache(default_ttl=86400)  # 24 hours

# Per-entry TTL override
cache.set("volatile_data", value, ttl=60)  # 1 minute
cache.set("stable_data", value, ttl=3600)  # 1 hour
```

### Cache Key Strategy

Use descriptive prefixes and include all relevant parameters:

```python
# Good: Specific and descriptive
key = cache.generate_key(
    "clockify_time_entries",
    workspace_id=workspace_id,
    start_date=start_date,
    end_date=end_date
)

# Bad: Too generic
key = cache.generate_key("data", id=id)
```

## Performance Considerations

### Memory Usage

The cache stores all data in memory. Monitor cache size:

```python
# Periodic cleanup
if cache.size() > 10000:
    cache.cleanup_expired()
    
# Or clear old data
if cache.size() > 10000:
    cache.clear()
```

### Thread Safety

All cache operations are thread-safe:

```python
# Safe to use from multiple threads
def worker_thread():
    cache.set(f"key_{thread_id}", data)
    result = cache.get(f"key_{thread_id}")
```

### Cache Hit Rate

Monitor cache effectiveness:

```python
stats = cache.get_stats()
hit_rate = stats['valid_entries'] / max(stats['total_entries'], 1)
print(f"Cache hit rate: {hit_rate:.2%}")
```

## Best Practices

1. **Choose appropriate TTL**: Balance freshness vs. performance
2. **Use descriptive cache keys**: Include all relevant parameters
3. **Monitor cache size**: Implement cleanup strategies
4. **Handle cache misses gracefully**: Always have fallback logic
5. **Invalidate on updates**: Clear cache when data changes
6. **Use global caches for common patterns**: Leverage pre-configured instances
7. **Test cache behavior**: Verify TTL and invalidation logic

## Examples

See `examples/cache_usage_example.py` for comprehensive usage examples including:
- Basic cache operations
- TTL expiration
- API response caching
- Decorator usage
- Cache statistics
- Invalidation patterns

## Testing

Run the test suite:

```bash
pytest tests/test_cache.py -v
```

Tests cover:
- Basic operations (get, set, delete, clear)
- TTL expiration
- Thread safety
- Decorator functionality
- Cache statistics
- Integration patterns

## Troubleshooting

### Cache Not Working

```python
# Verify cache is enabled
cache = SimpleCache(default_ttl=3600)
cache.set("test", "value")
assert cache.get("test") == "value"
```

### Entries Expiring Too Quickly

```python
# Check TTL configuration
print(f"Default TTL: {cache.default_ttl}s")

# Use longer TTL
cache.set("key", "value", ttl=7200)  # 2 hours
```

### Memory Issues

```python
# Monitor cache size
print(f"Cache size: {cache.size()} entries")

# Cleanup expired entries
removed = cache.cleanup_expired()
print(f"Removed {removed} expired entries")

# Clear if needed
if cache.size() > 10000:
    cache.clear()
```

## Related Modules

- `tools/api_connectors.py`: Base API connector with rate limiting
- `tools/you_com_client.py`: You.com API client with built-in caching
- `utils/retry.py`: Retry logic for API calls

## License

Part of the R&D Tax Credit Automation Agent project.
