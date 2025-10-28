"""
Unit tests for base API connector class.

Tests cover:
- Rate limiting functionality
- Request/response handling
- Error handling for various HTTP status codes
- Retry logic with exponential backoff
- Request statistics tracking
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import httpx

from tools.api_connectors import BaseAPIConnector, RateLimiter
from utils.exceptions import APIConnectionError


class MockAPIConnector(BaseAPIConnector):
    """Mock API connector for testing."""
    
    def __init__(self, base_url="https://api.example.com", api_key="test_key", **kwargs):
        self.base_url = base_url
        self.api_key = api_key
        super().__init__(api_name="MockAPI", **kwargs)
    
    def _get_base_url(self) -> str:
        return self.base_url
    
    def _get_auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter(requests_per_second=10.0)
        assert limiter.requests_per_second == 10.0
        assert limiter.burst_size == 10
        assert limiter.tokens == 10.0
    
    def test_rate_limiter_custom_burst(self):
        """Test rate limiter with custom burst size."""
        limiter = RateLimiter(requests_per_second=5.0, burst_size=20)
        assert limiter.requests_per_second == 5.0
        assert limiter.burst_size == 20
        assert limiter.tokens == 20.0
    
    def test_rate_limiter_acquire_no_wait(self):
        """Test acquiring token when tokens are available."""
        limiter = RateLimiter(requests_per_second=10.0)
        wait_time = limiter.acquire()
        assert wait_time == 0.0
        assert limiter.tokens < 10.0
    
    def test_rate_limiter_acquire_with_wait(self):
        """Test acquiring token when no tokens available."""
        limiter = RateLimiter(requests_per_second=10.0)
        
        # Exhaust all tokens
        for _ in range(10):
            limiter.acquire()
        
        # Next acquire should wait
        start_time = time.time()
        wait_time = limiter.acquire()
        elapsed = time.time() - start_time
        
        assert wait_time > 0.0
        assert elapsed >= 0.09  # Should wait ~0.1s for 10 req/s
    
    def test_rate_limiter_reset(self):
        """Test resetting rate limiter."""
        limiter = RateLimiter(requests_per_second=10.0)
        
        # Exhaust tokens
        for _ in range(10):
            limiter.acquire()
        
        # Reset
        limiter.reset()
        assert limiter.tokens == 10.0
        
        # Should be able to acquire immediately
        wait_time = limiter.acquire()
        assert wait_time == 0.0


class TestBaseAPIConnector:
    """Test cases for BaseAPIConnector class."""
    
    def test_connector_initialization(self):
        """Test connector initializes with correct parameters."""
        connector = MockAPIConnector(
            rate_limit=5.0,
            timeout=20.0,
            max_retries=5
        )
        
        assert connector.api_name == "MockAPI"
        assert connector.timeout == 20.0
        assert connector.max_retries == 5
        assert connector.rate_limiter is not None
        assert connector.rate_limiter.requests_per_second == 5.0
        assert connector.request_count == 0
        assert connector.error_count == 0
    
    def test_connector_without_rate_limit(self):
        """Test connector without rate limiting."""
        connector = MockAPIConnector(rate_limit=None)
        assert connector.rate_limiter is None
    
    def test_get_base_url(self):
        """Test getting base URL."""
        connector = MockAPIConnector(base_url="https://test.api.com")
        assert connector._get_base_url() == "https://test.api.com"
    
    def test_get_auth_headers(self):
        """Test getting authentication headers."""
        connector = MockAPIConnector(api_key="secret_key")
        headers = connector._get_auth_headers()
        assert headers == {"Authorization": "Bearer secret_key"}
    
    @patch('httpx.Client.request')
    def test_make_request_success(self, mock_request):
        """Test successful API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        connector = MockAPIConnector()
        result = connector._make_request("GET", "/test")
        
        assert result == {"data": "test"}
        assert connector.request_count == 1
        assert connector.error_count == 0
    
    @patch('httpx.Client.request')
    def test_make_request_with_params(self, mock_request):
        """Test request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        connector = MockAPIConnector()
        result = connector._make_request(
            "GET",
            "/test",
            params={"key": "value"}
        )
        
        assert result == {"data": "test"}
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['params'] == {"key": "value"}
    
    @patch('httpx.Client.request')
    def test_make_request_with_json_body(self, mock_request):
        """Test request with JSON body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response
        
        connector = MockAPIConnector()
        result = connector._make_request(
            "POST",
            "/test",
            json_data={"field": "value"}
        )
        
        assert result == {"success": True}
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['json'] == {"field": "value"}
    
    @patch('httpx.Client.request')
    def test_make_request_401_error(self, mock_request):
        """Test handling of 401 Unauthorized error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_request.return_value = mock_response
        
        connector = MockAPIConnector(max_retries=1)
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector._make_request("GET", "/test", retry=False)
        
        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)
    
    @patch('httpx.Client.request')
    def test_make_request_404_error(self, mock_request):
        """Test handling of 404 Not Found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Resource not found"}
        mock_request.return_value = mock_response
        
        connector = MockAPIConnector(max_retries=1)
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector._make_request("GET", "/test", retry=False)
        
        assert exc_info.value.status_code == 404
        assert "Resource not found" in str(exc_info.value)
    
    @patch('httpx.Client.request')
    def test_make_request_429_rate_limit_error(self, mock_request):
        """Test handling of 429 Rate Limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Too many requests"}
        mock_request.return_value = mock_response
        
        connector = MockAPIConnector(max_retries=1)
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector._make_request("GET", "/test", retry=False)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value)
    
    @patch('httpx.Client.request')
    def test_make_request_500_server_error(self, mock_request):
        """Test handling of 500 Server Error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_request.return_value = mock_response
        
        connector = MockAPIConnector(max_retries=1)
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector._make_request("GET", "/test", retry=False)
        
        assert exc_info.value.status_code == 500
        assert "Server error" in str(exc_info.value)
    
    @patch('httpx.Client.request')
    def test_make_request_timeout(self, mock_request):
        """Test handling of request timeout."""
        mock_request.side_effect = httpx.TimeoutException("Request timeout")
        
        connector = MockAPIConnector(timeout=5.0, max_retries=1)
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector._make_request("GET", "/test", retry=False)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('httpx.Client.request')
    def test_retry_logic_success_after_failure(self, mock_request):
        """Test retry logic succeeds after initial failure."""
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.json.return_value = {"error": "Server error"}
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": "success"}
        
        mock_request.side_effect = [mock_response_fail, mock_response_success]
        
        connector = MockAPIConnector(max_retries=3)
        result = connector._make_request("GET", "/test")
        
        assert result == {"data": "success"}
        assert mock_request.call_count == 2
    
    @patch('httpx.Client.request')
    def test_retry_logic_exhausted(self, mock_request):
        """Test retry logic fails after max attempts."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Server error"}
        mock_request.return_value = mock_response
        
        connector = MockAPIConnector(max_retries=2)
        
        with pytest.raises(APIConnectionError):
            connector._make_request("GET", "/test")
        
        # Should try initial + 1 retry = 2 times
        assert mock_request.call_count == 2
        assert connector.error_count == 1
    
    @patch('httpx.Client.request')
    def test_rate_limiting_applied(self, mock_request):
        """Test rate limiting is applied to requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response
        
        # Create connector with low rate limit
        connector = MockAPIConnector(rate_limit=5.0)
        
        # Make multiple requests
        start_time = time.time()
        for _ in range(6):
            connector._make_request("GET", "/test")
        elapsed = time.time() - start_time
        
        # Should take at least 0.2s for 6 requests at 5 req/s
        assert elapsed >= 0.15
        assert connector.total_wait_time > 0
    
    def test_get_statistics(self):
        """Test getting connector statistics."""
        connector = MockAPIConnector()
        connector.request_count = 10
        connector.error_count = 2
        connector.total_wait_time = 1.5
        
        stats = connector.get_statistics()
        
        assert stats['api_name'] == "MockAPI"
        assert stats['request_count'] == 10
        assert stats['error_count'] == 2
        assert stats['error_rate'] == 0.2
        assert stats['total_wait_time'] == 1.5
    
    def test_context_manager(self):
        """Test connector works as context manager."""
        with MockAPIConnector() as connector:
            assert connector.client is not None
        
        # Client should be closed after context exit
        # (We can't easily test this without accessing internals)
    
    def test_close(self):
        """Test closing connector."""
        connector = MockAPIConnector()
        connector.close()
        # Should not raise any errors


class TestClockifyConnector:
    """Test cases for ClockifyConnector class."""
    
    def test_clockify_initialization(self):
        """Test Clockify connector initializes correctly."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_api_key",
            workspace_id="test_workspace_id"
        )
        
        assert connector.api_name == "Clockify"
        assert connector.api_key == "test_api_key"
        assert connector.workspace_id == "test_workspace_id"
        assert connector.rate_limiter is not None
        assert connector.rate_limiter.requests_per_second == 10.0
    
    def test_clockify_initialization_empty_api_key(self):
        """Test Clockify connector raises error with empty API key."""
        from tools.api_connectors import ClockifyConnector
        
        with pytest.raises(ValueError) as exc_info:
            ClockifyConnector(api_key="", workspace_id="test_workspace")
        
        assert "API key cannot be empty" in str(exc_info.value)
    
    def test_clockify_initialization_empty_workspace_id(self):
        """Test Clockify connector raises error with empty workspace ID."""
        from tools.api_connectors import ClockifyConnector
        
        with pytest.raises(ValueError) as exc_info:
            ClockifyConnector(api_key="test_key", workspace_id="")
        
        assert "workspace ID cannot be empty" in str(exc_info.value)
    
    def test_clockify_get_base_url(self):
        """Test Clockify base URL."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        assert connector._get_base_url() == "https://api.clockify.me/api/v1"
    
    def test_clockify_get_auth_headers(self):
        """Test Clockify authentication headers."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="secret_key",
            workspace_id="test_workspace"
        )
        
        headers = connector._get_auth_headers()
        assert headers["X-Api-Key"] == "secret_key"
        assert headers["Content-Type"] == "application/json"
    
    @patch('httpx.Client.request')
    def test_clockify_test_authentication_success(self, mock_request):
        """Test successful Clockify authentication."""
        from tools.api_connectors import ClockifyConnector
        
        # Mock successful user info response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user123",
            "email": "test@example.com",
            "name": "Test User",
            "activeWorkspace": "workspace123",
            "status": "ACTIVE"
        }
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        user_info = connector.test_authentication()
        
        assert user_info["id"] == "user123"
        assert user_info["email"] == "test@example.com"
        assert user_info["name"] == "Test User"
    
    @patch('httpx.Client.request')
    def test_clockify_test_authentication_failure(self, mock_request):
        """Test failed Clockify authentication."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid API key"}
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="invalid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.test_authentication()
        
        assert exc_info.value.status_code == 401
        assert "Invalid Clockify API key" in str(exc_info.value)
    
    @patch('httpx.Client.request')
    def test_fetch_time_entries_single_page(self, mock_request):
        """Test fetching time entries with single page of results."""
        from tools.api_connectors import ClockifyConnector
        from datetime import datetime
        
        # Mock time entries response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "entry1",
                "description": "Task 1",
                "userId": "user1",
                "projectId": "project1",
                "timeInterval": {
                    "start": "2024-01-15T09:00:00Z",
                    "end": "2024-01-15T17:00:00Z"
                },
                "duration": "PT8H"
            },
            {
                "id": "entry2",
                "description": "Task 2",
                "userId": "user2",
                "projectId": "project2",
                "timeInterval": {
                    "start": "2024-01-16T09:00:00Z",
                    "end": "2024-01-16T13:00:00Z"
                },
                "duration": "PT4H"
            }
        ]
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        entries = connector.fetch_time_entries(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert len(entries) == 2
        assert entries[0]["id"] == "entry1"
        assert entries[1]["id"] == "entry2"
        assert mock_request.call_count == 1
    
    @patch('httpx.Client.request')
    def test_fetch_time_entries_multiple_pages(self, mock_request):
        """Test fetching time entries with pagination."""
        from tools.api_connectors import ClockifyConnector
        from datetime import datetime
        
        # Mock paginated responses
        page1_entries = [{"id": f"entry{i}"} for i in range(1, 51)]  # 50 entries
        page2_entries = [{"id": f"entry{i}"} for i in range(51, 76)]  # 25 entries
        
        mock_response_page1 = Mock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = page1_entries
        
        mock_response_page2 = Mock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = page2_entries
        
        mock_request.side_effect = [mock_response_page1, mock_response_page2]
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        entries = connector.fetch_time_entries(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            page_size=50
        )
        
        assert len(entries) == 75
        assert entries[0]["id"] == "entry1"
        assert entries[74]["id"] == "entry75"
        assert mock_request.call_count == 2
    
    @patch('httpx.Client.request')
    def test_fetch_time_entries_empty_result(self, mock_request):
        """Test fetching time entries with no results."""
        from tools.api_connectors import ClockifyConnector
        from datetime import datetime
        
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        entries = connector.fetch_time_entries(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert len(entries) == 0
        assert mock_request.call_count == 1
    
    def test_fetch_time_entries_invalid_date_range(self):
        """Test fetch_time_entries with invalid date range."""
        from tools.api_connectors import ClockifyConnector
        from datetime import datetime
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 31),
                end_date=datetime(2024, 1, 1)
            )
        
        assert "start_date must be before or equal to end_date" in str(exc_info.value)
    
    def test_fetch_time_entries_invalid_page_size(self):
        """Test fetch_time_entries with invalid page size."""
        from tools.api_connectors import ClockifyConnector
        from datetime import datetime
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Test page_size too small
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                page_size=0
            )
        
        assert "page_size must be between 1 and 50" in str(exc_info.value)
        
        # Test page_size too large
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                page_size=51
            )
        
        assert "page_size must be between 1 and 50" in str(exc_info.value)
    
    @patch('httpx.Client.request')
    def test_fetch_time_entries_api_error(self, mock_request):
        """Test fetch_time_entries handles API errors."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        assert exc_info.value.status_code == 500



class TestClockifyDataTransformation:
    """Test cases for Clockify data transformation methods."""
    
    def test_parse_duration_hours_only(self):
        """Test parsing duration with hours only."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        assert connector._parse_duration("PT8H") == 8.0
        assert connector._parse_duration("PT1H") == 1.0
        assert connector._parse_duration("PT24H") == 24.0
    
    def test_parse_duration_hours_and_minutes(self):
        """Test parsing duration with hours and minutes."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        assert connector._parse_duration("PT8H30M") == 8.5
        assert connector._parse_duration("PT2H15M") == 2.25
        assert connector._parse_duration("PT0H45M") == 0.75
    
    def test_parse_duration_hours_minutes_seconds(self):
        """Test parsing duration with hours, minutes, and seconds."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # 2 hours, 15 minutes, 30 seconds = 2.258333... hours
        result = connector._parse_duration("PT2H15M30S")
        assert abs(result - 2.26) < 0.01  # Rounded to 2 decimal places
        
        # 8 hours, 0 minutes, 30 seconds
        result = connector._parse_duration("PT8H0M30S")
        assert abs(result - 8.01) < 0.01
    
    def test_parse_duration_minutes_only(self):
        """Test parsing duration with minutes only."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        assert connector._parse_duration("PT30M") == 0.5
        assert connector._parse_duration("PT45M") == 0.75
        assert connector._parse_duration("PT90M") == 1.5
    
    def test_parse_duration_invalid(self):
        """Test parsing invalid duration strings."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        assert connector._parse_duration("") is None
        assert connector._parse_duration("invalid") is None
        assert connector._parse_duration("PT") is None
    
    def test_transform_time_entry_complete_data(self):
        """Test transforming time entry with all fields present."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_entry = {
            "id": "entry123",
            "userId": "user456",
            "userName": "John Doe",
            "description": "Implemented authentication algorithm",
            "projectId": "project789",
            "projectName": "Alpha Development",
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T17:30:00Z"
            },
            "duration": "PT8H30M"
        }
        
        entry = connector._transform_time_entry(raw_entry)
        
        assert entry is not None
        assert entry.employee_id == "user456"
        assert entry.employee_name == "John Doe"
        assert entry.project_name == "Alpha Development"
        assert entry.task_description == "Implemented authentication algorithm"
        assert entry.hours_spent == 8.5
        assert entry.date.year == 2024
        assert entry.date.month == 1
        assert entry.date.day == 15
        assert entry.is_rd_classified is False
    
    def test_transform_time_entry_missing_optional_fields(self):
        """Test transforming time entry with missing optional fields."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_entry = {
            "id": "entry123",
            "userId": "user456",
            "projectId": "project789",
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T17:00:00Z"
            },
            "duration": "PT8H"
        }
        
        entry = connector._transform_time_entry(raw_entry)
        
        assert entry is not None
        assert entry.employee_id == "user456"
        assert entry.employee_name == "user456"  # Falls back to userId
        assert entry.project_name == "project789"  # Falls back to projectId
        assert entry.task_description == "No description provided"  # Default value
        assert entry.hours_spent == 8.0
    
    def test_transform_time_entry_empty_description(self):
        """Test transforming time entry with empty description."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_entry = {
            "id": "entry123",
            "userId": "user456",
            "userName": "John Doe",
            "projectName": "Alpha Development",
            "description": "",  # Empty description
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T17:00:00Z"
            },
            "duration": "PT8H"
        }
        
        entry = connector._transform_time_entry(raw_entry)
        
        assert entry is not None
        assert entry.task_description == "No description provided"
    
    def test_transform_time_entry_missing_user_id(self):
        """Test transforming time entry without userId (should fail)."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_entry = {
            "id": "entry123",
            "projectName": "Alpha Development",
            "description": "Some work",
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T17:00:00Z"
            },
            "duration": "PT8H"
        }
        
        entry = connector._transform_time_entry(raw_entry)
        
        assert entry is None  # Should return None for missing userId
    
    def test_transform_time_entry_invalid_duration(self):
        """Test transforming time entry with invalid duration."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_entry = {
            "id": "entry123",
            "userId": "user456",
            "userName": "John Doe",
            "projectName": "Alpha Development",
            "description": "Some work",
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T17:00:00Z"
            },
            "duration": "invalid"
        }
        
        entry = connector._transform_time_entry(raw_entry)
        
        assert entry is None  # Should return None for invalid duration
    
    def test_transform_time_entry_zero_duration(self):
        """Test transforming time entry with zero duration."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_entry = {
            "id": "entry123",
            "userId": "user456",
            "userName": "John Doe",
            "projectName": "Alpha Development",
            "description": "Some work",
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-15T09:00:00Z"
            },
            "duration": "PT0H"
        }
        
        entry = connector._transform_time_entry(raw_entry)
        
        assert entry is None  # Should return None for zero duration
    
    def test_transform_time_entry_missing_start_time(self):
        """Test transforming time entry without start time."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_entry = {
            "id": "entry123",
            "userId": "user456",
            "userName": "John Doe",
            "projectName": "Alpha Development",
            "description": "Some work",
            "timeInterval": {},
            "duration": "PT8H"
        }
        
        entry = connector._transform_time_entry(raw_entry)
        
        assert entry is None  # Should return None for missing start time
    
    def test_transform_time_entry_hours_exceeding_24(self):
        """Test transforming time entry with hours exceeding 24 (should fail validation)."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_entry = {
            "id": "entry123",
            "userId": "user456",
            "userName": "John Doe",
            "projectName": "Alpha Development",
            "description": "Some work",
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z",
                "end": "2024-01-16T10:00:00Z"
            },
            "duration": "PT25H"  # More than 24 hours
        }
        
        entry = connector._transform_time_entry(raw_entry)
        
        assert entry is None  # Should return None due to validation error
    
    def test_transform_time_entry_various_date_formats(self):
        """Test transforming time entries with various ISO 8601 date formats."""
        from tools.api_connectors import ClockifyConnector
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Test with Z timezone
        raw_entry_z = {
            "id": "entry1",
            "userId": "user456",
            "userName": "John Doe",
            "projectName": "Alpha Development",
            "description": "Work",
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z"
            },
            "duration": "PT8H"
        }
        
        entry = connector._transform_time_entry(raw_entry_z)
        assert entry is not None
        assert entry.date.year == 2024
        
        # Test with +00:00 timezone
        raw_entry_offset = {
            "id": "entry2",
            "userId": "user456",
            "userName": "John Doe",
            "projectName": "Alpha Development",
            "description": "Work",
            "timeInterval": {
                "start": "2024-01-15T09:00:00+00:00"
            },
            "duration": "PT8H"
        }
        
        entry = connector._transform_time_entry(raw_entry_offset)
        assert entry is not None
        assert entry.date.year == 2024
    
    def test_transform_time_entry_logging_on_error(self, caplog):
        """Test that transformation errors are properly logged."""
        from tools.api_connectors import ClockifyConnector
        import logging
        
        connector = ClockifyConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Entry with missing userId
        raw_entry = {
            "id": "entry123",
            "projectName": "Alpha Development",
            "description": "Some work",
            "timeInterval": {
                "start": "2024-01-15T09:00:00Z"
            },
            "duration": "PT8H"
        }
        
        with caplog.at_level(logging.WARNING):
            entry = connector._transform_time_entry(raw_entry)
        
        assert entry is None
        assert "missing userId" in caplog.text


class TestClockifyErrorHandling:
    """Test cases for Clockify-specific error handling (Task 58)."""
    
    @patch('httpx.Client.request')
    def test_clockify_401_unauthorized_invalid_api_key(self, mock_request):
        """Test handling of 401 Unauthorized error with invalid API key."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid API key"}
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="invalid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.status_code == 401
        assert error.api_name == "Clockify"
        assert "Authentication failed" in str(error)
        assert error.endpoint is not None
    
    @patch('httpx.Client.request')
    def test_clockify_404_not_found_invalid_workspace(self, mock_request):
        """Test handling of 404 Not Found error with invalid workspace ID."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Workspace not found"}
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="invalid_workspace_id"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.status_code == 404
        assert error.api_name == "Clockify"
        assert "Resource not found" in str(error)
        assert "Workspace not found" in str(error)
    
    @patch('httpx.Client.request')
    def test_clockify_429_rate_limit_exceeded(self, mock_request):
        """Test handling of 429 Too Many Requests error (rate limiting)."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock 429 response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "message": "Too many requests",
            "retryAfter": 60
        }
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.status_code == 429
        assert error.api_name == "Clockify"
        assert "Rate limit exceeded" in str(error)
    
    @patch('httpx.Client.request')
    def test_clockify_exponential_backoff_retry(self, mock_request):
        """Test exponential backoff retry logic for transient errors."""
        from tools.api_connectors import ClockifyConnector
        from datetime import datetime
        
        # First two calls fail with 500, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.json.return_value = {"error": "Internal server error"}
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = [
            {
                "id": "entry1",
                "userId": "user1",
                "projectName": "Project A",
                "description": "Task 1",
                "timeInterval": {"start": "2024-01-15T09:00:00Z"},
                "duration": "PT8H"
            }
        ]
        
        mock_request.side_effect = [
            mock_response_fail,
            mock_response_success
        ]
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="workspace123"
        )
        
        # Should succeed after retry
        entries = connector.fetch_time_entries(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert len(entries) == 1
        assert entries[0]["id"] == "entry1"
        assert mock_request.call_count == 2
    
    @patch('httpx.Client.request')
    def test_clockify_retry_exhausted_raises_error(self, mock_request):
        """Test that error is raised after retry attempts are exhausted."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # All calls fail with 500
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.status_code == 500
        assert error.api_name == "Clockify"
        assert "Server error" in str(error)
        
        # Should have tried max_retries times (default is 3)
        assert mock_request.call_count == 3
    
    @patch('httpx.Client.request')
    def test_clockify_401_on_test_authentication(self, mock_request):
        """Test 401 error handling specifically for test_authentication method."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="invalid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.test_authentication()
        
        error = exc_info.value
        assert error.status_code == 401
        assert "Invalid Clockify API key" in str(error)
        assert "check your credentials" in str(error)
    
    @patch('httpx.Client.request')
    def test_clockify_404_on_fetch_time_entries(self, mock_request):
        """Test 404 error handling for invalid workspace in fetch_time_entries."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "message": "Workspace 'invalid_id' not found"
        }
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="invalid_id"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.status_code == 404
        assert error.api_name == "Clockify"
        assert "not found" in str(error).lower()
    
    @patch('httpx.Client.request')
    def test_clockify_429_with_retry_after_header(self, mock_request):
        """Test 429 rate limit error includes retry information."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock 429 response with Retry-After header
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "message": "Rate limit exceeded. Please retry after 60 seconds."
        }
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.status_code == 429
        assert "Rate limit exceeded" in str(error)
    
    @patch('httpx.Client.request')
    def test_clockify_error_context_preserved(self, mock_request):
        """Test that error context (endpoint, details) is preserved."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "Access forbidden: insufficient permissions"
        }
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.status_code == 403
        assert error.api_name == "Clockify"
        assert error.endpoint is not None
        assert "workspace123" in error.endpoint
        assert error.details is not None
        assert "insufficient permissions" in str(error.details)
    
    @patch('httpx.Client.request')
    def test_clockify_multiple_retry_attempts_with_backoff(self, mock_request):
        """Test that multiple retry attempts use exponential backoff."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        import time
        
        # All calls fail
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"error": "Service unavailable"}
        mock_request.return_value = mock_response
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="workspace123"
        )
        
        start_time = time.time()
        
        with pytest.raises(APIConnectionError):
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        elapsed = time.time() - start_time
        
        # With exponential backoff, there should be some delay between retries
        # We'll be lenient due to test timing variability and jitter
        assert elapsed >= 0.2  # At least some delay occurred
        assert mock_request.call_count == 3  # max_retries = 3
    
    @patch('httpx.Client.request')
    def test_clockify_network_timeout_error(self, mock_request):
        """Test handling of network timeout errors."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock timeout exception
        mock_request.side_effect = httpx.TimeoutException("Request timeout")
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.api_name == "Clockify"
        assert "timeout" in str(error).lower()
    
    @patch('httpx.Client.request')
    def test_clockify_connection_error(self, mock_request):
        """Test handling of connection errors."""
        from tools.api_connectors import ClockifyConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock connection error
        mock_request.side_effect = httpx.ConnectError("Connection refused")
        
        connector = ClockifyConnector(
            api_key="valid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_time_entries(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        error = exc_info.value
        assert error.api_name == "Clockify"
        assert "failed" in str(error).lower()



class TestUnifiedToConnector:
    """Test cases for UnifiedToConnector class (Task 60)."""
    
    def test_unified_to_initialization(self):
        """Test Unified.to connector initializes correctly."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_api_key",
            workspace_id="test_workspace_id"
        )
        
        assert connector.api_name == "Unified.to"
        assert connector.api_key == "test_api_key"
        assert connector.workspace_id == "test_workspace_id"
        assert connector.rate_limiter is not None
        assert connector.rate_limiter.requests_per_second == 5.0
        assert connector.access_token is None
        assert connector.token_expires_at is None
        assert connector.refresh_token is None
    
    def test_unified_to_initialization_empty_api_key(self):
        """Test Unified.to connector raises error with empty API key."""
        from tools.api_connectors import UnifiedToConnector
        
        with pytest.raises(ValueError) as exc_info:
            UnifiedToConnector(api_key="", workspace_id="test_workspace")
        
        assert "API key cannot be empty" in str(exc_info.value)
    
    def test_unified_to_initialization_empty_workspace_id(self):
        """Test Unified.to connector raises error with empty workspace ID."""
        from tools.api_connectors import UnifiedToConnector
        
        with pytest.raises(ValueError) as exc_info:
            UnifiedToConnector(api_key="test_key", workspace_id="")
        
        assert "workspace ID cannot be empty" in str(exc_info.value)
    
    def test_unified_to_get_base_url(self):
        """Test Unified.to base URL."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        assert connector._get_base_url() == "https://api.unified.to"
    
    def test_unified_to_is_token_expired_no_token(self):
        """Test token expiration check when no token is set."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        assert connector._is_token_expired() is True
    
    def test_unified_to_is_token_expired_no_expiration(self):
        """Test token expiration check when token has no expiration."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        connector.access_token = "test_token"
        
        assert connector._is_token_expired() is True
    
    def test_unified_to_is_token_expired_valid_token(self):
        """Test token expiration check with valid token."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime, timedelta
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        connector.access_token = "test_token"
        connector.token_expires_at = datetime.now() + timedelta(hours=1)
        
        assert connector._is_token_expired() is False
    
    def test_unified_to_is_token_expired_expired_token(self):
        """Test token expiration check with expired token."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime, timedelta
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        connector.access_token = "test_token"
        connector.token_expires_at = datetime.now() - timedelta(hours=1)
        
        assert connector._is_token_expired() is True
    
    def test_unified_to_is_token_expired_near_expiration(self):
        """Test token expiration check with token near expiration (60s buffer)."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime, timedelta
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        connector.access_token = "test_token"
        # Token expires in 30 seconds (within 60s buffer)
        connector.token_expires_at = datetime.now() + timedelta(seconds=30)
        
        assert connector._is_token_expired() is True
    
    @patch('httpx.Client.post')
    def test_unified_to_refresh_access_token_success(self, mock_post):
        """Test successful OAuth 2.0 token refresh."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime, timedelta
        
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token_123",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token_456"
        }
        mock_post.return_value = mock_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        # Refresh token
        connector._refresh_access_token()
        
        assert connector.access_token == "new_access_token_123"
        assert connector.refresh_token == "new_refresh_token_456"
        assert connector.token_expires_at is not None
        
        # Check expiration is approximately 1 hour from now
        time_until_expiry = (connector.token_expires_at - datetime.now()).total_seconds()
        assert 3500 < time_until_expiry < 3700  # Allow some variance
    
    @patch('httpx.Client.post')
    def test_unified_to_refresh_access_token_failure(self, mock_post):
        """Test failed OAuth 2.0 token refresh."""
        from tools.api_connectors import UnifiedToConnector
        from utils.exceptions import APIConnectionError
        
        # Mock failed token response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid credentials"}
        mock_response.text = "Invalid credentials"
        mock_post.return_value = mock_response
        
        connector = UnifiedToConnector(
            api_key="invalid_key",
            workspace_id="test_workspace"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector._refresh_access_token()
        
        error = exc_info.value
        assert error.status_code == 401
        assert error.api_name == "Unified.to"
        assert "Token refresh failed" in str(error)
    
    @patch('httpx.Client.post')
    def test_unified_to_refresh_access_token_no_access_token_in_response(self, mock_post):
        """Test token refresh with missing access_token in response."""
        from tools.api_connectors import UnifiedToConnector
        from utils.exceptions import APIConnectionError
        
        # Mock response without access_token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "expires_in": 3600
            # Missing access_token
        }
        mock_post.return_value = mock_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector._refresh_access_token()
        
        error = exc_info.value
        assert "No access_token in token response" in str(error)
    
    @patch('httpx.Client.post')
    def test_unified_to_refresh_access_token_network_error(self, mock_post):
        """Test token refresh with network error."""
        from tools.api_connectors import UnifiedToConnector
        from utils.exceptions import APIConnectionError
        
        # Mock network error
        mock_post.side_effect = httpx.ConnectError("Connection failed")
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector._refresh_access_token()
        
        error = exc_info.value
        assert error.api_name == "Unified.to"
        assert "Token refresh request failed" in str(error)
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_unified_to_get_auth_headers_triggers_refresh(self, mock_request, mock_post):
        """Test that getting auth headers triggers token refresh if needed."""
        from tools.api_connectors import UnifiedToConnector
        
        # Mock successful token response
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "fresh_token_123",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        # Get auth headers (should trigger refresh)
        headers = connector._get_auth_headers()
        
        assert headers["Authorization"] == "Bearer fresh_token_123"
        assert headers["Content-Type"] == "application/json"
        assert mock_post.call_count == 1
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_unified_to_get_auth_headers_no_refresh_if_valid(self, mock_request, mock_post):
        """Test that auth headers don't trigger refresh if token is valid."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime, timedelta
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        # Set valid token
        connector.access_token = "valid_token_123"
        connector.token_expires_at = datetime.now() + timedelta(hours=1)
        
        # Get auth headers (should NOT trigger refresh)
        headers = connector._get_auth_headers()
        
        assert headers["Authorization"] == "Bearer valid_token_123"
        assert mock_post.call_count == 0  # No token refresh call
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_unified_to_test_authentication_success(self, mock_request, mock_post):
        """Test successful Unified.to authentication."""
        from tools.api_connectors import UnifiedToConnector
        
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock workspace info response
        mock_workspace_response = Mock()
        mock_workspace_response.status_code = 200
        mock_workspace_response.json.return_value = {
            "id": "workspace123",
            "name": "Test Workspace",
            "status": "active"
        }
        mock_request.return_value = mock_workspace_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        workspace_info = connector.test_authentication()
        
        assert workspace_info["id"] == "workspace123"
        assert workspace_info["name"] == "Test Workspace"
        assert workspace_info["status"] == "active"
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_unified_to_test_authentication_401_failure(self, mock_request, mock_post):
        """Test failed Unified.to authentication with 401."""
        from tools.api_connectors import UnifiedToConnector
        from utils.exceptions import APIConnectionError
        
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock 401 workspace response
        mock_workspace_response = Mock()
        mock_workspace_response.status_code = 401
        mock_workspace_response.json.return_value = {"error": "Unauthorized"}
        mock_request.return_value = mock_workspace_response
        
        connector = UnifiedToConnector(
            api_key="invalid_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.test_authentication()
        
        error = exc_info.value
        assert error.status_code == 401
        assert "Invalid Unified.to API key or workspace ID" in str(error)
        assert "check your credentials" in str(error)
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_unified_to_test_authentication_403_failure(self, mock_request, mock_post):
        """Test failed Unified.to authentication with 403."""
        from tools.api_connectors import UnifiedToConnector
        from utils.exceptions import APIConnectionError
        
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock 403 workspace response
        mock_workspace_response = Mock()
        mock_workspace_response.status_code = 403
        mock_workspace_response.json.return_value = {"error": "Forbidden"}
        mock_request.return_value = mock_workspace_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.test_authentication()
        
        error = exc_info.value
        assert error.status_code == 403
        assert "Invalid Unified.to API key or workspace ID" in str(error)


class TestUnifiedToEmployeeFetching:
    """Test cases for UnifiedToConnector employee fetching."""
    
    def test_fetch_employees_returns_mock_data(self):
        """Test fetch_employees returns mock employee data."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        employees = connector.fetch_employees()
        
        # Verify we get mock data
        assert len(employees) == 11
        assert all(isinstance(emp, dict) for emp in employees)
        
        # Verify first employee has expected structure
        first_emp = employees[0]
        assert first_emp["id"] == "EMP001"
        assert first_emp["name"] == "Alice Johnson"
        assert first_emp["email"] == "alice.johnson@company.com"
        assert first_emp["job_title"] == "Senior Software Engineer"
        assert first_emp["department"] == "Engineering"
        assert first_emp["compensation"] == 150000.00
        assert first_emp["hire_date"] == "2022-01-15T00:00:00Z"
        assert first_emp["employment_status"] == "active"
        assert first_emp["manager_id"] == "MGR001"
    
    def test_fetch_employees_with_connection_id(self):
        """Test fetch_employees accepts connection_id parameter."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Should work with connection_id (even though it's mock data)
        employees = connector.fetch_employees(connection_id="conn_123")
        
        assert len(employees) == 11
        assert employees[0]["id"] == "EMP001"
    
    def test_fetch_employees_with_custom_page_size(self):
        """Test fetch_employees accepts custom page_size."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Should work with custom page_size (even though it's mock data)
        employees = connector.fetch_employees(page_size=50)
        
        assert len(employees) == 11
    
    def test_fetch_employees_invalid_page_size(self):
        """Test fetch_employees validates page_size parameter."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Test page_size too small
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_employees(page_size=0)
        
        assert "page_size must be between 1 and 200" in str(exc_info.value)
        
        # Test page_size too large
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_employees(page_size=201)
        
        assert "page_size must be between 1 and 200" in str(exc_info.value)
    
    def test_fetch_employees_all_fields_present(self):
        """Test all employees have required fields."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        employees = connector.fetch_employees()
        
        required_fields = [
            "id", "name", "email", "job_title", "department",
            "compensation", "hire_date", "employment_status", "manager_id"
        ]
        
        for emp in employees:
            for field in required_fields:
                assert field in emp, f"Employee {emp.get('id')} missing field: {field}"
    
    def test_fetch_employees_includes_managers(self):
        """Test fetch_employees includes manager records."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        employees = connector.fetch_employees()
        
        # Find managers (employees with manager_id = None)
        managers = [emp for emp in employees if emp["manager_id"] is None]
        
        assert len(managers) == 4
        assert any(emp["id"] == "MGR001" for emp in managers)
        assert any(emp["id"] == "MGR002" for emp in managers)
    
    def test_fetch_employees_compensation_types(self):
        """Test employee compensation values are numeric."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        employees = connector.fetch_employees()
        
        for emp in employees:
            assert isinstance(emp["compensation"], (int, float))
            assert emp["compensation"] > 0
    
    def test_fetch_employees_departments(self):
        """Test employees have various departments."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        employees = connector.fetch_employees()
        
        departments = set(emp["department"] for emp in employees)
        
        # Should have multiple departments
        assert len(departments) >= 4
        assert "Engineering" in departments
        assert "Data Science" in departments
        assert "Security" in departments
        assert "Customer Support" in departments


class TestUnifiedToPayslipFetching:
    """Test cases for UnifiedToConnector payslip fetching (Task 62)."""
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_single_page(self, mock_request, mock_post):
        """Test fetching payslips with single page of results."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime
        
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock payslips response
        mock_payslips_response = Mock()
        mock_payslips_response.status_code = 200
        mock_payslips_response.json.return_value = [
            {
                "id": "PAY001",
                "employee_id": "EMP001",
                "pay_period_start": "2024-03-01T00:00:00Z",
                "pay_period_end": "2024-03-31T00:00:00Z",
                "pay_date": "2024-03-31T00:00:00Z",
                "gross_pay": 12500.00,
                "net_pay": 9375.00,
                "deductions": 1875.00,
                "taxes": 1250.00,
                "currency": "USD",
                "employee_name": "Alice Johnson",
                "department": "Engineering"
            },
            {
                "id": "PAY002",
                "employee_id": "EMP002",
                "pay_period_start": "2024-03-01T00:00:00Z",
                "pay_period_end": "2024-03-31T00:00:00Z",
                "pay_date": "2024-03-31T00:00:00Z",
                "gross_pay": 13750.00,
                "net_pay": 10312.50,
                "deductions": 2062.50,
                "taxes": 1375.00,
                "currency": "USD",
                "employee_name": "Bob Smith",
                "department": "Engineering"
            }
        ]
        mock_request.return_value = mock_payslips_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        payslips = connector.fetch_payslips(
            connection_id="conn_123",
            start_date=datetime(2024, 3, 1),
            end_date=datetime(2024, 3, 31)
        )
        
        assert len(payslips) == 2
        assert payslips[0]["id"] == "PAY001"
        assert payslips[0]["employee_id"] == "EMP001"
        assert payslips[0]["gross_pay"] == 12500.00
        assert payslips[1]["id"] == "PAY002"
        assert payslips[1]["employee_id"] == "EMP002"
        assert payslips[1]["gross_pay"] == 13750.00
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_multiple_pages(self, mock_request, mock_post):
        """Test fetching payslips with pagination."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime
        
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock paginated responses
        page1_payslips = [
            {
                "id": f"PAY{str(i).zfill(3)}",
                "employee_id": f"EMP{str(i).zfill(3)}",
                "pay_period_start": "2024-01-01T00:00:00Z",
                "pay_period_end": "2024-01-31T00:00:00Z",
                "pay_date": "2024-01-31T00:00:00Z",
                "gross_pay": 10000.00 + (i * 100),
                "net_pay": 7500.00 + (i * 75),
                "deductions": 1500.00,
                "taxes": 1000.00,
                "currency": "USD"
            }
            for i in range(1, 101)  # 100 payslips
        ]
        
        page2_payslips = [
            {
                "id": f"PAY{str(i).zfill(3)}",
                "employee_id": f"EMP{str(i).zfill(3)}",
                "pay_period_start": "2024-01-01T00:00:00Z",
                "pay_period_end": "2024-01-31T00:00:00Z",
                "pay_date": "2024-01-31T00:00:00Z",
                "gross_pay": 10000.00 + (i * 100),
                "net_pay": 7500.00 + (i * 75),
                "deductions": 1500.00,
                "taxes": 1000.00,
                "currency": "USD"
            }
            for i in range(101, 151)  # 50 payslips
        ]
        
        mock_response_page1 = Mock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = page1_payslips
        
        mock_response_page2 = Mock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = page2_payslips
        
        mock_request.side_effect = [mock_response_page1, mock_response_page2]
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        payslips = connector.fetch_payslips(
            connection_id="conn_123",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            page_size=100
        )
        
        assert len(payslips) == 150
        assert payslips[0]["id"] == "PAY001"
        assert payslips[149]["id"] == "PAY150"
        assert mock_request.call_count == 2
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_empty_result(self, mock_request, mock_post):
        """Test fetching payslips with no results."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime
        
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock empty response
        mock_payslips_response = Mock()
        mock_payslips_response.status_code = 200
        mock_payslips_response.json.return_value = []
        mock_request.return_value = mock_payslips_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        payslips = connector.fetch_payslips(
            connection_id="conn_123",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert len(payslips) == 0
        assert mock_request.call_count == 1
    
    def test_fetch_payslips_invalid_date_range(self):
        """Test fetch_payslips with invalid date range."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_payslips(
                connection_id="conn_123",
                start_date=datetime(2024, 3, 31),
                end_date=datetime(2024, 3, 1)
            )
        
        assert "start_date must be before or equal to end_date" in str(exc_info.value)
    
    def test_fetch_payslips_invalid_page_size(self):
        """Test fetch_payslips with invalid page size."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Test page_size too small
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_payslips(
                connection_id="conn_123",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                page_size=0
            )
        
        assert "page_size must be between 1 and 200" in str(exc_info.value)
        
        # Test page_size too large
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_payslips(
                connection_id="conn_123",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                page_size=201
            )
        
        assert "page_size must be between 1 and 200" in str(exc_info.value)
    
    def test_fetch_payslips_empty_connection_id(self):
        """Test fetch_payslips with empty connection_id."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_payslips(
                connection_id="",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        assert "connection_id cannot be empty" in str(exc_info.value)
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_api_error(self, mock_request, mock_post):
        """Test fetch_payslips handles API errors."""
        from tools.api_connectors import UnifiedToConnector
        from utils.exceptions import APIConnectionError
        from datetime import datetime
        
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock error response
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.json.return_value = {"error": "Internal server error"}
        mock_request.return_value = mock_error_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_payslips(
                connection_id="conn_123",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        assert exc_info.value.status_code == 500
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_multiple_pay_periods(self, mock_request, mock_post):
        """Test fetching payslips handles multiple pay periods per employee."""
        from tools.api_connectors import UnifiedToConnector
        from datetime import datetime
        
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock payslips with multiple pay periods for same employee
        mock_payslips_response = Mock()
        mock_payslips_response.status_code = 200
        mock_payslips_response.json.return_value = [
            {
                "id": "PAY001_JAN",
                "employee_id": "EMP001",
                "pay_period_start": "2024-01-01T00:00:00Z",
                "pay_period_end": "2024-01-31T00:00:00Z",
                "pay_date": "2024-01-31T00:00:00Z",
                "gross_pay": 12500.00,
                "net_pay": 9375.00,
                "deductions": 1875.00,
                "taxes": 1250.00,
                "currency": "USD"
            },
            {
                "id": "PAY001_FEB",
                "employee_id": "EMP001",
                "pay_period_start": "2024-02-01T00:00:00Z",
                "pay_period_end": "2024-02-29T00:00:00Z",
                "pay_date": "2024-02-29T00:00:00Z",
                "gross_pay": 12500.00,
                "net_pay": 9375.00,
                "deductions": 1875.00,
                "taxes": 1250.00,
                "currency": "USD"
            },
            {
                "id": "PAY001_MAR",
                "employee_id": "EMP001",
                "pay_period_start": "2024-03-01T00:00:00Z",
                "pay_period_end": "2024-03-31T00:00:00Z",
                "pay_date": "2024-03-31T00:00:00Z",
                "gross_pay": 12500.00,
                "net_pay": 9375.00,
                "deductions": 1875.00,
                "taxes": 1250.00,
                "currency": "USD"
            }
        ]
        mock_request.return_value = mock_payslips_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        payslips = connector.fetch_payslips(
            connection_id="conn_123",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31)
        )
        
        # Should get all 3 pay periods for the same employee
        assert len(payslips) == 3
        assert all(p["employee_id"] == "EMP001" for p in payslips)
        assert payslips[0]["id"] == "PAY001_JAN"
        assert payslips[1]["id"] == "PAY001_FEB"
        assert payslips[2]["id"] == "PAY001_MAR"


class TestUnifiedToPayslipTransformation:
    """Test cases for UnifiedToConnector payslip transformation (Task 62)."""
    
    def test_transform_payslip_complete_data(self):
        """Test transforming payslip with all fields present."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_period_start": "2024-03-01T00:00:00Z",
            "pay_period_end": "2024-03-31T00:00:00Z",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00,
            "net_pay": 9375.00,
            "deductions": 1875.00,
            "taxes": 1250.00,
            "currency": "USD",
            "employee_name": "Alice Johnson",
            "department": "Engineering"
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip, "Alpha Development")
        
        assert cost is not None
        assert cost.cost_id == "PAYSLIP_PAY001"
        assert cost.cost_type == "Payroll"
        assert cost.amount == 12500.00
        assert cost.project_name == "Alpha Development"
        assert cost.employee_id == "EMP001"
        assert cost.date.year == 2024
        assert cost.date.month == 3
        assert cost.date.day == 31
        assert cost.is_rd_classified is False
        
        # Check metadata
        assert cost.metadata is not None
        assert cost.metadata["payslip_id"] == "PAY001"
        assert cost.metadata["gross_pay"] == 12500.00
        assert cost.metadata["net_pay"] == 9375.00
        assert cost.metadata["deductions"] == 1875.00
        assert cost.metadata["taxes"] == 1250.00
        assert cost.metadata["currency"] == "USD"
        assert cost.metadata["employee_name"] == "Alice Johnson"
        assert cost.metadata["department"] == "Engineering"
        
        # Check computed hourly rate (12500 / 173.33 ≈ 72.12)
        assert cost.metadata["hourly_rate"] is not None
        assert abs(cost.metadata["hourly_rate"] - 72.12) < 0.1
        
        # Check annual salary (12500 * 12 = 150000)
        assert cost.metadata["annual_salary"] == 150000.00
    
    def test_transform_payslip_missing_optional_fields(self):
        """Test transforming payslip with missing optional fields."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY002",
            "employee_id": "EMP002",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 13750.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        assert cost.cost_id == "PAYSLIP_PAY002"
        assert cost.cost_type == "Payroll"
        assert cost.amount == 13750.00
        assert cost.project_name == "General Operations"  # Default value
        assert cost.employee_id == "EMP002"
        
        # Check metadata has required fields but not optional ones
        assert cost.metadata is not None
        assert cost.metadata["payslip_id"] == "PAY002"
        assert cost.metadata["gross_pay"] == 13750.00
        assert "employee_name" not in cost.metadata
        assert "department" not in cost.metadata
    
    def test_transform_payslip_missing_id(self):
        """Test transforming payslip with missing id."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is None
    
    def test_transform_payslip_missing_employee_id(self):
        """Test transforming payslip with missing employee_id."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is None
    
    def test_transform_payslip_invalid_gross_pay(self):
        """Test transforming payslip with invalid gross_pay."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Test zero gross_pay
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 0
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        assert cost is None
        
        # Test negative gross_pay
        raw_payslip["gross_pay"] = -1000.00
        cost = connector._transform_payslip_to_cost(raw_payslip)
        assert cost is None
    
    def test_transform_payslip_missing_pay_date(self):
        """Test transforming payslip with missing pay_date."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is None
    
    def test_transform_payslip_hourly_rate_calculation(self):
        """Test hourly rate calculation from gross pay."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 10000.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        # Hourly rate = 10000 / 173.33 ≈ 57.69
        assert cost.metadata["hourly_rate"] is not None
        assert abs(cost.metadata["hourly_rate"] - 57.69) < 0.1
    
    def test_transform_payslip_annual_salary_calculation(self):
        """Test annual salary calculation from monthly gross pay."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 8333.33
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        # Annual salary = 8333.33 * 12 ≈ 100000
        assert cost.metadata["annual_salary"] is not None
        assert abs(cost.metadata["annual_salary"] - 99999.96) < 0.1
    
    def test_transform_payslip_custom_project_name(self):
        """Test transforming payslip with custom project name."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip, "Beta Project")
        
        assert cost is not None
        assert cost.project_name == "Beta Project"
    
    def test_transform_payslip_default_project_name(self):
        """Test transforming payslip with default project name."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        assert cost.project_name == "General Operations"
    
    def test_transform_payslip_computed_hourly_rate_from_metadata(self):
        """Test that ProjectCost.hourly_rate computed field works with metadata."""
        from tools.api_connectors import UnifiedToConnector
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        # Test the computed field from ProjectCost model
        assert cost.hourly_rate is not None
        assert abs(cost.hourly_rate - 72.12) < 0.1



class TestUnifiedToConnector:
    """Test cases for UnifiedToConnector class with enhanced error handl