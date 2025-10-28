"""
Retry and exponential backoff utilities for handling transient failures.

This module provides decorators and utilities for implementing retry logic
with exponential backoff and jitter to handle transient failures in API calls,
database operations, and other potentially unreliable operations.
"""

import functools
import random
import time
import logging
from typing import Callable, Type, Tuple, Optional

from .exceptions import APIConnectionError, RAGRetrievalError, AgentExecutionError


# Configure logger for retry operations
logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    multiplier: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """
    Decorator that retries a function with exponential backoff on failure.
    
    This decorator implements a robust retry mechanism with exponential backoff
    and optional jitter to prevent thundering herd problems. It's designed for
    handling transient failures in API calls, network operations, and other
    potentially unreliable operations.
    
    Args:
        max_attempts: Maximum number of attempts (including initial call).
                     Default is 3 attempts.
        initial_delay: Initial delay in seconds before first retry.
                      Default is 1.0 second.
        multiplier: Multiplier for exponential backoff. Each retry delay is
                   multiplied by this value. Default is 2.0 (doubles each time).
        max_delay: Maximum delay in seconds between retries. Prevents delays
                  from growing too large. Default is 60.0 seconds.
        jitter: If True, adds random jitter to delay to prevent thundering herd.
               Jitter is uniformly distributed between 0 and the calculated delay.
               Default is True.
        exceptions: Tuple of exception types to catch and retry. Only these
                   exceptions will trigger a retry. Default is (Exception,).
        on_retry: Optional callback function called before each retry.
                 Receives (exception, attempt_number, delay) as arguments.
                 Useful for logging or custom retry logic.
    
    Returns:
        Decorated function that implements retry logic.
    
    Raises:
        The last exception encountered if all retry attempts are exhausted.
    
    Example:
        >>> @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        ... def fetch_data_from_api():
        ...     response = requests.get('https://api.example.com/data')
        ...     response.raise_for_status()
        ...     return response.json()
        
        >>> @retry_with_backoff(
        ...     max_attempts=5,
        ...     initial_delay=2.0,
        ...     multiplier=2.0,
        ...     exceptions=(APIConnectionError, TimeoutError)
        ... )
        ... def call_external_service():
        ...     return service.call()
    
    Notes:
        - The decorator calculates delay as: initial_delay * (multiplier ** attempt)
        - Jitter adds randomness: actual_delay = random.uniform(0, calculated_delay)
        - The first call (attempt 1) happens immediately without delay
        - Retries start from attempt 2 onwards
        - If max_delay is reached, subsequent delays are capped at max_delay
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    # Attempt to call the function
                    result = func(*args, **kwargs)
                    
                    # Log success if this was a retry
                    if attempt > 1:
                        logger.info(
                            f"Function '{func.__name__}' succeeded on attempt {attempt}/{max_attempts}"
                        )
                    
                    return result
                
                except exceptions as e:
                    last_exception = e
                    
                    # If this was the last attempt, raise the exception
                    if attempt == max_attempts:
                        logger.error(
                            f"Function '{func.__name__}' failed after {max_attempts} attempts. "
                            f"Last error: {str(e)}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    # Formula: initial_delay * (multiplier ^ (attempt - 1))
                    delay = initial_delay * (multiplier ** (attempt - 1))
                    
                    # Cap delay at max_delay
                    delay = min(delay, max_delay)
                    
                    # Add jitter if enabled
                    if jitter:
                        # Uniform random jitter between 0 and calculated delay
                        delay = random.uniform(0, delay)
                    
                    # Log retry attempt
                    logger.warning(
                        f"Function '{func.__name__}' failed on attempt {attempt}/{max_attempts}. "
                        f"Error: {str(e)}. Retrying in {delay:.2f} seconds..."
                    )
                    
                    # Call custom retry callback if provided
                    if on_retry:
                        try:
                            on_retry(e, attempt, delay)
                        except Exception as callback_error:
                            logger.error(
                                f"Error in on_retry callback: {str(callback_error)}"
                            )
                    
                    # Wait before retrying
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_api_call(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    multiplier: float = 2.0
):
    """
    Specialized retry decorator for API calls.
    
    This is a convenience wrapper around retry_with_backoff specifically
    configured for API calls. It catches common API-related exceptions
    and uses sensible defaults for API retry scenarios.
    
    Args:
        max_attempts: Maximum number of attempts. Default is 3.
        initial_delay: Initial delay in seconds. Default is 1.0.
        multiplier: Backoff multiplier. Default is 2.0.
    
    Returns:
        Decorated function with API-specific retry logic.
    
    Example:
        >>> @retry_api_call(max_attempts=5)
        ... def fetch_clockify_data(workspace_id: str):
        ...     return clockify_client.get_time_entries(workspace_id)
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        multiplier=multiplier,
        max_delay=30.0,  # Cap at 30 seconds for API calls
        jitter=True,
        exceptions=(
            APIConnectionError,
            ConnectionError,
            TimeoutError,
        )
    )


def retry_rag_operation(
    max_attempts: int = 2,
    initial_delay: float = 0.5,
    multiplier: float = 2.0
):
    """
    Specialized retry decorator for RAG operations.
    
    This is a convenience wrapper around retry_with_backoff specifically
    configured for RAG knowledge base operations. Uses shorter delays
    since RAG operations are typically local or fast.
    
    Args:
        max_attempts: Maximum number of attempts. Default is 2.
        initial_delay: Initial delay in seconds. Default is 0.5.
        multiplier: Backoff multiplier. Default is 2.0.
    
    Returns:
        Decorated function with RAG-specific retry logic.
    
    Example:
        >>> @retry_rag_operation()
        ... def query_knowledge_base(question: str):
        ...     return rag_tool.query(question)
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        multiplier=multiplier,
        max_delay=5.0,  # Cap at 5 seconds for RAG operations
        jitter=True,
        exceptions=(
            RAGRetrievalError,
            ConnectionError,
        )
    )


# Default retry policy configuration
DEFAULT_RETRY_CONFIG = {
    'max_attempts': 3,
    'initial_delay': 1.0,
    'multiplier': 2.0,
    'max_delay': 60.0,
    'jitter': True
}


def get_default_retry_decorator():
    """
    Get a retry decorator with default configuration.
    
    This function returns a retry decorator configured with the default
    retry policy (3 attempts, 1s initial delay, 2x multiplier).
    
    Returns:
        Retry decorator with default configuration.
    
    Example:
        >>> default_retry = get_default_retry_decorator()
        >>> @default_retry
        ... def my_function():
        ...     # Function implementation
        ...     pass
    """
    return retry_with_backoff(**DEFAULT_RETRY_CONFIG)
