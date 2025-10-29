"""
Unit tests for GLMReasoner class
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
import httpx

from tools.glm_reasoner import GLMReasoner
from utils.exceptions import APIConnectionError


@pytest.fixture
def reasoner():
    """Create GLMReasoner instance for testing"""
    with patch('tools.glm_reasoner.get_config') as mock_config:
        mock_config.return_value.openrouter_api_key = "test_api_key"
        return GLMReasoner()


@pytest.fixture
def mock_response():
    """Create mock HTTP response"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {
        "choices": [{
            "message": {
                "content": "This is a test response from GLM 4.5 Air"
            }
        }]
    }
    return mock


class TestGLMReasonerInit:
    """Test GLMReasoner initialization"""
    
    def test_init_with_api_key(self):
        """Test initialization with explicit API key"""
        reasoner = GLMReasoner(api_key="explicit_key")
        assert reasoner.api_key == "explicit_key"
        assert reasoner.model == "z-ai/glm-4.5-air:free"
        assert reasoner.base_url == "https://openrouter.ai/api/v1"
    
    def test_init_with_config(self):
        """Test initialization with config API key"""
        with patch('tools.glm_reasoner.get_config') as mock_config:
            mock_config.return_value.openrouter_api_key = "config_key"
            reasoner = GLMReasoner()
            assert reasoner.api_key == "config_key"
    
    def test_init_without_api_key(self):
        """Test initialization fails without API key"""
        with patch('tools.glm_reasoner.get_config') as mock_config:
            mock_config.return_value.openrouter_api_key = None
            with pytest.raises(ValueError, match="OpenRouter API key is required"):
                GLMReasoner()
    
    def test_init_custom_timeout(self):
        """Test initialization with custom timeout"""
        with patch('tools.glm_reasoner.get_config') as mock_config:
            mock_config.return_value.openrouter_api_key = "test_key"
            reasoner = GLMReasoner(timeout=60)
            assert reasoner.timeout == 60


class TestGLMReasonerReason:
    """Test GLMReasoner.reason() method"""
    
    @pytest.mark.asyncio
    async def test_reason_success(self, reasoner, mock_response):
        """Test successful reasoning call"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            response = await reasoner.reason("Test prompt")
            
            assert response == "This is a test response from GLM 4.5 Air"
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reason_with_system_prompt(self, reasoner, mock_response):
        """Test reasoning with system prompt"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            response = await reasoner.reason(
                "Test prompt",
                system_prompt="You are an expert"
            )
            
            # Verify system message was included
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert len(payload['messages']) == 2
            assert payload['messages'][0]['role'] == 'system'
            assert payload['messages'][1]['role'] == 'user'
    
    @pytest.mark.asyncio
    async def test_reason_custom_temperature(self, reasoner, mock_response):
        """Test reasoning with custom temperature"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await reasoner.reason("Test prompt", temperature=0.8)
            
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['temperature'] == 0.8
    
    @pytest.mark.asyncio
    async def test_reason_custom_max_tokens(self, reasoner, mock_response):
        """Test reasoning with custom max_tokens"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await reasoner.reason("Test prompt", max_tokens=1000)
            
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['max_tokens'] == 1000
    
    @pytest.mark.asyncio
    async def test_reason_401_error(self, reasoner):
        """Test handling of 401 Unauthorized error"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_post.side_effect = httpx.HTTPStatusError(
                "Unauthorized",
                request=Mock(),
                response=mock_response
            )
            
            with pytest.raises(APIConnectionError, match="Invalid OpenRouter API key"):
                await reasoner.reason("Test prompt")
    
    @pytest.mark.asyncio
    async def test_reason_429_error_retry(self, reasoner, mock_response):
        """Test retry logic for 429 Rate Limit error"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            # First two calls fail with 429, third succeeds
            error_response = Mock()
            error_response.status_code = 429
            mock_post.side_effect = [
                httpx.HTTPStatusError("Rate limit", request=Mock(), response=error_response),
                httpx.HTTPStatusError("Rate limit", request=Mock(), response=error_response),
                mock_response
            ]
            
            response = await reasoner.reason("Test prompt")
            
            assert response == "This is a test response from GLM 4.5 Air"
            assert mock_post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_reason_429_error_exhausted(self, reasoner):
        """Test 429 error after all retries exhausted"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            error_response = Mock()
            error_response.status_code = 429
            mock_post.side_effect = httpx.HTTPStatusError(
                "Rate limit",
                request=Mock(),
                response=error_response
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await reasoner.reason("Test prompt")
            
            # Should retry 3 times
            assert mock_post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_reason_500_error_retry(self, reasoner, mock_response):
        """Test retry logic for 500 Internal Server Error"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            # First call fails with 500, second succeeds
            error_response = Mock()
            error_response.status_code = 500
            mock_post.side_effect = [
                httpx.HTTPStatusError("Server error", request=Mock(), response=error_response),
                mock_response
            ]
            
            response = await reasoner.reason("Test prompt")
            
            assert response == "This is a test response from GLM 4.5 Air"
            assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reason_500_error_exhausted(self, reasoner):
        """Test 500 error after all retries exhausted"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            error_response = Mock()
            error_response.status_code = 500
            mock_post.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=Mock(),
                response=error_response
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await reasoner.reason("Test prompt")
            
            # Should retry 3 times
            assert mock_post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_reason_502_error_retry(self, reasoner, mock_response):
        """Test retry logic for 502 Bad Gateway"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            error_response = Mock()
            error_response.status_code = 502
            mock_post.side_effect = [
                httpx.HTTPStatusError("Bad Gateway", request=Mock(), response=error_response),
                mock_response
            ]
            
            response = await reasoner.reason("Test prompt")
            
            assert response == "This is a test response from GLM 4.5 Air"
            assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reason_503_error_retry(self, reasoner, mock_response):
        """Test retry logic for 503 Service Unavailable"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            error_response = Mock()
            error_response.status_code = 503
            mock_post.side_effect = [
                httpx.HTTPStatusError("Service Unavailable", request=Mock(), response=error_response),
                mock_response
            ]
            
            response = await reasoner.reason("Test prompt")
            
            assert response == "This is a test response from GLM 4.5 Air"
            assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reason_504_error_retry(self, reasoner, mock_response):
        """Test retry logic for 504 Gateway Timeout"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            error_response = Mock()
            error_response.status_code = 504
            mock_post.side_effect = [
                httpx.HTTPStatusError("Gateway Timeout", request=Mock(), response=error_response),
                mock_response
            ]
            
            response = await reasoner.reason("Test prompt")
            
            assert response == "This is a test response from GLM 4.5 Air"
            assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reason_timeout_retry(self, reasoner, mock_response):
        """Test retry logic for timeout error"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            # First call times out, second succeeds
            mock_post.side_effect = [
                httpx.TimeoutException("Timeout"),
                mock_response
            ]
            
            response = await reasoner.reason("Test prompt")
            
            assert response == "This is a test response from GLM 4.5 Air"
            assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reason_timeout_exhausted(self, reasoner):
        """Test timeout error after all retries exhausted"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(httpx.TimeoutException):
                await reasoner.reason("Test prompt")
            
            # Should retry 3 times
            assert mock_post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_reason_connect_error_retry(self, reasoner, mock_response):
        """Test retry logic for connection error"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            # First call fails to connect, second succeeds
            mock_post.side_effect = [
                httpx.ConnectError("Connection failed"),
                mock_response
            ]
            
            response = await reasoner.reason("Test prompt")
            
            assert response == "This is a test response from GLM 4.5 Air"
            assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reason_network_error(self, reasoner):
        """Test handling of network error (non-retryable)"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.NetworkError("Network error")
            
            with pytest.raises(APIConnectionError, match="Network error"):
                await reasoner.reason("Test prompt")
            
            # Should not retry network errors
            assert mock_post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_reason_invalid_json_response(self, reasoner):
        """Test handling of invalid JSON response"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_post.return_value = mock_response
            
            with pytest.raises(APIConnectionError, match="Failed to parse.*JSON"):
                await reasoner.reason("Test prompt")
    
    @pytest.mark.asyncio
    async def test_reason_missing_choices_field(self, reasoner):
        """Test handling of response missing 'choices' field"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"error": "No choices"}
            mock_post.return_value = mock_response
            
            with pytest.raises(APIConnectionError, match="missing 'choices' field"):
                await reasoner.reason("Test prompt")
    
    @pytest.mark.asyncio
    async def test_reason_empty_choices_array(self, reasoner):
        """Test handling of empty choices array"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": []}
            mock_post.return_value = mock_response
            
            with pytest.raises(APIConnectionError, match="missing 'choices' field"):
                await reasoner.reason("Test prompt")
    
    @pytest.mark.asyncio
    async def test_reason_missing_message_field(self, reasoner):
        """Test handling of response missing 'message' field"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": [{"index": 0}]}
            mock_post.return_value = mock_response
            
            with pytest.raises(APIConnectionError, match="missing 'message' field"):
                await reasoner.reason("Test prompt")
    
    @pytest.mark.asyncio
    async def test_reason_missing_content_field(self, reasoner):
        """Test handling of response missing 'content' field"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": [{"message": {"role": "assistant"}}]}
            mock_post.return_value = mock_response
            
            with pytest.raises(APIConnectionError, match="missing 'content' field"):
                await reasoner.reason("Test prompt")
    
    @pytest.mark.asyncio
    async def test_reason_custom_timeout(self, reasoner):
        """Test that custom timeout is respected"""
        custom_reasoner = GLMReasoner(api_key="test_key", timeout=60)
        assert custom_reasoner.timeout == 60
    
    @pytest.mark.asyncio
    async def test_reason_unexpected_error(self, reasoner):
        """Test handling of unexpected errors"""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Unexpected error")
            
            with pytest.raises(APIConnectionError, match="Unexpected error"):
                await reasoner.reason("Test prompt")


class TestParseQualificationResponse:
    """Test parse_qualification_response() method"""
    
    def test_parse_json_response(self, reasoner):
        """Test parsing JSON response"""
        json_response = """{
            "qualification_percentage": 85.5,
            "confidence_score": 0.9,
            "reasoning": "Project demonstrates R&D activities",
            "citations": ["CFR Title 26 § 1.41-4", "Form 6765"]
        }"""
        
        result = reasoner.parse_qualification_response(json_response)
        
        assert result['qualification_percentage'] == 85.5
        assert result['confidence_score'] == 0.9
        assert "R&D activities" in result['reasoning']
        assert len(result['citations']) == 2
    
    def test_parse_natural_language_response(self, reasoner):
        """Test parsing natural language response"""
        nl_response = """
        Based on my analysis, this project qualifies at 75% for R&D credit.
        My confidence is 0.85.
        
        The project demonstrates technological uncertainty per CFR Title 26 § 1.41-4.
        See also Form 6765 for qualified expenses.
        """
        
        result = reasoner.parse_qualification_response(nl_response)
        
        assert result['qualification_percentage'] == 75.0
        assert result['confidence_score'] == 0.85
        assert len(result['citations']) > 0
    
    def test_parse_percentage_formats(self, reasoner):
        """Test parsing various percentage formats"""
        test_cases = [
            ("Qualification: 80%", 80.0),
            ("Qualifies at 75.5%", 75.5),
            ("100% qualified", 100.0),
        ]
        
        for response, expected in test_cases:
            result = reasoner.parse_qualification_response(response)
            assert result['qualification_percentage'] == expected
    
    def test_parse_confidence_formats(self, reasoner):
        """Test parsing various confidence formats"""
        test_cases = [
            ("Confidence: 0.9", 0.9),
            ("confidence score: 0.85", 0.85),
            ("Confidence: 90", 0.9),  # Percentage converted to 0-1
        ]
        
        for response, expected in test_cases:
            result = reasoner.parse_qualification_response(response)
            assert result['confidence_score'] == expected
    
    def test_parse_citations(self, reasoner):
        """Test citation extraction"""
        response = """
        Per CFR Title 26 § 1.41-4 and Form 6765, this qualifies.
        See also Publication 542 and § 41.
        """
        
        result = reasoner.parse_qualification_response(response)
        
        assert len(result['citations']) > 0
        assert any('CFR' in c for c in result['citations'])
    
    def test_parse_invalid_response(self, reasoner):
        """Test parsing invalid response"""
        with pytest.raises(ValueError, match="Invalid qualification response"):
            reasoner.parse_qualification_response("{invalid json")
    
    def test_validate_qualification_percentage_bounds(self, reasoner):
        """Test qualification percentage is clamped to 0-100"""
        # Test over 100
        response = '{"qualification_percentage": 150, "confidence_score": 0.9, "reasoning": "test", "citations": []}'
        result = reasoner.parse_qualification_response(response)
        assert result['qualification_percentage'] == 100.0
        
        # Test under 0
        response = '{"qualification_percentage": -10, "confidence_score": 0.9, "reasoning": "test", "citations": []}'
        result = reasoner.parse_qualification_response(response)
        assert result['qualification_percentage'] == 0.0
    
    def test_validate_confidence_score_bounds(self, reasoner):
        """Test confidence score is clamped to 0-1"""
        # Test over 1
        response = '{"qualification_percentage": 80, "confidence_score": 1.5, "reasoning": "test", "citations": []}'
        result = reasoner.parse_qualification_response(response)
        assert result['confidence_score'] == 1.0
        
        # Test under 0
        response = '{"qualification_percentage": 80, "confidence_score": -0.5, "reasoning": "test", "citations": []}'
        result = reasoner.parse_qualification_response(response)
        assert result['confidence_score'] == 0.0


class TestParseStructuredResponse:
    """Test parse_structured_response() method"""
    
    def test_parse_json_object(self, reasoner):
        """Test parsing JSON object"""
        json_response = '{"key": "value", "number": 42}'
        result = reasoner.parse_structured_response(json_response)
        
        assert result['key'] == 'value'
        assert result['number'] == 42
    
    def test_parse_json_array(self, reasoner):
        """Test parsing JSON array"""
        json_response = '[1, 2, 3]'
        result = reasoner.parse_structured_response(json_response)
        
        assert result == [1, 2, 3]
    
    def test_parse_natural_language(self, reasoner):
        """Test parsing natural language as text"""
        nl_response = "This is a natural language response"
        result = reasoner.parse_structured_response(nl_response)
        
        assert result['content'] == nl_response
    
    def test_parse_invalid_json(self, reasoner):
        """Test parsing invalid JSON returns as text"""
        invalid_json = "{invalid: json}"
        result = reasoner.parse_structured_response(invalid_json)
        
        assert result['content'] == invalid_json
    
    def test_parse_empty_response(self, reasoner):
        """Test parsing empty response raises ValueError"""
        with pytest.raises(ValueError, match="Response cannot be empty"):
            reasoner.parse_structured_response("")
    
    def test_parse_none_response(self, reasoner):
        """Test parsing None response raises ValueError"""
        with pytest.raises(ValueError, match="Response cannot be empty"):
            reasoner.parse_structured_response(None)
    
    def test_parse_json_from_markdown_json_block(self, reasoner):
        """Test extracting JSON from markdown ```json block"""
        markdown_response = """Here is the data:
```json
{"status": "success", "count": 5}
```
That's all."""
        
        result = reasoner.parse_structured_response(markdown_response)
        
        assert result['status'] == 'success'
        assert result['count'] == 5
    
    def test_parse_json_from_markdown_plain_block(self, reasoner):
        """Test extracting JSON from markdown ``` block"""
        markdown_response = """Here is the data:
```
{"status": "success", "count": 5}
```
That's all."""
        
        result = reasoner.parse_structured_response(markdown_response)
        
        assert result['status'] == 'success'
        assert result['count'] == 5
    
    def test_parse_json_array_from_markdown(self, reasoner):
        """Test extracting JSON array from markdown block"""
        markdown_response = """Here are the items:
```
[1, 2, 3, 4, 5]
```"""
        
        result = reasoner.parse_structured_response(markdown_response)
        
        assert result == [1, 2, 3, 4, 5]
    
    def test_parse_nested_json(self, reasoner):
        """Test parsing nested JSON structures"""
        nested_json = '{"outer": {"inner": {"value": 42}}, "array": [1, 2, 3]}'
        result = reasoner.parse_structured_response(nested_json)
        
        assert result['outer']['inner']['value'] == 42
        assert result['array'] == [1, 2, 3]
    
    def test_parse_key_value_pairs_colon(self, reasoner):
        """Test extracting key-value pairs with colon separator"""
        text = """
        name: John Doe
        age: 30
        city: New York
        """
        
        result = reasoner.parse_structured_response(text)
        
        assert result['name'] == 'John Doe'
        assert result['age'] == 30
        assert result['city'] == 'New York'
        assert 'content' in result
    
    def test_parse_key_value_pairs_equals(self, reasoner):
        """Test extracting key-value pairs with equals separator"""
        text = """
        status = active
        count = 42
        enabled = true
        """
        
        result = reasoner.parse_structured_response(text)
        
        assert result['status'] == 'active'
        assert result['count'] == 42
        assert result['enabled'] is True
    
    def test_parse_key_value_pairs_boolean(self, reasoner):
        """Test extracting boolean values"""
        text = """
        is_active: yes
        is_valid: true
        is_disabled: no
        is_error: false
        """
        
        result = reasoner.parse_structured_response(text)
        
        assert result['is_active'] is True
        assert result['is_valid'] is True
        assert result['is_disabled'] is False
        assert result['is_error'] is False
    
    def test_parse_key_value_pairs_numeric(self, reasoner):
        """Test extracting numeric values"""
        text = """
        count: 42
        percentage: 85.5
        total: 1000
        """
        
        result = reasoner.parse_structured_response(text)
        
        assert result['count'] == 42
        assert result['percentage'] == 85.5
        assert result['total'] == 1000
    
    def test_parse_mixed_format(self, reasoner):
        """Test parsing response with mixed formats"""
        text = """
        Here's the analysis:
        
        status: complete
        confidence: 0.95
        
        The project qualifies for R&D credit.
        """
        
        result = reasoner.parse_structured_response(text)
        
        assert result['status'] == 'complete'
        assert result['confidence'] == 0.95
        assert 'content' in result
    
    def test_parse_whitespace_handling(self, reasoner):
        """Test handling of extra whitespace"""
        json_with_whitespace = '  \n  {"key": "value"}  \n  '
        result = reasoner.parse_structured_response(json_with_whitespace)
        
        assert result['key'] == 'value'
    
    def test_parse_complex_json_with_special_chars(self, reasoner):
        """Test parsing JSON with special characters"""
        complex_json = '{"message": "Hello, world!", "path": "/usr/local/bin", "regex": "\\\\d+"}'
        result = reasoner.parse_structured_response(complex_json)
        
        assert result['message'] == 'Hello, world!'
        assert result['path'] == '/usr/local/bin'
        assert result['regex'] == '\\d+'
    
    def test_extract_json_from_markdown_helper(self, reasoner):
        """Test _extract_json_from_markdown helper method"""
        text = """Some text before
```json
{"key": "value"}
```
Some text after"""
        
        extracted = reasoner._extract_json_from_markdown(text)
        assert extracted == '{"key": "value"}'
    
    def test_extract_json_from_markdown_no_match(self, reasoner):
        """Test _extract_json_from_markdown returns None when no match"""
        text = "Just plain text with no code blocks"
        
        extracted = reasoner._extract_json_from_markdown(text)
        assert extracted is None
    
    def test_extract_key_value_pairs_helper(self, reasoner):
        """Test _extract_key_value_pairs helper method"""
        text = """
        name: Alice
        score: 95
        passed: yes
        """
        
        result = reasoner._extract_key_value_pairs(text)
        
        assert result['name'] == 'Alice'
        assert result['score'] == 95
        assert result['passed'] is True
        assert 'content' in result


class TestIntegration:
    """Integration tests with actual API"""
    
    @pytest.mark.asyncio
    async def test_real_api_call(self):
        """Test real API call with OpenRouter"""
        reasoner = GLMReasoner()
        
        response = await reasoner.reason(
            "What is 2+2?",
            temperature=0.1
        )
        
        assert response is not None
        assert len(response) > 0
        assert "4" in response
    
    @pytest.mark.asyncio
    async def test_real_qualification_analysis(self):
        """Test real qualification analysis with RAG context"""
        reasoner = GLMReasoner()
        
        prompt = """Analyze this project for R&D qualification:
        
Project: Machine Learning Model Development
Description: Developed novel neural network architecture for fraud detection

Provide qualification percentage, confidence, reasoning, and citations in JSON format."""
        
        response = await reasoner.reason(prompt, temperature=0.2)
        qualification_data = reasoner.parse_qualification_response(response)
        
        assert 0 <= qualification_data['qualification_percentage'] <= 100
        assert 0 <= qualification_data['confidence_score'] <= 1
        assert len(qualification_data['reasoning']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
