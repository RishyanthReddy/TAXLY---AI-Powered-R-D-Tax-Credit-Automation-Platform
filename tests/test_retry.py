"""
Unit tests for retry and backoff utilities.

This module tests the retry_with_backoff decorator and related utilities
to ensure proper exponential backoff, jitter, and error handling behavior.
"""

import pytest
import time
from unittest.mock import Mock, patch

from utils.retry import (
    retry_with_backoff,
    retry_api_call,
    retry_rag_operation,
    get_default_retry_decorator,
    DEFAULT_RETRY_CONFIG
)
from utils.exceptions import (
    APIConnectionError,
    RAGRetrievalError
)


class TestRetryWithBackoff:
    """Test suite for retry_with_backoff decorator."""
    
    def test_successful_call_no_retry(self):
        """Test that successful calls don't trigger retries."""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        
        assert result == "success"
        assert call_count == 1  # Should only be called once
    
    def test_retry_on_failure_then_success(self):
        """Test that function retries on failure and succeeds eventually."""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.1, jitter=False)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = flaky_function()
        
        assert result == "success"
        assert call_count == 3  # Should be called 3 times
    
    def test_all_attempts_fail(self):
        """Test that exception is raised after all attempts fail."""
        call_count = 0
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.1, jitter=False)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent failure")
        
        with pytest.raises(ValueError, match="Permanent failure"):
            always_fails()
        
        assert call_count == 3  # Should attempt all 3 times
    
    def test_exponential_backoff_timing(self):
        """Test that delays follow exponential backoff pattern."""
        call_times = []
        
        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.1,
            multiplier=2.0,
            jitter=False
        )
        def timed_function():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Retry needed")
            return "success"
        
        result = timed_function()
        
        assert result == "success"
        assert len(call_times) == 3
        
        # Check delays between calls (with some tolerance for timing)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        # First delay should be ~0.1s, second should be ~0.2s
        assert 0.08 < delay1 < 0.15  # Allow 20% tolerance
        assert 0.18 < delay2 < 0.25  # Allow 20% tolerance
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        call_times = []
        
        @retry_with_backoff(
            max_attempts=4,
            initial_delay=1.0,
            multiplier=10.0,  # Would grow very large
            max_delay=0.5,    # But capped at 0.5s
            jitter=False
        )
        def capped_function():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise ValueError("Retry needed")
            return "success"
        
        result = capped_function()
        
        assert result == "success"
        
        # All delays should be capped at max_delay (0.5s)
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i-1]
            assert delay <= 0.6  # Allow small tolerance
    
    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays."""
        delays = []
        
        for _ in range(5):
            call_times = []
            
            @retry_with_backoff(
                max_attempts=2,
                initial_delay=0.2,
                multiplier=2.0,
                jitter=True
            )
            def jittered_function():
                call_times.append(time.time())
                if len(call_times) < 2:
                    raise ValueError("Retry needed")
                return "success"
            
            jittered_function()
            
            if len(call_times) >= 2:
                delays.append(call_times[1] - call_times[0])
        
        # With jitter, delays should vary
        # Check that not all delays are identical
        assert len(set(delays)) > 1 or len(delays) == 0
    
    def test_specific_exception_types(self):
        """Test that only specified exceptions trigger retries."""
        call_count = 0
        
        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.1,
            exceptions=(ValueError,)
        )
        def selective_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("This should retry")
            elif call_count == 2:
                raise TypeError("This should not retry")
            return "success"
        
        with pytest.raises(TypeError, match="This should not retry"):
            selective_retry()
        
        assert call_count == 2  # Should stop after TypeError
    
    def test_on_retry_callback(self):
        """Test that on_retry callback is called before each retry."""
        callback_calls = []
        
        def retry_callback(exception, attempt, delay):
            callback_calls.append({
                'exception': str(exception),
                'attempt': attempt,
                'delay': delay
            })
        
        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.1,
            jitter=False,
            on_retry=retry_callback
        )
        def callback_function():
            if len(callback_calls) < 2:
                raise ValueError("Retry needed")
            return "success"
        
        result = callback_function()
        
        assert result == "success"
        assert len(callback_calls) == 2  # Called before 2nd and 3rd attempts
        assert callback_calls[0]['attempt'] == 1
        assert callback_calls[1]['attempt'] == 2


class TestRetryAPICall:
    """Test suite for retry_api_call decorator."""
    
    def test_api_call_retry_on_api_error(self):
        """Test that API calls retry on APIConnectionError."""
        call_count = 0
        
        @retry_api_call(max_attempts=3, initial_delay=0.1)
        def api_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIConnectionError(
                    "API temporarily unavailable",
                    api_name="TestAPI",
                    status_code=503
                )
            return {"data": "success"}
        
        result = api_function()
        
        assert result == {"data": "success"}
        assert call_count == 3
    
    def test_api_call_retry_on_timeout(self):
        """Test that API calls retry on TimeoutError."""
        call_count = 0
        
        @retry_api_call(max_attempts=2, initial_delay=0.1)
        def timeout_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Request timed out")
            return "success"
        
        result = timeout_function()
        
        assert result == "success"
        assert call_count == 2


class TestRetryRAGOperation:
    """Test suite for retry_rag_operation decorator."""
    
    def test_rag_operation_retry(self):
        """Test that RAG operations retry on RAGRetrievalError."""
        call_count = 0
        
        @retry_rag_operation(max_attempts=2, initial_delay=0.1)
        def rag_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RAGRetrievalError(
                    "Vector database temporarily unavailable",
                    query="test query"
                )
            return ["result1", "result2"]
        
        result = rag_function()
        
        assert result == ["result1", "result2"]
        assert call_count == 2


class TestDefaultRetryDecorator:
    """Test suite for default retry decorator."""
    
    def test_default_config_values(self):
        """Test that default configuration has expected values."""
        assert DEFAULT_RETRY_CONFIG['max_attempts'] == 3
        assert DEFAULT_RETRY_CONFIG['initial_delay'] == 1.0
        assert DEFAULT_RETRY_CONFIG['multiplier'] == 2.0
        assert DEFAULT_RETRY_CONFIG['max_delay'] == 60.0
        assert DEFAULT_RETRY_CONFIG['jitter'] is True
    
    def test_get_default_retry_decorator(self):
        """Test that default retry decorator works correctly."""
        call_count = 0
        
        default_retry = get_default_retry_decorator()
        
        @default_retry
        def default_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry needed")
            return "success"
        
        result = default_function()
        
        assert result == "success"
        assert call_count == 2
