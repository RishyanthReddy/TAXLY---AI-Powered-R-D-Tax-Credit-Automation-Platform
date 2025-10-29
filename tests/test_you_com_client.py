"""
Unit tests for You.com API client.

Tests the YouComClient class including:
- Initialization and validation
- Authentication
- Base URL and headers
- Error handling
- Search API integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from tools.you_com_client import YouComClient
from utils.exceptions import APIConnectionError


class TestYouComClientInitialization:
    """Test YouComClient initialization and validation."""
    
    def test_initialization_with_valid_key(self):
        """Test successful initialization with valid API key."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        assert client.api_key == api_key
        assert client.api_name == "You.com"
        assert client.timeout == 60.0
        assert client.max_retries == 3
    
    def test_initialization_with_empty_key_raises_error(self):
        """Test that empty API key raises ValueError."""
        with pytest.raises(ValueError, match="You.com API key cannot be empty"):
            YouComClient(api_key="")
    
    def test_initialization_with_none_key_raises_error(self):
        """Test that None API key raises ValueError."""
        with pytest.raises(ValueError):
            YouComClient(api_key=None)
    
    def test_initialization_warns_on_invalid_key_format(self, caplog):
        """Test that invalid key format logs a warning."""
        api_key = "invalid-key-format"
        client = YouComClient(api_key=api_key)
        
        # Check that warning was logged
        assert "does not start with 'ydc-sk-'" in caplog.text
    
    def test_rate_limiter_configured(self):
        """Test that rate limiter is properly configured."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Rate limiter should be configured for 10 req/min
        assert client.rate_limiter is not None
        # 10 requests per minute = 10/60 = 0.167 requests per second
        assert abs(client.rate_limiter.requests_per_second - (10.0 / 60.0)) < 0.001


class TestYouComClientBaseConfiguration:
    """Test base configuration methods."""
    
    def test_get_base_url(self):
        """Test that base URL is correct."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        assert client._get_base_url() == "https://api.you.com"
    
    def test_get_auth_headers(self):
        """Test that authentication headers are correct."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        headers = client._get_auth_headers()
        
        assert headers["X-API-Key"] == api_key
        assert headers["Content-Type"] == "application/json"
    
    def test_auth_headers_include_api_key(self):
        """Test that auth headers include the API key."""
        api_key = "ydc-sk-secret-key-123"
        client = YouComClient(api_key=api_key)
        
        headers = client._get_auth_headers()
        
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == api_key


class TestYouComClientAuthentication:
    """Test authentication functionality."""
    
    @patch.object(YouComClient, '_make_request')
    def test_authentication_success(self, mock_make_request):
        """Test successful authentication."""
        mock_make_request.return_value = {"results": []}
        
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        result = client.test_authentication()
        
        assert result is True
        mock_make_request.assert_called_once()
    
    @patch.object(YouComClient, '_make_request')
    def test_authentication_failure_401(self, mock_make_request):
        """Test authentication failure with 401 error."""
        mock_make_request.side_effect = APIConnectionError(
            message="Invalid API key",
            api_name="You.com",
            status_code=401,
            endpoint="/v1/search"
        )
        
        api_key = "ydc-sk-invalid"
        client = YouComClient(api_key=api_key)
        
        result = client.test_authentication()
        
        assert result is False
    
    @patch.object(YouComClient, '_make_request')
    def test_authentication_failure_other_error(self, mock_make_request):
        """Test authentication failure with non-401 error."""
        mock_make_request.side_effect = APIConnectionError(
            message="Server error",
            api_name="You.com",
            status_code=500,
            endpoint="/v1/search"
        )
        
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        result = client.test_authentication()
        
        assert result is False
    
    @patch.object(YouComClient, '_make_request')
    def test_authentication_unexpected_exception(self, mock_make_request):
        """Test authentication with unexpected exception."""
        mock_make_request.side_effect = Exception("Unexpected error")
        
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        result = client.test_authentication()
        
        assert result is False


class TestYouComClientStatistics:
    """Test statistics tracking."""
    
    def test_get_statistics_initial(self):
        """Test statistics when no requests have been made."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        stats = client.get_statistics()
        
        assert stats['api_name'] == "You.com"
        assert stats['request_count'] == 0
        assert stats['error_count'] == 0
        assert stats['error_rate'] == 0.0
        assert stats['total_wait_time'] == 0.0
        assert stats['rate_limit'] == "10 requests per minute"
    
    def test_get_statistics_after_requests(self):
        """Test statistics after making requests."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Manually increment request count to simulate a request
        client.request_count = 1
        
        stats = client.get_statistics()
        
        assert stats['request_count'] == 1
        assert 'rate_limit' in stats


class TestYouComClientContextManager:
    """Test context manager functionality."""
    
    def test_context_manager_usage(self):
        """Test that client can be used as context manager."""
        api_key = "ydc-sk-test123"
        
        with YouComClient(api_key=api_key) as client:
            assert client.api_key == api_key
            assert client.client is not None
    
    @patch.object(YouComClient, 'close')
    def test_context_manager_closes_client(self, mock_close):
        """Test that context manager closes client on exit."""
        api_key = "ydc-sk-test123"
        
        with YouComClient(api_key=api_key) as client:
            pass
        
        mock_close.assert_called_once()


class TestYouComClientErrorHandling:
    """Test error handling in You.com client."""
    
    def test_invalid_api_key_format_still_initializes(self):
        """Test that invalid format still allows initialization."""
        # This should initialize but log a warning
        api_key = "not-a-valid-format"
        client = YouComClient(api_key=api_key)
        
        assert client.api_key == api_key
    
    def test_client_has_proper_timeout(self):
        """Test that client has appropriate timeout for agent operations."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # You.com agent operations can take longer, so timeout should be 60s
        assert client.timeout == 60.0
    
    def test_client_has_retry_configured(self):
        """Test that client has retry logic configured."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        assert client.max_retries == 3
    
    def test_handle_youcom_error_401_unauthorized(self, caplog):
        """Test handling of 401 Unauthorized errors with detailed logging."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        error = APIConnectionError(
            message="Invalid API key",
            api_name="You.com",
            status_code=401,
            endpoint="/v1/search",
            details={"error": "Unauthorized"}
        )
        
        with pytest.raises(APIConnectionError):
            client._handle_youcom_error(
                error=error,
                endpoint="/v1/search",
                context={"query": "test"}
            )
        
        # Verify detailed logging
        assert "401 Unauthorized" in caplog.text
        assert "Invalid or expired API key" in caplog.text
        assert "Verify YOUCOM_API_KEY" in caplog.text
    
    def test_handle_youcom_error_429_rate_limit(self, caplog):
        """Test handling of 429 Rate Limit Exceeded errors."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        error = APIConnectionError(
            message="Rate limit exceeded",
            api_name="You.com",
            status_code=429,
            endpoint="/v1/agents/runs",
            details={"error": "Too many requests"}
        )
        
        with pytest.raises(APIConnectionError):
            client._handle_youcom_error(
                error=error,
                endpoint="/v1/agents/runs",
                context={"agent_mode": "express"}
            )
        
        # Verify detailed logging
        assert "429 Rate Limit Exceeded" in caplog.text
        assert "Too many requests" in caplog.text
        assert "10 requests per minute" in caplog.text
    
    def test_handle_youcom_error_500_server_error(self, caplog):
        """Test handling of 500 Internal Server Error."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        error = APIConnectionError(
            message="Internal server error",
            api_name="You.com",
            status_code=500,
            endpoint="/v1/contents",
            details={"error": "Server error"}
        )
        
        with pytest.raises(APIConnectionError):
            client._handle_youcom_error(
                error=error,
                endpoint="/v1/contents",
                context={"url": "https://example.com"}
            )
        
        # Verify detailed logging
        assert "500 Internal Server Error" in caplog.text
        assert "Server error" in caplog.text
        assert "Retry the request" in caplog.text
    
    def test_handle_youcom_error_503_service_unavailable(self, caplog):
        """Test handling of 503 Service Unavailable errors."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        error = APIConnectionError(
            message="Service unavailable",
            api_name="You.com",
            status_code=503,
            endpoint="/v1/search",
            details={"error": "Service temporarily unavailable"}
        )
        
        with pytest.raises(APIConnectionError):
            client._handle_youcom_error(
                error=error,
                endpoint="/v1/search",
                context={"query": "test"}
            )
        
        # Verify detailed logging
        assert "503 Service Unavailable" in caplog.text
        assert "temporarily unavailable" in caplog.text
    
    def test_handle_youcom_error_400_bad_request(self, caplog):
        """Test handling of 400 Bad Request errors."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        error = APIConnectionError(
            message="Invalid parameters",
            api_name="You.com",
            status_code=400,
            endpoint="/v1/search",
            details={"error": "Invalid query parameter"}
        )
        
        with pytest.raises(APIConnectionError):
            client._handle_youcom_error(
                error=error,
                endpoint="/v1/search",
                context={"query": ""}
            )
        
        # Verify detailed logging
        assert "400 Bad Request" in caplog.text
        assert "Invalid request parameters" in caplog.text
    
    def test_handle_youcom_error_403_forbidden(self, caplog):
        """Test handling of 403 Forbidden errors."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        error = APIConnectionError(
            message="Access forbidden",
            api_name="You.com",
            status_code=403,
            endpoint="/v1/agents/runs",
            details={"error": "Insufficient permissions"}
        )
        
        with pytest.raises(APIConnectionError):
            client._handle_youcom_error(
                error=error,
                endpoint="/v1/agents/runs",
                context={"agent_mode": "advanced"}
            )
        
        # Verify detailed logging
        assert "403 Forbidden" in caplog.text
        assert "lacks permission" in caplog.text
    
    def test_handle_youcom_error_with_context(self, caplog):
        """Test that error context is included in logging."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        error = APIConnectionError(
            message="Error",
            api_name="You.com",
            status_code=500,
            endpoint="/v1/search",
            details={}
        )
        
        context = {
            "query": "test query",
            "count": 10,
            "freshness": "week"
        }
        
        with pytest.raises(APIConnectionError):
            client._handle_youcom_error(
                error=error,
                endpoint="/v1/search",
                context=context
            )
        
        # Verify context is in log
        assert "query=test query" in caplog.text
        assert "count=10" in caplog.text
        assert "freshness=week" in caplog.text
    
    def test_search_error_uses_enhanced_handler(self, caplog):
        """Test that search method uses enhanced error handler."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with patch.object(client, '_make_request', side_effect=APIConnectionError(
            message="Rate limit exceeded",
            api_name="You.com",
            status_code=429,
            endpoint="/v1/search",
            details={}
        )):
            with pytest.raises(APIConnectionError):
                client.search(query="test")
        
        # Verify enhanced error handling was used
        assert "429 Rate Limit Exceeded" in caplog.text
    
    def test_agent_run_error_uses_enhanced_handler(self, caplog):
        """Test that agent_run method uses enhanced error handler."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with patch.object(client, '_make_request', side_effect=APIConnectionError(
            message="Server error",
            api_name="You.com",
            status_code=500,
            endpoint="/v1/agents/runs",
            details={}
        )):
            with pytest.raises(APIConnectionError):
                client.agent_run(prompt="test prompt")
        
        # Verify enhanced error handling was used
        assert "500 Internal Server Error" in caplog.text
    
    def test_fetch_content_error_uses_enhanced_handler(self, caplog):
        """Test that fetch_content method uses enhanced error handler."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with patch.object(client, '_make_request', side_effect=APIConnectionError(
            message="Unauthorized",
            api_name="You.com",
            status_code=401,
            endpoint="/v1/contents",
            details={}
        )):
            with pytest.raises(APIConnectionError):
                client.fetch_content(url="https://example.com")
        
        # Verify enhanced error handling was used
        assert "401 Unauthorized" in caplog.text
    
    def test_express_agent_error_uses_enhanced_handler(self, caplog):
        """Test that express_agent method uses enhanced error handler."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with patch.object(client, 'agent_run', side_effect=APIConnectionError(
            message="Rate limit",
            api_name="You.com",
            status_code=429,
            endpoint="/v1/agents/runs (express)",
            details={}
        )):
            with pytest.raises(APIConnectionError):
                client.express_agent(narrative_text="test narrative")
        
        # Verify enhanced error handling was used
        assert "429 Rate Limit Exceeded" in caplog.text


class TestYouComClientSearch:
    """Test You.com Search API integration."""
    
    def test_search_with_valid_query(self):
        """Test successful search with valid query."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Mock response matching You.com API structure
        mock_response = {
            "results": {
                "web": [
                    {
                        "url": "https://www.irs.gov/credits-deductions/research-credit",
                        "title": "Research Credit | Internal Revenue Service",
                        "description": "Information about the R&D tax credit",
                        "snippets": [
                            "The research credit is available for increasing research activities.",
                            "Qualified research expenses include wages, supplies, and contract research."
                        ],
                        "thumbnail_url": "https://example.com/thumb.jpg",
                        "page_age": "2025-01-15T10:00:00",
                        "authors": ["IRS"],
                        "favicon_url": "https://www.irs.gov/favicon.ico"
                    }
                ],
                "news": [
                    {
                        "title": "New IRS Guidance on R&D Credits",
                        "description": "IRS releases updated guidance for 2025",
                        "page_age": "2025-01-20T14:30:00",
                        "thumbnail_url": "https://example.com/news-thumb.jpg",
                        "url": "https://news.example.com/irs-rd-2025"
                    }
                ]
            },
            "metadata": {
                "request_uuid": "test-uuid-123",
                "query": "IRS R&D tax credit 2025",
                "latency": 0.123
            }
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            results = client.search(query="IRS R&D tax credit 2025", count=5)
        
        # Should return combined web and news results
        assert len(results) == 2
        
        # Check web result
        web_result = results[0]
        assert web_result['title'] == "Research Credit | Internal Revenue Service"
        assert web_result['url'] == "https://www.irs.gov/credits-deductions/research-credit"
        assert web_result['description'] == "Information about the R&D tax credit"
        assert len(web_result['snippets']) == 2
        assert web_result['source_type'] == 'web'
        assert 'thumbnail_url' in web_result
        assert 'page_age' in web_result
        
        # Check news result
        news_result = results[1]
        assert news_result['title'] == "New IRS Guidance on R&D Credits"
        assert news_result['source_type'] == 'news'
        assert news_result['url'] == "https://news.example.com/irs-rd-2025"
    
    def test_search_with_empty_query_raises_error(self):
        """Test that empty query raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Search query cannot be empty"):
            client.search(query="")
    
    def test_search_with_invalid_count_raises_error(self):
        """Test that invalid count raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Count must be between 1 and 100"):
            client.search(query="test", count=0)
        
        with pytest.raises(ValueError, match="Count must be between 1 and 100"):
            client.search(query="test", count=101)
    
    def test_search_with_invalid_offset_raises_error(self):
        """Test that invalid offset raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Offset must be between 0 and 9"):
            client.search(query="test", offset=-1)
        
        with pytest.raises(ValueError, match="Offset must be between 0 and 9"):
            client.search(query="test", offset=10)
    
    def test_search_with_invalid_freshness_raises_error(self):
        """Test that invalid freshness raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Freshness must be one of"):
            client.search(query="test", freshness="invalid")
    
    def test_search_with_invalid_safesearch_raises_error(self):
        """Test that invalid safesearch raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Safesearch must be one of"):
            client.search(query="test", safesearch="invalid")
    
    def test_search_with_freshness_parameter(self):
        """Test search with freshness parameter."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "results": {"web": [], "news": []},
            "metadata": {}
        }
        
        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            client.search(query="test", freshness="week")
            
            # Verify freshness was included in params
            call_args = mock_request.call_args
            assert call_args[1]['params']['freshness'] == "week"
    
    def test_search_uses_correct_base_url(self):
        """Test that search uses api.ydc-index.io base URL."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "results": {"web": [], "news": []},
            "metadata": {}
        }
        
        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            client.search(query="test")
            
            # Verify correct base URL was used
            call_args = mock_request.call_args
            assert call_args[1]['base_url'] == "https://api.ydc-index.io"
    
    def test_search_handles_api_error(self):
        """Test search error handling."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with patch.object(client, '_make_request', side_effect=APIConnectionError(
            message="API error",
            api_name="You.com",
            endpoint="/v1/search"
        )):
            with pytest.raises(APIConnectionError):
                client.search(query="test")
    
    def test_search_with_empty_results(self):
        """Test search with no results."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "results": {"web": [], "news": []},
            "metadata": {}
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            results = client.search(query="very specific query with no results")
        
        assert len(results) == 0
    
    def test_parse_search_results_with_minimal_fields(self):
        """Test parsing results with only required fields."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "results": {
                "web": [
                    {
                        "title": "Test Title",
                        "url": "https://example.com",
                        "description": "Test description",
                        "snippets": []
                    }
                ],
                "news": []
            }
        }
        
        results = client._parse_search_results(mock_response)
        
        assert len(results) == 1
        assert results[0]['title'] == "Test Title"
        assert results[0]['url'] == "https://example.com"
        assert results[0]['description'] == "Test description"
        assert results[0]['snippets'] == []
        assert results[0]['source_type'] == 'web'


class TestYouComClientAgentAPI:
    """Test You.com Agent API integration."""
    
    def test_agent_run_with_valid_prompt(self):
        """Test successful agent run with valid prompt."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Mock response matching You.com Agent API structure
        mock_response = {
            "output": [
                {
                    "type": "web_search.results, chat_node.answer",
                    "text": """```json
{
  "qualification_percentage": 85.0,
  "confidence_score": 0.88,
  "reasoning": "The project demonstrates clear technological uncertainty in optimizing API response times. The team employed a systematic process of experimentation by testing multiple caching strategies and algorithm optimizations. This aligns with IRS Section 41 requirements for qualified research.",
  "citations": ["CFR Title 26 § 1.41-4", "Form 6765 Instructions"],
  "four_part_test_results": {
    "technological_in_nature": true,
    "elimination_of_uncertainty": true,
    "process_of_experimentation": true,
    "qualified_purpose": true
  },
  "technical_details": "The project involved researching novel caching algorithms and performance optimization techniques that were not readily available in existing literature."
}
```""",
                    "content": "Analyze this R&D project for tax credit qualification",
                    "agent": "express"
                }
            ]
        }
        
        prompt = """Analyze this R&D project for tax credit qualification:
        
Project: API Optimization
Description: Improve API response times through algorithm optimization
Activities: Algorithm research, caching strategies, performance testing
Hours: 120.5
Cost: $15,000
"""
        
        with patch.object(client, '_make_request', return_value=mock_response):
            response = client.agent_run(prompt=prompt, agent_mode="express")
        
        assert 'output' in response
        assert len(response['output']) > 0
        assert 'text' in response['output'][0]
        assert 'agent' in response['output'][0]
        assert response['output'][0]['agent'] == "express"
    
    def test_agent_run_with_empty_prompt_raises_error(self):
        """Test that empty prompt raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Agent prompt cannot be empty"):
            client.agent_run(prompt="")
    
    def test_agent_run_with_invalid_agent_mode_raises_error(self):
        """Test that invalid agent mode raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Agent mode must be one of"):
            client.agent_run(prompt="test", agent_mode="invalid")
    
    def test_agent_run_with_invalid_agent_mode_raises_error(self):
        """Test that invalid agent mode raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Agent mode must be one of"):
            client.agent_run(prompt="test", agent_mode="invalid")
    
    def test_agent_run_with_tools_parameter(self):
        """Test agent run with tools parameter."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "output": [
                {
                    "type": "chat_node.answer",
                    "text": "test response",
                    "content": "test",
                    "agent": "express"
                }
            ]
        }
        
        tools = [{"type": "web_search"}]
        
        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            client.agent_run(prompt="test", tools=tools)
            
            # Verify tools was included in payload
            call_args = mock_request.call_args
            assert call_args[1]['json_data']['tools'] == tools
    
    def test_agent_run_without_tools_parameter(self):
        """Test agent run without tools parameter."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "output": [
                {
                    "type": "chat_node.answer",
                    "text": "test response",
                    "content": "test",
                    "agent": "express"
                }
            ]
        }
        
        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            client.agent_run(prompt="test")
            
            # Verify tools was not included in payload
            call_args = mock_request.call_args
            assert 'tools' not in call_args[1]['json_data'] or call_args[1]['json_data'].get('tools') is None
    
    def test_agent_run_uses_correct_endpoint(self):
        """Test that agent run uses correct endpoint."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "output": [
                {
                    "type": "chat_node.answer",
                    "text": "test",
                    "content": "test",
                    "agent": "express"
                }
            ]
        }
        
        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            client.agent_run(prompt="test")
            
            # Verify correct endpoint was used
            call_args = mock_request.call_args
            assert call_args[1]['endpoint'] == "/v1/agents/runs"
            assert call_args[1]['method'] == "POST"
    
    def test_agent_run_handles_api_error(self):
        """Test agent run error handling."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with patch.object(client, '_make_request', side_effect=APIConnectionError(
            message="API error",
            api_name="You.com",
            endpoint="/v1/agents/runs"
        )):
            with pytest.raises(APIConnectionError):
                client.agent_run(prompt="test")
    
    def test_agent_run_with_different_modes(self):
        """Test agent run with different agent modes."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "output": [
                {
                    "type": "chat_node.answer",
                    "text": "test",
                    "content": "test",
                    "agent": "express"
                }
            ]
        }
        
        # Valid modes according to the implementation
        modes = ["express", "custom", "advanced"]
        
        for mode in modes:
            with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
                client.agent_run(prompt="test", agent_mode=mode)
                
                # Verify mode was included in payload
                call_args = mock_request.call_args
                assert call_args[1]['json_data']['agent'] == mode
    
    def test_agent_run_with_stream_parameter(self):
        """Test that streaming parameter is passed to API."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "output": [
                {
                    "type": "chat_node.answer",
                    "text": "test",
                    "content": "test",
                    "agent": "express"
                }
            ]
        }
        
        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            client.agent_run(prompt="test", stream=True)
            
            # Verify stream parameter was included in payload
            call_args = mock_request.call_args
            assert call_args[1]['json_data']['stream'] is True


class TestYouComClientAgentResponseParsing:
    """Test parsing of You.com Agent API responses."""
    
    def test_parse_agent_response_with_json_in_markdown(self):
        """Test parsing JSON response in markdown code fence."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """Here is the analysis:

```json
{
  "qualification_percentage": 85.0,
  "confidence_score": 0.88,
  "reasoning": "Project meets all four-part test criteria",
  "citations": ["CFR Title 26 § 1.41-4", "Form 6765"],
  "four_part_test_results": {
    "technological_in_nature": true,
    "elimination_of_uncertainty": true,
    "process_of_experimentation": true,
    "qualified_purpose": true
  }
}
```

This project qualifies for R&D tax credit."""
        
        result = client._parse_agent_response(response_text)
        
        assert result['qualification_percentage'] == 85.0
        assert result['confidence_score'] == 0.88
        assert result['reasoning'] == "Project meets all four-part test criteria"
        assert len(result['citations']) == 2
        assert 'four_part_test_results' in result
    
    def test_parse_agent_response_with_pure_json(self):
        """Test parsing pure JSON response."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "qualification_percentage": 75.5,
  "confidence_score": 0.82,
  "reasoning": "Project demonstrates technological uncertainty",
  "citations": ["Publication 542"]
}"""
        
        result = client._parse_agent_response(response_text)
        
        assert result['qualification_percentage'] == 75.5
        assert result['confidence_score'] == 0.82
        assert result['reasoning'] == "Project demonstrates technological uncertainty"
        assert result['citations'] == ["Publication 542"]
    
    def test_parse_agent_response_validates_percentage_range(self):
        """Test that qualification percentage is validated."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Test percentage > 100
        response_text = """{
  "qualification_percentage": 150,
  "confidence_score": 0.9,
  "reasoning": "test"
}"""
        
        with pytest.raises(ValueError, match="qualification_percentage must be between 0-100"):
            client._parse_agent_response(response_text)
        
        # Test negative percentage
        response_text = """{
  "qualification_percentage": -10,
  "confidence_score": 0.9,
  "reasoning": "test"
}"""
        
        with pytest.raises(ValueError, match="qualification_percentage must be between 0-100"):
            client._parse_agent_response(response_text)
    
    def test_parse_agent_response_validates_confidence_range(self):
        """Test that confidence score is validated."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Test confidence > 1
        response_text = """{
  "qualification_percentage": 80,
  "confidence_score": 1.5,
  "reasoning": "test"
}"""
        
        with pytest.raises(ValueError, match="confidence_score must be between 0-1"):
            client._parse_agent_response(response_text)
        
        # Test negative confidence
        response_text = """{
  "qualification_percentage": 80,
  "confidence_score": -0.1,
  "reasoning": "test"
}"""
        
        with pytest.raises(ValueError, match="confidence_score must be between 0-1"):
            client._parse_agent_response(response_text)
    
    def test_parse_agent_response_handles_missing_citations(self):
        """Test parsing response without citations field."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "qualification_percentage": 80,
  "confidence_score": 0.85,
  "reasoning": "Project qualifies"
}"""
        
        result = client._parse_agent_response(response_text)
        
        assert result['citations'] == []
    
    def test_parse_agent_response_converts_single_citation_to_list(self):
        """Test that single citation string is converted to list."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "qualification_percentage": 80,
  "confidence_score": 0.85,
  "reasoning": "Project qualifies",
  "citations": "CFR Title 26 § 1.41-4"
}"""
        
        result = client._parse_agent_response(response_text)
        
        assert isinstance(result['citations'], list)
        assert len(result['citations']) == 1
    
    def test_parse_agent_response_natural_language_fallback(self):
        """Test parsing natural language response as fallback."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """Based on my analysis, this project has a qualification percentage of 85% 
with a confidence score of 0.88. The project clearly demonstrates technological uncertainty 
and follows a systematic process of experimentation as required by CFR Title 26 § 1.41-4 
and Form 6765 Instructions."""
        
        result = client._parse_agent_response(response_text)
        
        assert result['qualification_percentage'] == 85.0
        assert result['confidence_score'] == 0.88
        assert len(result['citations']) > 0
        assert result['reasoning'] == response_text
    
    def test_parse_agent_response_natural_language_with_percentage_confidence(self):
        """Test parsing natural language with confidence as percentage."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """The qualification is 75% with confidence: 85 (meaning 85% confidence)."""
        
        result = client._parse_agent_response(response_text)
        
        assert result['qualification_percentage'] == 75.0
        # Confidence should be converted from 85 to 0.85
        assert result['confidence_score'] == 0.85
    
    def test_parse_agent_response_missing_required_fields_raises_error(self):
        """Test that missing required fields raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Missing confidence_score
        response_text = """{
  "qualification_percentage": 80,
  "reasoning": "test"
}"""
        
        with pytest.raises(ValueError, match="Missing required fields"):
            client._parse_agent_response(response_text)
    
    def test_parse_agent_response_unparseable_raises_error(self):
        """Test that completely unparseable response raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = "This is just some random text without any qualification data."
        
        with pytest.raises(ValueError, match="Unable to parse agent response"):
            client._parse_agent_response(response_text)
    
    def test_parse_agent_response_extracts_irs_citations(self):
        """Test extraction of IRS citations from natural language."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """Qualification: 80%, confidence: 0.85. 
According to CFR Title 26 § 1.41-4 and IRS Publication 542, this project qualifies. 
See also Form 6765 Instructions for details."""
        
        result = client._parse_agent_response(response_text)
        
        # Should extract multiple IRS citations
        assert len(result['citations']) >= 2
        # Check that at least some expected citations are present
        citation_text = ' '.join(result['citations'])
        assert 'CFR' in citation_text or 'Form' in citation_text or 'Publication' in citation_text


class TestYouComClientContentsAPI:
    """Test You.com Contents API integration."""
    
    def test_fetch_content_with_valid_url(self):
        """Test successful content fetching with valid URL."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Mock response matching You.com Contents API structure
        mock_response = {
            "content": """# R&D Project Narrative Template

## Project Overview
[Project Name] was undertaken to address [specific technical challenge].

## Technical Uncertainty
The project involved resolving uncertainty regarding [describe uncertainty].

## Process of Experimentation
The team conducted the following experiments:
1. [Experiment 1]
2. [Experiment 2]
3. [Experiment 3]

## Qualified Purpose
The research was conducted to develop new or improved business components.""",
            "title": "R&D Project Narrative Template",
            "description": "Template for documenting R&D tax credit projects",
            "author": "Tax Professional Resources",
            "published_date": "2024-06-15"
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.fetch_content(
                url="https://example.com/rd-narrative-template",
                format="markdown"
            )
        
        assert 'content' in result
        assert result['content'].startswith("# R&D Project Narrative Template")
        assert result['url'] == "https://example.com/rd-narrative-template"
        assert result['format'] == "markdown"
        assert result['title'] == "R&D Project Narrative Template"
        assert result['description'] == "Template for documenting R&D tax credit projects"
        assert result['author'] == "Tax Professional Resources"
        assert result['published_date'] == "2024-06-15"
        assert result['word_count'] > 0
    
    def test_fetch_content_with_html_format(self):
        """Test fetching content in HTML format."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "content": "<h1>R&D Template</h1><p>Content here</p>",
            "title": "R&D Template"
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.fetch_content(
                url="https://example.com/template",
                format="html"
            )
        
        assert result['format'] == "html"
        assert result['content'].startswith("<h1>")
    
    def test_fetch_content_with_empty_url_raises_error(self):
        """Test that empty URL raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="URL cannot be empty"):
            client.fetch_content(url="")
    
    def test_fetch_content_with_invalid_url_raises_error(self):
        """Test that invalid URL raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="URL must start with http"):
            client.fetch_content(url="not-a-url")
        
        with pytest.raises(ValueError, match="URL must start with http"):
            client.fetch_content(url="ftp://example.com")
    
    def test_fetch_content_with_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Format must be 'markdown' or 'html'"):
            client.fetch_content(
                url="https://example.com",
                format="invalid"
            )
    
    def test_fetch_content_uses_correct_endpoint(self):
        """Test that fetch_content uses correct endpoint."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "content": "test content",
            "title": "Test"
        }
        
        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            client.fetch_content(url="https://example.com")
            
            # Verify correct endpoint was used
            call_args = mock_request.call_args
            assert call_args[1]['endpoint'] == "/v1/contents"
            assert call_args[1]['method'] == "POST"
    
    def test_fetch_content_sends_correct_payload(self):
        """Test that fetch_content sends correct payload."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "content": "test content"
        }
        
        with patch.object(client, '_make_request', return_value=mock_response) as mock_request:
            client.fetch_content(
                url="https://example.com/template",
                format="markdown"
            )
            
            # Verify payload
            call_args = mock_request.call_args
            payload = call_args[1]['json_data']
            assert payload['url'] == "https://example.com/template"
            assert payload['format'] == "markdown"
    
    def test_fetch_content_handles_api_error(self):
        """Test fetch_content error handling."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with patch.object(client, '_make_request', side_effect=APIConnectionError(
            message="API error",
            api_name="You.com",
            endpoint="/v1/contents"
        )):
            with pytest.raises(APIConnectionError):
                client.fetch_content(url="https://example.com")
    
    def test_fetch_content_with_minimal_response(self):
        """Test fetching content with minimal response fields."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Response with only content field
        mock_response = {
            "content": "Minimal content here"
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.fetch_content(url="https://example.com")
        
        assert result['content'] == "Minimal content here"
        assert result['url'] == "https://example.com"
        assert result['format'] == "markdown"
        assert result['word_count'] == 3
        # Optional fields should not be present
        assert 'title' not in result
        assert 'description' not in result
    
    def test_fetch_content_with_empty_content(self):
        """Test handling of empty content response."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "content": ""
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.fetch_content(url="https://example.com")
        
        assert result['content'] == ""
        assert result['word_count'] == 0
    
    def test_fetch_content_calculates_word_count(self):
        """Test that word count is calculated correctly."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        mock_response = {
            "content": "This is a test with exactly nine words here."
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            result = client.fetch_content(url="https://example.com")
        
        assert result['word_count'] == 9
    
    def test_parse_content_response_with_all_fields(self):
        """Test parsing content response with all optional fields."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response = {
            "content": "Test content here",
            "title": "Test Title",
            "description": "Test description",
            "author": "Test Author",
            "published_date": "2024-01-15"
        }
        
        result = client._parse_content_response(
            response=response,
            url="https://example.com",
            format="markdown"
        )
        
        assert result['content'] == "Test content here"
        assert result['url'] == "https://example.com"
        assert result['format'] == "markdown"
        assert result['title'] == "Test Title"
        assert result['description'] == "Test description"
        assert result['author'] == "Test Author"
        assert result['published_date'] == "2024-01-15"
        assert result['word_count'] == 3
    
    def test_parse_content_response_with_no_content(self):
        """Test parsing response with missing content field."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response = {
            "title": "Test Title"
        }
        
        result = client._parse_content_response(
            response=response,
            url="https://example.com",
            format="markdown"
        )
        
        assert result['content'] == ""
        assert result['word_count'] == 0



class TestYouComClientExpressAgentAPI:
    """Test You.com Express Agent API integration for compliance reviews."""
    
    def test_express_agent_with_valid_narrative(self):
        """Test successful compliance review with valid narrative."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = """
        Project Overview: This project aimed to develop a new caching algorithm.
        
        Technical Uncertainties: We faced uncertainty about optimal cache eviction strategies.
        
        Process of Experimentation: We systematically tested multiple approaches including LRU, LFU, and ARC.
        
        Technological Nature: The work relied on computer science principles and algorithm optimization.
        
        Qualified Purpose: To create an improved caching system for our API infrastructure.
        """
        
        # Mock agent_run response
        mock_agent_response = {
            "output": [{
                "text": """```json
{
  "compliance_status": "compliant",
  "completeness_score": 0.92,
  "missing_elements": [],
  "suggestions": ["Consider adding more specific performance metrics"],
  "strengths": ["Clear technical uncertainties", "Well-documented experimentation process"],
  "overall_assessment": "The narrative meets all IRS requirements for R&D documentation."
}
```""",
                "type": "chat_node.answer",
                "agent": "express"
            }]
        }
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response):
            result = client.express_agent(narrative_text=narrative)
        
        assert result['compliance_status'] == "compliant"
        assert result['completeness_score'] == 0.92
        assert result['missing_elements'] == []
        assert len(result['suggestions']) == 1
        assert len(result['strengths']) == 2
        assert 'overall_assessment' in result
        assert 'raw_response' in result
    
    def test_express_agent_with_needs_revision_status(self):
        """Test compliance review that needs revision."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Brief incomplete narrative."
        
        mock_agent_response = {
            "output": [{
                "text": """```json
{
  "compliance_status": "needs_revision",
  "completeness_score": 0.45,
  "missing_elements": ["Technical uncertainties not clearly identified", "Process of experimentation missing"],
  "suggestions": ["Add detailed technical uncertainties section", "Document systematic experimentation process"],
  "strengths": ["Project overview is clear"],
  "overall_assessment": "The narrative requires significant additions to meet IRS requirements."
}
```""",
                "type": "chat_node.answer",
                "agent": "express"
            }]
        }
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response):
            result = client.express_agent(narrative_text=narrative)
        
        assert result['compliance_status'] == "needs_revision"
        assert result['completeness_score'] == 0.45
        assert len(result['missing_elements']) == 2
        assert len(result['suggestions']) == 2
    
    def test_express_agent_with_non_compliant_status(self):
        """Test compliance review with non-compliant status."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Not a proper R&D narrative."
        
        mock_agent_response = {
            "output": [{
                "text": """```json
{
  "compliance_status": "non_compliant",
  "completeness_score": 0.15,
  "missing_elements": ["All required sections missing"],
  "suggestions": ["Start with a complete narrative template", "Review IRS requirements"],
  "strengths": [],
  "overall_assessment": "The narrative does not meet IRS requirements and needs complete rewrite."
}
```""",
                "type": "chat_node.answer",
                "agent": "express"
            }]
        }
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response):
            result = client.express_agent(narrative_text=narrative)
        
        assert result['compliance_status'] == "non_compliant"
        assert result['completeness_score'] == 0.15
        assert len(result['missing_elements']) > 0
    
    def test_express_agent_with_empty_narrative_raises_error(self):
        """Test that empty narrative raises ValueError."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        with pytest.raises(ValueError, match="Narrative text cannot be empty"):
            client.express_agent(narrative_text="")
    
    def test_express_agent_with_custom_prompt(self):
        """Test express agent with custom compliance prompt."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Test narrative"
        custom_prompt = "Review this narrative for custom criteria."
        
        mock_agent_response = {
            "output": [{
                "text": """```json
{
  "compliance_status": "compliant",
  "completeness_score": 0.85,
  "missing_elements": [],
  "suggestions": [],
  "strengths": ["Meets custom criteria"],
  "overall_assessment": "Compliant with custom requirements."
}
```""",
                "type": "chat_node.answer",
                "agent": "express"
            }]
        }
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response) as mock_agent:
            result = client.express_agent(
                narrative_text=narrative,
                compliance_prompt=custom_prompt
            )
            
            # Verify custom prompt was used
            call_args = mock_agent.call_args
            assert call_args[1]['prompt'] == custom_prompt
        
        assert result['compliance_status'] == "compliant"
    
    def test_express_agent_uses_default_prompt_when_none_provided(self):
        """Test that default compliance prompt is used when none provided."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Test narrative"
        
        mock_agent_response = {
            "output": [{
                "text": """```json
{
  "compliance_status": "compliant",
  "completeness_score": 0.80,
  "missing_elements": [],
  "suggestions": [],
  "strengths": [],
  "overall_assessment": "Compliant."
}
```""",
                "type": "chat_node.answer",
                "agent": "express"
            }]
        }
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response) as mock_agent:
            with patch('tools.prompt_templates.populate_compliance_review_prompt') as mock_populate:
                mock_populate.return_value = "Default prompt"
                
                result = client.express_agent(narrative_text=narrative)
                
                # Verify default prompt was populated
                mock_populate.assert_called_once_with(narrative)
    
    def test_express_agent_calls_agent_run_with_express_mode(self):
        """Test that express_agent calls agent_run with express mode."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Test narrative"
        
        mock_agent_response = {
            "output": [{
                "text": """```json
{
  "compliance_status": "compliant",
  "completeness_score": 0.80,
  "missing_elements": [],
  "suggestions": [],
  "strengths": [],
  "overall_assessment": "Compliant."
}
```""",
                "type": "chat_node.answer",
                "agent": "express"
            }]
        }
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response) as mock_agent:
            client.express_agent(narrative_text=narrative)
            
            # Verify agent_run was called with express mode
            call_args = mock_agent.call_args
            assert call_args[1]['agent_mode'] == "express"
            assert call_args[1]['stream'] is False
    
    def test_express_agent_handles_missing_output_field(self):
        """Test error handling when agent response missing output field."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Test narrative"
        
        # Mock response without output field
        mock_agent_response = {}
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response):
            with pytest.raises(ValueError, match="Invalid agent response: missing output field"):
                client.express_agent(narrative_text=narrative)
    
    def test_express_agent_handles_empty_output_list(self):
        """Test error handling when agent response has empty output list."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Test narrative"
        
        # Mock response with empty output
        mock_agent_response = {"output": []}
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response):
            with pytest.raises(ValueError, match="Invalid agent response: missing output field"):
                client.express_agent(narrative_text=narrative)
    
    def test_express_agent_handles_empty_response_text(self):
        """Test error handling when response text is empty."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Test narrative"
        
        # Mock response with empty text
        mock_agent_response = {
            "output": [{
                "text": "",
                "type": "chat_node.answer"
            }]
        }
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response):
            with pytest.raises(ValueError, match="Invalid agent response: empty response text"):
                client.express_agent(narrative_text=narrative)
    
    def test_express_agent_handles_api_connection_error(self):
        """Test error handling for API connection errors."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Test narrative"
        
        with patch.object(client, 'agent_run', side_effect=APIConnectionError(
            message="API error",
            api_name="You.com",
            endpoint="/v1/agents/runs"
        )):
            with pytest.raises(APIConnectionError):
                client.express_agent(narrative_text=narrative)
    
    def test_parse_compliance_review_response_with_valid_json(self):
        """Test parsing valid JSON compliance review response."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """```json
{
  "compliance_status": "compliant",
  "completeness_score": 0.88,
  "missing_elements": ["Minor detail missing"],
  "suggestions": ["Add more specifics"],
  "strengths": ["Clear structure", "Good technical detail"],
  "overall_assessment": "Overall compliant with minor improvements needed."
}
```"""
        
        result = client._parse_compliance_review_response(response_text)
        
        assert result['compliance_status'] == "compliant"
        assert result['completeness_score'] == 0.88
        assert result['missing_elements'] == ["Minor detail missing"]
        assert result['suggestions'] == ["Add more specifics"]
        assert result['strengths'] == ["Clear structure", "Good technical detail"]
        assert result['overall_assessment'] == "Overall compliant with minor improvements needed."
    
    def test_parse_compliance_review_response_with_plain_json(self):
        """Test parsing plain JSON without markdown code fence."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "compliance_status": "needs_revision",
  "completeness_score": 0.65,
  "missing_elements": [],
  "suggestions": [],
  "strengths": [],
  "overall_assessment": "Needs work."
}"""
        
        result = client._parse_compliance_review_response(response_text)
        
        assert result['compliance_status'] == "needs_revision"
        assert result['completeness_score'] == 0.65
    
    def test_parse_compliance_review_response_validates_status(self):
        """Test that invalid compliance status raises error."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "compliance_status": "invalid_status",
  "completeness_score": 0.80
}"""
        
        with pytest.raises(ValueError, match="compliance_status must be one of"):
            client._parse_compliance_review_response(response_text)
    
    def test_parse_compliance_review_response_validates_score_range(self):
        """Test that completeness score out of range raises error."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "compliance_status": "compliant",
  "completeness_score": 1.5
}"""
        
        with pytest.raises(ValueError, match="completeness_score must be between 0-1"):
            client._parse_compliance_review_response(response_text)
    
    def test_parse_compliance_review_response_handles_missing_fields(self):
        """Test that missing required fields raises error."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "compliance_status": "compliant"
}"""
        
        with pytest.raises(ValueError, match="Missing required fields"):
            client._parse_compliance_review_response(response_text)
    
    def test_parse_compliance_review_response_converts_non_list_fields(self):
        """Test that non-list fields are converted to lists."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "compliance_status": "compliant",
  "completeness_score": 0.85,
  "missing_elements": "Single element",
  "suggestions": "Single suggestion",
  "strengths": "Single strength"
}"""
        
        result = client._parse_compliance_review_response(response_text)
        
        assert isinstance(result['missing_elements'], list)
        assert result['missing_elements'] == ["Single element"]
        assert isinstance(result['suggestions'], list)
        assert isinstance(result['strengths'], list)
    
    def test_parse_compliance_review_response_adds_default_assessment(self):
        """Test that missing overall_assessment gets default value."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """{
  "compliance_status": "compliant",
  "completeness_score": 0.90,
  "missing_elements": [],
  "suggestions": [],
  "strengths": []
}"""
        
        result = client._parse_compliance_review_response(response_text)
        
        assert 'overall_assessment' in result
        assert result['overall_assessment'] == "Review completed successfully."
    
    def test_parse_compliance_review_response_natural_language_fallback(self):
        """Test parsing natural language response when JSON fails."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """
        The narrative is compliant with IRS requirements.
        
        Compliance Status: compliant
        Completeness Score: 0.87
        
        Missing Elements:
        - More specific technical details needed
        - Timeline information missing
        
        Suggestions:
        - Add project timeline
        - Include more technical specifications
        
        Strengths:
        - Clear technical uncertainties
        - Well-documented experimentation
        
        Overall, the narrative meets requirements with minor improvements needed.
        """
        
        result = client._parse_compliance_review_response(response_text)
        
        assert result['compliance_status'] == "compliant"
        assert result['completeness_score'] == 0.87
        # Natural language parser extracts all bullet points it finds
        # It captures items from Missing Elements, Suggestions, and Strengths sections
        assert len(result['missing_elements']) >= 2
        assert len(result['suggestions']) >= 2
        assert len(result['strengths']) >= 2
    
    def test_parse_compliance_review_response_extracts_status_from_text(self):
        """Test extracting compliance status from natural language."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = "The document needs_revision based on our analysis."
        
        result = client._parse_compliance_review_response(response_text)
        
        assert result['compliance_status'] == "needs_revision"
    
    def test_parse_compliance_review_response_converts_percentage_score(self):
        """Test that percentage scores are converted to 0-1 range."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        response_text = """
        Completeness score: 85
        Status: compliant
        """
        
        result = client._parse_compliance_review_response(response_text)
        
        # 85 should be converted to 0.85
        assert result['completeness_score'] == 0.85
    
    def test_express_agent_includes_raw_response(self):
        """Test that raw response is included in result."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        narrative = "Test narrative"
        raw_text = """```json
{
  "compliance_status": "compliant",
  "completeness_score": 0.90,
  "missing_elements": [],
  "suggestions": [],
  "strengths": [],
  "overall_assessment": "Excellent."
}
```"""
        
        mock_agent_response = {
            "output": [{
                "text": raw_text,
                "type": "chat_node.answer",
                "agent": "express"
            }]
        }
        
        with patch.object(client, 'agent_run', return_value=mock_agent_response):
            result = client.express_agent(narrative_text=narrative)
        
        assert 'raw_response' in result
        assert result['raw_response'] == raw_text


class TestYouComClientCaching:
    """Test caching functionality for You.com API client."""
    
    def test_cache_initialization_default(self):
        """Test that cache is initialized with default settings."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        assert client.enable_cache is True
        assert client.search_cache_ttl == 3600  # 1 hour
        assert client.content_cache_ttl == 86400  # 24 hours
        assert isinstance(client.search_cache, dict)
        assert isinstance(client.content_cache, dict)
        assert len(client.search_cache) == 0
        assert len(client.content_cache) == 0
    
    def test_cache_initialization_custom(self):
        """Test cache initialization with custom settings."""
        api_key = "ydc-sk-test123"
        client = YouComClient(
            api_key=api_key,
            enable_cache=True,
            search_cache_ttl=1800,  # 30 minutes
            content_cache_ttl=43200  # 12 hours
        )
        
        assert client.enable_cache is True
        assert client.search_cache_ttl == 1800
        assert client.content_cache_ttl == 43200
    
    def test_cache_initialization_disabled(self):
        """Test cache initialization with caching disabled."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, enable_cache=False)
        
        assert client.enable_cache is False
    
    def test_generate_cache_key(self):
        """Test cache key generation."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Generate cache key with parameters
        key1 = client._generate_cache_key("search", query="test", count=10)
        key2 = client._generate_cache_key("search", query="test", count=10)
        key3 = client._generate_cache_key("search", query="test", count=5)
        
        # Same parameters should generate same key
        assert key1 == key2
        
        # Different parameters should generate different key
        assert key1 != key3
    
    @patch.object(YouComClient, '_make_request')
    def test_search_caching(self, mock_make_request):
        """Test that search results are cached."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, enable_cache=True)
        
        # Mock API response
        mock_response = {
            "results": {
                "web": [
                    {
                        "title": "Test Result",
                        "url": "https://example.com",
                        "description": "Test description",
                        "snippets": ["snippet1"]
                    }
                ],
                "news": []
            }
        }
        mock_make_request.return_value = mock_response
        
        # First call - should hit API
        results1 = client.search(query="test query", count=5)
        assert mock_make_request.call_count == 1
        assert len(results1) == 1
        
        # Second call with same parameters - should use cache
        results2 = client.search(query="test query", count=5)
        assert mock_make_request.call_count == 1  # Still 1, not 2
        assert results1 == results2
        
        # Verify cache statistics
        cache_stats = client.get_cache_statistics()
        assert cache_stats['search_cache_size'] == 1
    
    @patch.object(YouComClient, '_make_request')
    def test_search_caching_different_params(self, mock_make_request):
        """Test that different search parameters create separate cache entries."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, enable_cache=True)
        
        # Mock API response
        mock_response = {
            "results": {
                "web": [{"title": "Test", "url": "https://example.com", "description": "Test", "snippets": []}],
                "news": []
            }
        }
        mock_make_request.return_value = mock_response
        
        # Different queries should create separate cache entries
        client.search(query="query1", count=5)
        client.search(query="query2", count=5)
        
        assert mock_make_request.call_count == 2
        
        cache_stats = client.get_cache_statistics()
        assert cache_stats['search_cache_size'] == 2
    
    @patch.object(YouComClient, '_make_request')
    def test_content_caching(self, mock_make_request):
        """Test that content fetches are cached."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, enable_cache=True)
        
        # Mock API response
        mock_response = {
            "content": "Test content here",
            "title": "Test Title"
        }
        mock_make_request.return_value = mock_response
        
        # First call - should hit API
        result1 = client.fetch_content(url="https://example.com", format="markdown")
        assert mock_make_request.call_count == 1
        assert result1['content'] == "Test content here"
        
        # Second call with same URL - should use cache
        result2 = client.fetch_content(url="https://example.com", format="markdown")
        assert mock_make_request.call_count == 1  # Still 1, not 2
        assert result1 == result2
        
        # Verify cache statistics
        cache_stats = client.get_cache_statistics()
        assert cache_stats['content_cache_size'] == 1
    
    @patch.object(YouComClient, '_make_request')
    def test_cache_disabled(self, mock_make_request):
        """Test that caching can be disabled."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, enable_cache=False)
        
        # Mock API response
        mock_response = {
            "results": {
                "web": [{"title": "Test", "url": "https://example.com", "description": "Test", "snippets": []}],
                "news": []
            }
        }
        mock_make_request.return_value = mock_response
        
        # Make same search twice
        client.search(query="test", count=5)
        client.search(query="test", count=5)
        
        # Both should hit API (no caching)
        assert mock_make_request.call_count == 2
        
        # Cache should be empty
        cache_stats = client.get_cache_statistics()
        assert cache_stats['search_cache_size'] == 0
    
    def test_clear_search_cache(self):
        """Test clearing search cache."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Manually add some cache entries
        client.search_cache['key1'] = {'result': [], 'timestamp': datetime.now(), 'ttl': 3600}
        client.search_cache['key2'] = {'result': [], 'timestamp': datetime.now(), 'ttl': 3600}
        
        assert len(client.search_cache) == 2
        
        # Clear cache
        cleared = client.clear_search_cache()
        
        assert cleared == 2
        assert len(client.search_cache) == 0
    
    def test_clear_content_cache(self):
        """Test clearing content cache."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Manually add some cache entries
        client.content_cache['key1'] = {'result': {}, 'timestamp': datetime.now(), 'ttl': 86400}
        client.content_cache['key2'] = {'result': {}, 'timestamp': datetime.now(), 'ttl': 86400}
        
        assert len(client.content_cache) == 2
        
        # Clear cache
        cleared = client.clear_content_cache()
        
        assert cleared == 2
        assert len(client.content_cache) == 0
    
    def test_clear_all_caches(self):
        """Test clearing all caches."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Manually add cache entries
        client.search_cache['key1'] = {'result': [], 'timestamp': datetime.now(), 'ttl': 3600}
        client.content_cache['key1'] = {'result': {}, 'timestamp': datetime.now(), 'ttl': 86400}
        
        # Clear all caches
        cleared = client.clear_all_caches()
        
        assert cleared['search'] == 1
        assert cleared['content'] == 1
        assert cleared['total'] == 2
        assert len(client.search_cache) == 0
        assert len(client.content_cache) == 0
    
    def test_get_cache_statistics(self):
        """Test getting cache statistics."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, search_cache_ttl=1800, content_cache_ttl=43200)
        
        # Add some cache entries
        client.search_cache['key1'] = {'result': [], 'timestamp': datetime.now(), 'ttl': 1800}
        client.content_cache['key1'] = {'result': {}, 'timestamp': datetime.now(), 'ttl': 43200}
        client.content_cache['key2'] = {'result': {}, 'timestamp': datetime.now(), 'ttl': 43200}
        
        stats = client.get_cache_statistics()
        
        assert stats['enabled'] is True
        assert stats['search_cache_size'] == 1
        assert stats['content_cache_size'] == 2
        assert stats['total_cache_size'] == 3
        assert stats['search_ttl'] == 1800
        assert stats['content_ttl'] == 43200
    
    def test_cache_expiration(self):
        """Test that expired cache entries are not returned."""
        from datetime import timedelta
        
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, search_cache_ttl=1)  # 1 second TTL
        
        # Add a cache entry with old timestamp
        old_timestamp = datetime.now() - timedelta(seconds=2)
        cache_key = "test_key"
        client.search_cache[cache_key] = {
            'result': ['old_result'],
            'timestamp': old_timestamp,
            'ttl': 1
        }
        
        # Try to get cached result - should return None (expired)
        result = client._get_cached_result(client.search_cache, cache_key)
        
        assert result is None
        assert cache_key not in client.search_cache  # Should be removed
    
    def test_cache_not_expired(self):
        """Test that non-expired cache entries are returned."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, search_cache_ttl=3600)
        
        # Add a fresh cache entry
        cache_key = "test_key"
        expected_result = ['fresh_result']
        client.search_cache[cache_key] = {
            'result': expected_result,
            'timestamp': datetime.now(),
            'ttl': 3600
        }
        
        # Get cached result - should return the result
        result = client._get_cached_result(client.search_cache, cache_key)
        
        assert result == expected_result
    
    def test_cleanup_expired_entries(self):
        """Test cleanup of expired cache entries."""
        from datetime import timedelta
        
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Add mix of fresh and expired entries
        now = datetime.now()
        old_timestamp = now - timedelta(hours=2)
        
        client.search_cache['fresh'] = {'result': [], 'timestamp': now, 'ttl': 3600}
        client.search_cache['expired'] = {'result': [], 'timestamp': old_timestamp, 'ttl': 3600}
        client.content_cache['fresh'] = {'result': {}, 'timestamp': now, 'ttl': 86400}
        client.content_cache['expired'] = {'result': {}, 'timestamp': old_timestamp, 'ttl': 3600}
        
        # Cleanup
        cleaned = client._cleanup_expired_entries()
        
        assert cleaned['search'] == 1
        assert cleaned['content'] == 1
        assert cleaned['total'] == 2
        assert 'fresh' in client.search_cache
        assert 'expired' not in client.search_cache
        assert 'fresh' in client.content_cache
        assert 'expired' not in client.content_cache
    
    def test_get_statistics_includes_cache(self):
        """Test that get_statistics includes cache information."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key)
        
        # Add some cache entries
        client.search_cache['key1'] = {'result': [], 'timestamp': datetime.now(), 'ttl': 3600}
        
        stats = client.get_statistics()
        
        assert 'cache' in stats
        assert stats['cache']['enabled'] is True
        assert stats['cache']['search_cache_size'] == 1
        assert stats['cache']['total_cache_size'] == 1
    
    @patch.object(YouComClient, '_make_request')
    def test_agent_api_not_cached(self, mock_make_request):
        """Test that Agent API calls are NOT cached (always fresh reasoning)."""
        api_key = "ydc-sk-test123"
        client = YouComClient(api_key=api_key, enable_cache=True)
        
        # Mock API response
        mock_response = {
            "output": [
                {
                    "type": "chat_node.answer",
                    "text": "Test response",
                    "content": "Test prompt",
                    "agent": "express"
                }
            ]
        }
        mock_make_request.return_value = mock_response
        
        # Make same agent call twice
        prompt = "Test prompt for qualification"
        client.agent_run(prompt=prompt, agent_mode="express")
        client.agent_run(prompt=prompt, agent_mode="express")
        
        # Both should hit API (no caching for agent calls)
        assert mock_make_request.call_count == 2
        
        # Cache should not have agent results
        cache_stats = client.get_cache_statistics()
        assert cache_stats['total_cache_size'] == 0
