# Performance Monitoring and Metrics Tracking

This module provides comprehensive performance monitoring and metrics tracking for the R&D Tax Credit Automation Agent.

## Features

### 1. Timing Decorator
Track execution time of any function with a simple decorator:

```python
from utils.metrics import timing_decorator

@timing_decorator()
def my_function():
    # Your code here
    pass

# With memory tracking
@timing_decorator(track_memory=True)
def memory_intensive_function():
    # Your code here
    pass

# With custom metadata
@timing_decorator(metadata={'stage': 'ingestion', 'source': 'api'})
def fetch_data():
    # Your code here
    pass
```

### 2. Context Manager for Code Blocks
Track performance of specific code blocks:

```python
from utils.metrics import track_execution_time

with track_execution_time('data_processing', track_memory=True):
    # Your code block here
    process_data()
```

### 3. Memory Usage Tracking
Monitor memory consumption during execution:

```python
from utils.metrics import MemoryTracker

MemoryTracker.start_tracking()

# Your code here
data = [0] * 1000000

# Get current memory usage
current = MemoryTracker.get_current_memory()  # Returns MB
peak = MemoryTracker.get_peak_memory()  # Returns MB

# Get snapshot
snapshot = MemoryTracker.get_memory_snapshot()
# Returns: {'current': 10.5, 'peak': 15.2}

# Log memory usage
MemoryTracker.log_memory_usage("After processing")

MemoryTracker.stop_tracking()
```

### 4. Agent-Specific Metrics
Track performance of agent executions:

```python
from utils.metrics import AgentMetrics

@AgentMetrics.track_agent_execution('data_ingestion', track_memory=True)
def run_data_ingestion_agent():
    # Agent logic here
    pass

# Get agent statistics
stats = AgentMetrics.get_agent_statistics('data_ingestion')
# Returns: {
#     'count': 5,
#     'total_time': 25.5,
#     'avg_time': 5.1,
#     'min_time': 4.8,
#     'max_time': 5.5,
#     'success_rate': 1.0
# }

# Log agent summary
AgentMetrics.log_agent_summary('data_ingestion')
```

### 5. Metrics Collection and Analysis
Access and analyze collected metrics:

```python
from utils.metrics import get_metrics_collector, log_performance_summary

# Get the global metrics collector
collector = get_metrics_collector()

# Get all metrics
all_metrics = collector.get_metrics()

# Get metrics for specific function
function_metrics = collector.get_metrics(function_name='my_function')

# Get metrics for specific agent
agent_metrics = collector.get_metrics(agent_name='data_ingestion')

# Get statistics
stats = collector.get_statistics()

# Log overall performance summary
log_performance_summary()

# Export metrics to JSON
from pathlib import Path
output_file = Path('outputs/metrics.json')
collector.export_metrics(output_file)

# Clear all metrics
collector.clear_metrics()
```

## Data Structures

### ExecutionMetric
Each metric contains:
- `function_name`: Name of the function/operation
- `execution_time`: Time taken in seconds
- `timestamp`: When the execution occurred
- `memory_used`: Memory used in MB (optional)
- `success`: Whether execution completed successfully
- `error_message`: Error message if failed (optional)
- `metadata`: Custom metadata dictionary

## Integration with Logging

All metrics are automatically logged using the application's logging infrastructure:
- Successful executions: INFO level
- Failed executions: WARNING level
- Memory tracking warnings: WARNING level

## Performance Targets

Based on requirements (8.5), the system tracks:
- Function execution times
- Memory usage during operations
- Agent execution times
- Success rates

## Example Usage

See `examples/metrics_usage_example.py` for comprehensive examples of all features.

## Testing

Run tests with:
```bash
pytest tests/test_metrics.py -v
```

All 25 tests should pass with 88%+ code coverage for the metrics module.

## Best Practices

1. **Use decorators for functions**: Simplest way to track performance
2. **Use context managers for code blocks**: When you need to track specific sections
3. **Enable memory tracking selectively**: Only when needed, as it adds overhead
4. **Add metadata for context**: Helps with filtering and analysis later
5. **Export metrics regularly**: For long-running processes, export periodically
6. **Clear metrics when appropriate**: Prevent memory buildup in long-running applications

## Requirements Satisfied

This implementation satisfies requirement 8.5:
- ✅ Timing decorator for function execution time
- ✅ Memory usage tracker
- ✅ Metrics logging for agent execution times
- ✅ Performance statistics and analysis
- ✅ Export capabilities for metrics data
