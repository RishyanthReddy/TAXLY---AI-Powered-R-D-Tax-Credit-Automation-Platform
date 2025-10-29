# API Health Check Module

Comprehensive health check functionality for all external API connectors used in the R&D Tax Credit Automation system.

## Overview

The health check module provides:
- Individual API health checks (Clockify, Unified.to, You.com, GLM 4.5 Air)
- Batch health checks for all APIs
- Startup health verification
- Health status reporting
- Async and sync interfaces

## Health Status Levels

- **healthy**: API is accessible and authentication is valid
- **degraded**: API is accessible but experiencing issues (slow response, partial failures)
- **down**: API is not accessible or authentication failed

## Quick Start

### Check All APIs

```python
from tools.health_check import check_all_apis, print_health_report

# Check all APIs
results = check_all_apis()

# Print formatted report
print_health_report(results)
```

### Check Single API

```python
from tools.health_check import check_api_health

# Check Clockify
result = check_api_health('clockify')
print(f"Clockify: {result.status}")
print(f"Response time: {result.response_time:.2f}s")
```

### Startup Health Check

```python
from tools.health_check import startup_health_check

# Check on application startup
if not startup_health_check(fail_on_error=False):
    print("Warning: Some APIs are not available")
```

## API Reference

### Individual Health Checks

#### `check_clockify_health(api_key=None, workspace_id=None, timeout=10.0)`

Check Clockify API health.

**Parameters:**
- `api_key` (str, optional): Clockify API key (defaults to config)
- `workspace_id` (str, optional): Clockify workspace ID (defaults to config)
- `timeout` (float): Request timeout in seconds (default: 10.0)

**Returns:** `HealthCheckResult`

**Example:**
```python
result = check_clockify_health()
if result.status == HealthStatus.HEALTHY:
    print(f"Clockify is ready! ({result.response_time:.2f}s)")
```

#### `check_unified_to_health(api_key=None, workspace_id=None, timeout=10.0)`

Check Unified.to API health.

**Parameters:**
- `api_key` (str, optional): Unified.to API key (defaults to config)
- `workspace_id` (str, optional): Unified.to workspace ID (defaults to config)
- `timeout` (float): Request timeout in seconds (default: 10.0)

**Returns:** `HealthCheckResult`

#### `check_youcom_health(api_key=None, timeout=15.0)`

Check You.com API health.

**Parameters:**
- `api_key` (str, optional): You.com API key (defaults to config)
- `timeout` (float): Request timeout in seconds (default: 15.0)

**Returns:** `HealthCheckResult`

#### `check_glm_health(api_key=None, timeout=15)` (async)

Check GLM 4.5 Air (via OpenRouter) health.

**Parameters:**
- `api_key` (str, optional): OpenRouter API key (defaults to config)
- `timeout` (int): Request timeout in seconds (default: 15)

**Returns:** `HealthCheckResult`

**Example:**
```python
import asyncio

async def check():
    result = await check_glm_health()
    print(f"GLM 4.5 Air: {result.status}")

asyncio.run(check())
```

### Batch Health Checks

#### `check_api_health(api_name, **kwargs)`

Check health of a specific API by name.

**Parameters:**
- `api_name` (str): Name of API to check ('clockify', 'unified_to', 'youcom', 'glm')
- `**kwargs`: Additional arguments passed to specific health check function

**Returns:** `HealthCheckResult`

**Example:**
```python
# Check with custom timeout
result = check_api_health('youcom', timeout=20.0)
```

#### `check_all_apis(include_apis=None, parallel=True)`

Check health of all APIs (synchronous).

**Parameters:**
- `include_apis` (List[str], optional): List of API names to check (None = check all)
- `parallel` (bool): Run checks in parallel (default: True)

**Returns:** `Dict[str, HealthCheckResult]`

**Example:**
```python
# Check all APIs
results = check_all_apis()

# Check specific APIs
results = check_all_apis(include_apis=['clockify', 'youcom'])

# Check sequentially
results = check_all_apis(parallel=False)
```

#### `check_all_apis_async(include_apis=None, parallel=True)` (async)

Check health of all APIs asynchronously.

**Parameters:**
- `include_apis` (List[str], optional): List of API names to check (None = check all)
- `parallel` (bool): Run checks in parallel (default: True)

**Returns:** `Dict[str, HealthCheckResult]`

**Example:**
```python
import asyncio

async def check():
    results = await check_all_apis_async()
    for api_name, result in results.items():
        print(f"{api_name}: {result.status}")

asyncio.run(check())
```

### Utility Functions

#### `get_overall_health_status(results)`

Get overall health status from individual check results.

**Parameters:**
- `results` (Dict[str, HealthCheckResult]): Dictionary of health check results

**Returns:** `str` - Overall status: 'healthy', 'degraded', or 'down'

**Logic:**
- If any API is down: overall status is 'down'
- If any API is degraded: overall status is 'degraded'
- If all APIs are healthy: overall status is 'healthy'

**Example:**
```python
results = check_all_apis()
overall = get_overall_health_status(results)
print(f"Overall: {overall}")
```

#### `print_health_report(results)`

Print a formatted health check report.

**Parameters:**
- `results` (Dict[str, HealthCheckResult]): Dictionary of health check results

**Example:**
```python
results = check_all_apis()
print_health_report(results)
```

**Output:**
```
API Health Check Report
==================================================
✓ Clockify: healthy (125ms)
✓ Unified.to: healthy (234ms)
✓ You.com: healthy (456ms)
✓ GLM 4.5 Air: healthy (789ms)
==================================================
Overall Status: ✓ All systems operational
```

#### `startup_health_check(required_apis=None, fail_on_error=False)`

Perform health check on application startup.

**Parameters:**
- `required_apis` (List[str], optional): List of APIs that must be healthy (None = all APIs)
- `fail_on_error` (bool): Raise exception if any required API is down (default: False)

**Returns:** `bool` - True if all required APIs are healthy, False otherwise

**Raises:** `RuntimeError` - If fail_on_error=True and any required API is down

**Example:**
```python
# Warn on failure
if not startup_health_check():
    print("Warning: Some APIs are not available")

# Fail fast on failure
try:
    startup_health_check(fail_on_error=True)
except RuntimeError as e:
    print(f"Startup failed: {e}")
    sys.exit(1)

# Check only required APIs
startup_health_check(required_apis=['clockify', 'youcom'])
```

## HealthCheckResult Class

Container for health check results.

### Attributes

- `api_name` (str): Name of the API being checked
- `status` (str): Health status ('healthy', 'degraded', 'down')
- `response_time` (float): Response time in seconds
- `message` (str): Human-readable status message
- `details` (Dict[str, Any]): Additional details about the check
- `timestamp` (datetime): When the check was performed
- `error` (str, optional): Error message if check failed

### Methods

#### `to_dict()`

Convert to dictionary representation.

**Returns:** `Dict[str, Any]`

**Example:**
```python
result = check_api_health('clockify')
result_dict = result.to_dict()

# Convert to JSON
import json
json_str = json.dumps(result_dict, default=str)
```

## Usage Patterns

### Application Startup

```python
from tools.health_check import startup_health_check

def main():
    # Check APIs on startup
    if not startup_health_check(fail_on_error=False):
        logger.warning("Some APIs are not available")
    
    # Start application
    app.run()
```

### Conditional Feature Enablement

```python
from tools.health_check import check_api_health, HealthStatus

# Check if You.com is available
youcom_result = check_api_health('youcom')

if youcom_result.status == HealthStatus.HEALTHY:
    # Enable You.com features
    enable_youcom_features()
else:
    # Disable You.com features
    logger.warning(f"You.com unavailable: {youcom_result.message}")
    disable_youcom_features()
```

### Monitoring Loop

```python
import time
from tools.health_check import check_all_apis, get_overall_health_status

def monitor_apis(interval=60):
    """Monitor API health every 60 seconds."""
    while True:
        results = check_all_apis()
        overall = get_overall_health_status(results)
        
        if overall != HealthStatus.HEALTHY:
            logger.warning(f"API health degraded: {overall}")
            
            # Alert on specific failures
            for api_name, result in results.items():
                if result.status != HealthStatus.HEALTHY:
                    logger.error(f"{api_name}: {result.message}")
        
        time.sleep(interval)
```

### Health Check Endpoint (FastAPI)

```python
from fastapi import FastAPI
from tools.health_check import check_all_apis

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    results = check_all_apis()
    
    return {
        "status": get_overall_health_status(results),
        "apis": {
            name: result.to_dict()
            for name, result in results.items()
        }
    }
```

## Performance Considerations

### Response Time Thresholds

The health check module uses the following thresholds to determine degraded status:

- **Clockify**: > 5 seconds
- **Unified.to**: > 5 seconds
- **You.com**: > 8 seconds
- **GLM 4.5 Air**: > 10 seconds

### Parallel vs Sequential

**Parallel (default):**
- Faster overall execution
- All checks run simultaneously
- Recommended for most use cases

**Sequential:**
- Slower overall execution
- Checks run one at a time
- Useful for debugging or rate limit concerns

```python
# Parallel (fast)
results = check_all_apis(parallel=True)  # ~2-3 seconds

# Sequential (slow)
results = check_all_apis(parallel=False)  # ~10-15 seconds
```

### Custom Timeouts

Adjust timeouts based on your requirements:

```python
# Faster failure detection (5s timeout)
result = check_api_health('youcom', timeout=5.0)

# More patient (30s timeout)
result = check_api_health('glm', timeout=30)
```

## Error Handling

### Common Errors

**401 Unauthorized:**
```python
result = check_api_health('clockify')
if result.status == HealthStatus.DOWN and "authentication" in result.message.lower():
    print("Invalid API key. Check your .env file.")
```

**429 Rate Limit:**
```python
result = check_api_health('youcom')
if "rate limit" in result.message.lower():
    print("Rate limit exceeded. Wait before retrying.")
```

**Timeout:**
```python
result = check_api_health('glm', timeout=5.0)
if result.response_time >= 5.0:
    print("API is slow or unresponsive")
```

### Graceful Degradation

```python
from tools.health_check import check_all_apis, HealthStatus

results = check_all_apis()

# Determine available features
features = {
    'time_tracking': results['clockify'].status == HealthStatus.HEALTHY,
    'payroll': results['unified_to'].status == HealthStatus.HEALTHY,
    'ai_reasoning': results['youcom'].status == HealthStatus.HEALTHY,
    'rag_inference': results['glm'].status == HealthStatus.HEALTHY,
}

# Start with available features
start_application(features)
```

## Testing

The health check module includes comprehensive tests:

```bash
# Run health check tests
pytest tests/test_health_check.py -v

# Run with coverage
pytest tests/test_health_check.py --cov=tools.health_check --cov-report=html
```

## Integration with Application

### main.py Integration

```python
from tools.health_check import startup_health_check
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """Application entry point."""
    logger.info("Starting R&D Tax Credit Automation Agent...")
    
    # Perform startup health check
    try:
        if not startup_health_check(fail_on_error=True):
            logger.error("Startup health check failed")
            return 1
    except RuntimeError as e:
        logger.error(f"Critical APIs unavailable: {e}")
        return 1
    
    logger.info("All APIs healthy. Starting application...")
    
    # Start application
    app.run()
    
    return 0

if __name__ == "__main__":
    exit(main())
```

## Troubleshooting

### Health Check Always Fails

1. **Check API credentials:**
   ```bash
   # Verify .env file
   cat .env | grep API_KEY
   ```

2. **Test connectivity:**
   ```python
   from tools.health_check import check_api_health
   
   result = check_api_health('clockify')
   print(f"Error: {result.error}")
   print(f"Details: {result.details}")
   ```

3. **Check network:**
   ```bash
   # Test network connectivity
   curl -I https://api.clockify.me
   curl -I https://api.you.com
   ```

### Slow Health Checks

1. **Use custom timeouts:**
   ```python
   # Reduce timeout for faster failure
   result = check_api_health('youcom', timeout=5.0)
   ```

2. **Check specific APIs:**
   ```python
   # Only check critical APIs
   results = check_all_apis(include_apis=['clockify', 'youcom'])
   ```

3. **Use parallel mode:**
   ```python
   # Ensure parallel mode is enabled
   results = check_all_apis(parallel=True)
   ```

## See Also

- [API Connectors README](./API_CONNECTORS_README.md)
- [You.com Client README](./YOUCOM_CLIENT_README.md)
- [GLM Reasoner README](./GLM_REASONER_README.md)
- [Configuration Guide](../utils/CONFIG_README.md)
