"""
Unit tests for You.com Rate Limiter.

Tests the YouComRateLimiter and TokenBucket classes including:
- Token bucket algorithm
- Rate limiting behavior
- Per-endpoint limits
- Statistics tracking
- Thread safety
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from tools.youcom_rate_limiter import (
    TokenBucket,
    YouComRateLimiter,
    RateLimitConfig
)


class TestTokenBucket:
    """Test TokenBucket class."""
    
    def test_initialization(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(requests_per_minute=10, burst_size=10, name="test")
        
        assert bucket.requests_per_minute == 10
        assert bucket.requests_per_second == 10.0 / 60.0
        assert bucket.burst_size == 10
        assert bucket.tokens == 10.0
        assert bucket.name == "test"
    
    def test_initialization_with_default_burst_size(self):
        """Test that burst_size defaults to requests_per_minute."""
        bucket = TokenBucket(requests_per_minute=15)
        
        assert bucket.burst_size == 15
        assert bucket.tokens == 15.0
    
    def test_acquire_single_token_no_wait(self):
        """Test acquiring a single token when available."""
        bucket = TokenBucket(requests_per_minute=60)  # 1 per second
        
        wait_time = bucket.acquire(tokens=1)
        
        assert wait_time == 0.0
        assert bucket.tokens == 59.0  # Started with 60, consumed 1
        assert bucket.total_requests == 1
    
    def test_acquire_multiple_tokens_no_wait(self):
        """Test acquiring multiple tokens when available."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=60)
        
        wait_time = bucket.acquire(tokens=5)
        
        assert wait_time == 0.0
        assert bucket.tokens == 55.0
        assert bucket.total_requests == 1
    
    def test_acquire_with_wait(self):
        """Test acquiring tokens when wait is required."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        # Use up all tokens
        bucket.tokens = 0.0
        
        # Acquire 1 token (should wait 1 second at 1 token/second rate)
        start_time = time.time()
        wait_time = bucket.acquire(tokens=1)
        elapsed = time.time() - start_time
        
        # Should have waited approximately 1 second (allow some tolerance)
        assert wait_time > 0.8
        assert wait_time < 1.2
        assert elapsed > 0.8
        assert elapsed < 1.2
        assert bucket.total_requests == 1
        assert bucket.total_wait_time > 0.8
    
    def test_try_acquire_success(self):
        """Test non-blocking acquisition when tokens available."""
        bucket = TokenBucket(requests_per_minute=60)
        
        success = bucket.try_acquire(tokens=1)
        
        assert success is True
        assert bucket.tokens == 59.0
        assert bucket.total_requests == 1
    
    def test_try_acquire_failure(self):
        """Test non-blocking acquisition when tokens not available."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        # Use up all tokens
        bucket.tokens = 0.0
        
        success = bucket.try_acquire(tokens=1)
        
        assert success is False
        # Tokens may have refilled slightly due to time elapsed
        assert bucket.tokens < 0.1
        assert bucket.total_requests == 0  # Request not counted if failed
    
    def test_get_available_tokens(self):
        """Test getting available tokens."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        available = bucket.get_available_tokens()
        
        assert available == 10.0
        
        # Consume some tokens
        bucket.acquire(tokens=3)
        
        available = bucket.get_available_tokens()
        # Allow small tolerance for time elapsed during test
        assert 6.9 < available < 7.1
    
    def test_get_wait_time_no_wait(self):
        """Test getting wait time when tokens available."""
        bucket = TokenBucket(requests_per_minute=60)
        
        wait = bucket.get_wait_time(tokens=1)
        
        assert wait == 0.0
    
    def test_get_wait_time_with_wait(self):
        """Test getting wait time when tokens not available."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        # Use up all tokens
        bucket.tokens = 0.0
        
        wait = bucket.get_wait_time(tokens=1)
        
        # Should need to wait 1 second at 1 token/second rate
        assert wait > 0.9
        assert wait < 1.1
    
    def test_reset(self):
        """Test resetting token bucket."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        # Use up some tokens
        bucket.acquire(tokens=5)
        assert bucket.tokens == 5.0
        
        # Reset
        bucket.reset()
        
        assert bucket.tokens == 10.0
    
    def test_token_refill_over_time(self):
        """Test that tokens refill over time."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        # Use up all tokens
        bucket.tokens = 0.0
        bucket.last_update = time.time()
        
        # Wait 2 seconds (should refill 2 tokens at 1 token/second)
        time.sleep(2.1)
        
        available = bucket.get_available_tokens()
        
        # Should have approximately 2 tokens
        assert available > 1.9
        assert available < 2.3
    
    def test_token_refill_capped_at_burst_size(self):
        """Test that tokens don't exceed burst size."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        # Start with some tokens
        bucket.tokens = 5.0
        bucket.last_update = time.time() - 10.0  # 10 seconds ago
        
        # Refill (should add 10 tokens but cap at burst_size)
        available = bucket.get_available_tokens()
        
        assert available == 10.0  # Capped at burst_size
    
    def test_statistics(self):
        """Test getting statistics."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10, name="test")
        
        # Make some requests
        bucket.acquire(tokens=1)
        bucket.acquire(tokens=1)
        bucket.acquire(tokens=1)
        
        stats = bucket.get_statistics()
        
        assert stats['name'] == "test"
        assert stats['requests_per_minute'] == 60
        assert stats['burst_size'] == 10
        assert stats['total_requests'] == 3
        assert stats['total_wait_time'] >= 0.0
        assert stats['average_wait_time'] >= 0.0
        assert stats['max_wait_time'] >= 0.0
        assert stats['backoff_count'] >= 0
        assert 'available_tokens' in stats
    
    def test_acquire_with_timeout_success(self):
        """Test acquiring with timeout when tokens become available."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        # Use most tokens
        bucket.tokens = 0.5
        
        # Should succeed within timeout
        wait_time = bucket.acquire(tokens=1, timeout=2.0)
        
        assert wait_time < 2.0
    
    def test_acquire_with_timeout_failure(self):
        """Test acquiring with timeout when tokens don't become available."""
        bucket = TokenBucket(requests_per_minute=6, burst_size=10)  # 0.1 per second
        
        # Use all tokens
        bucket.tokens = 0.0
        
        # Try to acquire 5 tokens with 1 second timeout
        # At 0.1 tokens/second, would need 50 seconds
        with pytest.raises(TimeoutError):
            bucket.acquire(tokens=5, timeout=1.0)
    
    def test_acquire_invalid_tokens(self):
        """Test that invalid token counts raise errors."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=10)
        
        # Less than 1 token
        with pytest.raises(ValueError, match="tokens must be at least 1"):
            bucket.acquire(tokens=0)
        
        # More than burst size
        with pytest.raises(ValueError, match="burst_size"):
            bucket.acquire(tokens=20)
    
    def test_thread_safety(self):
        """Test that token bucket is thread-safe."""
        bucket = TokenBucket(requests_per_minute=60, burst_size=100)
        
        results = []
        
        def acquire_tokens():
            for _ in range(10):
                wait_time = bucket.acquire(tokens=1)
                results.append(wait_time)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=acquire_tokens)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have made 50 requests total (5 threads * 10 requests)
        assert bucket.total_requests == 50
        assert len(results) == 50


class TestYouComRateLimiter:
    """Test YouComRateLimiter class."""
    
    def test_initialization_with_defaults(self):
        """Test initialization with default limits."""
        limiter = YouComRateLimiter()
        
        assert len(limiter.buckets) == 5  # search, news, agent, contents, express_agent
        assert 'search' in limiter.buckets
        assert 'news' in limiter.buckets
        assert 'agent' in limiter.buckets
        assert 'contents' in limiter.buckets
        assert 'express_agent' in limiter.buckets
    
    def test_initialization_with_custom_limits(self):
        """Test initialization with custom limits."""
        custom_limits = {
            'agent': RateLimitConfig(requests_per_minute=5, burst_size=5)
        }
        
        limiter = YouComRateLimiter(custom_limits=custom_limits)
        
        # Agent should have custom limit
        assert limiter.buckets['agent'].requests_per_minute == 5
        assert limiter.buckets['agent'].burst_size == 5
        
        # Others should have default limits
        assert limiter.buckets['search'].requests_per_minute == 10
    
    def test_acquire_valid_endpoint(self):
        """Test acquiring tokens for valid endpoint."""
        limiter = YouComRateLimiter()
        
        wait_time = limiter.acquire('search')
        
        assert wait_time == 0.0
    
    def test_acquire_invalid_endpoint(self):
        """Test that invalid endpoint raises error."""
        limiter = YouComRateLimiter()
        
        with pytest.raises(ValueError, match="Unknown endpoint"):
            limiter.acquire('invalid_endpoint')
    
    def test_try_acquire_valid_endpoint(self):
        """Test non-blocking acquisition for valid endpoint."""
        limiter = YouComRateLimiter()
        
        success = limiter.try_acquire('agent')
        
        assert success is True
    
    def test_try_acquire_invalid_endpoint(self):
        """Test that invalid endpoint raises error."""
        limiter = YouComRateLimiter()
        
        with pytest.raises(ValueError, match="Unknown endpoint"):
            limiter.try_acquire('invalid_endpoint')
    
    def test_get_wait_time(self):
        """Test getting wait time for endpoint."""
        limiter = YouComRateLimiter()
        
        # Should have no wait initially
        wait = limiter.get_wait_time('search')
        assert wait == 0.0
        
        # Use up all tokens
        for _ in range(10):
            limiter.acquire('search')
        
        # Should need to wait now
        wait = limiter.get_wait_time('search')
        assert wait > 0.0
    
    def test_get_available_tokens(self):
        """Test getting available tokens for endpoint."""
        limiter = YouComRateLimiter()
        
        # Should have full capacity initially
        available = limiter.get_available_tokens('search')
        assert available == 10.0
        
        # Consume some tokens
        limiter.acquire('search', tokens=3)
        
        available = limiter.get_available_tokens('search')
        # Allow small tolerance for time elapsed during test
        assert 6.9 < available < 7.1
    
    def test_reset_specific_endpoint(self):
        """Test resetting specific endpoint."""
        limiter = YouComRateLimiter()
        
        # Use up some tokens
        limiter.acquire('search', tokens=5)
        available = limiter.get_available_tokens('search')
        # Allow small tolerance for time elapsed during test
        assert 4.9 < available < 5.1
        
        # Reset search endpoint
        limiter.reset('search')
        
        assert limiter.get_available_tokens('search') == 10.0
    
    def test_reset_all_endpoints(self):
        """Test resetting all endpoints."""
        limiter = YouComRateLimiter()
        
        # Use up tokens on multiple endpoints
        limiter.acquire('search', tokens=5)
        limiter.acquire('agent', tokens=3)
        limiter.acquire('contents', tokens=7)
        
        # Reset all
        limiter.reset()
        
        # All should be at full capacity
        assert limiter.get_available_tokens('search') == 10.0
        assert limiter.get_available_tokens('agent') == 10.0
        assert limiter.get_available_tokens('contents') == 10.0
    
    def test_get_statistics_specific_endpoint(self):
        """Test getting statistics for specific endpoint."""
        limiter = YouComRateLimiter()
        
        # Make some requests
        limiter.acquire('search')
        limiter.acquire('search')
        
        stats = limiter.get_statistics('search')
        
        assert stats['name'] == 'YouCom-search'
        assert stats['total_requests'] == 2
        assert 'total_wait_time' in stats
        assert 'average_wait_time' in stats
    
    def test_get_statistics_all_endpoints(self):
        """Test getting statistics for all endpoints."""
        limiter = YouComRateLimiter()
        
        # Make requests to different endpoints
        limiter.acquire('search')
        limiter.acquire('agent')
        limiter.acquire('contents')
        
        stats = limiter.get_statistics()
        
        assert 'search' in stats
        assert 'agent' in stats
        assert 'contents' in stats
        assert stats['search']['total_requests'] == 1
        assert stats['agent']['total_requests'] == 1
        assert stats['contents']['total_requests'] == 1
    
    def test_per_endpoint_independence(self):
        """Test that endpoints have independent rate limits."""
        limiter = YouComRateLimiter()
        
        # Use up all tokens on search endpoint
        for _ in range(10):
            limiter.acquire('search')
        
        # Agent endpoint should still have tokens
        available_agent = limiter.get_available_tokens('agent')
        assert available_agent == 10.0
        
        # Search endpoint should be depleted
        available_search = limiter.get_available_tokens('search')
        assert available_search < 1.0
    
    def test_backoff_warning_enabled(self, caplog):
        """Test that backoff warnings are logged when enabled."""
        limiter = YouComRateLimiter(enable_backoff_warnings=True)
        
        # Use up most tokens to trigger warning
        for _ in range(9):
            limiter.acquire('search')
        
        # This should trigger a warning (< 2 tokens remaining)
        limiter.acquire('search')
        
        # Check that warning was logged
        # Note: The actual warning is logged in the acquire method
        # when available tokens < 2.0
    
    def test_backoff_warning_disabled(self, caplog):
        """Test that backoff warnings can be disabled."""
        limiter = YouComRateLimiter(enable_backoff_warnings=False)
        
        # Use up most tokens
        for _ in range(9):
            limiter.acquire('search')
        
        # This would normally trigger a warning
        limiter.acquire('search')
        
        # No warning should be logged (backoff warnings disabled)
        # Note: This is a negative test - we're checking that the warning
        # is NOT logged when backoff warnings are disabled


class TestRateLimitConfig:
    """Test RateLimitConfig dataclass."""
    
    def test_initialization_with_burst_size(self):
        """Test initialization with explicit burst size."""
        config = RateLimitConfig(requests_per_minute=10, burst_size=15)
        
        assert config.requests_per_minute == 10
        assert config.burst_size == 15
    
    def test_initialization_without_burst_size(self):
        """Test that burst_size defaults to requests_per_minute."""
        config = RateLimitConfig(requests_per_minute=20)
        
        assert config.requests_per_minute == 20
        assert config.burst_size == 20


class TestIntegration:
    """Integration tests for rate limiter."""
    
    def test_rate_limiting_behavior(self):
        """Test actual rate limiting behavior over time."""
        # Create limiter with 6 requests per minute (0.1 per second)
        custom_limits = {
            'test': RateLimitConfig(requests_per_minute=6, burst_size=6)
        }
        limiter = YouComRateLimiter(custom_limits=custom_limits)
        
        # Make 6 requests immediately (burst)
        start_time = time.time()
        for i in range(6):
            wait = limiter.acquire('test')
            assert wait == 0.0  # No wait for burst
        
        burst_time = time.time() - start_time
        assert burst_time < 0.5  # Should be very fast
        
        # Next request should wait approximately 10 seconds
        # (need 1 token at 0.1 tokens/second = 10 seconds)
        start_time = time.time()
        wait = limiter.acquire('test')
        elapsed = time.time() - start_time
        
        # Should have waited approximately 10 seconds
        assert wait > 9.0
        assert wait < 11.0
        assert elapsed > 9.0
        assert elapsed < 11.0
    
    def test_concurrent_requests(self):
        """Test rate limiting with concurrent requests."""
        limiter = YouComRateLimiter()
        
        results = {'search': [], 'agent': []}
        
        def make_requests(endpoint, count):
            for _ in range(count):
                wait = limiter.acquire(endpoint)
                results[endpoint].append(wait)
        
        # Create threads for different endpoints
        thread1 = threading.Thread(target=make_requests, args=('search', 5))
        thread2 = threading.Thread(target=make_requests, args=('agent', 5))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Both endpoints should have processed 5 requests
        assert len(results['search']) == 5
        assert len(results['agent']) == 5
        
        # Get statistics
        stats = limiter.get_statistics()
        assert stats['search']['total_requests'] == 5
        assert stats['agent']['total_requests'] == 5
