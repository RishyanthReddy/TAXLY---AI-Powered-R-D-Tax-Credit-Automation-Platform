"""
Tests for You.com API monitoring module.

Tests cover:
- API call recording
- Statistics tracking
- Error rate monitoring
- Alert triggering
- Cost estimation
- Statistics export
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile

from tools.youcom_api_monitor import (
    APICallMetric,
    EndpointStatistics,
    YouComAPIMonitor,
    get_global_monitor,
    set_global_monitor
)


class TestAPICallMetric:
    """Test APICallMetric data class."""
    
    def test_create_successful_metric(self):
        """Test creating a successful API call metric."""
        metric = APICallMetric(
            endpoint='search',
            timestamp=datetime.now(),
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        assert metric.endpoint == 'search'
        assert metric.response_time == 1.5
        assert metric.success is True
        assert metric.status_code == 200
        assert metric.error_type is None
        assert metric.cached is False
        assert metric.wait_time == 0.0
    
    def test_create_failed_metric(self):
        """Test creating a failed API call metric."""
        metric = APICallMetric(
            endpoint='agent',
            timestamp=datetime.now(),
            response_time=0.5,
            success=False,
            status_code=429,
            error_type='RateLimitError',
            error_message='Rate limit exceeded'
        )
        
        assert metric.success is False
        assert metric.status_code == 429
        assert metric.error_type == 'RateLimitError'
        assert metric.error_message == 'Rate limit exceeded'
    
    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        timestamp = datetime.now()
        metric = APICallMetric(
            endpoint='search',
            timestamp=timestamp,
            response_time=1.5,
            success=True,
            status_code=200,
            cached=True,
            wait_time=0.5
        )
        
        metric_dict = metric.to_dict()
        
        assert metric_dict['endpoint'] == 'search'
        assert metric_dict['response_time'] == 1.5
        assert metric_dict['success'] is True
        assert metric_dict['status_code'] == 200
        assert metric_dict['cached'] is True
        assert metric_dict['wait_time'] == 0.5
        assert metric_dict['timestamp'] == timestamp.isoformat()


class TestEndpointStatistics:
    """Test EndpointStatistics class."""
    
    def test_create_endpoint_statistics(self):
        """Test creating endpoint statistics."""
        stats = EndpointStatistics(endpoint='search')
        
        assert stats.endpoint == 'search'
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
        assert stats.consecutive_failures == 0
    
    def test_update_with_successful_call(self):
        """Test updating statistics with successful call."""
        stats = EndpointStatistics(endpoint='search')
        
        metric = APICallMetric(
            endpoint='search',
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
        assert stats.total_response_time == 1.5
        assert stats.min_response_time == 1.5
        assert stats.max_response_time == 1.5
    
    def test_update_with_failed_call(self):
        """Test updating statistics with failed call."""
        stats = EndpointStatistics(endpoint='agent')
        
        metric = APICallMetric(
            endpoint='agent',
            timestamp=datetime.now(),
            response_time=0.5,
            success=False,
            status_code=429,
            error_type='RateLimitError',
            error_message='Rate limit exceeded'
        )
        
        stats.update(metric)
        
        assert stats.total_calls == 1
        assert stats.successful_calls == 0
        assert stats.failed_calls == 1
        assert stats.consecutive_failures == 1
        assert stats.error_counts['RateLimitError'] == 1
        assert len(stats.recent_errors) == 1
    
    def test_consecutive_failures_reset(self):
        """Test that consecutive failures reset on success."""
        stats = EndpointStatistics(endpoint='search')
        
        # Record 3 failures
        for _ in range(3):
            metric = APICallMetric(
                endpoint='search',
                timestamp=datetime.now(),
                response_time=0.5,
                success=False,
                error_type='APIError'
            )
            stats.update(metric)
        
        assert stats.consecutive_failures == 3
        
        # Record success
        success_metric = APICallMetric(
            endpoint='search',
            timestamp=datetime.now(),
            response_time=1.5,
            success=True
        )
        stats.update(success_metric)
        
        assert stats.consecutive_failures == 0
    
    def test_get_average_response_time(self):
        """Test calculating average response time."""
        stats = EndpointStatistics(endpoint='search')
        
        # Add multiple successful calls
        for response_time in [1.0, 2.0, 3.0]:
            metric = APICallMetric(
                endpoint='search',
                timestamp=datetime.now(),
                response_time=response_time,
                success=True
            )
            stats.update(metric)
        
        avg = stats.get_average_response_time()
        assert avg == 2.0  # (1.0 + 2.0 + 3.0) / 3
    
    def test_get_error_rate(self):
        """Test calculating error rate."""
        stats = EndpointStatistics(endpoint='agent')
        
        # Add 7 successful and 3 failed calls
        for _ in range(7):
            metric = APICallMetric(
                endpoint='agent',
                timestamp=datetime.now(),
                response_time=1.0,
                success=True
            )
            stats.update(metric)
        
        for _ in range(3):
            metric = APICallMetric(
                endpoint='agent',
                timestamp=datetime.now(),
                response_time=0.5,
                success=False,
                error_type='APIError'
            )
            stats.update(metric)
        
        error_rate = stats.get_error_rate()
        assert error_rate == 30.0  # 3 failures out of 10 calls = 30%
    
    def test_get_cache_hit_rate(self):
        """Test calculating cache hit rate."""
        stats = EndpointStatistics(endpoint='search')
        
        # Add 6 regular calls and 4 cached calls
        for _ in range(6):
            metric = APICallMetric(
                endpoint='search',
                timestamp=datetime.now(),
                response_time=1.0,
                success=True,
                cached=False
            )
            stats.update(metric)
        
        for _ in range(4):
            metric = APICallMetric(
                endpoint='search',
                timestamp=datetime.now(),
                response_time=0.1,
                success=True,
                cached=True
            )
            stats.update(metric)
        
        cache_hit_rate = stats.get_cache_hit_rate()
        assert cache_hit_rate == 40.0  # 4 cached out of 10 calls = 40%


class TestYouComAPIMonitor:
    """Test YouComAPIMonitor class."""
    
    def test_create_monitor(self):
        """Test creating API monitor."""
        monitor = YouComAPIMonitor()
        
        assert monitor.failure_threshold == 3
        assert monitor.error_rate_threshold == 50.0
        assert monitor.slow_response_threshold == 30.0
        assert monitor.enable_alerts is True
        assert len(monitor.endpoint_stats) == 0
    
    def test_create_monitor_with_custom_thresholds(self):
        """Test creating monitor with custom thresholds."""
        monitor = YouComAPIMonitor(
            failure_threshold=5,
            error_rate_threshold=25.0,
            slow_response_threshold=60.0,
            enable_alerts=False
        )
        
        assert monitor.failure_threshold == 5
        assert monitor.error_rate_threshold == 25.0
        assert monitor.slow_response_threshold == 60.0
        assert monitor.enable_alerts is False
    
    def test_record_successful_api_call(self):
        """Test recording a successful API call."""
        monitor = YouComAPIMonitor()
        
        monitor.record_api_call(
            endpoint='search',
            response_time=1.5,
            success=True,
            status_code=200
        )
        
        assert len(monitor.all_metrics) == 1
        assert 'search' in monitor.endpoint_stats
        assert monitor.endpoint_stats['search'].total_calls == 1
        assert monitor.endpoint_stats['search'].successful_calls == 1
    
    def test_record_failed_api_call(self):
        """Test recording a failed API call."""
        monitor = YouComAPIMonitor()
        
        monitor.record_api_call(
            endpoint='agent',
            response_time=0.5,
            success=False,
            status_code=429,
            error_type='RateLimitError',
            error_message='Rate limit exceeded'
        )
        
        assert len(monitor.all_metrics) == 1
        assert 'agent' in monitor.endpoint_stats
        assert monitor.endpoint_stats['agent'].failed_calls == 1
        assert monitor.endpoint_stats['agent'].error_counts['RateLimitError'] == 1
    
    def test_record_cached_api_call(self):
        """Test recording a cached API call."""
        monitor = YouComAPIMonitor()
        
        monitor.record_api_call(
            endpoint='search',
            response_time=0.1,
            success=True,
            cached=True
        )
        
        assert monitor.endpoint_stats['search'].cached_calls == 1
    
    def test_record_multiple_endpoints(self):
        """Test recording calls to multiple endpoints."""
        monitor = YouComAPIMonitor()
        
        monitor.record_api_call('search', 1.0, True)
        monitor.record_api_call('agent', 2.0, True)
        monitor.record_api_call('contents', 1.5, True)
        
        assert len(monitor.endpoint_stats) == 3
        assert 'search' in monitor.endpoint_stats
        assert 'agent' in monitor.endpoint_stats
        assert 'contents' in monitor.endpoint_stats
    
    def test_get_endpoint_statistics(self):
        """Test getting statistics for a specific endpoint."""
        monitor = YouComAPIMonitor()
        
        # Record some calls
        for _ in range(5):
            monitor.record_api_call('search', 1.0, True)
        
        stats = monitor.get_endpoint_statistics('search')
        
        assert stats is not None
        assert stats['endpoint'] == 'search'
        assert stats['total_calls'] == 5
        assert stats['successful_calls'] == 5
    
    def test_get_endpoint_statistics_nonexistent(self):
        """Test getting statistics for nonexistent endpoint."""
        monitor = YouComAPIMonitor()
        
        stats = monitor.get_endpoint_statistics('nonexistent')
        
        assert stats is None
    
    def test_get_all_statistics(self):
        """Test getting all statistics."""
        monitor = YouComAPIMonitor()
        
        # Record calls to multiple endpoints
        monitor.record_api_call('search', 1.0, True)
        monitor.record_api_call('search', 1.5, True)
        monitor.record_api_call('agent', 2.0, True)
        monitor.record_api_call('agent', 0.5, False, error_type='APIError')
        
        stats = monitor.get_all_statistics()
        
        assert stats['total_calls'] == 4
        assert stats['successful_calls'] == 3
        assert stats['failed_calls'] == 1
        assert stats['overall_error_rate'] == 25.0  # 1 failure out of 4 calls
        assert len(stats['endpoints']) == 2
    
    def test_get_cost_estimate(self):
        """Test getting cost estimate."""
        monitor = YouComAPIMonitor()
        
        # Record calls with some cached
        monitor.record_api_call('search', 1.0, True, cached=False)
        monitor.record_api_call('search', 0.1, True, cached=True)
        monitor.record_api_call('agent', 2.0, True, cached=False)
        
        cost_info = monitor.get_cost_estimate()
        
        assert 'search' in cost_info
        assert cost_info['search']['total_calls'] == 2
        assert cost_info['search']['cached_calls'] == 1
        assert cost_info['search']['billable_calls'] == 1  # 2 total - 1 cached
        
        assert 'agent' in cost_info
        assert cost_info['agent']['billable_calls'] == 1
        
        assert 'summary' in cost_info
        assert cost_info['summary']['total_billable_calls'] == 2
    
    def test_alert_on_consecutive_failures(self, caplog):
        """Test alert on consecutive failures."""
        monitor = YouComAPIMonitor(failure_threshold=3, enable_alerts=True)
        
        # Record 3 consecutive failures
        for i in range(3):
            monitor.record_api_call(
                'agent',
                0.5,
                False,
                error_type='APIError',
                error_message=f'Error {i+1}'
            )
        
        # Check that alert was logged
        assert any('[ALERT]' in record.message for record in caplog.records)
        assert any('consecutive failures' in record.message for record in caplog.records)
    
    def test_alert_on_high_error_rate(self, caplog):
        """Test alert on high error rate."""
        monitor = YouComAPIMonitor(error_rate_threshold=50.0, enable_alerts=True)
        
        # Record 10 calls with 6 failures (60% error rate)
        for _ in range(4):
            monitor.record_api_call('search', 1.0, True)
        
        for _ in range(6):
            monitor.record_api_call('search', 0.5, False, error_type='APIError')
        
        # Check that alert was logged
        assert any('[ALERT]' in record.message for record in caplog.records)
        assert any('high error rate' in record.message for record in caplog.records)
    
    def test_alert_on_slow_response(self, caplog):
        """Test alert on slow response."""
        monitor = YouComAPIMonitor(slow_response_threshold=30.0, enable_alerts=True)
        
        # Record a slow response
        monitor.record_api_call('agent', 35.0, True)
        
        # Check that alert was logged
        assert any('[ALERT]' in record.message for record in caplog.records)
        assert any('slow response' in record.message for record in caplog.records)
    
    def test_no_alerts_when_disabled(self, caplog):
        """Test that alerts are not triggered when disabled."""
        monitor = YouComAPIMonitor(failure_threshold=2, enable_alerts=False)
        
        # Record failures that would trigger alert
        for _ in range(3):
            monitor.record_api_call('agent', 0.5, False, error_type='APIError')
        
        # Check that no alerts were logged
        assert not any('[ALERT]' in record.message for record in caplog.records)
    
    def test_export_statistics(self):
        """Test exporting statistics to file."""
        monitor = YouComAPIMonitor()
        
        # Record some calls
        monitor.record_api_call('search', 1.0, True)
        monitor.record_api_call('agent', 2.0, True)
        
        # Export to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / 'stats.json'
            monitor.export_statistics(filepath)
            
            # Verify file was created
            assert filepath.exists()
            
            # Verify content
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert data['total_calls'] == 2
            assert 'endpoints' in data
            assert 'cost_estimate' in data
    
    def test_reset_statistics(self):
        """Test resetting statistics."""
        monitor = YouComAPIMonitor()
        
        # Record some calls
        monitor.record_api_call('search', 1.0, True)
        monitor.record_api_call('agent', 2.0, True)
        
        assert len(monitor.all_metrics) == 2
        assert len(monitor.endpoint_stats) == 2
        
        # Reset
        monitor.reset_statistics()
        
        assert len(monitor.all_metrics) == 0
        assert len(monitor.endpoint_stats) == 0
    
    def test_get_recent_errors_for_endpoint(self):
        """Test getting recent errors for specific endpoint."""
        monitor = YouComAPIMonitor()
        
        # Record errors for different endpoints
        monitor.record_api_call('search', 0.5, False, error_type='Error1', error_message='Search error')
        monitor.record_api_call('agent', 0.5, False, error_type='Error2', error_message='Agent error')
        monitor.record_api_call('search', 0.5, False, error_type='Error3', error_message='Another search error')
        
        # Get errors for search endpoint
        errors = monitor.get_recent_errors('search')
        
        assert len(errors) == 2
        assert all(error['error_message'].endswith('error') for error in errors)
    
    def test_get_recent_errors_all_endpoints(self):
        """Test getting recent errors for all endpoints."""
        monitor = YouComAPIMonitor()
        
        # Record errors for different endpoints
        monitor.record_api_call('search', 0.5, False, error_type='Error1')
        monitor.record_api_call('agent', 0.5, False, error_type='Error2')
        monitor.record_api_call('contents', 0.5, False, error_type='Error3')
        
        # Get all errors
        errors = monitor.get_recent_errors()
        
        assert len(errors) == 3
    
    def test_get_recent_errors_with_limit(self):
        """Test getting recent errors with limit."""
        monitor = YouComAPIMonitor()
        
        # Record 10 errors
        for i in range(10):
            monitor.record_api_call('search', 0.5, False, error_type=f'Error{i}')
        
        # Get only 5 most recent
        errors = monitor.get_recent_errors('search', limit=5)
        
        assert len(errors) == 5


class TestGlobalMonitor:
    """Test global monitor functions."""
    
    def test_get_global_monitor(self):
        """Test getting global monitor instance."""
        monitor1 = get_global_monitor()
        monitor2 = get_global_monitor()
        
        # Should return same instance
        assert monitor1 is monitor2
    
    def test_set_global_monitor(self):
        """Test setting global monitor instance."""
        custom_monitor = YouComAPIMonitor(failure_threshold=10)
        set_global_monitor(custom_monitor)
        
        retrieved_monitor = get_global_monitor()
        
        assert retrieved_monitor is custom_monitor
        assert retrieved_monitor.failure_threshold == 10


class TestIntegration:
    """Integration tests for API monitoring."""
    
    def test_realistic_usage_scenario(self):
        """Test realistic usage scenario with mixed success/failure."""
        monitor = YouComAPIMonitor()
        
        # Simulate realistic API usage
        # Search API: mostly successful with some cache hits
        for _ in range(8):
            monitor.record_api_call('search', 1.2, True, status_code=200)
        for _ in range(3):
            monitor.record_api_call('search', 0.1, True, cached=True)
        monitor.record_api_call('search', 0.5, False, status_code=429, error_type='RateLimitError')
        
        # Agent API: slower responses, some failures
        for _ in range(5):
            monitor.record_api_call('agent', 15.0, True, status_code=200)
        for _ in range(2):
            monitor.record_api_call('agent', 0.5, False, status_code=500, error_type='ServerError')
        
        # Contents API: all successful
        for _ in range(4):
            monitor.record_api_call('contents', 2.0, True, status_code=200)
        
        # Get overall statistics
        stats = monitor.get_all_statistics()
        
        assert stats['total_calls'] == 23
        assert stats['successful_calls'] == 20
        assert stats['failed_calls'] == 3
        assert stats['cached_calls'] == 3
        
        # Check endpoint-specific stats
        search_stats = monitor.get_endpoint_statistics('search')
        assert search_stats['total_calls'] == 12
        assert search_stats['cache_hit_rate'] == 25.0  # 3 out of 12
        
        agent_stats = monitor.get_endpoint_statistics('agent')
        assert agent_stats['error_rate'] > 0
        
        contents_stats = monitor.get_endpoint_statistics('contents')
        assert contents_stats['error_rate'] == 0.0
        
        # Check cost estimate
        cost_info = monitor.get_cost_estimate()
        assert cost_info['search']['billable_calls'] == 8  # 11 successful - 3 cached
        assert cost_info['summary']['total_billable_calls'] == 17  # All successful non-cached  # All successful non-cached


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
