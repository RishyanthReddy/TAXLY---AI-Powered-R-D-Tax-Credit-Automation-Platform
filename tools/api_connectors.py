"""
Base API connector class and utilities for external API integrations.

This module provides a base class for all API connectors with common functionality:
- Request/response handling with retry logic
- Rate limiting support
- Error handling and logging
- Request/response logging for debugging and audit trails
"""

import time
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta
import httpx

from utils.exceptions import APIConnectionError
from utils.retry import retry_with_backoff
from utils.logger import get_tool_logger

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from models.financial_models import EmployeeTimeEntry


# Get logger for API connectors
logger = get_tool_logger("api_connectors")


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Implements the token bucket algorithm to enforce rate limits on API calls.
    Tokens are added at a constant rate, and each API call consumes one token.
    If no tokens are available, the call is delayed until a token becomes available.
    """
    
    def __init__(self, requests_per_second: float, burst_size: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum number of requests per second
            burst_size: Maximum burst size (defaults to requests_per_second)
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size or int(requests_per_second)
        self.tokens = float(self.burst_size)
        self.last_update = time.time()
        self.lock_time = 0.0
    
    def acquire(self) -> float:
        """
        Acquire a token for making an API call.
        
        Returns:
            Time waited in seconds (0 if no wait was needed)
        """
        current_time = time.time()
        
        # Add tokens based on time elapsed
        time_elapsed = current_time - self.last_update
        self.tokens = min(
            self.burst_size,
            self.tokens + time_elapsed * self.requests_per_second
        )
        self.last_update = current_time
        
        # If we have tokens, consume one and return
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return 0.0
        
        # Otherwise, wait until we have a token
        wait_time = (1.0 - self.tokens) / self.requests_per_second
        time.sleep(wait_time)
        
        self.tokens = 0.0
        self.last_update = time.time()
        
        return wait_time
    
    def reset(self):
        """Reset the rate limiter to full capacity."""
        self.tokens = float(self.burst_size)
        self.last_update = time.time()


class BaseAPIConnector(ABC):
    """
    Abstract base class for all API connectors.
    
    Provides common functionality for API communication including:
    - HTTP request handling with retry logic
    - Rate limiting
    - Error handling and logging
    - Request/response logging
    
    Subclasses must implement:
    - _get_base_url(): Return the base URL for the API
    - _get_auth_headers(): Return authentication headers
    """
    
    def __init__(
        self,
        api_name: str,
        rate_limit: Optional[float] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize base API connector.
        
        Args:
            api_name: Name of the API (for logging and error messages)
            rate_limit: Maximum requests per second (None for no limit)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_name = api_name
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize rate limiter if rate limit is specified
        self.rate_limiter = RateLimiter(rate_limit) if rate_limit else None
        
        # Initialize HTTP client
        self.client = httpx.Client(timeout=timeout)
        
        # Track request statistics
        self.request_count = 0
        self.error_count = 0
        self.total_wait_time = 0.0
        
        logger.info(
            f"Initialized {api_name} connector "
            f"(rate_limit={rate_limit}, timeout={timeout}s, max_retries={max_retries})"
        )
    
    @abstractmethod
    def _get_base_url(self) -> str:
        """
        Get the base URL for the API.
        
        Returns:
            Base URL string
        """
        pass
    
    @abstractmethod
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dictionary of authentication headers
        """
        pass
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (relative to base URL)
            params: Query parameters
            json_data: JSON request body
            headers: Additional headers (merged with auth headers)
            retry: Whether to retry on failure
        
        Returns:
            Response JSON as dictionary
        
        Raises:
            APIConnectionError: If request fails after all retries
        """
        # Apply rate limiting if configured
        if self.rate_limiter:
            wait_time = self.rate_limiter.acquire()
            if wait_time > 0:
                self.total_wait_time += wait_time
                logger.debug(f"Rate limit: waited {wait_time:.2f}s before request")
        
        # Construct full URL
        base_url = self._get_base_url()
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Merge headers
        request_headers = self._get_auth_headers()
        if headers:
            request_headers.update(headers)
        
        # Log request
        self.request_count += 1
        logger.info(
            f"[{self.api_name}] {method} {endpoint} "
            f"(request #{self.request_count})"
        )
        logger.debug(f"URL: {url}")
        logger.debug(f"Params: {params}")
        logger.debug(f"Headers: {list(request_headers.keys())}")
        
        # Define the actual request function
        def _do_request():
            try:
                response = self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers
                )
                
                # Log response
                logger.debug(f"Response status: {response.status_code}")
                
                # Handle error status codes
                if response.status_code >= 400:
                    self._handle_error(response, endpoint)
                
                # Parse and return JSON response
                return response.json()
            
            except httpx.TimeoutException as e:
                logger.error(f"Request timeout after {self.timeout}s: {endpoint}")
                raise APIConnectionError(
                    message=f"Request timeout after {self.timeout}s",
                    api_name=self.api_name,
                    endpoint=endpoint,
                    details={'error': str(e)}
                )
            
            except httpx.RequestError as e:
                logger.error(f"Request error: {str(e)}")
                raise APIConnectionError(
                    message=f"Request failed: {str(e)}",
                    api_name=self.api_name,
                    endpoint=endpoint,
                    details={'error': str(e)}
                )
        
        # Execute with retry if enabled
        if retry:
            return self._retry_request(_do_request, endpoint)
        else:
            return _do_request()
    
    def _retry_request(self, request_func, endpoint: str) -> Dict[str, Any]:
        """
        Retry a request with exponential backoff.
        
        Args:
            request_func: Function that performs the request
            endpoint: API endpoint (for logging)
        
        Returns:
            Response JSON as dictionary
        
        Raises:
            APIConnectionError: If request fails after all retries
        """
        @retry_with_backoff(
            max_attempts=self.max_retries,
            initial_delay=1.0,
            multiplier=2.0,
            max_delay=30.0,
            jitter=True,
            exceptions=(APIConnectionError, ConnectionError, TimeoutError)
        )
        def _wrapped():
            return request_func()
        
        try:
            return _wrapped()
        except Exception as e:
            self.error_count += 1
            logger.error(
                f"Request failed after {self.max_retries} attempts: {endpoint}"
            )
            raise
    
    def _handle_error(self, response: httpx.Response, endpoint: str):
        """
        Handle HTTP error responses.
        
        Args:
            response: HTTP response object
            endpoint: API endpoint that was called
        
        Raises:
            APIConnectionError: Always raises with appropriate error details
        """
        status_code = response.status_code
        
        # Try to extract error message from response
        try:
            error_data = response.json()
            error_message = error_data.get('message') or error_data.get('error') or str(error_data)
        except Exception:
            error_message = response.text or f"HTTP {status_code}"
        
        # Log error
        logger.error(
            f"[{self.api_name}] HTTP {status_code} error on {endpoint}: {error_message}"
        )
        
        # Categorize error and raise appropriate exception
        if status_code == 401:
            raise APIConnectionError(
                message=f"Authentication failed: {error_message}",
                api_name=self.api_name,
                status_code=status_code,
                endpoint=endpoint,
                details={'error': error_message}
            )
        
        elif status_code == 403:
            raise APIConnectionError(
                message=f"Access forbidden: {error_message}",
                api_name=self.api_name,
                status_code=status_code,
                endpoint=endpoint,
                details={'error': error_message}
            )
        
        elif status_code == 404:
            raise APIConnectionError(
                message=f"Resource not found: {error_message}",
                api_name=self.api_name,
                status_code=status_code,
                endpoint=endpoint,
                details={'error': error_message}
            )
        
        elif status_code == 429:
            raise APIConnectionError(
                message=f"Rate limit exceeded: {error_message}",
                api_name=self.api_name,
                status_code=status_code,
                endpoint=endpoint,
                details={'error': error_message}
            )
        
        elif status_code >= 500:
            raise APIConnectionError(
                message=f"Server error: {error_message}",
                api_name=self.api_name,
                status_code=status_code,
                endpoint=endpoint,
                details={'error': error_message}
            )
        
        else:
            raise APIConnectionError(
                message=f"HTTP {status_code}: {error_message}",
                api_name=self.api_name,
                status_code=status_code,
                endpoint=endpoint,
                details={'error': error_message}
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get connector statistics.
        
        Returns:
            Dictionary with request statistics
        """
        return {
            'api_name': self.api_name,
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / self.request_count if self.request_count > 0 else 0.0,
            'total_wait_time': self.total_wait_time
        }
    
    def close(self):
        """Close the HTTP client and release resources."""
        self.client.close()
        logger.info(f"Closed {self.api_name} connector")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class ClockifyConnector(BaseAPIConnector):
    """
    Connector for Clockify time tracking API.
    
    Provides methods to fetch time entries and user information from Clockify.
    Handles authentication, pagination, and data transformation.
    
    API Documentation: https://docs.clockify.me/
    """
    
    def __init__(self, api_key: str, workspace_id: str):
        """
        Initialize Clockify connector.
        
        Args:
            api_key: Clockify API key (X-Api-Key header)
            workspace_id: Clockify workspace ID
        
        Raises:
            ValueError: If api_key or workspace_id is empty
        """
        if not api_key:
            raise ValueError("Clockify API key cannot be empty")
        if not workspace_id:
            raise ValueError("Clockify workspace ID cannot be empty")
        
        # Initialize base connector with Clockify-specific settings
        super().__init__(
            api_name="Clockify",
            rate_limit=10.0,  # 10 requests per second
            timeout=30.0,
            max_retries=3
        )
        
        self.api_key = api_key
        self.workspace_id = workspace_id
        
        logger.info(f"Initialized Clockify connector for workspace {workspace_id}")
    
    def _get_base_url(self) -> str:
        """
        Get the base URL for Clockify API.
        
        Returns:
            Base URL string
        """
        return "https://api.clockify.me/api/v1"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for Clockify API.
        
        Clockify uses X-Api-Key header for authentication.
        
        Returns:
            Dictionary with authentication headers
        """
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def test_authentication(self) -> Dict[str, Any]:
        """
        Test authentication by fetching current user information.
        
        This method calls the /user endpoint to verify that the API key is valid
        and the connection is working properly.
        
        Returns:
            User information dictionary with fields:
                - id: User ID
                - email: User email
                - name: User name
                - activeWorkspace: Active workspace ID
                - status: Account status
        
        Raises:
            APIConnectionError: If authentication fails or request fails
        
        Example:
            >>> connector = ClockifyConnector(api_key="...", workspace_id="...")
            >>> user_info = connector.test_authentication()
            >>> print(f"Authenticated as: {user_info['email']}")
        """
        logger.info("Testing Clockify authentication...")
        
        try:
            user_info = self._make_request(
                method="GET",
                endpoint="/user",
                retry=False  # Don't retry auth test
            )
            
            logger.info(
                f"Authentication successful! "
                f"User: {user_info.get('email', 'Unknown')} "
                f"(ID: {user_info.get('id', 'Unknown')})"
            )
            
            return user_info
            
        except APIConnectionError as e:
            if e.status_code == 401:
                logger.error("Authentication failed: Invalid API key")
                raise APIConnectionError(
                    message="Invalid Clockify API key. Please check your credentials.",
                    api_name=self.api_name,
                    status_code=401,
                    endpoint="/user",
                    details={'error': 'Invalid API key'}
                )
            else:
                logger.error(f"Authentication test failed: {e}")
                raise
    
    def fetch_time_entries(
        self,
        start_date: datetime,
        end_date: datetime,
        page_size: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fetch time entries from Clockify for a given date range.
        
        This method retrieves all time entries within the specified date range,
        handling pagination automatically to fetch large result sets. The raw
        time entry data is returned as dictionaries for further processing.
        
        Args:
            start_date: Start date for time entries (inclusive)
            end_date: End date for time entries (inclusive)
            page_size: Number of entries per page (default: 50, max: 50)
        
        Returns:
            List of time entry dictionaries with fields:
                - id: Time entry ID
                - description: Task description
                - userId: User ID who logged the time
                - projectId: Project ID
                - timeInterval: Dict with start and end timestamps
                - duration: Duration in ISO 8601 format (e.g., "PT8H30M")
                - And other Clockify-specific fields
        
        Raises:
            APIConnectionError: If request fails
            ValueError: If date range is invalid or page_size is out of range
        
        Example:
            >>> from datetime import datetime
            >>> connector = ClockifyConnector(api_key="...", workspace_id="...")
            >>> entries = connector.fetch_time_entries(
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 1, 31)
            ... )
            >>> print(f"Fetched {len(entries)} time entries")
        """
        # Validate inputs
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        if page_size < 1 or page_size > 50:
            raise ValueError("page_size must be between 1 and 50")
        
        logger.info(
            f"Fetching time entries from {start_date.date()} to {end_date.date()} "
            f"(page_size={page_size})"
        )
        
        # Format dates for API (ISO 8601 format with timezone)
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Collect all time entries across pages
        all_entries = []
        page = 1
        
        while True:
            logger.debug(f"Fetching page {page}...")
            
            # Construct endpoint for time entries
            # Using the reports/detailed endpoint which supports date filtering
            endpoint = f"/workspaces/{self.workspace_id}/user/time-entries"
            
            # Make request with pagination parameters
            params = {
                "start": start_str,
                "end": end_str,
                "page-size": page_size,
                "page": page
            }
            
            try:
                # Fetch page of time entries
                entries = self._make_request(
                    method="GET",
                    endpoint=endpoint,
                    params=params
                )
                
                # Check if we got any entries
                if not entries or len(entries) == 0:
                    logger.debug(f"No more entries on page {page}, stopping pagination")
                    break
                
                # Add entries to collection
                all_entries.extend(entries)
                logger.debug(f"Page {page}: fetched {len(entries)} entries")
                
                # If we got fewer entries than page_size, we've reached the end
                if len(entries) < page_size:
                    logger.debug(f"Received {len(entries)} < {page_size}, last page reached")
                    break
                
                # Move to next page
                page += 1
                
            except APIConnectionError as e:
                # Log error and re-raise
                logger.error(
                    f"Failed to fetch time entries page {page}: {e}"
                )
                raise
        
        logger.info(
            f"Successfully fetched {len(all_entries)} time entries "
            f"across {page} page(s)"
        )
        
        return all_entries
    
    def _transform_time_entry(self, raw_entry: Dict[str, Any]) -> Optional['EmployeeTimeEntry']:
        """
        Transform a raw Clockify time entry into an EmployeeTimeEntry model.
        
        This method maps Clockify API fields to the EmployeeTimeEntry Pydantic model,
        handles missing optional fields gracefully, and validates the transformed data.
        Invalid entries are logged and skipped.
        
        Args:
            raw_entry: Raw time entry dictionary from Clockify API with fields:
                - id: Time entry ID
                - userId: User ID who logged the time
                - description: Task description (optional)
                - projectId: Project ID (optional)
                - timeInterval: Dict with start and end timestamps
                - duration: Duration in ISO 8601 format (e.g., "PT8H30M")
        
        Returns:
            EmployeeTimeEntry object if transformation succeeds, None if validation fails
        
        Example:
            >>> raw_entry = {
            ...     "id": "entry123",
            ...     "userId": "user456",
            ...     "description": "Implemented authentication",
            ...     "projectId": "project789",
            ...     "timeInterval": {
            ...         "start": "2024-01-15T09:00:00Z",
            ...         "end": "2024-01-15T17:30:00Z"
            ...     },
            ...     "duration": "PT8H30M"
            ... }
            >>> entry = connector._transform_time_entry(raw_entry)
            >>> print(entry.hours_spent)
            8.5
        """
        from models.financial_models import EmployeeTimeEntry
        from pydantic import ValidationError
        import re
        
        try:
            # Extract required fields with fallbacks for missing data
            employee_id = raw_entry.get('userId', '')
            if not employee_id:
                logger.warning(f"Skipping entry {raw_entry.get('id')}: missing userId")
                return None
            
            # Get employee name - Clockify doesn't provide this in time entries
            # Use userId as fallback (will need to be enriched from user endpoint)
            employee_name = raw_entry.get('userName', employee_id)
            
            # Get project name - use projectId as fallback if name not available
            project_name = raw_entry.get('projectName', raw_entry.get('projectId', 'Unknown Project'))
            if not project_name or project_name == '':
                project_name = 'Unknown Project'
            
            # Get task description - use empty string if not provided
            task_description = raw_entry.get('description', '')
            if not task_description or task_description.strip() == '':
                task_description = 'No description provided'
            
            # Parse duration to calculate hours_spent
            duration_str = raw_entry.get('duration', '')
            hours_spent = self._parse_duration(duration_str)
            
            if hours_spent is None or hours_spent <= 0:
                logger.warning(
                    f"Skipping entry {raw_entry.get('id')}: invalid duration '{duration_str}'"
                )
                return None
            
            # Parse date from timeInterval.start
            time_interval = raw_entry.get('timeInterval', {})
            start_time_str = time_interval.get('start', '')
            
            if not start_time_str:
                logger.warning(f"Skipping entry {raw_entry.get('id')}: missing start time")
                return None
            
            # Parse ISO 8601 datetime and convert to naive datetime (remove timezone info)
            # This is needed because EmployeeTimeEntry validator compares with datetime.now()
            date_with_tz = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            date = date_with_tz.replace(tzinfo=None)
            
            # Create EmployeeTimeEntry with validated data
            entry = EmployeeTimeEntry(
                employee_id=employee_id,
                employee_name=employee_name,
                project_name=project_name,
                task_description=task_description,
                hours_spent=hours_spent,
                date=date,
                is_rd_classified=False  # Default to False, user will classify later
            )
            
            logger.debug(
                f"Successfully transformed entry {raw_entry.get('id')}: "
                f"{employee_id} - {hours_spent}h on {project_name}"
            )
            
            return entry
        
        except ValidationError as e:
            logger.error(
                f"Validation error transforming entry {raw_entry.get('id')}: {e}"
            )
            logger.debug(f"Raw entry data: {raw_entry}")
            return None
        
        except Exception as e:
            logger.error(
                f"Unexpected error transforming entry {raw_entry.get('id')}: {e}"
            )
            logger.debug(f"Raw entry data: {raw_entry}")
            return None
    
    def _parse_duration(self, duration_str: str) -> Optional[float]:
        """
        Parse ISO 8601 duration string to hours.
        
        Clockify returns durations in ISO 8601 format (e.g., "PT8H30M", "PT2H15M30S").
        This method converts these to decimal hours.
        
        Args:
            duration_str: ISO 8601 duration string (e.g., "PT8H30M")
        
        Returns:
            Duration in hours as float, or None if parsing fails
        
        Example:
            >>> connector._parse_duration("PT8H30M")
            8.5
            >>> connector._parse_duration("PT2H15M30S")
            2.258333...
        """
        import re
        
        if not duration_str or duration_str == '':
            return None
        
        # Check if the string starts with PT (ISO 8601 duration format)
        if not duration_str.startswith('PT'):
            return None
        
        try:
            # ISO 8601 duration format: PT[hours]H[minutes]M[seconds]S
            # Examples: PT8H, PT8H30M, PT2H15M30S
            
            hours = 0.0
            minutes = 0.0
            seconds = 0.0
            
            # Extract hours
            hours_match = re.search(r'(\d+)H', duration_str)
            if hours_match:
                hours = float(hours_match.group(1))
            
            # Extract minutes
            minutes_match = re.search(r'(\d+)M', duration_str)
            if minutes_match:
                minutes = float(minutes_match.group(1))
            
            # Extract seconds
            seconds_match = re.search(r'(\d+(?:\.\d+)?)S', duration_str)
            if seconds_match:
                seconds = float(seconds_match.group(1))
            
            # If no time components found, return None
            if hours == 0.0 and minutes == 0.0 and seconds == 0.0:
                return None
            
            # Convert to total hours
            total_hours = hours + (minutes / 60.0) + (seconds / 3600.0)
            
            # Round to 2 decimal places
            return round(total_hours, 2)
        
        except Exception as e:
            logger.error(f"Error parsing duration '{duration_str}': {e}")
            return None


class UnifiedToConnector(BaseAPIConnector):
    """
    Connector for Unified.to HRIS/Payroll API.
    
    Provides methods to fetch employee data and payslips from 190+ HRIS systems
    through the Unified.to integration platform. Handles OAuth 2.0 authentication,
    token management, and data transformation.
    
    API Documentation: https://docs.unified.to/
    """
    
    def __init__(self, api_key: str, workspace_id: str):
        """
        Initialize Unified.to connector.
        
        Args:
            api_key: Unified.to API key for OAuth 2.0 authentication
            workspace_id: Unified.to workspace ID
        
        Raises:
            ValueError: If api_key or workspace_id is empty
        """
        if not api_key:
            raise ValueError("Unified.to API key cannot be empty")
        if not workspace_id:
            raise ValueError("Unified.to workspace ID cannot be empty")
        
        # Initialize base connector with Unified.to-specific settings
        super().__init__(
            api_name="Unified.to",
            rate_limit=5.0,  # 5 requests per second (conservative)
            timeout=30.0,
            max_retries=3
        )
        
        self.api_key = api_key
        self.workspace_id = workspace_id
        
        # OAuth 2.0 token management
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.refresh_token: Optional[str] = None
        
        logger.info(f"Initialized Unified.to connector for workspace {workspace_id}")
    
    def _get_base_url(self) -> str:
        """
        Get the base URL for Unified.to API.
        
        Returns:
            Base URL string
        """
        return "https://api.unified.to"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for Unified.to API.
        
        Uses OAuth 2.0 Bearer token authentication. If token is expired or not set,
        automatically refreshes the token before returning headers.
        
        Returns:
            Dictionary with authentication headers
        
        Raises:
            APIConnectionError: If token refresh fails
        """
        # Check if token needs refresh
        if self._is_token_expired():
            logger.info("Access token expired or not set, refreshing...")
            try:
                self._refresh_access_token()
            except APIConnectionError as e:
                logger.error(f"Failed to refresh access token: {e}")
                raise APIConnectionError(
                    message=f"OAuth token refresh failed: {e.message}",
                    api_name=self.api_name,
                    status_code=e.status_code,
                    endpoint=e.endpoint,
                    details={
                        'error': 'Token refresh failed',
                        'original_error': str(e)
                    }
                )
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _is_token_expired(self) -> bool:
        """
        Check if the current access token is expired or not set.
        
        Returns:
            True if token is expired or not set, False otherwise
        """
        if not self.access_token:
            return True
        
        if not self.token_expires_at:
            return True
        
        # Add 60 second buffer to refresh before actual expiration
        return datetime.now() >= (self.token_expires_at - timedelta(seconds=60))
    
    def _refresh_access_token(self):
        """
        Refresh the OAuth 2.0 access token.
        
        This method implements the OAuth 2.0 client credentials flow to obtain
        a new access token. The token is stored along with its expiration time.
        Handles various error scenarios including network failures, invalid
        credentials, and malformed responses.
        
        Raises:
            APIConnectionError: If token refresh fails for any reason
        """
        logger.info("Refreshing OAuth 2.0 access token...")
        
        # Store original token in case we need to restore it
        original_access_token = self.access_token
        original_expires_at = self.token_expires_at
        
        try:
            # OAuth 2.0 token endpoint
            token_endpoint = "/oauth/token"
            
            # Prepare token request payload
            token_data = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_key,  # Unified.to uses API key as both
                "workspace_id": self.workspace_id
            }
            
            # Make token request without authentication (this is the auth request)
            # Temporarily bypass auth headers for this request
            self.access_token = "temp_token_for_refresh"  # Placeholder to avoid recursion
            
            try:
                # Use httpx directly to avoid auth header recursion
                logger.debug(f"Requesting new token from {self._get_base_url()}{token_endpoint}")
                
                response = self.client.post(
                    url=f"{self._get_base_url()}{token_endpoint}",
                    json=token_data,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout
                )
                
                # Handle non-200 responses
                if response.status_code != 200:
                    # Restore original token on failure
                    self.access_token = original_access_token
                    self.token_expires_at = original_expires_at
                    
                    # Extract error details
                    error_msg = f"Token refresh failed with status {response.status_code}"
                    error_details = {'status_code': response.status_code}
                    
                    try:
                        error_data = response.json()
                        error_msg += f": {error_data.get('error', error_data.get('message', error_data))}"
                        error_details['response'] = error_data
                    except:
                        error_msg += f": {response.text}"
                        error_details['response_text'] = response.text
                    
                    logger.error(
                        f"Token refresh failed: {error_msg}",
                        extra={
                            'api_name': self.api_name,
                            'endpoint': token_endpoint,
                            'status_code': response.status_code,
                            'workspace_id': self.workspace_id
                        }
                    )
                    
                    # Provide specific error messages based on status code
                    if response.status_code == 401:
                        raise APIConnectionError(
                            message="Token refresh failed: Invalid API key or credentials. Please verify your Unified.to API key.",
                            api_name=self.api_name,
                            status_code=401,
                            endpoint=token_endpoint,
                            details={
                                'error': 'Invalid credentials',
                                'workspace_id': self.workspace_id
                            }
                        )
                    elif response.status_code == 403:
                        raise APIConnectionError(
                            message="Insufficient permissions to obtain access token. Please check API key permissions.",
                            api_name=self.api_name,
                            status_code=403,
                            endpoint=token_endpoint,
                            details={
                                'error': 'Insufficient permissions',
                                'workspace_id': self.workspace_id
                            }
                        )
                    elif response.status_code == 429:
                        raise APIConnectionError(
                            message="Rate limit exceeded during token refresh. Please wait before retrying.",
                            api_name=self.api_name,
                            status_code=429,
                            endpoint=token_endpoint,
                            details={
                                'error': 'Rate limit exceeded',
                                'workspace_id': self.workspace_id
                            }
                        )
                    else:
                        raise APIConnectionError(
                            message=error_msg,
                            api_name=self.api_name,
                            status_code=response.status_code,
                            endpoint=token_endpoint,
                            details=error_details
                        )
                
                # Parse token response
                try:
                    token_response = response.json()
                except Exception as e:
                    # Restore original token on failure
                    self.access_token = original_access_token
                    self.token_expires_at = original_expires_at
                    
                    logger.error(f"Failed to parse token response as JSON: {e}")
                    raise APIConnectionError(
                        message=f"Invalid token response format: {e}",
                        api_name=self.api_name,
                        status_code=response.status_code,
                        endpoint=token_endpoint,
                        details={
                            'error': 'Invalid JSON response',
                            'response_text': response.text[:500]  # Truncate for logging
                        }
                    )
                
                # Extract and validate access token
                self.access_token = token_response.get('access_token')
                if not self.access_token or self.access_token.strip() == '':
                    # Restore original token on failure
                    self.access_token = original_access_token
                    self.token_expires_at = original_expires_at
                    
                    logger.error("Token response missing 'access_token' field")
                    raise APIConnectionError(
                        message="No access_token in token response",
                        api_name=self.api_name,
                        status_code=response.status_code,
                        endpoint=token_endpoint,
                        details={
                            'error': 'Missing access_token',
                            'response_keys': list(token_response.keys())
                        }
                    )
                
                # Extract expiration time (expires_in is in seconds)
                expires_in = token_response.get('expires_in', 3600)  # Default 1 hour
                if not isinstance(expires_in, (int, float)) or expires_in <= 0:
                    logger.warning(f"Invalid expires_in value: {expires_in}, using default 3600s")
                    expires_in = 3600
                
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Extract refresh token if provided
                self.refresh_token = token_response.get('refresh_token')
                
                logger.info(
                    f"Successfully refreshed access token "
                    f"(expires at {self.token_expires_at.strftime('%Y-%m-%d %H:%M:%S')}, "
                    f"valid for {expires_in}s)"
                )
                
            except httpx.TimeoutException as e:
                # Restore original token on failure
                self.access_token = original_access_token
                self.token_expires_at = original_expires_at
                
                logger.error(f"Token refresh request timed out after {self.timeout}s: {e}")
                raise APIConnectionError(
                    message=f"Token refresh request timed out after {self.timeout}s",
                    api_name=self.api_name,
                    endpoint=token_endpoint,
                    details={
                        'error': 'Request timeout',
                        'timeout': self.timeout
                    }
                )
            
            except httpx.RequestError as e:
                # Restore original token on failure
                self.access_token = original_access_token
                self.token_expires_at = original_expires_at
                
                logger.error(f"Token refresh request failed due to network error: {e}")
                raise APIConnectionError(
                    message=f"Token refresh request failed: {e}",
                    api_name=self.api_name,
                    endpoint=token_endpoint,
                    details={
                        'error': 'Network error',
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                )
        
        except APIConnectionError:
            # Re-raise APIConnectionError as-is
            raise
        
        except Exception as e:
            # Restore original token on unexpected failure
            self.access_token = original_access_token
            self.token_expires_at = original_expires_at
            
            logger.error(
                f"Unexpected error during token refresh: {e}",
                exc_info=True,
                extra={
                    'api_name': self.api_name,
                    'workspace_id': self.workspace_id
                }
            )
            raise APIConnectionError(
                message=f"Unexpected error during token refresh: {e}",
                api_name=self.api_name,
                endpoint="/oauth/token",
                details={
                    'error': 'Unexpected error',
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )
    
    def _handle_transient_error(self, error: APIConnectionError, operation: str, retry_count: int = 0, max_retries: int = 2) -> bool:
        """
        Handle transient errors with intelligent retry logic.
        
        This method determines if an error is transient (temporary) and whether
        it should be retried. It handles token expiration, rate limiting, and
        temporary server errors with appropriate backoff strategies.
        
        Args:
            error: The APIConnectionError that occurred
            operation: Description of the operation being performed (for logging)
            retry_count: Current retry attempt number (0-indexed)
            max_retries: Maximum number of retries allowed
        
        Returns:
            True if the operation should be retried, False otherwise
        
        Raises:
            APIConnectionError: If error is not transient or max retries exceeded
        """
        # Check if we've exceeded max retries
        if retry_count >= max_retries:
            logger.error(
                f"Max retries ({max_retries}) exceeded for {operation}",
                extra={
                    'api_name': self.api_name,
                    'operation': operation,
                    'retry_count': retry_count,
                    'error': error.message
                }
            )
            return False
        
        # Handle token expiration (401) - refresh and retry
        if error.status_code == 401:
            logger.warning(
                f"Authentication error during {operation} (attempt {retry_count + 1}/{max_retries + 1}), "
                f"attempting token refresh..."
            )
            try:
                self._refresh_access_token()
                logger.info("Token refreshed successfully, will retry operation")
                return True
            except APIConnectionError as refresh_error:
                logger.error(f"Token refresh failed: {refresh_error.message}")
                raise APIConnectionError(
                    message=f"Authentication failed during {operation}: {refresh_error.message}",
                    api_name=self.api_name,
                    status_code=401,
                    endpoint=error.endpoint,
                    details={
                        'error': 'Token refresh failed',
                        'operation': operation,
                        'retry_count': retry_count,
                        'original_error': error.message
                    }
                )
        
        # Handle rate limiting (429) - wait and retry
        elif error.status_code == 429:
            # Extract retry-after header if available
            retry_after = error.details.get('retry_after', 60)  # Default 60 seconds
            logger.warning(
                f"Rate limit exceeded during {operation} (attempt {retry_count + 1}/{max_retries + 1}), "
                f"waiting {retry_after}s before retry..."
            )
            time.sleep(retry_after)
            return True
        
        # Handle server errors (5xx) - transient, retry with backoff
        elif error.status_code >= 500:
            backoff_time = min(2 ** retry_count, 30)  # Exponential backoff, max 30s
            logger.warning(
                f"Server error during {operation} (attempt {retry_count + 1}/{max_retries + 1}), "
                f"waiting {backoff_time}s before retry..."
            )
            time.sleep(backoff_time)
            return True
        
        # Handle timeout errors - transient, retry with backoff
        elif 'timeout' in error.message.lower():
            backoff_time = min(2 ** retry_count, 30)
            logger.warning(
                f"Timeout during {operation} (attempt {retry_count + 1}/{max_retries + 1}), "
                f"waiting {backoff_time}s before retry..."
            )
            time.sleep(backoff_time)
            return True
        
        # Non-transient errors (403, 404, 400, etc.) - don't retry
        else:
            logger.error(
                f"Non-transient error during {operation}: {error.message}",
                extra={
                    'api_name': self.api_name,
                    'operation': operation,
                    'status_code': error.status_code,
                    'error_details': error.details
                }
            )
            return False
    
    def _validate_connection_id(self, connection_id: str) -> bool:
        """
        Validate that a connection_id exists and is accessible.
        
        This method checks if the provided connection_id is valid and the
        connector has permission to access it. This helps catch configuration
        errors early before attempting data fetches.
        
        Args:
            connection_id: Unified.to connection ID to validate
        
        Returns:
            True if connection_id is valid and accessible
        
        Raises:
            APIConnectionError: If connection_id is invalid or inaccessible
            ValueError: If connection_id is empty
        
        Example:
            >>> connector = UnifiedToConnector(api_key="...", workspace_id="...")
            >>> connector._validate_connection_id("conn_123")
            True
        """
        if not connection_id or connection_id.strip() == '':
            raise ValueError("connection_id cannot be empty")
        
        logger.debug(f"Validating connection_id: {connection_id}")
        
        try:
            # Attempt to fetch connection information
            endpoint = f"/unified/connection/{connection_id}"
            
            connection_info = self._make_request(
                method="GET",
                endpoint=endpoint,
                retry=False  # Don't retry validation checks
            )
            
            # Handle case where API returns unexpected format (e.g., list instead of dict)
            if not isinstance(connection_info, dict):
                logger.error(
                    f"Unexpected response format for connection validation: {type(connection_info).__name__}"
                )
                raise APIConnectionError(
                    message=f"Invalid response format from connection validation endpoint",
                    api_name=self.api_name,
                    status_code=500,
                    endpoint=endpoint,
                    details={
                        'error': 'Invalid response format',
                        'connection_id': connection_id,
                        'expected': 'dict',
                        'received': type(connection_info).__name__
                    }
                )
            
            # Check if connection is active
            if connection_info.get('status') != 'active':
                logger.warning(
                    f"Connection {connection_id} is not active: "
                    f"status={connection_info.get('status')}"
                )
                raise APIConnectionError(
                    message=f"Connection {connection_id} is not active (status: {connection_info.get('status')})",
                    api_name=self.api_name,
                    status_code=400,
                    endpoint=endpoint,
                    details={
                        'error': 'Inactive connection',
                        'connection_id': connection_id,
                        'status': connection_info.get('status')
                    }
                )
            
            logger.debug(f"Connection {connection_id} validated successfully")
            return True
            
        except APIConnectionError as e:
            if e.status_code == 404:
                logger.error(
                    f"Connection {connection_id} not found",
                    extra={
                        'api_name': self.api_name,
                        'connection_id': connection_id,
                        'endpoint': f"/unified/connection/{connection_id}"
                    }
                )
                raise APIConnectionError(
                    message=f"Connection ID '{connection_id}' not found. Please verify the connection exists.",
                    api_name=self.api_name,
                    status_code=404,
                    endpoint=f"/unified/connection/{connection_id}",
                    details={
                        'error': 'Connection not found',
                        'connection_id': connection_id
                    }
                )
            elif e.status_code == 403:
                logger.error(
                    f"Insufficient permissions to access connection {connection_id}",
                    extra={
                        'api_name': self.api_name,
                        'connection_id': connection_id,
                        'endpoint': f"/unified/connection/{connection_id}"
                    }
                )
                raise APIConnectionError(
                    message=f"Insufficient permissions to access connection '{connection_id}'. Check workspace permissions.",
                    api_name=self.api_name,
                    status_code=403,
                    endpoint=f"/unified/connection/{connection_id}",
                    details={
                        'error': 'Insufficient permissions',
                        'connection_id': connection_id
                    }
                )
            else:
                logger.error(
                    f"Failed to validate connection {connection_id}: {e.message}",
                    extra={
                        'api_name': self.api_name,
                        'connection_id': connection_id,
                        'status_code': e.status_code,
                        'error_details': e.details
                    }
                )
                raise
    
    def test_authentication(self) -> Dict[str, Any]:
        """
        Test authentication by fetching workspace information.
        
        This method verifies that the API key is valid and OAuth 2.0 token
        can be obtained successfully.
        
        Returns:
            Workspace information dictionary
        
        Raises:
            APIConnectionError: If authentication fails
        
        Example:
            >>> connector = UnifiedToConnector(api_key="...", workspace_id="...")
            >>> workspace_info = connector.test_authentication()
            >>> print(f"Authenticated to workspace: {workspace_info['name']}")
        """
        logger.info("Testing Unified.to authentication...")
        
        try:
            # Attempt to fetch workspace info or connections
            # This will trigger token refresh if needed
            workspace_info = self._make_request(
                method="GET",
                endpoint=f"/unified/workspace/{self.workspace_id}",
                retry=False
            )
            
            logger.info(
                f"Authentication successful! "
                f"Workspace: {workspace_info.get('name', 'Unknown')}"
            )
            
            return workspace_info
            
        except APIConnectionError as e:
            if e.status_code == 401:
                logger.error("Authentication failed: Invalid API key")
                raise APIConnectionError(
                    message="Invalid Unified.to API key or workspace ID. Please check your credentials.",
                    api_name=self.api_name,
                    status_code=401,
                    endpoint="/unified/workspace",
                    details={
                        'error': 'Invalid API key',
                        'workspace_id': self.workspace_id
                    }
                )
            elif e.status_code == 403:
                logger.error("Authentication failed: Insufficient permissions")
                raise APIConnectionError(
                    message="Invalid Unified.to API key or workspace ID. Insufficient permissions to access workspace.",
                    api_name=self.api_name,
                    status_code=403,
                    endpoint="/unified/workspace",
                    details={
                        'error': 'Insufficient permissions',
                        'workspace_id': self.workspace_id
                    }
                )
            else:
                logger.error(f"Authentication test failed: {e}")
                raise
    
    def fetch_employees(
        self,
        connection_id: Optional[str] = None,
        page_size: int = 100,
        validate_connection: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch employee profiles from HRIS system via Unified.to.
        
        This method retrieves employee data including job titles, departments,
        and compensation information. Handles pagination for large organizations.
        
        NOTE: Currently returns mock data for development/testing purposes.
        In production, this would call the actual Unified.to API endpoint:
        GET /hris/{connection_id}/employee
        
        Args:
            connection_id: Unified.to connection ID for the HRIS system (optional for mock)
            page_size: Number of employees per page (default: 100, max: 200)
            validate_connection: Whether to validate connection_id before fetching (default: True)
        
        Returns:
            List of employee dictionaries with fields:
                - id: Employee ID
                - name: Full name
                - email: Email address
                - job_title: Job title/position
                - department: Department name
                - compensation: Annual salary/compensation
                - hire_date: Date of hire (ISO 8601 format)
                - employment_status: Status (active, inactive, terminated)
                - manager_id: Manager's employee ID (if applicable)
        
        Raises:
            APIConnectionError: If request fails (in production mode) or connection is invalid
            ValueError: If page_size is out of range or connection_id is invalid
        
        Example:
            >>> connector = UnifiedToConnector(api_key="...", workspace_id="...")
            >>> employees = connector.fetch_employees(connection_id="conn_123")
            >>> for emp in employees:
            ...     print(f"{emp['name']} - {emp['job_title']} - ${emp['compensation']:,.2f}")
        """
        # Validate inputs
        if page_size < 1 or page_size > 200:
            raise ValueError("page_size must be between 1 and 200")
        
        # NOTE: Currently returns mock data, so skip connection validation
        # In production, uncomment the validation below
        # Validate connection_id if provided and validation is requested
        # if connection_id and validate_connection:
        #     try:
        #         self._validate_connection_id(connection_id)
        #     except APIConnectionError as e:
        #         logger.error(
        #             f"Connection validation failed for fetch_employees: {e.message}",
        #             extra={
        #                 'api_name': self.api_name,
        #                 'connection_id': connection_id,
        #                 'status_code': e.status_code,
        #                 'error_details': e.details
        #             }
        #         )
        #         raise
        #     except ValueError as e:
        #         logger.error(f"Invalid connection_id for fetch_employees: {e}")
        #         raise
        
        logger.info(
            f"Fetching employees from Unified.to "
            f"(connection_id={connection_id or 'mock'}, page_size={page_size})"
        )
        
        # MOCK DATA: Return sample employee data
        # In production, this would make actual API calls with pagination
        mock_employees = [
            {
                "id": "EMP001",
                "name": "Alice Johnson",
                "email": "alice.johnson@company.com",
                "job_title": "Senior Software Engineer",
                "department": "Engineering",
                "compensation": 150000.00,
                "hire_date": "2022-01-15T00:00:00Z",
                "employment_status": "active",
                "manager_id": "MGR001"
            },
            {
                "id": "EMP002",
                "name": "Bob Smith",
                "email": "bob.smith@company.com",
                "job_title": "Lead Backend Engineer",
                "department": "Engineering",
                "compensation": 165000.00,
                "hire_date": "2021-06-01T00:00:00Z",
                "employment_status": "active",
                "manager_id": "MGR001"
            },
            {
                "id": "EMP003",
                "name": "Carol Martinez",
                "email": "carol.martinez@company.com",
                "job_title": "Data Scientist",
                "department": "Data Science",
                "compensation": 175000.00,
                "hire_date": "2021-09-20T00:00:00Z",
                "employment_status": "active",
                "manager_id": "MGR002"
            },
            {
                "id": "EMP004",
                "name": "David Chen",
                "email": "david.chen@company.com",
                "job_title": "Security Engineer",
                "department": "Security",
                "compensation": 190000.00,
                "hire_date": "2020-03-10T00:00:00Z",
                "employment_status": "active",
                "manager_id": "MGR003"
            },
            {
                "id": "EMP005",
                "name": "Emma Wilson",
                "email": "emma.wilson@company.com",
                "job_title": "AI Research Scientist",
                "department": "AI Research",
                "compensation": 200000.00,
                "hire_date": "2020-11-01T00:00:00Z",
                "employment_status": "active",
                "manager_id": "MGR002"
            },
            {
                "id": "EMP006",
                "name": "Frank Brown",
                "email": "frank.brown@company.com",
                "job_title": "Customer Support Specialist",
                "department": "Customer Support",
                "compensation": 100000.00,
                "hire_date": "2023-02-14T00:00:00Z",
                "employment_status": "active",
                "manager_id": "MGR004"
            },
            {
                "id": "EMP007",
                "name": "Grace Lee",
                "email": "grace.lee@company.com",
                "job_title": "DevOps Engineer",
                "department": "Engineering",
                "compensation": 170000.00,
                "hire_date": "2021-04-05T00:00:00Z",
                "employment_status": "active",
                "manager_id": "MGR001"
            },
            {
                "id": "MGR001",
                "name": "Henry Davis",
                "email": "henry.davis@company.com",
                "job_title": "Engineering Manager",
                "department": "Engineering",
                "compensation": 220000.00,
                "hire_date": "2019-01-10T00:00:00Z",
                "employment_status": "active",
                "manager_id": None
            },
            {
                "id": "MGR002",
                "name": "Iris Taylor",
                "email": "iris.taylor@company.com",
                "job_title": "Data Science Manager",
                "department": "Data Science",
                "compensation": 210000.00,
                "hire_date": "2019-07-15T00:00:00Z",
                "employment_status": "active",
                "manager_id": None
            },
            {
                "id": "MGR003",
                "name": "Jack Anderson",
                "email": "jack.anderson@company.com",
                "job_title": "Security Manager",
                "department": "Security",
                "compensation": 215000.00,
                "hire_date": "2018-05-20T00:00:00Z",
                "employment_status": "active",
                "manager_id": None
            },
            {
                "id": "MGR004",
                "name": "Karen White",
                "email": "karen.white@company.com",
                "job_title": "Support Manager",
                "department": "Customer Support",
                "compensation": 140000.00,
                "hire_date": "2020-08-01T00:00:00Z",
                "employment_status": "active",
                "manager_id": None
            }
        ]
        
        logger.info(f"Successfully fetched {len(mock_employees)} employees (mock data)")
        
        # In production, this would be:
        # all_employees = []
        # page = 1
        # 
        # while True:
        #     endpoint = f"/hris/{connection_id}/employee"
        #     params = {
        #         "page_size": page_size,
        #         "page": page
        #     }
        #     
        #     employees = self._make_request(
        #         method="GET",
        #         endpoint=endpoint,
        #         params=params
        #     )
        #     
        #     if not employees or len(employees) == 0:
        #         break
        #     
        #     all_employees.extend(employees)
        #     
        #     if len(employees) < page_size:
        #         break
        #     
        #     page += 1
        # 
        # return all_employees
        
        return mock_employees
    
    def fetch_payslips(
        self,
        connection_id: str,
        start_date: datetime,
        end_date: datetime,
        page_size: int = 100,
        validate_connection: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch payslip data from HRIS system via Unified.to.
        
        This method retrieves payslip information including gross pay, net pay,
        deductions, and taxes for all employees within the specified date range.
        Handles pagination and multiple pay periods per employee.
        
        Args:
            connection_id: Unified.to connection ID for the HRIS system
            start_date: Start date for payslips (inclusive)
            end_date: End date for payslips (inclusive)
            page_size: Number of payslips per page (default: 100, max: 200)
            validate_connection: Whether to validate connection_id before fetching (default: True)
        
        Returns:
            List of payslip dictionaries with fields:
                - id: Payslip ID
                - employee_id: Employee ID
                - pay_period_start: Start date of pay period (ISO 8601)
                - pay_period_end: End date of pay period (ISO 8601)
                - pay_date: Date payment was issued (ISO 8601)
                - gross_pay: Gross pay amount before deductions
                - net_pay: Net pay amount after deductions
                - deductions: Total deductions amount
                - taxes: Total taxes withheld
                - currency: Currency code (e.g., "USD")
                - employee_name: Employee name (if available)
                - department: Department name (if available)
        
        Raises:
            APIConnectionError: If request fails or connection is invalid
            ValueError: If date range is invalid, page_size is out of range, or connection_id is empty
        
        Example:
            >>> from datetime import datetime
            >>> connector = UnifiedToConnector(api_key="...", workspace_id="...")
            >>> payslips = connector.fetch_payslips(
            ...     connection_id="conn_123",
            ...     start_date=datetime(2024, 1, 1),
            ...     end_date=datetime(2024, 3, 31)
            ... )
            >>> for payslip in payslips:
            ...     print(f"{payslip['employee_id']}: ${payslip['gross_pay']:,.2f} gross")
        """
        # Validate inputs
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        if page_size < 1 or page_size > 200:
            raise ValueError("page_size must be between 1 and 200")
        
        if not connection_id or connection_id.strip() == '':
            raise ValueError("connection_id cannot be empty")
        
        # Validate connection_id if requested
        if validate_connection:
            try:
                self._validate_connection_id(connection_id)
            except APIConnectionError as e:
                logger.error(f"Connection validation failed: {e}")
                raise
            except ValueError as e:
                logger.error(f"Invalid connection_id: {e}")
                raise
        
        logger.info(
            f"Fetching payslips from {start_date.date()} to {end_date.date()} "
            f"(connection_id={connection_id}, page_size={page_size})"
        )
        
        # Format dates for API (ISO 8601 format)
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Collect all payslips across pages
        all_payslips = []
        page = 1
        max_pages = 100  # Safety limit to prevent infinite loops
        
        while page <= max_pages:
            logger.debug(f"Fetching payslips page {page}...")
            
            # Construct endpoint for payslips
            endpoint = f"/hris/{connection_id}/payslip"
            
            # Make request with pagination and date filtering
            params = {
                "start_date": start_str,
                "end_date": end_str,
                "page_size": page_size,
                "page": page
            }
            
            retry_count = 0
            max_retries = 2
            
            while retry_count <= max_retries:
                try:
                    # Fetch page of payslips with retry logic
                    payslips = self._make_request(
                        method="GET",
                        endpoint=endpoint,
                        params=params,
                        retry=True  # Enable retry for transient failures
                    )
                    
                    # Check if we got any payslips
                    if not payslips or len(payslips) == 0:
                        logger.debug(f"No more payslips on page {page}, stopping pagination")
                        break
                    
                    # Add payslips to collection
                    all_payslips.extend(payslips)
                    logger.debug(f"Page {page}: fetched {len(payslips)} payslips")
                    
                    # If we got fewer payslips than page_size, we've reached the end
                    if len(payslips) < page_size:
                        logger.debug(f"Received {len(payslips)} < {page_size}, last page reached")
                        break
                    
                    # Move to next page
                    page += 1
                    break  # Success, exit retry loop
                    
                except APIConnectionError as e:
                    # Enhanced error logging with full context
                    logger.error(
                        f"Failed to fetch payslips page {page}: {e.message}",
                        extra={
                            'api_name': self.api_name,
                            'endpoint': endpoint,
                            'connection_id': connection_id,
                            'page': page,
                            'status_code': e.status_code,
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat(),
                            'error_details': e.details,
                            'retry_count': retry_count
                        }
                    )
                    
                    # Handle specific non-transient error cases
                    if e.status_code == 403:
                        raise APIConnectionError(
                            message=f"Insufficient permissions to access payslips for connection '{connection_id}'. "
                                    f"Please verify the connection has payroll data access enabled.",
                            api_name=self.api_name,
                            status_code=403,
                            endpoint=endpoint,
                            details={
                                'error': 'Insufficient permissions',
                                'connection_id': connection_id,
                                'required_permission': 'hris.payslip.read'
                            }
                        )
                    elif e.status_code == 404:
                        raise APIConnectionError(
                            message=f"Payslip endpoint not found for connection '{connection_id}'. "
                                    f"This HRIS system may not support payslip data.",
                            api_name=self.api_name,
                            status_code=404,
                            endpoint=endpoint,
                            details={
                                'error': 'Endpoint not found',
                                'connection_id': connection_id,
                                'suggestion': 'Verify the HRIS system supports payslip data'
                            }
                        )
                    
                    # Handle transient errors with intelligent retry logic
                    operation = f"fetch_payslips page {page}"
                    should_retry = self._handle_transient_error(e, operation, retry_count, max_retries)
                    
                    if should_retry:
                        retry_count += 1
                        logger.info(f"Retrying {operation} (attempt {retry_count + 1}/{max_retries + 1})")
                        continue
                    else:
                        # Non-transient error or max retries exceeded, re-raise
                        raise
        
        if page > max_pages:
            logger.warning(
                f"Reached maximum page limit ({max_pages}) while fetching payslips. "
                f"Some data may be missing."
            )
        
        logger.info(
            f"Successfully fetched {len(all_payslips)} payslips "
            f"across {page - 1} page(s)"
        )
        
        return all_payslips
    
    def _transform_payslip_to_cost(
        self,
        raw_payslip: Dict[str, Any],
        project_name: str = "General Operations"
    ) -> Optional['ProjectCost']:
        """
        Transform a raw Unified.to payslip into a ProjectCost model.
        
        This method maps payslip data to the ProjectCost Pydantic model,
        calculates hourly rates from annual salaries, and validates the
        transformed data. Invalid payslips are logged and skipped.
        
        Args:
            raw_payslip: Raw payslip dictionary from Unified.to API with fields:
                - id: Payslip ID
                - employee_id: Employee ID
                - pay_period_start: Start date of pay period
                - pay_period_end: End date of pay period
                - pay_date: Date payment was issued
                - gross_pay: Gross pay amount
                - net_pay: Net pay amount
                - deductions: Total deductions
                - taxes: Total taxes withheld
                - currency: Currency code
            project_name: Project name to associate with this cost (default: "General Operations")
        
        Returns:
            ProjectCost object if transformation succeeds, None if validation fails
        
        Example:
            >>> raw_payslip = {
            ...     "id": "PAY001",
            ...     "employee_id": "EMP001",
            ...     "pay_period_start": "2024-03-01T00:00:00Z",
            ...     "pay_period_end": "2024-03-31T00:00:00Z",
            ...     "pay_date": "2024-03-31T00:00:00Z",
            ...     "gross_pay": 12500.00,
            ...     "net_pay": 9375.00,
            ...     "deductions": 1875.00,
            ...     "taxes": 1250.00,
            ...     "currency": "USD",
            ...     "employee_name": "Alice Johnson",
            ...     "department": "Engineering"
            ... }
            >>> cost = connector._transform_payslip_to_cost(raw_payslip, "Alpha Development")
            >>> print(f"${cost.amount:,.2f}")
            12500.00
        """
        from models.financial_models import ProjectCost
        from pydantic import ValidationError
        
        try:
            # Extract required fields with fallbacks
            payslip_id = raw_payslip.get('id', '')
            if not payslip_id:
                logger.warning(f"Skipping payslip: missing id")
                return None
            
            employee_id = raw_payslip.get('employee_id', '')
            if not employee_id:
                logger.warning(f"Skipping payslip {payslip_id}: missing employee_id")
                return None
            
            # Extract gross pay as the cost amount
            gross_pay = raw_payslip.get('gross_pay')
            if gross_pay is None or gross_pay <= 0:
                logger.warning(
                    f"Skipping payslip {payslip_id}: invalid gross_pay '{gross_pay}'"
                )
                return None
            
            # Parse pay date
            pay_date_str = raw_payslip.get('pay_date', '')
            if not pay_date_str:
                logger.warning(f"Skipping payslip {payslip_id}: missing pay_date")
                return None
            
            # Parse ISO 8601 datetime and convert to naive datetime
            pay_date_with_tz = datetime.fromisoformat(pay_date_str.replace('Z', '+00:00'))
            pay_date = pay_date_with_tz.replace(tzinfo=None)
            
            # Calculate hourly rate from gross pay
            # Assume monthly pay period (2080 hours/year ÷ 12 months ≈ 173.33 hours/month)
            hours_per_month = 173.33
            hourly_rate = round(gross_pay / hours_per_month, 2)
            
            # Calculate annual salary from monthly gross pay
            annual_salary = gross_pay * 12
            
            # Build metadata with additional payslip information
            metadata = {
                'payslip_id': payslip_id,
                'gross_pay': gross_pay,
                'net_pay': raw_payslip.get('net_pay'),
                'deductions': raw_payslip.get('deductions'),
                'taxes': raw_payslip.get('taxes'),
                'currency': raw_payslip.get('currency', 'USD'),
                'pay_period_start': raw_payslip.get('pay_period_start'),
                'pay_period_end': raw_payslip.get('pay_period_end'),
                'annual_salary': annual_salary,
                'hourly_rate': hourly_rate,
                'hours_per_month': hours_per_month
            }
            
            # Add optional fields if available
            if 'employee_name' in raw_payslip:
                metadata['employee_name'] = raw_payslip['employee_name']
            
            if 'department' in raw_payslip:
                metadata['department'] = raw_payslip['department']
            
            # Create ProjectCost with validated data
            cost = ProjectCost(
                cost_id=f"PAYSLIP_{payslip_id}",
                cost_type="Payroll",
                amount=gross_pay,
                project_name=project_name,
                employee_id=employee_id,
                date=pay_date,
                is_rd_classified=False,  # Default to False, user will classify later
                metadata=metadata
            )
            
            logger.debug(
                f"Successfully transformed payslip {payslip_id}: "
                f"{employee_id} - ${gross_pay:,.2f} (hourly rate: ${hourly_rate:.2f})"
            )
            
            return cost
        
        except ValidationError as e:
            logger.error(
                f"Validation error transforming payslip {raw_payslip.get('id')}: {e}"
            )
            logger.debug(f"Raw payslip data: {raw_payslip}")
            return None
        
        except Exception as e:
            logger.error(
                f"Unexpected error transforming payslip {raw_payslip.get('id')}: {e}"
            )
            logger.debug(f"Raw payslip data: {raw_payslip}")
            return None
