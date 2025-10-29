# Rate Limiting Implementation

## Overview

The rate limiting system implements a token bucket algorithm with automatic backoff to prevent API rate limit violations. This ensures smooth operation when interacting with external APIs while respecting their rate limits.

## Features

### 1. Token Bucket Algorithm
- Tokens are added at a constant rate (requests per second)
- Each API call consumes one token
- Burst traffic is supported up to the burst size
- Smooth rate limiting over time

### 2. Automatic Backoff
- Proactively slows down when approaching rate limits
- Configurable backoff threshold (default: 20% tokens remaining)
- Prevents hitting hard rate limits
- Reduces API errors and retries

### 3. Per-API Configuration
- Different rate limits for different APIs
- Customizable burst sizes
- Adjustable backoff thresholds
- Optional warning logs

### 4. Statistics Tracking
- Total requests processed
- Total wait time
- Backoff count
- Current token count
- Token percentage

## Configuration

### Clockify API
```python
ClockifyConnector(
    api_key="...",
    workspace_id="...",
    # Rate limiting configured automatically:
    # - 10 requests per second
    # - Burst size: 10
    # - Backoff threshold: 20%
)
```

### You.com APIs
```python
YouComClient(
    api_key="...",
    # Per-endpoint rate limiting:
    # - Search API: 10 requests per minute
    # - Agent API: 10 requests per minute
    # - Contents API: 10 requests per minute
    # - Express Agent API: 10 requests per minute
)
```

### Unified.to API
```python
UnifiedToConnector(
    api_key="...",
    workspace_id="...",
    # Rate limiting configured automatically:
    # - 5 requests per second (conservative)
    # - Burst size: 5
    # - Backoff threshold: 20%
)
```

## Custom Configuration

### Basic Rate Limiter
```python
from tools.api_connectors import RateLimiter

limiter = RateLimiter(
    requests_per_second=10.0,
    burst_size=20,  # Allow bursts up to 20 requests
    backoff_threshold=0.3,  # Backoff when < 30% tokens remain
    enable_backoff_warnings=True  # Log warnings
)

# Acquire token before making request
wait_time = limiter.acquire()
# Make API request...
```

### Custom API Connector
```python
from tools.api_connectors import BaseAPIConnector

class MyAPIConnector(BaseAPIConnector):
    def __init__(self, api_key: str):
        super().__init__(
            api_name="MyAPI",
            rate_limit=5.0,  # 5 requests per second
            rate_limit_burst_size=10,  # Allow bursts
            rate_limit_backoff_threshold=0.25,  # Backoff at 25%
            enable_backoff_warnings=True
        )
        self.api_key = api_key
    
    def _get_base_url(self) -> str:
        return "https://api.example.com"
    
    def _get_auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}
```

## Monitoring

### View Statistics
```python
# Rate limiter statistics
stats = limiter.get_statistics()
print(f"Total requests: {stats['total_requests']}")
print(f"Total wait time: {stats['total_wait_time']:.2f}s")
print(f"Backoff count: {stats['backoff_count']}")
print(f"Current tokens: {stats['current_tokens']:.2f}")
print(f"Token percentage: {stats['token_percentage']:.1%}")

# Connector statistics (includes rate limiter stats)
connector_stats = connector.get_statistics()
print(f"API: {connector_stats['api_name']}")
print(f"Requests: {connector_stats['request_count']}")
print(f"Errors: {connector_stats['error_count']}")
print(f"Error rate: {connector_stats['error_rate']:.1%}")

if 'rate_limiter' in connector_stats:
    rl_stats = connector_stats['rate_limiter']
    print(f"Rate limiter backoff count: {rl_stats['backoff_count']}")
```

### Reset Rate Limiter
```python
# Reset to full capacity (useful for testing)
limiter.reset()
```

## How It Works

### Token Bucket Algorithm

1. **Initialization**: Bucket starts full with `burst_size` tokens
2. **Token Refill**: Tokens are added at `requests_per_second` rate
3. **Token Consumption**: Each request consumes 1 token
4. **Waiting**: If no tokens available, wait until tokens refill

### Automatic Backoff

1. **Threshold Check**: Before each request, check token percentage
2. **Backoff Calculation**: If below threshold, calculate backoff time
   - Backoff factor = (threshold - current%) / threshold
   - Backoff time = backoff_factor × (1 / requests_per_second)
3. **Apply Backoff**: Sleep for backoff time before consuming token
4. **Warning Log**: Log warning every 10 backoffs (if enabled)

### Example Timeline

```
Time    Tokens  Action              Wait Time
0.0s    10.0    Request 1           0.0s (no wait)
0.1s    9.0     Request 2           0.0s
0.2s    8.0     Request 3           0.0s
...
0.9s    1.0     Request 10          0.0s
1.0s    0.0     Request 11          0.1s (wait for token)
1.1s    0.0     Request 12          0.1s
```

With backoff (threshold=0.2, i.e., 2 tokens):
```
Time    Tokens  Action              Wait Time
0.0s    10.0    Request 1           0.0s
...
0.7s    3.0     Request 8           0.0s
0.8s    2.0     Request 9           0.0s (at threshold)
0.9s    1.0     Request 10          0.05s (backoff applied)
1.0s    0.0     Request 11          0.1s (backoff + token wait)
```

## Best Practices

### 1. Set Conservative Limits
Set rate limits slightly below API provider limits to account for:
- Network latency
- Clock skew
- Other clients using the same API key

```python
# If API allows 100 req/min, use 90 req/min
limiter = RateLimiter(requests_per_second=1.5)  # 90 req/min
```

### 2. Use Appropriate Burst Sizes
- Small burst size: Smoother rate limiting, less bursty traffic
- Large burst size: Better handling of traffic spikes

```python
# For steady traffic
limiter = RateLimiter(requests_per_second=10.0, burst_size=10)

# For bursty traffic
limiter = RateLimiter(requests_per_second=10.0, burst_size=30)
```

### 3. Tune Backoff Threshold
- Higher threshold (e.g., 0.5): More aggressive backoff, smoother traffic
- Lower threshold (e.g., 0.1): Less backoff, faster processing

```python
# Aggressive backoff (recommended for production)
limiter = RateLimiter(
    requests_per_second=10.0,
    backoff_threshold=0.3  # Backoff at 30% tokens
)

# Minimal backoff (for development/testing)
limiter = RateLimiter(
    requests_per_second=10.0,
    backoff_threshold=0.1  # Backoff at 10% tokens
)
```

### 4. Monitor Statistics
Regularly check rate limiter statistics to:
- Identify bottlenecks
- Tune configuration
- Detect rate limit issues early

```python
# Log statistics periodically
import logging
logger = logging.getLogger(__name__)

stats = limiter.get_statistics()
if stats['backoff_count'] > 100:
    logger.warning(
        f"High backoff count: {stats['backoff_count']}. "
        f"Consider increasing rate limit or burst size."
    )
```

### 5. Disable Warnings in Production
Backoff warnings are useful for development but can create log noise in production:

```python
# Development
limiter = RateLimiter(
    requests_per_second=10.0,
    enable_backoff_warnings=True  # Enable for debugging
)

# Production
limiter = RateLimiter(
    requests_per_second=10.0,
    enable_backoff_warnings=False  # Disable to reduce log noise
)
```

## Troubleshooting

### Issue: Too Many 429 Errors
**Symptoms**: Receiving rate limit errors from API despite rate limiting

**Solutions**:
1. Reduce `requests_per_second`
2. Increase `backoff_threshold` (e.g., from 0.2 to 0.4)
3. Reduce `burst_size` to prevent traffic spikes

### Issue: Slow Performance
**Symptoms**: Requests taking too long, high wait times

**Solutions**:
1. Check `total_wait_time` in statistics
2. Increase `requests_per_second` if API allows
3. Decrease `backoff_threshold` (e.g., from 0.3 to 0.1)
4. Increase `burst_size` for better burst handling

### Issue: High Backoff Count
**Symptoms**: `backoff_count` is very high in statistics

**Solutions**:
1. This indicates you're frequently approaching rate limits
2. Consider increasing `requests_per_second` if API allows
3. Or accept the backoff as working correctly to prevent rate limit errors
4. Monitor for actual rate limit errors (429 responses)

## API Rate Limits Reference

| API | Rate Limit | Burst Size | Backoff Threshold |
|-----|-----------|-----------|------------------|
| Clockify | 10 req/s | 10 | 20% |
| You.com Search | 10 req/min | 10 | 20% |
| You.com Agent | 10 req/min | 10 | 20% |
| You.com Contents | 10 req/min | 10 | 20% |
| You.com Express | 10 req/min | 10 | 20% |
| Unified.to | 5 req/s | 5 | 20% |

## Examples

See `examples/rate_limiting_usage_example.py` for comprehensive examples including:
1. Basic rate limiting
2. Custom backoff threshold
3. Monitoring statistics
4. Connector integration
5. Warning handling

## Testing

Run tests with:
```bash
pytest tests/test_api_connectors.py::TestRateLimiter -v
pytest tests/test_api_connectors.py::TestBaseAPIConnector -v
```

## References

- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Rate Limiting Patterns](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
- Task 93: Implement rate limiting (Requirements: 7.1)
