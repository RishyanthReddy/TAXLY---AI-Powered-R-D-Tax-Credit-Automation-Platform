"""
You.com API Monitoring

This module provides comprehensive monitoring for You.com API usage including:
- API call counts per endpoint
- Response times for each API
- Error rates and types
- Usage statistics for cost tracking
- Alerts on repeated failures

The monitor integrates with YouComClient to track all API interactions
and provides detailed statistics and alerting capabilities.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from pathlib import Path
import json

from utils.logger import get_tool_logger


# Get logger for API monitor
logger = get_tool_logger("youcom_api_monitor")


@dataclass
class APICallMetric:
    """
    Data class for storing individual API call metrics.
    
    Attributes:
        endpoint: API endpoint name (search, agent, contents, express_agent, news)
        timestamp: When the call was made
        response_time: Time taken for the API call in seconds
        success: Whether the call succeeded
        status_code: HTTP status code (if applicable)
        error_type: Type of error if call failed (optional)
        error_message: Error message if call failed (optional)
        cached: Whether the result was served from cache
        wait_time: Time spent waiting for rate limit (seconds)
    """
    endpoint: str
    timestamp: datetime
    response_time: float
    success: bool
    status_code: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    cached: bool = False
    wait_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary for serialization."""
        return {
            'endpoint': self.endpoint,
            'timestamp': self.timestamp.isoformat(),
            'response_time': self.response_time,
            'success': self.success,
            'status_code': self.status_code,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'cached': self.cached,
            'wait_time': self.wait_time
        }


@dataclass
class EndpointStatistics:
    """
    Statistics for a specific API endpoint.
    
    Attributes:
        endpoint: Endpoint name
        total_calls: Total number of API calls
        successful_calls: Number of successful calls
        failed_calls: Number of failed calls
        cached_calls: Number of calls served from cache
        total_response_time: Sum of all response times
        total_wait_time: Sum of all rate limit wait times
        min_response_time: Minimum response time
        max_response_time: Maximum response time
        error_counts: Count of errors by type
        recent_errors: Recent error messages (last 10)
        last_call_time: Timestamp of last API call
        consecutive_failures: Number of consecutive failures
    """
    endpoint: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    cached_calls: int = 0
    total_response_time: float = 0.0
    total_wait_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=10))
    last_call_time: Optional[datetime] = None
    consecutive_failures: int = 0
    
    def update(self, metric: APICallMetric):
        """
        Update statistics with a new metric.
        
        Args:
            metric: APICallMetric to incorporate into statistics
        """
        self.total_calls += 1
        self.last_call_time = metric.timestamp
        
        if metric.cached:
            self.cached_calls += 1
        
        if metric.success:
            self.successful_calls += 1
            self.consecutive_failures = 0
        else:
            self.failed_calls += 1
            self.consecutive_failures += 1
            
            # Track error type
            if metric.error_type:
                self.error_counts[metric.error_type] += 1
            
            # Store recent error
            error_info = {
                'timestamp': metric.timestamp.isoformat(),
                'error_type': metric.error_type,
                'error_message': metric.error_message,
                'status_code': metric.status_code
            }
            self.recent_errors.append(error_info)
        
        # Update response time statistics
        if metric.response_time > 0:
            self.total_response_time += metric.response_time
            self.min_response_time = min(self.min_response_time, metric.response_time)
            self.max_response_time = max(self.max_response_time, metric.response_time)
        
        # Update wait time
        if metric.wait_time > 0:
            self.total_wait_time += metric.wait_time
    
    def get_average_response_time(self) -> float:
        """Get average response time for successful calls."""
        if self.successful_calls == 0:
            return 0.0
        return self.total_response_time / self.successful_calls
    
    def get_error_rate(self) -> float:
        """Get error rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.failed_calls / self.total_calls) * 100.0
    
    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate as a percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.cached_calls / self.total_calls) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            'endpoint': self.endpoint,
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'cached_calls': self.cached_calls,
            'average_response_time': self.get_average_response_time(),
            'min_response_time': self.min_response_time if self.min_response_time != float('inf') else 0.0,
            'max_response_time': self.max_response_time,
            'total_wait_time': self.total_wait_time,
            'error_rate': self.get_error_rate(),
            'cache_hit_rate': self.get_cache_hit_rate(),
            'error_counts': dict(self.error_counts),
            'recent_errors': list(self.recent_errors),
            'last_call_time': self.last_call_time.isoformat() if self.last_call_time else None,
            'consecutive_failures': self.consecutive_failures
        }


class YouComAPIMonitor:
    """
    Monitor for You.com API usage and performance.
    
    This class tracks all You.com API calls, response times, errors, and provides
    alerting capabilities for repeated failures. It integrates with YouComClient
    to provide comprehensive monitoring.
    
    Features:
    - Per-endpoint call tracking
    - Response time monitoring
    - Error rate tracking
    - Cost estimation based on usage
    - Automatic alerting on repeated failures
    - Statistics export for analysis
    """
    
    # Alert thresholds
    DEFAULT_FAILURE_THRESHOLD = 3  # Alert after 3 consecutive failures
    DEFAULT_ERROR_RATE_THRESHOLD = 50.0  # Alert if error rate exceeds 50%
    DEFAULT_SLOW_RESPONSE_THRESHOLD = 30.0  # Alert if response time exceeds 30s
    
    def __init__(
        self,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        error_rate_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
        slow_response_threshold: float = DEFAULT_SLOW_RESPONSE_THRESHOLD,
        enable_alerts: bool = True
    ):
        """
        Initialize You.com API monitor.
        
        Args:
            failure_threshold: Number of consecutive failures before alerting (default: 3)
            error_rate_threshold: Error rate percentage threshold for alerting (default: 50.0)
            slow_response_threshold: Response time threshold in seconds for alerting (default: 30.0)
            enable_alerts: Enable automatic alerting (default: True)
        
        Example:
            >>> monitor = YouComAPIMonitor()
            >>> # Monitor will automatically track API calls when integrated with YouComClient
            >>> 
            >>> # With custom thresholds
            >>> monitor = YouComAPIMonitor(
            ...     failure_threshold=5,
            ...     error_rate_threshold=25.0,
            ...     slow_response_threshold=60.0
            ... )
        """
        self.failure_threshold = failure_threshold
        self.error_rate_threshold = error_rate_threshold
        self.slow_response_threshold = slow_response_threshold
        self.enable_alerts = enable_alerts
        
        # Statistics storage
        self.endpoint_stats: Dict[str, EndpointStatistics] = {}
        self.all_metrics: List[APICallMetric] = []
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Monitoring start time
        self.start_time = datetime.now()
        
        logger.info(
            f"Initialized You.com API monitor "
            f"(failure_threshold={failure_threshold}, "
            f"error_rate_threshold={error_rate_threshold}%, "
            f"slow_response_threshold={slow_response_threshold}s, "
            f"alerts_enabled={enable_alerts})"
        )
    
    def record_api_call(
        self,
        endpoint: str,
        response_time: float,
        success: bool,
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        cached: bool = False,
        wait_time: float = 0.0
    ):
        """
        Record an API call for monitoring.
        
        This method should be called after each You.com API call to track
        performance and errors.
        
        Args:
            endpoint: API endpoint name (search, agent, contents, express_agent, news)
            response_time: Time taken for the API call in seconds
            success: Whether the call succeeded
            status_code: HTTP status code (if applicable)
            error_type: Type of error if call failed (e.g., "APIConnectionError")
            error_message: Error message if call failed
            cached: Whether the result was served from cache
            wait_time: Time spent waiting for rate limit (seconds)
        
        Example:
            >>> monitor = YouComAPIMonitor()
            >>> 
            >>> # Record successful call
            >>> monitor.record_api_call(
            ...     endpoint='search',
            ...     response_time=1.5,
            ...     success=True,
            ...     status_code=200
            ... )
            >>> 
            >>> # Record failed call
            >>> monitor.record_api_call(
            ...     endpoint='agent',
            ...     response_time=0.5,
            ...     success=False,
            ...     status_code=429,
            ...     error_type='RateLimitError',
            ...     error_message='Rate limit exceeded'
            ... )
        """
        with self.lock:
            # Create metric
            metric = APICallMetric(
                endpoint=endpoint,
                timestamp=datetime.now(),
                response_time=response_time,
                success=success,
                status_code=status_code,
                error_type=error_type,
                error_message=error_message,
                cached=cached,
                wait_time=wait_time
            )
            
            # Store metric
            self.all_metrics.append(metric)
            
            # Update endpoint statistics
            if endpoint not in self.endpoint_stats:
                self.endpoint_stats[endpoint] = EndpointStatistics(endpoint=endpoint)
            
            self.endpoint_stats[endpoint].update(metric)
            
            # Check for alerts
            if self.enable_alerts:
                self._check_alerts(endpoint, metric)
    
    def _check_alerts(self, endpoint: str, metric: APICallMetric):
        """
        Check if any alert conditions are met.
        
        Args:
            endpoint: Endpoint that was called
            metric: Metric for the call
        """
        stats = self.endpoint_stats[endpoint]
        
        # Alert on consecutive failures
        if stats.consecutive_failures >= self.failure_threshold:
            logger.error(
                f"[ALERT] You.com API: {endpoint} has {stats.consecutive_failures} "
                f"consecutive failures (threshold: {self.failure_threshold})\n"
                f"Last error: {metric.error_type} - {metric.error_message}\n"
                f"Recommendation: Check API key, network connectivity, and You.com status"
            )
        
        # Alert on high error rate (only if we have enough samples)
        if stats.total_calls >= 10:
            error_rate = stats.get_error_rate()
            if error_rate >= self.error_rate_threshold:
                logger.warning(
                    f"[ALERT] You.com API: {endpoint} has high error rate "
                    f"({error_rate:.1f}%, threshold: {self.error_rate_threshold}%)\n"
                    f"Total calls: {stats.total_calls}, Failed: {stats.failed_calls}\n"
                    f"Top errors: {self._get_top_errors(stats)}\n"
                    f"Recommendation: Review error patterns and adjust usage"
                )
        
        # Alert on slow response
        if metric.success and metric.response_time >= self.slow_response_threshold:
            logger.warning(
                f"[ALERT] You.com API: {endpoint} slow response "
                f"({metric.response_time:.1f}s, threshold: {self.slow_response_threshold}s)\n"
                f"This may indicate API performance issues or network latency\n"
                f"Recommendation: Monitor for continued slow responses"
            )
    
    def _get_top_errors(self, stats: EndpointStatistics, top_n: int = 3) -> str:
        """
        Get top N error types for an endpoint.
        
        Args:
            stats: Endpoint statistics
            top_n: Number of top errors to return
        
        Returns:
            Formatted string with top errors
        """
        if not stats.error_counts:
            return "No errors"
        
        sorted_errors = sorted(
            stats.error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return ", ".join([f"{error}({count})" for error, count in sorted_errors])
    
    def get_endpoint_statistics(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific endpoint.
        
        Args:
            endpoint: Endpoint name
        
        Returns:
            Dictionary with endpoint statistics, or None if endpoint not found
        
        Example:
            >>> monitor = YouComAPIMonitor()
            >>> # ... make some API calls ...
            >>> stats = monitor.get_endpoint_statistics('search')
            >>> print(f"Total calls: {stats['total_calls']}")
            >>> print(f"Error rate: {stats['error_rate']:.1f}%")
            >>> print(f"Avg response time: {stats['average_response_time']:.2f}s")
        """
        with self.lock:
            if endpoint not in self.endpoint_stats:
                return None
            return self.endpoint_stats[endpoint].to_dict()
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for all endpoints.
        
        Returns:
            Dictionary with overall statistics and per-endpoint statistics
        
        Example:
            >>> monitor = YouComAPIMonitor()
            >>> # ... make some API calls ...
            >>> stats = monitor.get_all_statistics()
            >>> print(f"Total API calls: {stats['total_calls']}")
            >>> print(f"Overall error rate: {stats['overall_error_rate']:.1f}%")
            >>> for endpoint, endpoint_stats in stats['endpoints'].items():
            ...     print(f"{endpoint}: {endpoint_stats['total_calls']} calls")
        """
        with self.lock:
            # Calculate overall statistics
            total_calls = sum(s.total_calls for s in self.endpoint_stats.values())
            total_successful = sum(s.successful_calls for s in self.endpoint_stats.values())
            total_failed = sum(s.failed_calls for s in self.endpoint_stats.values())
            total_cached = sum(s.cached_calls for s in self.endpoint_stats.values())
            total_response_time = sum(s.total_response_time for s in self.endpoint_stats.values())
            total_wait_time = sum(s.total_wait_time for s in self.endpoint_stats.values())
            
            overall_error_rate = (total_failed / total_calls * 100.0) if total_calls > 0 else 0.0
            overall_cache_hit_rate = (total_cached / total_calls * 100.0) if total_calls > 0 else 0.0
            avg_response_time = (total_response_time / total_successful) if total_successful > 0 else 0.0
            
            # Monitoring duration
            duration = (datetime.now() - self.start_time).total_seconds()
            calls_per_minute = (total_calls / duration * 60.0) if duration > 0 else 0.0
            
            return {
                'monitoring_start_time': self.start_time.isoformat(),
                'monitoring_duration_seconds': duration,
                'total_calls': total_calls,
                'successful_calls': total_successful,
                'failed_calls': total_failed,
                'cached_calls': total_cached,
                'overall_error_rate': overall_error_rate,
                'overall_cache_hit_rate': overall_cache_hit_rate,
                'average_response_time': avg_response_time,
                'total_wait_time': total_wait_time,
                'calls_per_minute': calls_per_minute,
                'endpoints': {
                    endpoint: stats.to_dict()
                    for endpoint, stats in self.endpoint_stats.items()
                }
            }
    
    def get_cost_estimate(self) -> Dict[str, Any]:
        """
        Get estimated cost based on API usage.
        
        Note: You.com API pricing varies by plan. This provides a usage summary
        that can be used to estimate costs based on your specific plan.
        
        Returns:
            Dictionary with usage counts per endpoint for cost estimation
        
        Example:
            >>> monitor = YouComAPIMonitor()
            >>> # ... make some API calls ...
            >>> cost_info = monitor.get_cost_estimate()
            >>> print(f"Search API calls: {cost_info['search']['total_calls']}")
            >>> print(f"Agent API calls: {cost_info['agent']['total_calls']}")
            >>> print("Use these numbers with your You.com plan pricing")
        """
        with self.lock:
            cost_info = {}
            
            for endpoint, stats in self.endpoint_stats.items():
                cost_info[endpoint] = {
                    'total_calls': stats.total_calls,
                    'successful_calls': stats.successful_calls,
                    'cached_calls': stats.cached_calls,
                    'billable_calls': stats.successful_calls - stats.cached_calls,
                    'note': 'Cached calls typically do not count toward API limits'
                }
            
            # Add summary
            total_billable = sum(info['billable_calls'] for info in cost_info.values())
            cost_info['summary'] = {
                'total_billable_calls': total_billable,
                'note': 'Refer to your You.com plan for specific pricing'
            }
            
            return cost_info
    
    def log_statistics(self):
        """
        Log comprehensive statistics for all endpoints.
        
        This method logs a detailed summary of API usage, performance, and errors.
        
        Example:
            >>> monitor = YouComAPIMonitor()
            >>> # ... make some API calls ...
            >>> monitor.log_statistics()
        """
        stats = self.get_all_statistics()
        
        logger.info("=" * 60)
        logger.info("You.com API Monitoring Statistics")
        logger.info("=" * 60)
        logger.info(f"Monitoring Duration: {stats['monitoring_duration_seconds']:.1f}s")
        logger.info(f"Total API Calls: {stats['total_calls']}")
        logger.info(f"Successful: {stats['successful_calls']}")
        logger.info(f"Failed: {stats['failed_calls']}")
        logger.info(f"Cached: {stats['cached_calls']}")
        logger.info(f"Overall Error Rate: {stats['overall_error_rate']:.1f}%")
        logger.info(f"Overall Cache Hit Rate: {stats['overall_cache_hit_rate']:.1f}%")
        logger.info(f"Average Response Time: {stats['average_response_time']:.2f}s")
        logger.info(f"Total Wait Time: {stats['total_wait_time']:.2f}s")
        logger.info(f"Calls Per Minute: {stats['calls_per_minute']:.2f}")
        logger.info("-" * 60)
        
        for endpoint, endpoint_stats in stats['endpoints'].items():
            logger.info(f"Endpoint: {endpoint}")
            logger.info(f"  Total Calls: {endpoint_stats['total_calls']}")
            logger.info(f"  Success Rate: {100 - endpoint_stats['error_rate']:.1f}%")
            logger.info(f"  Error Rate: {endpoint_stats['error_rate']:.1f}%")
            logger.info(f"  Cache Hit Rate: {endpoint_stats['cache_hit_rate']:.1f}%")
            logger.info(f"  Avg Response Time: {endpoint_stats['average_response_time']:.2f}s")
            logger.info(f"  Min Response Time: {endpoint_stats['min_response_time']:.2f}s")
            logger.info(f"  Max Response Time: {endpoint_stats['max_response_time']:.2f}s")
            logger.info(f"  Total Wait Time: {endpoint_stats['total_wait_time']:.2f}s")
            logger.info(f"  Consecutive Failures: {endpoint_stats['consecutive_failures']}")
            
            if endpoint_stats['error_counts']:
                logger.info(f"  Error Types: {endpoint_stats['error_counts']}")
            
            if endpoint_stats['recent_errors']:
                logger.info(f"  Recent Errors: {len(endpoint_stats['recent_errors'])}")
            
            logger.info("-" * 60)
        
        logger.info("=" * 60)
    
    def export_statistics(self, filepath: Path):
        """
        Export all statistics to a JSON file.
        
        Args:
            filepath: Path to the output JSON file
        
        Example:
            >>> from pathlib import Path
            >>> monitor = YouComAPIMonitor()
            >>> # ... make some API calls ...
            >>> monitor.export_statistics(Path('logs/youcom_stats.json'))
        """
        stats = self.get_all_statistics()
        
        # Add cost estimate
        stats['cost_estimate'] = self.get_cost_estimate()
        
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Exported You.com API statistics to {filepath}")
    
    def reset_statistics(self):
        """
        Reset all statistics.
        
        This clears all tracked metrics and statistics. Use with caution.
        
        Example:
            >>> monitor = YouComAPIMonitor()
            >>> # ... make some API calls ...
            >>> monitor.reset_statistics()  # Clear all stats
        """
        with self.lock:
            self.endpoint_stats.clear()
            self.all_metrics.clear()
            self.start_time = datetime.now()
            logger.info("Reset all You.com API monitoring statistics")
    
    def get_recent_errors(self, endpoint: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent errors for an endpoint or all endpoints.
        
        Args:
            endpoint: Specific endpoint to get errors for, or None for all endpoints
            limit: Maximum number of errors to return
        
        Returns:
            List of recent error dictionaries
        
        Example:
            >>> monitor = YouComAPIMonitor()
            >>> # ... make some API calls ...
            >>> errors = monitor.get_recent_errors('agent', limit=5)
            >>> for error in errors:
            ...     print(f"{error['timestamp']}: {error['error_type']} - {error['error_message']}")
        """
        with self.lock:
            if endpoint:
                if endpoint not in self.endpoint_stats:
                    return []
                return list(self.endpoint_stats[endpoint].recent_errors)[-limit:]
            else:
                # Collect errors from all endpoints
                all_errors = []
                for stats in self.endpoint_stats.values():
                    all_errors.extend(stats.recent_errors)
                
                # Sort by timestamp (most recent first)
                all_errors.sort(key=lambda x: x['timestamp'], reverse=True)
                
                return all_errors[:limit]


# Global monitor instance
_global_monitor: Optional[YouComAPIMonitor] = None


def get_global_monitor() -> YouComAPIMonitor:
    """
    Get the global You.com API monitor instance.
    
    Returns:
        Global YouComAPIMonitor instance
    
    Example:
        >>> from tools.youcom_api_monitor import get_global_monitor
        >>> monitor = get_global_monitor()
        >>> stats = monitor.get_all_statistics()
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = YouComAPIMonitor()
    return _global_monitor


def set_global_monitor(monitor: YouComAPIMonitor):
    """
    Set the global You.com API monitor instance.
    
    Args:
        monitor: YouComAPIMonitor instance to use as global
    
    Example:
        >>> from tools.youcom_api_monitor import YouComAPIMonitor, set_global_monitor
        >>> custom_monitor = YouComAPIMonitor(failure_threshold=5)
        >>> set_global_monitor(custom_monitor)
    """
    global _global_monitor
    _global_monitor = monitor


__all__ = [
    'APICallMetric',
    'EndpointStatistics',
    'YouComAPIMonitor',
    'get_global_monitor',
    'set_global_monitor'
]
