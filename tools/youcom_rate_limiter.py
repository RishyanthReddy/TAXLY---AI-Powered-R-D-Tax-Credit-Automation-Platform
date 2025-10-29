"""
You.com API Rate Limiter

This module provides endpoint-specific rate limiting for You.com APIs using
the token bucket algorithm. Different endpoints have different rate limits,
and this module ensures compliance with those limits while providing automatic
backoff when limits are approached.

Rate Limits by Endpoint:
- Search API: 10 requests per minute
- Agent API: 10 requests per minute
- Contents API: 10 requests per minute
- Express Agent API: 10 requests per minute
- News API: 10 requests per minute

The token bucket algorithm allows for burst traffic while maintaining average
rate limits over time.
"""

import time
import logging
import threading
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass

from utils.logger import get_tool_logger


# Get logger for rate limiter
logger = get_tool_logger("youcom_rate_limiter")


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""
    requests_per_minute: float
    burst_size: Optional[int] = None
    
    def __post_init__(self):
        """Set default burst size if not provided."""
        if self.burst_size is None:
            self.burst_size = int(self.requests_per_minute)


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    The token bucket algorithm maintains a bucket of tokens that are consumed
    by requests. Tokens are added to the bucket at a constant rate. When a
    request is made, it consumes a token. If no tokens are available, the
    request must wait until tokens become available.
    
    This allows for burst traffic (up to burst_size requests) while maintaining
    an average rate limit over time.
    """
    
    def __init__(
        self,
        requests_per_minute: float,
        burst_size: Optional[int] = None,
        name: str = "TokenBucket"
    ):
        """
        Initialize token bucket.
        
        Args:
            requests_per_minute: Maximum number of requests per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
            name: Name for logging purposes
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60.0
        self.burst_size = burst_size or int(requests_per_minute)
        self.name = name
        
        # Token state
        self.tokens = float(self.burst_size)
        self.last_update = time.time()
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Statistics
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.max_wait_time = 0.0
        self.backoff_count = 0
        
        logger.info(
            f"Initialized {name} token bucket "
            f"(rate={requests_per_minute}/min, burst={self.burst_size})"
        )
    
    def _refill_tokens(self):
        """
        Refill tokens based on time elapsed since last update.
        
        This method is called internally before each token acquisition to
        add tokens based on the configured rate.
        """
        current_time = time.time()
        time_elapsed = current_time - self.last_update
        
        # Add tokens based on time elapsed
        tokens_to_add = time_elapsed * self.requests_per_second
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        
        self.last_update = current_time
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> float:
        """
        Acquire tokens for making API requests.
        
        This method blocks until the requested number of tokens are available.
        If timeout is specified and tokens cannot be acquired within that time,
        raises TimeoutError.
        
        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum time to wait in seconds (None for no timeout)
        
        Returns:
            Time waited in seconds (0 if no wait was needed)
        
        Raises:
            TimeoutError: If tokens cannot be acquired within timeout
            ValueError: If tokens is less than 1 or greater than burst_size
        
        Example:
            >>> bucket = TokenBucket(requests_per_minute=10)
            >>> wait_time = bucket.acquire()  # Acquire 1 token
            >>> print(f"Waited {wait_time:.2f}s")
        """
        if tokens < 1:
            raise ValueError("tokens must be at least 1")
        
        if tokens > self.burst_size:
            raise ValueError(
                f"Cannot acquire {tokens} tokens, burst_size is {self.burst_size}"
            )
        
        start_time = time.time()
        
        with self.lock:
            # Refill tokens based on time elapsed
            self._refill_tokens()
            
            # If we have enough tokens, consume them and return
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.total_requests += 1
                return 0.0
            
            # Calculate wait time needed
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.requests_per_second
            
            # Check timeout
            if timeout is not None and wait_time > timeout:
                raise TimeoutError(
                    f"Cannot acquire {tokens} tokens within {timeout}s timeout "
                    f"(would need to wait {wait_time:.2f}s)"
                )
            
            # Log warning if wait time is significant
            if wait_time > 5.0:
                logger.warning(
                    f"[{self.name}] Rate limit: waiting {wait_time:.2f}s for {tokens} token(s)"
                )
                self.backoff_count += 1
            elif wait_time > 1.0:
                logger.info(
                    f"[{self.name}] Rate limit: waiting {wait_time:.2f}s for {tokens} token(s)"
                )
            else:
                logger.debug(
                    f"[{self.name}] Rate limit: waiting {wait_time:.2f}s for {tokens} token(s)"
                )
        
        # Wait outside the lock to allow other threads to check token availability
        time.sleep(wait_time)
        
        with self.lock:
            # Refill tokens after waiting
            self._refill_tokens()
            
            # Consume tokens
            self.tokens = max(0.0, self.tokens - tokens)
            
            # Update statistics
            self.total_requests += 1
            self.total_wait_time += wait_time
            self.max_wait_time = max(self.max_wait_time, wait_time)
            
            self.last_update = time.time()
        
        return wait_time
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.
        
        This method attempts to acquire tokens immediately. If tokens are not
        available, it returns False without waiting.
        
        Args:
            tokens: Number of tokens to acquire (default: 1)
        
        Returns:
            True if tokens were acquired, False otherwise
        
        Example:
            >>> bucket = TokenBucket(requests_per_minute=10)
            >>> if bucket.try_acquire():
            ...     # Make API request
            ...     pass
            ... else:
            ...     # Rate limit reached, handle accordingly
            ...     pass
        """
        with self.lock:
            # Refill tokens based on time elapsed
            self._refill_tokens()
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.total_requests += 1
                return True
            
            return False
    
    def get_available_tokens(self) -> float:
        """
        Get the current number of available tokens.
        
        Returns:
            Number of tokens currently available
        
        Example:
            >>> bucket = TokenBucket(requests_per_minute=10)
            >>> available = bucket.get_available_tokens()
            >>> print(f"{available:.1f} tokens available")
        """
        with self.lock:
            self._refill_tokens()
            return self.tokens
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get the estimated wait time to acquire tokens.
        
        Args:
            tokens: Number of tokens to check (default: 1)
        
        Returns:
            Estimated wait time in seconds (0 if tokens are available)
        
        Example:
            >>> bucket = TokenBucket(requests_per_minute=10)
            >>> wait = bucket.get_wait_time()
            >>> if wait > 0:
            ...     print(f"Would need to wait {wait:.2f}s")
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.requests_per_second
    
    def reset(self):
        """
        Reset the token bucket to full capacity.
        
        This method is useful for testing or when you want to clear the
        rate limit state.
        
        Example:
            >>> bucket = TokenBucket(requests_per_minute=10)
            >>> # ... make some requests ...
            >>> bucket.reset()  # Reset to full capacity
        """
        with self.lock:
            self.tokens = float(self.burst_size)
            self.last_update = time.time()
            logger.debug(f"[{self.name}] Token bucket reset to full capacity")
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about token bucket usage.
        
        Returns:
            Dictionary with statistics:
                - name: Bucket name
                - requests_per_minute: Configured rate limit
                - burst_size: Maximum burst size
                - total_requests: Total number of requests made
                - total_wait_time: Total time spent waiting (seconds)
                - average_wait_time: Average wait time per request (seconds)
                - max_wait_time: Maximum wait time for a single request (seconds)
                - backoff_count: Number of times significant backoff occurred (>5s wait)
                - available_tokens: Current number of available tokens
        
        Example:
            >>> bucket = TokenBucket(requests_per_minute=10)
            >>> # ... make some requests ...
            >>> stats = bucket.get_statistics()
            >>> print(f"Made {stats['total_requests']} requests")
            >>> print(f"Average wait: {stats['average_wait_time']:.2f}s")
        """
        with self.lock:
            self._refill_tokens()
            
            avg_wait = (
                self.total_wait_time / self.total_requests
                if self.total_requests > 0
                else 0.0
            )
            
            return {
                'name': self.name,
                'requests_per_minute': self.requests_per_minute,
                'burst_size': self.burst_size,
                'total_requests': self.total_requests,
                'total_wait_time': self.total_wait_time,
                'average_wait_time': avg_wait,
                'max_wait_time': self.max_wait_time,
                'backoff_count': self.backoff_count,
                'available_tokens': self.tokens
            }


class YouComRateLimiter:
    """
    Rate limiter for You.com APIs with per-endpoint limits.
    
    This class manages separate token buckets for each You.com API endpoint,
    ensuring that rate limits are enforced correctly for each API. It provides
    automatic backoff when limits are approached and detailed logging of rate
    limit events.
    
    Endpoint Rate Limits:
    - Search API: 10 requests per minute
    - Agent API: 10 requests per minute
    - Contents API: 10 requests per minute
    - Express Agent API: 10 requests per minute (same as Agent API)
    - News API: 10 requests per minute
    """
    
    # Default rate limit configurations for each endpoint
    DEFAULT_LIMITS = {
        'search': RateLimitConfig(requests_per_minute=10, burst_size=10),
        'news': RateLimitConfig(requests_per_minute=10, burst_size=10),
        'agent': RateLimitConfig(requests_per_minute=10, burst_size=10),
        'contents': RateLimitConfig(requests_per_minute=10, burst_size=10),
        'express_agent': RateLimitConfig(requests_per_minute=10, burst_size=10),
    }
    
    def __init__(
        self,
        custom_limits: Optional[Dict[str, RateLimitConfig]] = None,
        enable_backoff_warnings: bool = True
    ):
        """
        Initialize You.com rate limiter.
        
        Args:
            custom_limits: Optional custom rate limit configurations per endpoint
                          Format: {'endpoint_name': RateLimitConfig(...)}
                          If not provided, uses DEFAULT_LIMITS
            enable_backoff_warnings: Enable warnings when significant backoff occurs
        
        Example:
            >>> # Use default limits
            >>> limiter = YouComRateLimiter()
            >>> 
            >>> # Use custom limits
            >>> from tools.youcom_rate_limiter import RateLimitConfig
            >>> custom = {
            ...     'agent': RateLimitConfig(requests_per_minute=5, burst_size=5)
            ... }
            >>> limiter = YouComRateLimiter(custom_limits=custom)
        """
        self.enable_backoff_warnings = enable_backoff_warnings
        
        # Merge custom limits with defaults
        limits = self.DEFAULT_LIMITS.copy()
        if custom_limits:
            limits.update(custom_limits)
        
        # Create token buckets for each endpoint
        self.buckets: Dict[str, TokenBucket] = {}
        for endpoint, config in limits.items():
            self.buckets[endpoint] = TokenBucket(
                requests_per_minute=config.requests_per_minute,
                burst_size=config.burst_size,
                name=f"YouCom-{endpoint}"
            )
        
        logger.info(
            f"Initialized You.com rate limiter with {len(self.buckets)} endpoint(s)"
        )
    
    def acquire(self, endpoint: str, tokens: int = 1) -> float:
        """
        Acquire tokens for a specific endpoint.
        
        This method blocks until tokens are available for the specified endpoint.
        It automatically handles rate limiting and logs warnings when significant
        backoff occurs.
        
        Args:
            endpoint: Endpoint name ('search', 'agent', 'contents', 'express_agent', 'news')
            tokens: Number of tokens to acquire (default: 1)
        
        Returns:
            Time waited in seconds (0 if no wait was needed)
        
        Raises:
            ValueError: If endpoint is not recognized
        
        Example:
            >>> limiter = YouComRateLimiter()
            >>> 
            >>> # Before making a search API call
            >>> wait_time = limiter.acquire('search')
            >>> # Now safe to make the API call
            >>> result = client.search(query="...")
        """
        if endpoint not in self.buckets:
            raise ValueError(
                f"Unknown endpoint '{endpoint}'. "
                f"Valid endpoints: {list(self.buckets.keys())}"
            )
        
        bucket = self.buckets[endpoint]
        
        # Check if we're approaching the limit
        available = bucket.get_available_tokens()
        if available < 2.0 and self.enable_backoff_warnings:
            logger.warning(
                f"[YouCom-{endpoint}] Approaching rate limit "
                f"({available:.1f} tokens remaining)"
            )
        
        # Acquire tokens
        wait_time = bucket.acquire(tokens=tokens)
        
        return wait_time
    
    def try_acquire(self, endpoint: str, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.
        
        This method attempts to acquire tokens immediately. If tokens are not
        available, it returns False without waiting. This is useful when you
        want to implement custom backoff logic or skip requests when rate
        limited.
        
        Args:
            endpoint: Endpoint name ('search', 'agent', 'contents', 'express_agent', 'news')
            tokens: Number of tokens to acquire (default: 1)
        
        Returns:
            True if tokens were acquired, False otherwise
        
        Raises:
            ValueError: If endpoint is not recognized
        
        Example:
            >>> limiter = YouComRateLimiter()
            >>> 
            >>> if limiter.try_acquire('agent'):
            ...     # Make API call
            ...     result = client.agent_run(prompt="...")
            ... else:
            ...     # Rate limited, handle accordingly
            ...     print("Rate limited, try again later")
        """
        if endpoint not in self.buckets:
            raise ValueError(
                f"Unknown endpoint '{endpoint}'. "
                f"Valid endpoints: {list(self.buckets.keys())}"
            )
        
        return self.buckets[endpoint].try_acquire(tokens=tokens)
    
    def get_wait_time(self, endpoint: str, tokens: int = 1) -> float:
        """
        Get estimated wait time for an endpoint.
        
        Args:
            endpoint: Endpoint name ('search', 'agent', 'contents', 'express_agent', 'news')
            tokens: Number of tokens to check (default: 1)
        
        Returns:
            Estimated wait time in seconds (0 if tokens are available)
        
        Raises:
            ValueError: If endpoint is not recognized
        
        Example:
            >>> limiter = YouComRateLimiter()
            >>> wait = limiter.get_wait_time('search')
            >>> if wait > 0:
            ...     print(f"Would need to wait {wait:.2f}s before next search")
        """
        if endpoint not in self.buckets:
            raise ValueError(
                f"Unknown endpoint '{endpoint}'. "
                f"Valid endpoints: {list(self.buckets.keys())}"
            )
        
        return self.buckets[endpoint].get_wait_time(tokens=tokens)
    
    def get_available_tokens(self, endpoint: str) -> float:
        """
        Get available tokens for an endpoint.
        
        Args:
            endpoint: Endpoint name ('search', 'agent', 'contents', 'express_agent', 'news')
        
        Returns:
            Number of tokens currently available
        
        Raises:
            ValueError: If endpoint is not recognized
        
        Example:
            >>> limiter = YouComRateLimiter()
            >>> available = limiter.get_available_tokens('agent')
            >>> print(f"{available:.1f} tokens available for agent API")
        """
        if endpoint not in self.buckets:
            raise ValueError(
                f"Unknown endpoint '{endpoint}'. "
                f"Valid endpoints: {list(self.buckets.keys())}"
            )
        
        return self.buckets[endpoint].get_available_tokens()
    
    def reset(self, endpoint: Optional[str] = None):
        """
        Reset rate limiter(s) to full capacity.
        
        Args:
            endpoint: Specific endpoint to reset, or None to reset all
        
        Example:
            >>> limiter = YouComRateLimiter()
            >>> 
            >>> # Reset specific endpoint
            >>> limiter.reset('search')
            >>> 
            >>> # Reset all endpoints
            >>> limiter.reset()
        """
        if endpoint is not None:
            if endpoint not in self.buckets:
                raise ValueError(
                    f"Unknown endpoint '{endpoint}'. "
                    f"Valid endpoints: {list(self.buckets.keys())}"
                )
            self.buckets[endpoint].reset()
            logger.info(f"Reset rate limiter for endpoint: {endpoint}")
        else:
            for bucket in self.buckets.values():
                bucket.reset()
            logger.info("Reset all rate limiters")
    
    def get_statistics(self, endpoint: Optional[str] = None) -> Dict[str, any]:
        """
        Get rate limiter statistics.
        
        Args:
            endpoint: Specific endpoint to get stats for, or None for all endpoints
        
        Returns:
            Dictionary with statistics:
                - If endpoint specified: Statistics for that endpoint
                - If endpoint is None: Dictionary mapping endpoint names to their statistics
        
        Example:
            >>> limiter = YouComRateLimiter()
            >>> # ... make some API calls ...
            >>> 
            >>> # Get stats for specific endpoint
            >>> search_stats = limiter.get_statistics('search')
            >>> print(f"Search API: {search_stats['total_requests']} requests")
            >>> 
            >>> # Get stats for all endpoints
            >>> all_stats = limiter.get_statistics()
            >>> for endpoint, stats in all_stats.items():
            ...     print(f"{endpoint}: {stats['total_requests']} requests")
        """
        if endpoint is not None:
            if endpoint not in self.buckets:
                raise ValueError(
                    f"Unknown endpoint '{endpoint}'. "
                    f"Valid endpoints: {list(self.buckets.keys())}"
                )
            return self.buckets[endpoint].get_statistics()
        else:
            return {
                endpoint: bucket.get_statistics()
                for endpoint, bucket in self.buckets.items()
            }
    
    def log_statistics(self):
        """
        Log statistics for all endpoints.
        
        This method logs a summary of rate limiter usage for all endpoints,
        including request counts, wait times, and backoff events.
        
        Example:
            >>> limiter = YouComRateLimiter()
            >>> # ... make some API calls ...
            >>> limiter.log_statistics()
        """
        logger.info("=== You.com Rate Limiter Statistics ===")
        
        all_stats = self.get_statistics()
        
        for endpoint, stats in all_stats.items():
            logger.info(
                f"[{endpoint}] "
                f"Requests: {stats['total_requests']}, "
                f"Total wait: {stats['total_wait_time']:.2f}s, "
                f"Avg wait: {stats['average_wait_time']:.3f}s, "
                f"Max wait: {stats['max_wait_time']:.2f}s, "
                f"Backoffs: {stats['backoff_count']}, "
                f"Available: {stats['available_tokens']:.1f} tokens"
            )
        
        logger.info("=" * 40)
