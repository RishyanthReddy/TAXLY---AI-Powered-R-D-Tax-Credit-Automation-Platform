"""
Performance monitoring and metrics tracking for the R&D Tax Credit Automation Agent.

This module provides utilities for tracking and logging performance metrics including:
- Function execution time tracking with decorators
- Memory usage monitoring
- Agent execution time metrics
- Performance statistics aggregation
"""

import functools
import logging
import time
import tracemalloc
from contextlib import contextmanager
from datetime import datetime
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json

from .logger import AgentLogger


# Configure logger for metrics
logger = AgentLogger.get_logger("utils.metrics")


@dataclass
class ExecutionMetric:
    """
    Data class for storing execution metrics.
    
    Attributes:
        function_name: Name of the function being measured
        execution_time: Time taken to execute in seconds
        timestamp: When the execution occurred
        memory_used: Memory used during execution in MB (optional)
        success: Whether the execution completed successfully
        error_message: Error message if execution failed (optional)
        metadata: Additional metadata about the execution
    """
    function_name: str
    execution_time: float
    timestamp: datetime
    memory_used: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary for serialization."""
        return {
            'function_name': self.function_name,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat(),
            'memory_used': self.memory_used,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata
        }


class MetricsCollector:
    """
    Centralized metrics collection and storage.
    
    Collects and stores performance metrics for analysis and monitoring.
    Provides methods for querying and exporting metrics.
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self._metrics: List[ExecutionMetric] = []
        self._agent_metrics: Dict[str, List[ExecutionMetric]] = {}
    
    def add_metric(self, metric: ExecutionMetric) -> None:
        """
        Add a metric to the collection.
        
        Args:
            metric: ExecutionMetric instance to add
        """
        self._metrics.append(metric)
        
        # Log the metric
        log_message = (
            f"Performance: {metric.function_name} completed in "
            f"{metric.execution_time:.3f}s"
        )
        
        if metric.memory_used is not None:
            log_message += f" (Memory: {metric.memory_used:.2f} MB)"
        
        if metric.success:
            logger.info(log_message)
        else:
            logger.warning(f"{log_message} - Failed: {metric.error_message}")
    
    def add_agent_metric(self, agent_name: str, metric: ExecutionMetric) -> None:
        """
        Add a metric for a specific agent.
        
        Args:
            agent_name: Name of the agent (e.g., 'data_ingestion', 'qualification')
            metric: ExecutionMetric instance to add
        """
        if agent_name not in self._agent_metrics:
            self._agent_metrics[agent_name] = []
        
        self._agent_metrics[agent_name].append(metric)
        self.add_metric(metric)
    
    def get_metrics(
        self,
        function_name: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> List[ExecutionMetric]:
        """
        Get metrics filtered by function name or agent name.
        
        Args:
            function_name: Filter by function name (optional)
            agent_name: Filter by agent name (optional)
        
        Returns:
            List of matching ExecutionMetric instances
        """
        if agent_name:
            metrics = self._agent_metrics.get(agent_name, [])
        else:
            metrics = self._metrics
        
        if function_name:
            metrics = [m for m in metrics if m.function_name == function_name]
        
        return metrics
    
    def get_statistics(
        self,
        function_name: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistical summary of metrics.
        
        Args:
            function_name: Filter by function name (optional)
            agent_name: Filter by agent name (optional)
        
        Returns:
            Dictionary containing statistical summary
        """
        metrics = self.get_metrics(function_name, agent_name)
        
        if not metrics:
            return {
                'count': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'min_time': 0.0,
                'max_time': 0.0,
                'success_rate': 0.0
            }
        
        execution_times = [m.execution_time for m in metrics]
        successful = sum(1 for m in metrics if m.success)
        
        return {
            'count': len(metrics),
            'total_time': sum(execution_times),
            'avg_time': sum(execution_times) / len(execution_times),
            'min_time': min(execution_times),
            'max_time': max(execution_times),
            'success_rate': successful / len(metrics) if metrics else 0.0
        }
    
    def export_metrics(self, filepath: Path) -> None:
        """
        Export all metrics to a JSON file.
        
        Args:
            filepath: Path to the output JSON file
        """
        data = {
            'exported_at': datetime.now().isoformat(),
            'total_metrics': len(self._metrics),
            'metrics': [m.to_dict() for m in self._metrics],
            'agent_metrics': {
                agent: [m.to_dict() for m in metrics]
                for agent, metrics in self._agent_metrics.items()
            }
        }
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(self._metrics)} metrics to {filepath}")
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self._metrics.clear()
        self._agent_metrics.clear()
        logger.info("Cleared all metrics")


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        Global MetricsCollector instance
    """
    return _metrics_collector


def timing_decorator(
    track_memory: bool = False,
    metadata: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    Decorator to measure and log function execution time.
    
    This decorator tracks how long a function takes to execute and optionally
    monitors memory usage. Results are logged and stored in the metrics collector.
    
    Args:
        track_memory: If True, also track memory usage during execution
        metadata: Optional metadata to attach to the metric
    
    Returns:
        Decorated function with timing instrumentation
    
    Example:
        >>> @timing_decorator()
        ... def process_data(data):
        ...     # Process data
        ...     return result
        
        >>> @timing_decorator(track_memory=True, metadata={'stage': 'ingestion'})
        ... def fetch_api_data():
        ...     # Fetch data from API
        ...     return data
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            function_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            memory_used = None
            success = True
            error_message = None
            
            # Start memory tracking if requested
            if track_memory:
                tracemalloc.start()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                return result
            
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            
            finally:
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Get memory usage if tracking
                if track_memory:
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    memory_used = peak / (1024 * 1024)  # Convert to MB
                
                # Create and store metric
                metric = ExecutionMetric(
                    function_name=function_name,
                    execution_time=execution_time,
                    timestamp=datetime.now(),
                    memory_used=memory_used,
                    success=success,
                    error_message=error_message,
                    metadata=metadata or {}
                )
                
                _metrics_collector.add_metric(metric)
        
        return wrapper
    return decorator


@contextmanager
def track_execution_time(
    operation_name: str,
    track_memory: bool = False,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Context manager for tracking execution time of code blocks.
    
    This context manager allows tracking performance of arbitrary code blocks
    without using a decorator. Useful for measuring specific sections of code.
    
    Args:
        operation_name: Name to identify this operation in metrics
        track_memory: If True, also track memory usage
        metadata: Optional metadata to attach to the metric
    
    Yields:
        None
    
    Example:
        >>> with track_execution_time('data_processing', track_memory=True):
        ...     # Process large dataset
        ...     result = process_large_dataset(data)
    """
    start_time = time.time()
    memory_used = None
    success = True
    error_message = None
    
    # Start memory tracking if requested
    if track_memory:
        tracemalloc.start()
    
    try:
        yield
    
    except Exception as e:
        success = False
        error_message = str(e)
        raise
    
    finally:
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Get memory usage if tracking
        if track_memory:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            memory_used = peak / (1024 * 1024)  # Convert to MB
        
        # Create and store metric
        metric = ExecutionMetric(
            function_name=operation_name,
            execution_time=execution_time,
            timestamp=datetime.now(),
            memory_used=memory_used,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        _metrics_collector.add_metric(metric)


class MemoryTracker:
    """
    Utility class for tracking memory usage.
    
    Provides methods for monitoring memory consumption during application execution.
    """
    
    @staticmethod
    def start_tracking() -> None:
        """Start tracking memory allocations."""
        tracemalloc.start()
        logger.debug("Started memory tracking")
    
    @staticmethod
    def stop_tracking() -> None:
        """Stop tracking memory allocations."""
        tracemalloc.stop()
        logger.debug("Stopped memory tracking")
    
    @staticmethod
    def get_current_memory() -> float:
        """
        Get current memory usage in MB.
        
        Returns:
            Current memory usage in megabytes
        """
        if not tracemalloc.is_tracing():
            logger.warning("Memory tracking not started. Call start_tracking() first.")
            return 0.0
        
        current, peak = tracemalloc.get_traced_memory()
        return current / (1024 * 1024)  # Convert to MB
    
    @staticmethod
    def get_peak_memory() -> float:
        """
        Get peak memory usage in MB since tracking started.
        
        Returns:
            Peak memory usage in megabytes
        """
        if not tracemalloc.is_tracing():
            logger.warning("Memory tracking not started. Call start_tracking() first.")
            return 0.0
        
        current, peak = tracemalloc.get_traced_memory()
        return peak / (1024 * 1024)  # Convert to MB
    
    @staticmethod
    def get_memory_snapshot() -> Dict[str, float]:
        """
        Get a snapshot of current and peak memory usage.
        
        Returns:
            Dictionary with 'current' and 'peak' memory in MB
        """
        if not tracemalloc.is_tracing():
            logger.warning("Memory tracking not started. Call start_tracking() first.")
            return {'current': 0.0, 'peak': 0.0}
        
        current, peak = tracemalloc.get_traced_memory()
        return {
            'current': current / (1024 * 1024),
            'peak': peak / (1024 * 1024)
        }
    
    @staticmethod
    def log_memory_usage(label: str = "Memory Usage") -> None:
        """
        Log current memory usage.
        
        Args:
            label: Label for the log message
        """
        snapshot = MemoryTracker.get_memory_snapshot()
        logger.info(
            f"{label}: Current={snapshot['current']:.2f} MB, "
            f"Peak={snapshot['peak']:.2f} MB"
        )


class AgentMetrics:
    """
    Specialized metrics tracking for agent execution.
    
    Provides methods for tracking agent-specific performance metrics including
    execution time, success rates, and stage-specific timings.
    """
    
    @staticmethod
    def track_agent_execution(
        agent_name: str,
        track_memory: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Callable:
        """
        Decorator for tracking agent execution metrics.
        
        Args:
            agent_name: Name of the agent (e.g., 'data_ingestion', 'qualification')
            track_memory: If True, track memory usage
            metadata: Optional metadata to attach to the metric
        
        Returns:
            Decorated function with agent-specific metrics tracking
        
        Example:
            >>> @AgentMetrics.track_agent_execution('data_ingestion')
            ... def run_data_ingestion():
            ...     # Agent logic
            ...     pass
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                function_name = f"agent.{agent_name}.{func.__name__}"
                start_time = time.time()
                memory_used = None
                success = True
                error_message = None
                
                # Start memory tracking if requested
                if track_memory:
                    tracemalloc.start()
                
                try:
                    # Execute the agent function
                    result = func(*args, **kwargs)
                    return result
                
                except Exception as e:
                    success = False
                    error_message = str(e)
                    raise
                
                finally:
                    # Calculate execution time
                    execution_time = time.time() - start_time
                    
                    # Get memory usage if tracking
                    if track_memory:
                        current, peak = tracemalloc.get_traced_memory()
                        tracemalloc.stop()
                        memory_used = peak / (1024 * 1024)  # Convert to MB
                    
                    # Create and store metric
                    metric = ExecutionMetric(
                        function_name=function_name,
                        execution_time=execution_time,
                        timestamp=datetime.now(),
                        memory_used=memory_used,
                        success=success,
                        error_message=error_message,
                        metadata=metadata or {}
                    )
                    
                    _metrics_collector.add_agent_metric(agent_name, metric)
            
            return wrapper
        return decorator
    
    @staticmethod
    def get_agent_statistics(agent_name: str) -> Dict[str, Any]:
        """
        Get performance statistics for a specific agent.
        
        Args:
            agent_name: Name of the agent
        
        Returns:
            Dictionary containing agent performance statistics
        """
        return _metrics_collector.get_statistics(agent_name=agent_name)
    
    @staticmethod
    def log_agent_summary(agent_name: str) -> None:
        """
        Log a summary of agent performance metrics.
        
        Args:
            agent_name: Name of the agent
        """
        stats = AgentMetrics.get_agent_statistics(agent_name)
        
        if stats['count'] == 0:
            logger.info(f"No metrics available for agent: {agent_name}")
            return
        
        logger.info(
            f"Agent '{agent_name}' Performance Summary:\n"
            f"  Executions: {stats['count']}\n"
            f"  Total Time: {stats['total_time']:.2f}s\n"
            f"  Average Time: {stats['avg_time']:.2f}s\n"
            f"  Min Time: {stats['min_time']:.2f}s\n"
            f"  Max Time: {stats['max_time']:.2f}s\n"
            f"  Success Rate: {stats['success_rate']:.1%}"
        )


# Convenience functions
def log_performance_summary() -> None:
    """Log a summary of all performance metrics."""
    stats = _metrics_collector.get_statistics()
    
    if stats['count'] == 0:
        logger.info("No performance metrics available")
        return
    
    logger.info(
        f"Overall Performance Summary:\n"
        f"  Total Operations: {stats['count']}\n"
        f"  Total Time: {stats['total_time']:.2f}s\n"
        f"  Average Time: {stats['avg_time']:.2f}s\n"
        f"  Min Time: {stats['min_time']:.2f}s\n"
        f"  Max Time: {stats['max_time']:.2f}s\n"
        f"  Success Rate: {stats['success_rate']:.1%}"
    )


__all__ = [
    'ExecutionMetric',
    'MetricsCollector',
    'get_metrics_collector',
    'timing_decorator',
    'track_execution_time',
    'MemoryTracker',
    'AgentMetrics',
    'log_performance_summary'
]
