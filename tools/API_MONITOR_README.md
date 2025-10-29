# API Monitor

Comprehensive monitoring for all API connectors in the R&D Tax Credit Automation Agent.

## Overview

The API Monitor tracks all API interactions across different services including:
- **Clockify**: Time tracking API
- **Unified.to**: Payroll data API
- **You.com**: Search, Agent, Contents, Express Agent, and News APIs
- **OpenRouter**: GLM 4.5 Air model API
- **Other external services**

## Features

- **Call Tracking**: Track API call counts per endpoint
- **Performance Monitoring**: Monitor response times and identify slow endpoints
- **Error Tracking**: Track error rates, types, and recent failures
- **Cost Estimation**: Calculate billable API calls (excluding cached responses)
- **Automatic Alerts**: Alert on consecutive failures, high error rates, and slow responses
- **Statistics Export**: Export detailed metrics to JSON for analysis
- **Thread-Safe**: Safe for use in multi-threaded environments

## Installation

The API Monitor is part of the `tools` package and requires no additional installation.

```python
from tools.api_monitor import APIMonitor, get_global_monitor
```

## Quick Start

### Basic Usage

```python
from tools.api_monitor import APIMonitor

# Create monitor
monitor = APIMonitor()

# Record an API call
monitor.record_api_call(
    api_name='Clockify',
    endpoint='/time-entries',
    response_time=1.5,
    success=True,
    status_code=200
)

# Get statistics
stats = monitor.get_all_statistics()
print(f"Total API calls: {stats['total_calls']}")
print(f"Error rate: {stats['overall_error_rate']:.1f}%")
```

### Using Global Monitor

```python
from tools.api_monitor import get_global_monitor

# Get global monitor instance (shared across application)
monitor = get_global_monitor()

# Record calls from anywhere in the application
monitor.record_api_call(
    api_name='You.com',
    endpoint='agent',
    response_time=2.5,
    success=True,
    status_code=200
)
```

## API Reference

### APIMonitor Class

#### Constructor

```python
monitor = APIMonitor(
    failure_threshold=3,           # Alert after N consecutive failures
    error_rate_threshold=50.0,     # Alert if error rate exceeds N%
    slow_response_threshold=30.0,  # Alert if response time exceeds N seconds
    enable_alerts=True             # Enable automatic alerting
)
```

#### Recording API Calls

```python
monitor.record_api_call(
    api_name='You.com',              # Name of the API
    endpoint='agent',                # Endpoint name or path
    response_time=2.5,               # Response time in seconds
    success=True,                    # Whether call succeeded
    status_code=200,                 # HTTP status code (optional)
    error_type='RateLimitError',     # Error type if failed (optional)
    error_message='Rate limit...',   # Error message if failed (optional)
    cached=False,                    # Whether result was cached
    wait_time=0.5,                   # Rate limit wait time (optional)
    metadata={'key': 'value'}        # Additional metadata (optional)
)
```

#### Getting Statistics

```python
# All statistics
all_stats = monitor.get_all_statistics()

# Statistics for specific API
api_stats = monitor.get_api_statistics('You.com')

# Statistics for specific endpoint
endpoint_stats = monitor.get_endpoint_statistics('You.com', 'agent')

# Cost estimate
cost_info = monitor.get_cost_estimate()
```

#### Error Analysis

```python
# Get recent errors
errors = monitor.get_recent_errors(
    api_name='You.com',  # Optional: filter by API
    endpoint='agent',    # Optional: filter by endpoint
    limit=10             # Maximum number of errors
)

# Get metrics by time range
from datetime import datetime, timedelta
now = datetime.now()
last_hour = now - timedelta(hours=1)

metrics = monitor.get_metrics_by_time_range(
    start_time=last_hour,
    end_time=now,
    api_name='You.com'  # Optional: filter by API
)
```

#### Logging and Export

```python
# Log statistics to console
monitor.log_statistics()

# Export to JSON file
from pathlib import Path
monitor.export_statistics(Path('logs/api_stats.json'))

# Reset all statistics
monitor.reset_statistics()
```

## Integration with API Connectors

### Manual Integration

Add monitoring to your API connector:

```python
from tools.api_monitor import get_global_monitor
import time

class MyAPIConnector:
    def __init__(self):
        self.monitor = get_global_monitor()
    
    def make_api_call(self, endpoint):
        start_time = time.time()
        success = False
        status_code = None
        error_type = None
        error_message = None
        
        try:
            # Make API call
            response = self.client.get(endpoint)
            status_code = response.status_code
            success = True
            return response.json()
        
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            raise
        
        finally:
            response_time = time.time() - start_time
            
            # Record the call
            self.monitor.record_api_call(
                api_name='MyAPI',
                endpoint=endpoint,
                response_time=response_time,
                success=success,
                status_code=status_code,
                error_type=error_type,
                error_message=error_message
            )
```

### Integration with BaseAPIConnector

The `BaseAPIConnector` class can be extended to automatically track all API calls:

```python
from tools.api_connectors import BaseAPIConnector
from tools.api_monitor import get_global_monitor

class MonitoredAPIConnector(BaseAPIConnector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_monitor = get_global_monitor()
    
    def _make_request(self, method, endpoint, **kwargs):
        import time
        start_time = time.time()
        success = False
        status_code = None
        error_type = None
        error_message = None
        
        try:
            response = super()._make_request(method, endpoint, **kwargs)
            success = True
            status_code = 200
            return response
        
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            if hasattr(e, 'status_code'):
                status_code = e.status_code
            raise
        
        finally:
            response_time = time.time() - start_time
            
            self.api_monitor.record_api_call(
                api_name=self.api_name,
                endpoint=endpoint,
                response_time=response_time,
                success=success,
                status_code=status_code,
                error_type=error_type,
                error_message=error_message
            )
```

## Alert System

The monitor automatically generates alerts when:

1. **Consecutive Failures**: When an endpoint fails N times in a row
2. **High Error Rate**: When error rate exceeds threshold (requires 10+ samples)
3. **Slow Response**: When response time exceeds threshold

Alerts are logged at ERROR or WARNING level:

```
[ALERT] You.com API: agent has 3 consecutive failures (threshold: 3)
Last error: RateLimitError - Rate limit exceeded
Recommendation: Check API key, network connectivity, and service status
```

## Cost Tracking

The monitor helps estimate API costs by tracking:
- Total API calls
- Successful calls
- Cached calls (typically not billable)
- Billable calls (successful - cached)

```python
cost_info = monitor.get_cost_estimate()

for api_name, info in cost_info.items():
    if api_name == 'summary':
        continue
    
    print(f"{api_name}:")
    print(f"  Total calls: {info['total_calls']}")
    print(f"  Billable calls: {info['billable_calls']}")
    
    # Calculate cost based on your pricing
    cost_per_call = 0.01  # Example: $0.01 per call
    estimated_cost = info['billable_calls'] * cost_per_call
    print(f"  Estimated cost: ${estimated_cost:.2f}")
```

## Statistics Format

### Overall Statistics

```json
{
  "monitoring_start_time": "2024-01-15T10:00:00",
  "monitoring_duration_seconds": 3600.0,
  "total_calls": 150,
  "successful_calls": 145,
  "failed_calls": 5,
  "cached_calls": 30,
  "overall_error_rate": 3.33,
  "overall_cache_hit_rate": 20.0,
  "average_response_time": 2.5,
  "total_wait_time": 15.0,
  "calls_per_minute": 2.5,
  "apis": {
    "You.com": { ... },
    "Clockify": { ... }
  }
}
```

### Per-API Statistics

```json
{
  "api_name": "You.com",
  "total_calls": 50,
  "successful_calls": 48,
  "failed_calls": 2,
  "cached_calls": 10,
  "error_rate": 4.0,
  "cache_hit_rate": 20.0,
  "average_response_time": 2.3,
  "total_wait_time": 5.0,
  "endpoints": {
    "search": { ... },
    "agent": { ... }
  }
}
```

### Per-Endpoint Statistics

```json
{
  "api_name": "You.com",
  "endpoint": "agent",
  "total_calls": 25,
  "successful_calls": 24,
  "failed_calls": 1,
  "cached_calls": 0,
  "average_response_time": 2.5,
  "min_response_time": 1.8,
  "max_response_time": 4.2,
  "total_wait_time": 2.0,
  "error_rate": 4.0,
  "cache_hit_rate": 0.0,
  "error_counts": {
    "RateLimitError": 1
  },
  "recent_errors": [
    {
      "timestamp": "2024-01-15T10:30:00",
      "error_type": "RateLimitError",
      "error_message": "Rate limit exceeded",
      "status_code": 429
    }
  ],
  "last_call_time": "2024-01-15T10:35:00",
  "consecutive_failures": 0
}
```

## Best Practices

1. **Use Global Monitor**: Use `get_global_monitor()` for consistent tracking across the application
2. **Record All Calls**: Record both successful and failed API calls for accurate statistics
3. **Include Metadata**: Add relevant metadata to help with debugging and analysis
4. **Export Regularly**: Export statistics periodically for long-term analysis
5. **Monitor Alerts**: Pay attention to alerts and investigate patterns
6. **Track Cache Hits**: Record cached responses to accurately estimate costs
7. **Set Appropriate Thresholds**: Adjust alert thresholds based on your API usage patterns

## Examples

See `examples/api_monitor_usage_example.py` for comprehensive examples including:
- Basic monitoring
- Per-API statistics
- Error tracking
- Cost estimation
- Statistics export
- Time range analysis

## Testing

Run the test suite:

```bash
pytest tests/test_api_monitor.py -v
```

## Requirements

- Python 3.8+
- No external dependencies (uses only standard library)

## Related Modules

- `tools.youcom_api_monitor`: Specialized monitoring for You.com APIs
- `tools.api_connectors`: Base API connector classes
- `utils.metrics`: General performance metrics tracking
- `utils.logger`: Logging infrastructure

## License

Part of the R&D Tax Credit Automation Agent project.
