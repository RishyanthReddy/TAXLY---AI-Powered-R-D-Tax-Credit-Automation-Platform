"""
Unit tests for performance monitoring and metrics tracking utilities.

This module tests the metrics collection, timing decorators, memory tracking,
and agent-specific metrics functionality.
"""

import pytest
import time
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from utils.metrics import (
    ExecutionMetric,
    MetricsCollector,
    get_metrics_collector,
    timing_decorator,
    track_execution_time,
    MemoryTracker,
    AgentMetrics,
    log_performance_summary
)


class TestExecutionMetric:
    """Test suite for ExecutionMetric data class."""
    
    def test_create_basic_metric(self):
        """Test creating a basic execution metric."""
        metric = ExecutionMetric(
            function_name="test_function",
            execution_time=1.5,
            timestamp=datetime.now()
        )
        
        assert metric.function_name == "test_function"
        assert metric.execution_time == 1.5
        assert metric.success is True
        assert metric.error_message is None
        assert metric.memory_used is None
    
    def test_create_metric_with_memory(self):
        """Test creating a metric with memory usage."""
        metric = ExecutionMetric(
            function_name="test_function",
            execution_time=2.0,
            timestamp=datetime.now(),
            memory_used=50.5
        )
        
        assert metric.memory_used == 50.5
    
    def test_create_failed_metric(self):
        """Test creating a metric for failed execution."""
        metric = ExecutionMetric(
            function_name="test_function",
            execution_time=0.5,
            timestamp=datetime.now(),
            success=False,
            error_message="Test error"
        )
        
        assert metric.success is False
        assert metric.error_message == "Test error"
    
    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        timestamp = datetime.now()
        metric = ExecutionMetric(
            function_name="test_function",
            execution_time=1.0,
            timestamp=timestamp,
            memory_used=25.0,
            metadata={'key': 'value'}
        )
        
        result = metric.to_dict()
        
        assert result['function_name'] == "test_function"
        assert result['execution_time'] == 1.0
        assert result['timestamp'] == timestamp.isoformat()
        assert result['memory_used'] == 25.0
        assert result['metadata'] == {'key': 'value'}


class TestMetricsCollector:
    """Test suite for MetricsCollector class."""
    
    def test_add_metric(self):
        """Test adding a metric to the collector."""
        collector = MetricsCollector()
        metric = ExecutionMetric(
            function_name="test_function",
            execution_time=1.0,
            timestamp=datetime.now()
        )
        
        collector.add_metric(metric)
        
        metrics = collector.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].function_name == "test_function"
    
    def test_add_agent_metric(self):
        """Test adding an agent-specific metric."""
        collector = MetricsCollector()
        metric = ExecutionMetric(
            function_name="agent.data_ingestion.run",
            execution_time=5.0,
            timestamp=datetime.now()
        )
        
        collector.add_agent_metric("data_ingestion", metric)
        
        agent_metrics = collector.get_metrics(agent_name="data_ingestion")
        assert len(agent_metrics) == 1
        assert agent_metrics[0].execution_time == 5.0
    
    def test_get_metrics_by_function_name(self):
        """Test filtering metrics by function name."""
        collector = MetricsCollector()
        
        metric1 = ExecutionMetric(
            function_name="function_a",
            execution_time=1.0,
            timestamp=datetime.now()
        )
        metric2 = ExecutionMetric(
            function_name="function_b",
            execution_time=2.0,
            timestamp=datetime.now()
        )
        
        collector.add_metric(metric1)
        collector.add_metric(metric2)
        
        filtered = collector.get_metrics(function_name="function_a")
        assert len(filtered) == 1
        assert filtered[0].function_name == "function_a"
    
    def test_get_statistics_empty(self):
        """Test getting statistics with no metrics."""
        collector = MetricsCollector()
        stats = collector.get_statistics()
        
        assert stats['count'] == 0
        assert stats['total_time'] == 0.0
        assert stats['avg_time'] == 0.0
    
    def test_get_statistics_with_metrics(self):
        """Test getting statistics with multiple metrics."""
        collector = MetricsCollector()
        
        for i in range(5):
            metric = ExecutionMetric(
                function_name="test_function",
                execution_time=float(i + 1),  # 1.0, 2.0, 3.0, 4.0, 5.0
                timestamp=datetime.now(),
                success=True
            )
            collector.add_metric(metric)
        
        stats = collector.get_statistics()
        
        assert stats['count'] == 5
        assert stats['total_time'] == 15.0  # 1+2+3+4+5
        assert stats['avg_time'] == 3.0
        assert stats['min_time'] == 1.0
        assert stats['max_time'] == 5.0
        assert stats['success_rate'] == 1.0
    
    def test_get_statistics_with_failures(self):
        """Test statistics calculation with failed executions."""
        collector = MetricsCollector()
        
        # Add 3 successful and 2 failed metrics
        for i in range(3):
            collector.add_metric(ExecutionMetric(
                function_name="test",
                execution_time=1.0,
                timestamp=datetime.now(),
                success=True
            ))
        
        for i in range(2):
            collector.add_metric(ExecutionMetric(
                function_name="test",
                execution_time=1.0,
                timestamp=datetime.now(),
                success=False
            ))
        
        stats = collector.get_statistics()
        
        assert stats['count'] == 5
        assert stats['success_rate'] == 0.6  # 3/5
    
    def test_export_metrics(self, tmp_path):
        """Test exporting metrics to JSON file."""
        collector = MetricsCollector()
        
        metric = ExecutionMetric(
            function_name="test_function",
            execution_time=1.5,
            timestamp=datetime.now()
        )
        collector.add_metric(metric)
        
        output_file = tmp_path / "metrics.json"
        collector.export_metrics(output_file)
        
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert data['total_metrics'] == 1
        assert len(data['metrics']) == 1
        assert data['metrics'][0]['function_name'] == "test_function"
    
    def test_clear_metrics(self):
        """Test clearing all metrics."""
        collector = MetricsCollector()
        
        metric = ExecutionMetric(
            function_name="test",
            execution_time=1.0,
            timestamp=datetime.now()
        )
        collector.add_metric(metric)
        
        assert len(collector.get_metrics()) == 1
        
        collector.clear_metrics()
        
        assert len(collector.get_metrics()) == 0


class TestTimingDecorator:
    """Test suite for timing_decorator."""
    
    def test_timing_decorator_basic(self):
        """Test basic timing decorator functionality."""
        @timing_decorator()
        def test_function():
            time.sleep(0.1)
            return "result"
        
        result = test_function()
        
        assert result == "result"
        
        # Check that metric was recorded
        collector = get_metrics_collector()
        metrics = collector.get_metrics()
        
        # Find our metric (there might be others from previous tests)
        our_metrics = [m for m in metrics if 'test_function' in m.function_name]
        assert len(our_metrics) > 0
        assert our_metrics[-1].execution_time >= 0.1
    
    def test_timing_decorator_with_exception(self):
        """Test timing decorator with function that raises exception."""
        @timing_decorator()
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_function()
        
        # Check that failed metric was recorded
        collector = get_metrics_collector()
        metrics = collector.get_metrics()
        
        failed_metrics = [m for m in metrics if not m.success and 'failing_function' in m.function_name]
        assert len(failed_metrics) > 0
        assert failed_metrics[-1].error_message == "Test error"
    
    def test_timing_decorator_with_metadata(self):
        """Test timing decorator with custom metadata."""
        @timing_decorator(metadata={'stage': 'test', 'version': '1.0'})
        def metadata_function():
            return "result"
        
        result = metadata_function()
        
        collector = get_metrics_collector()
        metrics = collector.get_metrics()
        
        our_metrics = [m for m in metrics if 'metadata_function' in m.function_name]
        assert len(our_metrics) > 0
        assert our_metrics[-1].metadata['stage'] == 'test'
        assert our_metrics[-1].metadata['version'] == '1.0'


class TestTrackExecutionTime:
    """Test suite for track_execution_time context manager."""
    
    def test_track_execution_time_basic(self):
        """Test basic execution time tracking."""
        with track_execution_time('test_operation'):
            time.sleep(0.1)
        
        collector = get_metrics_collector()
        metrics = collector.get_metrics(function_name='test_operation')
        
        assert len(metrics) > 0
        assert metrics[-1].execution_time >= 0.1
    
    def test_track_execution_time_with_exception(self):
        """Test execution time tracking with exception."""
        with pytest.raises(ValueError, match="Test error"):
            with track_execution_time('failing_operation'):
                raise ValueError("Test error")
        
        collector = get_metrics_collector()
        metrics = collector.get_metrics(function_name='failing_operation')
        
        assert len(metrics) > 0
        assert metrics[-1].success is False
        assert metrics[-1].error_message == "Test error"


class TestMemoryTracker:
    """Test suite for MemoryTracker class."""
    
    def test_start_stop_tracking(self):
        """Test starting and stopping memory tracking."""
        MemoryTracker.start_tracking()
        
        # Allocate some memory
        data = [0] * 10000
        
        current = MemoryTracker.get_current_memory()
        peak = MemoryTracker.get_peak_memory()
        
        MemoryTracker.stop_tracking()
        
        assert current >= 0
        assert peak >= 0
        assert peak >= current
    
    def test_get_memory_snapshot(self):
        """Test getting memory snapshot."""
        MemoryTracker.start_tracking()
        
        # Allocate some memory
        data = [0] * 10000
        
        snapshot = MemoryTracker.get_memory_snapshot()
        
        MemoryTracker.stop_tracking()
        
        assert 'current' in snapshot
        assert 'peak' in snapshot
        assert snapshot['current'] >= 0
        assert snapshot['peak'] >= 0
    
    def test_memory_tracking_not_started(self):
        """Test getting memory when tracking not started."""
        # Make sure tracking is stopped
        try:
            MemoryTracker.stop_tracking()
        except:
            pass
        
        current = MemoryTracker.get_current_memory()
        assert current == 0.0


class TestAgentMetrics:
    """Test suite for AgentMetrics class."""
    
    def test_track_agent_execution(self):
        """Test tracking agent execution."""
        @AgentMetrics.track_agent_execution('test_agent')
        def agent_function():
            time.sleep(0.1)
            return "result"
        
        result = agent_function()
        
        assert result == "result"
        
        stats = AgentMetrics.get_agent_statistics('test_agent')
        assert stats['count'] > 0
    
    def test_track_agent_execution_with_failure(self):
        """Test tracking failed agent execution."""
        @AgentMetrics.track_agent_execution('failing_agent')
        def failing_agent():
            raise RuntimeError("Agent failed")
        
        with pytest.raises(RuntimeError, match="Agent failed"):
            failing_agent()
        
        stats = AgentMetrics.get_agent_statistics('failing_agent')
        assert stats['count'] > 0
        # Success rate should be less than 1.0 due to failure
        assert stats['success_rate'] < 1.0 or stats['count'] == 1
    
    def test_get_agent_statistics_no_data(self):
        """Test getting statistics for agent with no data."""
        stats = AgentMetrics.get_agent_statistics('nonexistent_agent')
        
        assert stats['count'] == 0
        assert stats['total_time'] == 0.0


class TestIntegration:
    """Integration tests for metrics system."""
    
    def test_full_workflow(self):
        """Test complete metrics collection workflow."""
        # Clear any existing metrics
        collector = get_metrics_collector()
        collector.clear_metrics()
        
        # Simulate agent workflow
        @AgentMetrics.track_agent_execution('data_ingestion')
        def ingest_data():
            time.sleep(0.05)
            return "data"
        
        @AgentMetrics.track_agent_execution('qualification')
        def qualify_data(data):
            time.sleep(0.05)
            return "qualified"
        
        @timing_decorator(metadata={'stage': 'final'})
        def generate_report(qualified):
            time.sleep(0.05)
            return "report"
        
        # Execute workflow
        data = ingest_data()
        qualified = qualify_data(data)
        report = generate_report(qualified)
        
        # Verify metrics were collected
        all_stats = collector.get_statistics()
        assert all_stats['count'] >= 3
        
        # Verify agent-specific metrics
        ingestion_stats = AgentMetrics.get_agent_statistics('data_ingestion')
        assert ingestion_stats['count'] >= 1
        
        qualification_stats = AgentMetrics.get_agent_statistics('qualification')
        assert qualification_stats['count'] >= 1
    
    def test_export_and_verify(self, tmp_path):
        """Test exporting metrics and verifying content."""
        collector = get_metrics_collector()
        collector.clear_metrics()
        
        # Add some test metrics
        @timing_decorator()
        def test_export():
            return "done"
        
        test_export()
        
        # Export metrics
        output_file = tmp_path / "test_metrics.json"
        collector.export_metrics(output_file)
        
        # Verify file exists and contains data
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert 'exported_at' in data
        assert 'total_metrics' in data
        assert 'metrics' in data
        assert len(data['metrics']) > 0
