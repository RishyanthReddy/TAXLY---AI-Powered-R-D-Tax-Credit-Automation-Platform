"""
Example usage of retry and backoff utilities.

This module demonstrates how to use the retry decorators for handling
transient failures in API calls, RAG operations, and other unreliable operations.
"""

import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.retry import (
    retry_with_backoff,
    retry_api_call,
    retry_rag_operation,
    get_default_retry_decorator
)
from utils.exceptions import APIConnectionError, RAGRetrievalError


# Example 1: Basic retry with default configuration
@retry_with_backoff()
def fetch_data_with_default_retry():
    """
    Function that uses default retry configuration:
    - 3 attempts
    - 1 second initial delay
    - 2x multiplier
    - Jitter enabled
    """
    print("Attempting to fetch data...")
    # Simulate API call that might fail
    return {"status": "success", "data": [1, 2, 3]}


# Example 2: Custom retry configuration
@retry_with_backoff(
    max_attempts=5,
    initial_delay=2.0,
    multiplier=1.5,
    max_delay=30.0,
    jitter=True
)
def fetch_data_with_custom_retry():
    """
    Function with custom retry configuration:
    - 5 attempts
    - 2 second initial delay
    - 1.5x multiplier (slower growth)
    - Max 30 second delay
    """
    print("Attempting to fetch data with custom config...")
    return {"status": "success"}


# Example 3: API-specific retry
@retry_api_call(max_attempts=3, initial_delay=1.0)
def call_clockify_api(workspace_id: str):
    """
    Example API call with retry logic.
    Automatically retries on APIConnectionError, ConnectionError, TimeoutError.
    """
    print(f"Calling Clockify API for workspace {workspace_id}...")
    
    # Simulate API call
    # If this raises APIConnectionError, it will be retried
    return {
        "workspace_id": workspace_id,
        "time_entries": []
    }


# Example 4: RAG operation retry
@retry_rag_operation(max_attempts=2, initial_delay=0.5)
def query_knowledge_base(question: str):
    """
    Example RAG query with retry logic.
    Automatically retries on RAGRetrievalError, ConnectionError.
    """
    print(f"Querying knowledge base: {question}")
    
    # Simulate RAG query
    return [
        {"text": "IRS guidance excerpt 1", "source": "CFR 26"},
        {"text": "IRS guidance excerpt 2", "source": "Form 6765"}
    ]


# Example 5: Retry with custom callback
def log_retry_attempt(exception, attempt, delay):
    """Custom callback function called before each retry."""
    print(f"⚠️  Retry attempt {attempt} after error: {exception}")
    print(f"   Waiting {delay:.2f} seconds before retry...")


@retry_with_backoff(
    max_attempts=3,
    initial_delay=1.0,
    on_retry=log_retry_attempt
)
def fetch_with_logging():
    """Function that logs retry attempts."""
    print("Attempting operation...")
    return "success"


# Example 6: Retry only specific exceptions
@retry_with_backoff(
    max_attempts=3,
    initial_delay=1.0,
    exceptions=(APIConnectionError, TimeoutError)
)
def selective_retry_function():
    """
    Only retries on APIConnectionError and TimeoutError.
    Other exceptions will be raised immediately.
    """
    print("Attempting operation with selective retry...")
    return "success"


# Example 7: Using the default retry decorator factory
default_retry = get_default_retry_decorator()

@default_retry
def another_function():
    """Function using the default retry decorator."""
    print("Using default retry decorator...")
    return "success"


# Example 8: Simulating a flaky API call
call_count = 0

@retry_api_call(max_attempts=5, initial_delay=0.5)
def flaky_api_call():
    """
    Simulates an API call that fails the first 2 times,
    then succeeds on the 3rd attempt.
    """
    global call_count
    call_count += 1
    
    print(f"API call attempt #{call_count}")
    
    if call_count < 3:
        # Simulate transient failure
        raise APIConnectionError(
            "Service temporarily unavailable",
            api_name="ExampleAPI",
            status_code=503
        )
    
    # Success on 3rd attempt
    return {"status": "success", "attempt": call_count}


def main():
    """Run examples to demonstrate retry functionality."""
    print("=" * 60)
    print("Retry and Backoff Utilities - Usage Examples")
    print("=" * 60)
    
    # Example 1
    print("\n1. Basic retry with defaults:")
    result = fetch_data_with_default_retry()
    print(f"   Result: {result}")
    
    # Example 2
    print("\n2. Custom retry configuration:")
    result = fetch_data_with_custom_retry()
    print(f"   Result: {result}")
    
    # Example 3
    print("\n3. API-specific retry:")
    result = call_clockify_api("workspace-123")
    print(f"   Result: {result}")
    
    # Example 4
    print("\n4. RAG operation retry:")
    result = query_knowledge_base("What is qualified research?")
    print(f"   Result: {len(result)} documents retrieved")
    
    # Example 5
    print("\n5. Retry with custom logging:")
    result = fetch_with_logging()
    print(f"   Result: {result}")
    
    # Example 6
    print("\n6. Selective exception retry:")
    result = selective_retry_function()
    print(f"   Result: {result}")
    
    # Example 7
    print("\n7. Default retry decorator:")
    result = another_function()
    print(f"   Result: {result}")
    
    # Example 8
    print("\n8. Flaky API call (will retry and succeed):")
    global call_count
    call_count = 0  # Reset counter
    result = flaky_api_call()
    print(f"   Result: {result}")
    print(f"   Total attempts: {call_count}")
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
