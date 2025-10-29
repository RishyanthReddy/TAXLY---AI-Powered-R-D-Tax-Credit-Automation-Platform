# You.com Rate Limiter

## Overview

The You.com Rate Limiter provides endpoint-specific rate limiting for You.com APIs using the token bucket algorithm. It ensures compliance with API rate limits while providing automatic backoff when limits are approached.

## Features

- **Per-Endpoint Rate Limiting**: Different rate limits for each API endpoint
- **Token Bucket Algorithm**: Allows burst traffic while maintaining average rate limits
- **Automatic Backoff**: Automatically waits when rate limits are approached
- **Detailed Logging**: Logs rate limit events and warnings
- **Thread-Safe**: Safe to use in multi-threaded environments
- **Statistics Tracking**: Tracks request counts, wait times, and backoff events

## Rate Limits by Endpoint

| Endpoint | Requests per Minute | Burst Size |
|----------|---------------------|------------|
| Search API | 10 | 10 |
| News API | 10 | 10 |
| Agent API | 10 | 10 |
| Express Agent API | 10 | 10 |
| Contents API | 10 | 10 |

## Usage

### Basic Usage

The rate limiter is automatically integrated into the `YouComClient`:

```python
from tools.you_com_client import YouComClient
from utils.config import get_config

config = get_config()
client = YouComClient(api_key=config.youcom_api_key)

# Rate limiting is automatically applied
results = client.search(query="IRS R&D tax credit")
# If rate limit is reached, the call will automatically wait
```

### Custom Rate Limits

You can configure custom rate limits per endpoint:

```python
from tools.you_com_client import YouComClient
from tools.youcom_rate_limiter import RateLimitConfig

# Configure custom rate limits
custom_limits = {
    'agent': RateLimitConfig(requests_per_minute=5, burst_size=5),
    'search': RateLimitConfig(requests_per_minute=15, burst_size=20)
}

client = YouComClient(
    api_key="ydc-sk-...",
    custom_rate_limits=custom_limits
)
```

### Disable Backoff Warnings

You can disable warnings when rate limits are approached:

```python
client = YouComClient(
    api_key="ydc-sk-...",
    enable_backoff_warnings=False
)
```

### Direct Rate Limiter Usage

You can also use the rate limiter directly:

```python
from tools.youcom_rate_limiter import YouComRateLimiter

# Initialize rate limiter
limiter = YouComRateLimiter()

# Acquire token before making API call
wait_time = limiter.acquire('search')
print(f"Waited {wait_time:.2f}s")

# Now safe to make the API call
# ... make API call ...
```

### Non-Blocking Acquisition

Try to acquire tokens without blocking:

```python
limiter = YouComRateLimiter()

if limiter.try_acquire('agent'):
    # Make API call
    result = client.agent_run(prompt="...")
else:
    # Rate limited, handle accordingly
    print("Rate limited, try again later")
```

### Check Wait Time

Check estimated wait time before making a request:

```python
limiter = YouComRateLimiter()

wait = limiter.get_wait_time('search')
if wait > 0:
    print(f"Would need to wait {wait:.2f}s before next search")
```

### Get Available Tokens

Check how many tokens are available:

```python
limiter = YouComRateLimiter()

available = limiter.get_available_tokens('agent')
print(f"{available:.1f} tokens available for agent API")
```

## Statistics

### Get Rate Limiter Statistics

```python
client = YouComClient(api_key="ydc-sk-...")

# ... make some API calls ...

# Get stats for specific endpoint
search_stats = client.get_rate_limiter_statistics()['search']
print(f"Search API: {search_stats['total_requests']} requests")
print(f"Average wait: {search_stats['average_wait_time']:.3f}s")
print(f"Backoff count: {search_stats['backoff_count']}")

# Get stats for all endpoints
all_stats = client.get_rate_limiter_statistics()
for endpoint, stats in all_stats.items():
    print(f"{endpoint}: {stats['total_requests']} requests")
```

### Log Statistics

```python
client = YouComClient(api_key="ydc-sk-...")

# ... make some API calls ...

# Log statistics for all endpoints
client.log_rate_limiter_statistics()
```

Output:
```
=== You.com Rate Limiter Statistics ===
[search] Requests: 25, Total wait: 12.50s, Avg wait: 0.500s, Max wait: 2.00s, Backoffs: 2, Available: 8.5 tokens
[agent] Requests: 10, Total wait: 5.00s, Avg wait: 0.500s, Max wait: 1.50s, Backoffs: 0, Available: 9.0 tokens
[contents] Requests: 5, Total wait: 0.00s, Avg wait: 0.000s, Max wait: 0.00s, Backoffs: 0, Available: 10.0 tokens
========================================
```

## Token Bucket Algorithm

The token bucket algorithm works as follows:

1. **Bucket Initialization**: The bucket starts with a full capacity of tokens (burst_size)
2. **Token Refill**: Tokens are added to the bucket at a constant rate (requests_per_minute / 60)
3. **Token Consumption**: Each API request consumes one token
4. **Waiting**: If no tokens are available, the request waits until a token becomes available
5. **Burst Traffic**: The burst_size allows for temporary bursts of traffic above the average rate

### Example

With a rate limit of 10 requests per minute and burst size of 10:

- You can make 10 requests immediately (burst)
- After that, you can make 1 request every 6 seconds (10/min = 1/6s)
- If you wait 30 seconds, you'll have 5 tokens available (30s * 10/60 = 5)
- Maximum tokens is always capped at burst_size (10)

## Logging

The rate limiter logs various events:

### Debug Level
- Token acquisition with wait time < 1s
- Token refills

### Info Level
- Token acquisition with wait time 1-5s
- Statistics summaries

### Warning Level
- Token acquisition with wait time > 5s (significant backoff)
- Approaching rate limit (< 2 tokens remaining)

## Thread Safety

The rate limiter is thread-safe and can be used in multi-threaded environments. Each token bucket uses a lock to ensure atomic operations.

## Best Practices

1. **Use the Integrated Client**: The `YouComClient` automatically handles rate limiting
2. **Monitor Statistics**: Regularly check rate limiter statistics to understand usage patterns
3. **Adjust Limits**: If you have a higher rate limit from You.com, configure custom limits
4. **Handle Backoff**: Be aware that requests may be delayed when rate limits are reached
5. **Cache Results**: Use the built-in caching to reduce API calls

## Error Handling

The rate limiter raises `TimeoutError` if tokens cannot be acquired within a specified timeout:

```python
from tools.youcom_rate_limiter import TokenBucket

bucket = TokenBucket(requests_per_minute=10)

try:
    # Try to acquire with 5 second timeout
    wait_time = bucket.acquire(tokens=1, timeout=5.0)
except TimeoutError as e:
    print(f"Could not acquire token: {e}")
```

## Testing

Reset rate limiters for testing:

```python
limiter = YouComRateLimiter()

# Reset specific endpoint
limiter.reset('search')

# Reset all endpoints
limiter.reset()
```

## Integration with You.com Client

The rate limiter is automatically integrated into the `YouComClient`:

```python
# When you call any API method, rate limiting is automatically applied
client = YouComClient(api_key="ydc-sk-...")

# Search API - rate limited to 10/min
results = client.search(query="...")

# Agent API - rate limited to 10/min
response = client.agent_run(prompt="...")

# Contents API - rate limited to 10/min
content = client.fetch_content(url="...")

# Express Agent API - rate limited to 10/min
review = client.express_agent(narrative_text="...")

# News API - rate limited to 10/min
news = client.news(query="...")
```

## Configuration

### Default Configuration

```python
DEFAULT_LIMITS = {
    'search': RateLimitConfig(requests_per_minute=10, burst_size=10),
    'news': RateLimitConfig(requests_per_minute=10, burst_size=10),
    'agent': RateLimitConfig(requests_per_minute=10, burst_size=10),
    'contents': RateLimitConfig(requests_per_minute=10, burst_size=10),
    'express_agent': RateLimitConfig(requests_per_minute=10, burst_size=10),
}
```

### Custom Configuration

```python
from tools.youcom_rate_limiter import RateLimitConfig

custom_limits = {
    # More restrictive for agent API
    'agent': RateLimitConfig(requests_per_minute=5, burst_size=5),
    
    # More permissive for search API
    'search': RateLimitConfig(requests_per_minute=20, burst_size=30),
}

client = YouComClient(
    api_key="ydc-sk-...",
    custom_rate_limits=custom_limits
)
```

## See Also

- [You.com API Documentation](https://documentation.you.com/)
- [You.com Client README](./YOU_COM_CLIENT_README.md)
- [API Connectors README](./API_CONNECTORS_README.md)
