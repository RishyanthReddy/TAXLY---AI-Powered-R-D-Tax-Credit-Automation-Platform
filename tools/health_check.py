"""
API Health Check Module

This module provides health check functionality for all API connectors used in the
R&D Tax Credit Automation system. Health checks verify authentication and basic
connectivity for each external service.

Health Status Levels:
- healthy: API is accessible and authentication is valid
- degraded: API is accessible but experiencing issues (slow response, partial failures)
- down: API is not accessible or authentication failed

Usage:
    >>> from tools.health_check import check_all_apis, check_api_health
    >>> 
    >>> # Check all APIs
    >>> results = check_all_apis()
    >>> for api_name, status in results.items():
    ...     print(f"{api_name}: {status['status']}")
    >>> 
    >>> # Check specific API
    >>> status = check_api_health('clockify')
    >>> if status['status'] == 'healthy':
    ...     print("Clockify is ready!")
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from utils.config import get_config
from utils.exceptions import APIConnectionError
from utils.logger import get_tool_logger
from tools.api_connectors import ClockifyConnector, UnifiedToConnector
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner


# Get logger for health checks
logger = get_tool_logger("health_check")


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class HealthCheckResult:
    """
    Health check result container.
    
    Attributes:
        api_name: Name of the API being checked
        status: Health status (healthy, degraded, down)
        response_time: Response time in seconds
        message: Human-readable status message
        details: Additional details about the check
        timestamp: When the check was performed
        error: Error message if check failed
    """
    
    def __init__(
        self,
        api_name: str,
        status: str,
        response_time: float,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.api_name = api_name
        self.status = status
        self.response_time = response_time
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'api_name': self.api_name,
            'status': self.status,
            'response_time_ms': round(self.response_time * 1000, 2),
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
        }
        
        if self.details:
            result['details'] = self.details
        
        if self.error:
            result['error'] = self.error
        
        return result
    
    def __repr__(self) -> str:
        return (
            f"HealthCheckResult(api_name='{self.api_name}', "
            f"status='{self.status}', "
            f"response_time={self.response_time:.3f}s)"
        )


def check_clockify_health(
    api_key: Optional[str] = None,
    workspace_id: Optional[str] = None,
    timeout: float = 10.0
) -> HealthCheckResult:
    """
    Check Clockify API health.
    
    Tests authentication and basic connectivity by fetching user information.
    
    Args:
        api_key: Clockify API key (defaults to config)
        workspace_id: Clockify workspace ID (defaults to config)
        timeout: Request timeout in seconds (default: 10.0)
    
    Returns:
        HealthCheckResult with status and details
    
    Example:
        >>> result = check_clockify_health()
        >>> print(f"Clockify: {result.status}")
        >>> print(f"Response time: {result.response_time:.2f}s")
    """
    logger.info("Checking Clockify API health...")
    start_time = time.time()
    
    try:
        # Get credentials from config if not provided
        if api_key is None or workspace_id is None:
            config = get_config()
            api_key = api_key or config.clockify_api_key
            workspace_id = workspace_id or config.clockify_workspace_id
        
        # Create connector with custom timeout
        connector = ClockifyConnector(
            api_key=api_key,
            workspace_id=workspace_id
        )
        connector.timeout = timeout
        
        # Test authentication
        user_info = connector.test_authentication()
        
        response_time = time.time() - start_time
        
        # Check response time for degraded status
        if response_time > 5.0:
            status = HealthStatus.DEGRADED
            message = f"Clockify API is slow (response time: {response_time:.2f}s)"
            logger.warning(message)
        else:
            status = HealthStatus.HEALTHY
            message = "Clockify API is healthy"
            logger.info(f"{message} (response time: {response_time:.2f}s)")
        
        return HealthCheckResult(
            api_name="Clockify",
            status=status,
            response_time=response_time,
            message=message,
            details={
                'user_id': user_info.get('id'),
                'user_email': user_info.get('email'),
                'workspace_id': workspace_id
            }
        )
    
    except APIConnectionError as e:
        response_time = time.time() - start_time
        
        if e.status_code == 401:
            message = "Clockify authentication failed: Invalid API key"
        elif e.status_code == 404:
            message = "Clockify workspace not found"
        elif e.status_code == 429:
            message = "Clockify rate limit exceeded"
        else:
            message = f"Clockify API error: {e.message}"
        
        logger.error(message)
        
        return HealthCheckResult(
            api_name="Clockify",
            status=HealthStatus.DOWN,
            response_time=response_time,
            message=message,
            error=str(e)
        )
    
    except Exception as e:
        response_time = time.time() - start_time
        message = f"Clockify health check failed: {str(e)}"
        logger.error(message)
        
        return HealthCheckResult(
            api_name="Clockify",
            status=HealthStatus.DOWN,
            response_time=response_time,
            message=message,
            error=str(e)
        )


def check_unified_to_health(
    api_key: Optional[str] = None,
    workspace_id: Optional[str] = None,
    timeout: float = 10.0
) -> HealthCheckResult:
    """
    Check Unified.to API health.
    
    Tests authentication and basic connectivity by fetching workspace information.
    
    Args:
        api_key: Unified.to API key (defaults to config)
        workspace_id: Unified.to workspace ID (defaults to config)
        timeout: Request timeout in seconds (default: 10.0)
    
    Returns:
        HealthCheckResult with status and details
    
    Example:
        >>> result = check_unified_to_health()
        >>> print(f"Unified.to: {result.status}")
        >>> print(f"Response time: {result.response_time:.2f}s")
    """
    logger.info("Checking Unified.to API health...")
    start_time = time.time()
    
    try:
        # Get credentials from config if not provided
        if api_key is None or workspace_id is None:
            config = get_config()
            api_key = api_key or config.unified_to_api_key
            workspace_id = workspace_id or config.unified_to_workspace_id
        
        # Create connector with custom timeout
        connector = UnifiedToConnector(
            api_key=api_key,
            workspace_id=workspace_id
        )
        connector.timeout = timeout
        
        # Test authentication
        workspace_info = connector.test_authentication()
        
        response_time = time.time() - start_time
        
        # Check response time for degraded status
        if response_time > 5.0:
            status = HealthStatus.DEGRADED
            message = f"Unified.to API is slow (response time: {response_time:.2f}s)"
            logger.warning(message)
        else:
            status = HealthStatus.HEALTHY
            message = "Unified.to API is healthy"
            logger.info(f"{message} (response time: {response_time:.2f}s)")
        
        return HealthCheckResult(
            api_name="Unified.to",
            status=status,
            response_time=response_time,
            message=message,
            details={
                'workspace_id': workspace_id,
                'workspace_name': workspace_info.get('name', 'Unknown')
            }
        )
    
    except APIConnectionError as e:
        response_time = time.time() - start_time
        
        if e.status_code == 401:
            message = "Unified.to authentication failed: Invalid API key"
        elif e.status_code == 403:
            message = "Unified.to access forbidden: Insufficient permissions"
        elif e.status_code == 404:
            message = "Unified.to workspace not found"
        elif e.status_code == 429:
            message = "Unified.to rate limit exceeded"
        else:
            message = f"Unified.to API error: {e.message}"
        
        logger.error(message)
        
        return HealthCheckResult(
            api_name="Unified.to",
            status=HealthStatus.DOWN,
            response_time=response_time,
            message=message,
            error=str(e)
        )
    
    except Exception as e:
        response_time = time.time() - start_time
        message = f"Unified.to health check failed: {str(e)}"
        logger.error(message)
        
        return HealthCheckResult(
            api_name="Unified.to",
            status=HealthStatus.DOWN,
            response_time=response_time,
            message=message,
            error=str(e)
        )


def check_youcom_health(
    api_key: Optional[str] = None,
    timeout: float = 15.0
) -> HealthCheckResult:
    """
    Check You.com API health.
    
    Tests authentication and basic connectivity by making a simple search query.
    
    Args:
        api_key: You.com API key (defaults to config)
        timeout: Request timeout in seconds (default: 15.0)
    
    Returns:
        HealthCheckResult with status and details
    
    Example:
        >>> result = check_youcom_health()
        >>> print(f"You.com: {result.status}")
        >>> print(f"Response time: {result.response_time:.2f}s")
    """
    logger.info("Checking You.com API health...")
    start_time = time.time()
    
    try:
        # Get credentials from config if not provided
        if api_key is None:
            config = get_config()
            api_key = config.youcom_api_key
        
        # Create client with custom timeout
        client = YouComClient(
            api_key=api_key,
            enable_cache=False  # Disable cache for health check
        )
        client.timeout = timeout
        
        # Test authentication
        auth_success = client.test_authentication()
        
        response_time = time.time() - start_time
        
        if not auth_success:
            return HealthCheckResult(
                api_name="You.com",
                status=HealthStatus.DOWN,
                response_time=response_time,
                message="You.com authentication failed",
                error="Authentication test returned False"
            )
        
        # Check response time for degraded status
        if response_time > 8.0:
            status = HealthStatus.DEGRADED
            message = f"You.com API is slow (response time: {response_time:.2f}s)"
            logger.warning(message)
        else:
            status = HealthStatus.HEALTHY
            message = "You.com API is healthy"
            logger.info(f"{message} (response time: {response_time:.2f}s)")
        
        return HealthCheckResult(
            api_name="You.com",
            status=status,
            response_time=response_time,
            message=message,
            details={
                'api_key_prefix': api_key[:10] + '...' if len(api_key) > 10 else api_key
            }
        )
    
    except APIConnectionError as e:
        response_time = time.time() - start_time
        
        if e.status_code == 401:
            message = "You.com authentication failed: Invalid API key"
        elif e.status_code == 429:
            message = "You.com rate limit exceeded"
        elif e.status_code and e.status_code >= 500:
            message = f"You.com server error: HTTP {e.status_code}"
        else:
            message = f"You.com API error: {e.message}"
        
        logger.error(message)
        
        return HealthCheckResult(
            api_name="You.com",
            status=HealthStatus.DOWN,
            response_time=response_time,
            message=message,
            error=str(e)
        )
    
    except Exception as e:
        response_time = time.time() - start_time
        message = f"You.com health check failed: {str(e)}"
        logger.error(message)
        
        return HealthCheckResult(
            api_name="You.com",
            status=HealthStatus.DOWN,
            response_time=response_time,
            message=message,
            error=str(e)
        )


async def check_glm_health(
    api_key: Optional[str] = None,
    timeout: int = 15
) -> HealthCheckResult:
    """
    Check GLM 4.5 Air (via OpenRouter) health.
    
    Tests authentication and basic connectivity by making a simple reasoning call.
    
    Args:
        api_key: OpenRouter API key (defaults to config)
        timeout: Request timeout in seconds (default: 15)
    
    Returns:
        HealthCheckResult with status and details
    
    Example:
        >>> result = await check_glm_health()
        >>> print(f"GLM 4.5 Air: {result.status}")
        >>> print(f"Response time: {result.response_time:.2f}s")
    """
    logger.info("Checking GLM 4.5 Air (OpenRouter) health...")
    start_time = time.time()
    
    try:
        # Get credentials from config if not provided
        if api_key is None:
            config = get_config()
            api_key = config.openrouter_api_key
        
        # Create reasoner with custom timeout
        reasoner = GLMReasoner(
            api_key=api_key,
            timeout=timeout
        )
        
        # Test with a simple prompt
        response = await reasoner.reason(
            prompt="Respond with 'OK' if you can read this.",
            temperature=0.0,
            max_tokens=10
        )
        
        response_time = time.time() - start_time
        
        # Verify we got a response
        if not response or len(response.strip()) == 0:
            return HealthCheckResult(
                api_name="GLM 4.5 Air",
                status=HealthStatus.DOWN,
                response_time=response_time,
                message="GLM 4.5 Air returned empty response",
                error="Empty response from API"
            )
        
        # Check response time for degraded status
        if response_time > 10.0:
            status = HealthStatus.DEGRADED
            message = f"GLM 4.5 Air is slow (response time: {response_time:.2f}s)"
            logger.warning(message)
        else:
            status = HealthStatus.HEALTHY
            message = "GLM 4.5 Air is healthy"
            logger.info(f"{message} (response time: {response_time:.2f}s)")
        
        return HealthCheckResult(
            api_name="GLM 4.5 Air",
            status=status,
            response_time=response_time,
            message=message,
            details={
                'model': reasoner.model,
                'response_length': len(response)
            }
        )
    
    except APIConnectionError as e:
        response_time = time.time() - start_time
        
        if "401" in str(e) or "Unauthorized" in str(e):
            message = "GLM 4.5 Air authentication failed: Invalid OpenRouter API key"
        elif "429" in str(e) or "Rate limit" in str(e):
            message = "GLM 4.5 Air rate limit exceeded"
        elif "500" in str(e) or "502" in str(e) or "503" in str(e):
            message = "GLM 4.5 Air server error"
        else:
            message = f"GLM 4.5 Air API error: {str(e)}"
        
        logger.error(message)
        
        return HealthCheckResult(
            api_name="GLM 4.5 Air",
            status=HealthStatus.DOWN,
            response_time=response_time,
            message=message,
            error=str(e)
        )
    
    except Exception as e:
        response_time = time.time() - start_time
        message = f"GLM 4.5 Air health check failed: {str(e)}"
        logger.error(message)
        
        return HealthCheckResult(
            api_name="GLM 4.5 Air",
            status=HealthStatus.DOWN,
            response_time=response_time,
            message=message,
            error=str(e)
        )


def check_api_health(
    api_name: str,
    **kwargs
) -> HealthCheckResult:
    """
    Check health of a specific API by name.
    
    Args:
        api_name: Name of API to check ('clockify', 'unified_to', 'youcom', 'glm')
        **kwargs: Additional arguments passed to specific health check function
    
    Returns:
        HealthCheckResult for the specified API
    
    Raises:
        ValueError: If api_name is not recognized
    
    Example:
        >>> result = check_api_health('clockify')
        >>> print(f"Status: {result.status}")
        >>> 
        >>> # With custom timeout
        >>> result = check_api_health('youcom', timeout=20.0)
    """
    api_name_lower = api_name.lower()
    
    if api_name_lower == 'clockify':
        return check_clockify_health(**kwargs)
    elif api_name_lower in ('unified_to', 'unifiedto', 'unified.to'):
        return check_unified_to_health(**kwargs)
    elif api_name_lower in ('youcom', 'you.com', 'you_com'):
        return check_youcom_health(**kwargs)
    elif api_name_lower in ('glm', 'glm_4.5_air', 'openrouter'):
        # GLM check is async, so we need to run it in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(check_glm_health(**kwargs))
    else:
        raise ValueError(
            f"Unknown API name: {api_name}. "
            f"Valid options: clockify, unified_to, youcom, glm"
        )


async def check_all_apis_async(
    include_apis: Optional[List[str]] = None,
    parallel: bool = True
) -> Dict[str, HealthCheckResult]:
    """
    Check health of all APIs asynchronously.
    
    Args:
        include_apis: List of API names to check (None = check all)
        parallel: Run checks in parallel (default: True)
    
    Returns:
        Dictionary mapping API names to HealthCheckResult objects
    
    Example:
        >>> results = await check_all_apis_async()
        >>> for api_name, result in results.items():
        ...     print(f"{api_name}: {result.status}")
        >>> 
        >>> # Check specific APIs
        >>> results = await check_all_apis_async(include_apis=['clockify', 'youcom'])
    """
    all_apis = ['clockify', 'unified_to', 'youcom', 'glm']
    
    if include_apis:
        apis_to_check = [api for api in include_apis if api.lower() in all_apis]
    else:
        apis_to_check = all_apis
    
    logger.info(f"Checking health of {len(apis_to_check)} APIs...")
    
    results = {}
    
    if parallel:
        # Run all checks in parallel
        tasks = []
        
        for api_name in apis_to_check:
            if api_name.lower() == 'glm':
                # GLM is already async
                tasks.append(check_glm_health())
            else:
                # Wrap sync functions in async
                async def run_sync_check(name):
                    loop = asyncio.get_event_loop()
                    if name.lower() == 'clockify':
                        return await loop.run_in_executor(None, check_clockify_health)
                    elif name.lower() == 'unified_to':
                        return await loop.run_in_executor(None, check_unified_to_health)
                    elif name.lower() == 'youcom':
                        return await loop.run_in_executor(None, check_youcom_health)
                
                tasks.append(run_sync_check(api_name))
        
        # Wait for all checks to complete
        check_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results back to API names
        for api_name, result in zip(apis_to_check, check_results):
            if isinstance(result, Exception):
                logger.error(f"Health check failed for {api_name}: {result}")
                results[api_name] = HealthCheckResult(
                    api_name=api_name,
                    status=HealthStatus.DOWN,
                    response_time=0.0,
                    message=f"Health check failed: {str(result)}",
                    error=str(result)
                )
            else:
                results[api_name] = result
    else:
        # Run checks sequentially
        for api_name in apis_to_check:
            try:
                if api_name.lower() == 'glm':
                    result = await check_glm_health()
                else:
                    result = check_api_health(api_name)
                results[api_name] = result
            except Exception as e:
                logger.error(f"Health check failed for {api_name}: {e}")
                results[api_name] = HealthCheckResult(
                    api_name=api_name,
                    status=HealthStatus.DOWN,
                    response_time=0.0,
                    message=f"Health check failed: {str(e)}",
                    error=str(e)
                )
    
    return results


def check_all_apis(
    include_apis: Optional[List[str]] = None,
    parallel: bool = True
) -> Dict[str, HealthCheckResult]:
    """
    Check health of all APIs (synchronous wrapper).
    
    Args:
        include_apis: List of API names to check (None = check all)
        parallel: Run checks in parallel (default: True)
    
    Returns:
        Dictionary mapping API names to HealthCheckResult objects
    
    Example:
        >>> results = check_all_apis()
        >>> for api_name, result in results.items():
        ...     print(f"{api_name}: {result.status}")
        >>> 
        >>> # Check specific APIs sequentially
        >>> results = check_all_apis(
        ...     include_apis=['clockify', 'youcom'],
        ...     parallel=False
        ... )
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        check_all_apis_async(include_apis=include_apis, parallel=parallel)
    )


def print_health_report(results: Dict[str, HealthCheckResult]) -> None:
    """
    Print a formatted health check report.
    
    Args:
        results: Dictionary of health check results
    
    Example:
        >>> results = check_all_apis()
        >>> print_health_report(results)
        
        API Health Check Report
        =======================
        Clockify: ✓ healthy (125ms)
        Unified.to: ✓ healthy (234ms)
        You.com: ✓ healthy (456ms)
        GLM 4.5 Air: ✓ healthy (789ms)
        
        Overall Status: All systems operational
    """
    print("\nAPI Health Check Report")
    print("=" * 50)
    
    all_healthy = True
    
    for api_name, result in results.items():
        # Status symbol
        if result.status == HealthStatus.HEALTHY:
            symbol = "✓"
        elif result.status == HealthStatus.DEGRADED:
            symbol = "⚠"
            all_healthy = False
        else:
            symbol = "✗"
            all_healthy = False
        
        # Format response time
        response_time_ms = round(result.response_time * 1000)
        
        print(f"{symbol} {result.api_name}: {result.status} ({response_time_ms}ms)")
        
        if result.status != HealthStatus.HEALTHY:
            print(f"  Message: {result.message}")
            if result.error:
                print(f"  Error: {result.error}")
    
    print("=" * 50)
    
    if all_healthy:
        print("Overall Status: ✓ All systems operational")
    else:
        print("Overall Status: ⚠ Some systems experiencing issues")
    
    print()


def get_overall_health_status(results: Dict[str, HealthCheckResult]) -> str:
    """
    Get overall health status from individual check results.
    
    Args:
        results: Dictionary of health check results
    
    Returns:
        Overall status: 'healthy', 'degraded', or 'down'
    
    Logic:
        - If any API is down: overall status is 'down'
        - If any API is degraded: overall status is 'degraded'
        - If all APIs are healthy: overall status is 'healthy'
    
    Example:
        >>> results = check_all_apis()
        >>> status = get_overall_health_status(results)
        >>> print(f"Overall: {status}")
    """
    if not results:
        return HealthStatus.DOWN
    
    statuses = [result.status for result in results.values()]
    
    if HealthStatus.DOWN in statuses:
        return HealthStatus.DOWN
    elif HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    else:
        return HealthStatus.HEALTHY


# Application startup health check
def startup_health_check(
    required_apis: Optional[List[str]] = None,
    fail_on_error: bool = False
) -> bool:
    """
    Perform health check on application startup.
    
    This function should be called during application initialization to verify
    that all required APIs are accessible before starting the main application.
    
    Args:
        required_apis: List of APIs that must be healthy (None = all APIs)
        fail_on_error: Raise exception if any required API is down (default: False)
    
    Returns:
        True if all required APIs are healthy, False otherwise
    
    Raises:
        RuntimeError: If fail_on_error=True and any required API is down
    
    Example:
        >>> # In main.py or application startup
        >>> if not startup_health_check(required_apis=['clockify', 'youcom']):
        ...     print("Warning: Some APIs are not available")
        >>> 
        >>> # Fail fast if APIs are down
        >>> startup_health_check(fail_on_error=True)
    """
    logger.info("Performing startup health check...")
    
    results = check_all_apis(include_apis=required_apis, parallel=True)
    
    print_health_report(results)
    
    # Check if all required APIs are healthy
    all_healthy = all(
        result.status == HealthStatus.HEALTHY
        for result in results.values()
    )
    
    if not all_healthy and fail_on_error:
        failed_apis = [
            name for name, result in results.items()
            if result.status != HealthStatus.HEALTHY
        ]
        raise RuntimeError(
            f"Startup health check failed. The following APIs are not healthy: "
            f"{', '.join(failed_apis)}"
        )
    
    return all_healthy
