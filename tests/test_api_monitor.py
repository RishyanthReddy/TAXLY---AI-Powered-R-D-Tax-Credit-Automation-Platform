"""
Tests for API Monitor

This module tests the APIMonitor class functionality including:
- Recording API calls
- Tracking statistics
- Error monitoring
- Cost estimation
- Alert generation
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
import json

from tools.api_monitor import (
    APIMonitor,
    APICallMetric,
    EndpointStatistics,
    get_global_monitor,
    set_global_monitor
)


class TestAPICallMetric:
    """Tests for APICallMetric data class."""
    
    def test_create_metric(self):
        """Test creating an API call metric."""
        metric = APICallMetric(
            api_name='Clockify',
            endpoint='/time-entries',
            timestamp=datetime.now(),
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        assert metric.api_name == 'Clockify'
        assert metric.endpoint == '/time-entries'
        assert metric.response_time == 1.5
        assert metric.success is True
        assert metric.status_code == 200
        assert metric.cached is False
        assert metric.wait_time == 0.0
    
    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        timestamp = datetime.now()
        metric = APICallMetric(
            api_name='You.com',
            endpoint='agent',
            timestamp=timestamp,
            response_time=2.3,
            success=False,
            status_code=429,
            error_type='RateLimitError',
            error_message='Rate limit exceeded',
            cached=False,
            wait_time=1.5
        )
        
        metric_dict = metric.to_dict()
        
        assert metric_dict['api_name'] == 'You.com'
        assert metric_dict['endpoint'] == 'agent'
        assert metric_dict['response_time'] == 2.3
        assert metric_dict['success'] is False
        assert metric_dict['status_code'] == 429
        assert metric_dict['error_type'] == 'RateLimitError'
        assert metric_dict['cached'] is False
        assert metric_dict['wait_time'] == 1.5


class TestEndpointStatistics:
    """Tests for EndpointStatistics data class."""
    
    def test_create_statistics(self):
        """Test creating endpoint statistics."""
        stats = EndpointStatistics(
            api_name='Clockify',
            endpoint='/time-entries'
        )
        
        assert stats.api_name == 'Clockify'
        assert stats.endpoint == '/time-entries'
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
    
    def test_update_with_successful_call(self):
        """Test updating statistics with successful call."""
        stats = EndpointStatistics(
            api_name='Clockify',
            endpoint='/time-entries'
        )
        
        metric = APICallMetric(
            api_name='Clockify',
            endpoint='/time-entries',
            timestamp=datetime.now(),
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        stats.update(metric)
        
        assert stats.total_calls == 1
        assert stats.successful_calls == 1
        assert stats.failed_calls == 0
        assert stats.consecutive_failures == 0
        assert stats.min_response_time == 1.5
        assert stats.max_response_time == 1.5
    
    def test_update_with_failed_call(self):
        """Test updating statistics with failed call."""
        stats = EndpointStatistics(
            api_name='You.com',
            endpoint='agent'
        )
        
        metric = APICallMetric(
            api_name='You.com',
            endpoint='agent',
            timestamp=datetime.now(),
            response_time=0.5,
            success=False,
            status_code=500,
            error_type='ServerError',
            error_message='Internal server error'
        )
        
        stats.update(metric)
        
        assert stats.total_calls == 1
        assert stats.successful_calls == 0
        assert stats.failed_calls == 1
        assert stats.consecutive_failures == 1
        assert stats.error_counts['ServerError'] == 1
        assert len(stats.recent_errors) == 1
    
    def test_consecutive_failures_reset(self):
        """Test that consecutive failures reset on success."""
        stats = EndpointStatistics(
            api_name='You.com',
            endpoint='agent'
        )
        
        # Add two failures
        for i in range(2):
            metric = APICallMetric(
                api_name='You.com',
                endpoint='agent',
                timestamp=datetime.now(),
                response_time=0.5,
                success=False,
                status_code=500
            )
            stats.update(metric)
        
        assert stats.consecutive_failures == 2
        
        # Add success
        success_metric = APICallMetric(
            api_name='You.com',
            endpoint='agent',
            timestamp=datetime.now(),
            response_time=2.0,
            success=True,
            status_code=200
        )
        stats.update(success_metric)
        
        assert stats.consecutive_failures == 0
    
    def test_get_average_response_time(self):
        """Test calculating average response time."""
        stats = EndpointStatistics(
            api_name='Clockify',
            endpoint='/time-entries'
        )
        
        # Add multiple successful calls
        for response_time in [1.0, 2.0, 3.0]:
            metric = APICallMetric(
                api_name='Clockify',
                endpoint='/time-entries',
                timestamp=datetime.now(),
                response_time=response_time,
                success=True,
                status_code=200
            )
            stats.update(metric)
        
        assert stats.get_average_response_time() == 2.0
    
    def test_get_error_rate(self):
        """Test calculating error rate."""
        stats = EndpointStatistics(
            api_name='You.com',
            endpoint='agent'
        )
        
        # Add 7 successful and 3 failed calls
        for i in range(10):
            metric = APICallMetric(
                api_name='You.com',
                endpoint='agent',
                timestamp=datetime.now(),
                response_time=1.0,
                success=i < 7,
                status_code=200 if i < 7 else 500
            )
            stats.update(metric)
        
        assert stats.get_error_rate() == 30.0
    
    def test_get_cache_hit_rate(self):
        """Test calculating cache hit rate."""
        stats = EndpointStatistics(
            api_name='You.com',
            endpoint='search'
        )
        
        # Add 6 regular and 4 cached calls
        for i in range(10):
            metric = APICallMetric(
                api_name='You.com',
                endpoint='search',
                timestamp=datetime.now(),
                response_time=0.1 if i >= 6 else 2.0,
                success=True,
                status_code=200,
                cached=i >= 6
            )
            stats.update(metric)
        
        assert stats.get_cache_hit_rate() == 40.0


class TestAPIMonitor:
    """Tests for APIMonitor class."""
    
    def test_create_monitor(self):
        """Test creating an API monitor."""
        monitor = APIMonitor()
        
        assert monitor.failure_threshold == 3
        assert monitor.error_rate_threshold == 50.0
        assert monitor.slow_response_threshold == 30.0
        assert monitor.enable_alerts is True
        assert len(monitor.endpoint_stats) == 0
        assert len(monitor.all_metrics) == 0
    
    def test_create_monitor_with_custom_thresholds(self):
        """Test creating monitor with custom thresholds."""
        monitor = APIMonitor(
            failure_threshold=5,
            error_rate_threshold=25.0,
            slow_response_threshold=60.0,
            enable_alerts=False
        )
        
        assert monitor.failure_threshold == 5
        assert monitor.error_rate_threshold == 25.0
        assert monitor.slow_response_threshold == 60.0
        assert monitor.enable_alerts is False
    
    def test_record_api_call(self):
        """Test recording an API call."""
        monitor = APIMonitor()
        
        monitor.record_api_call(
            api_name='Clockify',
            endpoint='/time-entries',
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        assert len(monitor.all_metrics) == 1
        assert len(monitor.endpoint_stats) == 1
        
        key = ('Clockify', '/time-entries')
        assert key in monitor.endpoint_stats
        assert monitor.endpoint_stats[key].total_calls == 1
    
    def test_record_multiple_api_calls(self):
        """Test recording multiple API calls."""
        monitor = APIMonitor()
        
        # Record calls to different APIs
        monitor.record_api_call(
            api_name='Clockify',
            endpoint='/time-entries',
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        monitor.record_api_call(
            api_name='You.com',
            endpoint='search',
            response_time=2.0,
            success=True,
            status_code=200
        )
        
        monitor.record_api_call(
            api_name='Clockify',
            endpoint='/time-entries',
            response_time=1.8,
            success=True,
            status_code=200
        )
        
        assert len(monitor.all_metrics) == 3
        assert len(monitor.endpoint_stats) == 2
        
        clockify_key = ('Clockify', '/time-entries')
        assert monitor.endpoint_stats[clockify_key].total_calls == 2
    
    def test_get_api_statistics(self):
        """Test getting statistics for a specific API."""
        monitor = APIMonitor()
        
        # Record calls to Clockify
        for i in range(5):
            monitor.record_api_call(
                api_name='Clockify',
                endpoint='/time-entries',
                response_time=1.0 + i * 0.2,
                success=True,
                status_code=200
            )
        
        stats = monitor.get_api_statistics('Clockify')
        
        assert stats['api_name'] == 'Clockify'
        assert stats['total_calls'] == 5
        assert stats['successful_calls'] == 5
        assert stats['failed_calls'] == 0
    
    def test_get_endpoint_statistics(self):
        """Test getting statistics for a specific endpoint."""
        monitor = APIMonitor()
        
        monitor.record_api_call(
            api_name='You.com',
            endpoint='agent',
            response_time=2.5,
            success=True,
            status_code=200
        )
        
        stats = monitor.get_endpoint_statistics('You.com', 'agent')
        
        assert stats is not None
        assert stats['api_name'] == 'You.com'
        assert stats['endpoint'] == 'agent'
        assert stats['total_calls'] == 1
    
    def test_get_all_statistics(self):
        """Test getting all statistics."""
        monitor = APIMonitor()
        
        # Record calls to multiple APIs
        monitor.record_api_call(
            api_name='Clockify',
            endpoint='/time-entries',
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        monitor.record_api_call(
            api_name='You.com',
            endpoint='search',
            response_time=2.0,
            success=True,
            status_code=200
        )
        
        stats = monitor.get_all_statistics()
        
        assert stats['total_calls'] == 2
        assert stats['successful_calls'] == 2
        assert stats['failed_calls'] == 0
        assert 'Clockify' in stats['apis']
        assert 'You.com' in stats['apis']
    
    def test_get_cost_estimate(self):
        """Test getting cost estimate."""
        monitor = APIMonitor()
        
        # Record calls with some cached
        for i in range(10):
            monitor.record_api_call(
                api_name='You.com',
                endpoint='search',
                response_time=0.1 if i % 3 == 0 else 2.0,
                success=True,
                status_code=200,
                cached=i % 3 == 0
            )
        
        cost_info = monitor.get_cost_estimate()
        
        assert 'You.com' in cost_info
        assert cost_info['You.com']['total_calls'] == 10
        assert cost_info['You.com']['cached_calls'] == 4  # Every 3rd call
        assert cost_info['You.com']['billable_calls'] == 6
    
    def test_get_recent_errors(self):
        """Test getting recent errors."""
        monitor = APIMonitor()
        
        # Record some errors
        for i in range(3):
            monitor.record_api_call(
                api_name='You.com',
                endpoint='agent',
                response_time=0.5,
                success=False,
                status_code=500,
                error_type='ServerError',
                error_message=f'Error {i}'
            )
        
        errors = monitor.get_recent_errors('You.com', 'agent')
        
        assert len(errors) == 3
        assert all(e['error_type'] == 'ServerError' for e in errors)
    
    def test_reset_statistics(self):
        """Test resetting statistics."""
        monitor = APIMonitor()
        
        # Record some calls
        monitor.record_api_call(
            api_name='Clockify',
            endpoint='/time-entries',
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        assert len(monitor.all_metrics) == 1
        assert len(monitor.endpoint_stats) == 1
        
        # Reset
        monitor.reset_statistics()
        
        assert len(monitor.all_metrics) == 0
        assert len(monitor.endpoint_stats) == 0
    
    def test_export_statistics(self, tmp_path):
        """Test exporting statistics to file."""
        monitor = APIMonitor()
        
        # Record some calls
        monitor.record_api_call(
            api_name='Clockify',
            endpoint='/time-entries',
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        # Export to file
        output_file = tmp_path / "stats.json"
        monitor.export_statistics(output_file)
        
        assert output_file.exists()
        
        # Verify content
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert data['total_calls'] == 1
        assert 'Clockify' in data['apis']
    
    def test_get_metrics_by_time_range(self):
        """Test getting metrics by time range."""
        monitor = APIMonitor()
        
        # Record calls with delays
        start_time = datetime.now()
        
        for i in range(3):
            monitor.record_api_call(
                api_name='You.com',
                endpoint='search',
                response_time=1.5,
                success=True,
                status_code=200
            )
            time.sleep(0.1)
        
        end_time = datetime.now()
        
        # Get metrics in range
        metrics = monitor.get_metrics_by_time_range(start_time, end_time, 'You.com')
        
        assert len(metrics) == 3
        assert all(m.api_name == 'You.com' for m in metrics)


class TestGlobalMonitor:
    """Tests for global monitor instance."""
    
    def test_get_global_monitor(self):
        """Test getting global monitor instance."""
        monitor1 = get_global_monitor()
        monitor2 = get_global_monitor()
        
        # Should return same instance
        assert monitor1 is monitor2
    
    def test_set_global_monitor(self):
        """Test setting global monitor instance."""
        custom_monitor = APIMonitor(failure_threshold=10)
        set_global_monitor(custom_monitor)
        
        retrieved_monitor = get_global_monitor()
        
        assert retrieved_monitor is custom_monitor
        assert retrieved_monitor.failure_threshold == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
