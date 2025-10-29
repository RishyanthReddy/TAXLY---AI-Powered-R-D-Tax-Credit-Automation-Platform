"""
GLM 4.5 Air Reasoner for PydanticAI Agent Reasoning

This module provides the GLMReasoner class that interfaces with GLM 4.5 Air
via OpenRouter for RAG inference and agent decision-making in the R&D Tax Credit
Automation system.

GLM 4.5 Air is used as the core reasoning engine for:
- RAG-augmented inference with IRS document context
- Agent decision-making in PydanticAI workflows
- Structured response parsing for qualification logic
"""

import json
import logging
import re
from typing import Dict, Optional, Any
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from utils.config import get_config
from utils.exceptions import APIConnectionError

logger = logging.getLogger(__name__)


class GLMReasoner:
    """
    GLM 4.5 Air reasoner for PydanticAI agent reasoning.
    
    This class provides an interface to GLM 4.5 Air via OpenRouter for:
    - RAG-augmented inference
    - Agent decision-making
    - Structured response parsing
    
    Attributes:
        api_key (str): OpenRouter API key
        model (str): Model identifier (z-ai/glm-4.5-air:free)
        base_url (str): OpenRouter API base URL
        timeout (int): Request timeout in seconds
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize GLMReasoner with OpenRouter credentials.
        
        Args:
            api_key: OpenRouter API key (defaults to config)
            timeout: Request timeout in seconds (default: 30)
        """
        config = get_config()
        self.api_key = api_key or config.openrouter_api_key
        self.model = "z-ai/glm-4.5-air:free"
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        
        logger.info(f"Initialized GLMReasoner with model: {self.model}")
    
    def _should_retry(self, exception: Exception) -> bool:
        """
        Determine if an exception should trigger a retry.
        
        Retryable errors:
        - 429 Rate Limit Exceeded
        - 500 Internal Server Error
        - 502 Bad Gateway
        - 503 Service Unavailable
        - 504 Gateway Timeout
        - Timeout exceptions
        - Connection errors
        
        Non-retryable errors:
        - 401 Unauthorized (invalid API key)
        - 400 Bad Request (invalid parameters)
        - 403 Forbidden (insufficient permissions)
        - Other client errors (4xx)
        
        Args:
            exception: The exception to evaluate
        
        Returns:
            bool: True if the error should be retried
        """
        if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
            return True
        
        if isinstance(exception, httpx.HTTPStatusError):
            status_code = exception.response.status_code
            # Retry on server errors and rate limiting
            return status_code in (429, 500, 502, 503, 504)
        
        return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=lambda retry_state: retry_state.outcome.failed and 
              isinstance(retry_state.outcome.exception(), 
                        (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)) and
              (isinstance(retry_state.outcome.exception(), (httpx.TimeoutException, httpx.ConnectError)) or
               retry_state.outcome.exception().response.status_code in (429, 500, 502, 503, 504)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def reason(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000
    ) -> str:
        """
        Call GLM 4.5 Air for reasoning with comprehensive error handling.
        
        This method implements robust error handling for all common API failure scenarios:
        - 401 Unauthorized: Invalid API key (no retry)
        - 429 Rate Limit Exceeded: Retries with exponential backoff
        - 500 Internal Server Error: Retries with exponential backoff
        - Timeout: Retries with exponential backoff (default 30s timeout)
        - Connection errors: Retries with exponential backoff
        
        The retry logic uses exponential backoff with:
        - Maximum 3 attempts
        - Initial delay: 2 seconds
        - Maximum delay: 10 seconds
        - Multiplier: 1 (linear backoff)
        
        Args:
            prompt: User prompt for reasoning
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0-1.0, default: 0.2)
            max_tokens: Maximum tokens in response (default: 2000)
        
        Returns:
            str: LLM response text
        
        Raises:
            APIConnectionError: If API call fails after retries or for non-retryable errors
        
        Examples:
            >>> reasoner = GLMReasoner()
            >>> response = await reasoner.reason("What is R&D?")
            >>> print(response)
        """
        try:
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/rd-tax-agent",
                "X-Title": "R&D Tax Credit Automation"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            logger.debug(f"Calling GLM 4.5 Air with prompt length: {len(prompt)}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Validate response structure
                if "choices" not in result or not result["choices"]:
                    raise APIConnectionError("Invalid API response: missing 'choices' field")
                
                if "message" not in result["choices"][0]:
                    raise APIConnectionError("Invalid API response: missing 'message' field")
                
                if "content" not in result["choices"][0]["message"]:
                    raise APIConnectionError("Invalid API response: missing 'content' field")
                
                content = result["choices"][0]["message"]["content"]
                
                logger.info(f"GLM 4.5 Air response received (length: {len(content)})")
                return content
                
        except httpx.HTTPStatusError as e:
            # Handle specific HTTP status codes
            status_code = e.response.status_code
            
            if status_code == 401:
                error_msg = "Invalid OpenRouter API key (401 Unauthorized)"
                logger.error(f"{error_msg}. Please check your OPENROUTER_API_KEY environment variable.")
                raise APIConnectionError(error_msg) from e
            
            elif status_code == 429:
                error_msg = "Rate limit exceeded for GLM 4.5 Air (429 Too Many Requests)"
                logger.warning(f"{error_msg}. Request will be retried with exponential backoff.")
                # Re-raise to trigger retry logic
                raise
            
            elif status_code == 500:
                error_msg = "GLM 4.5 Air internal server error (500)"
                logger.warning(f"{error_msg}. Request will be retried with exponential backoff.")
                # Re-raise to trigger retry logic
                raise
            
            elif status_code == 502:
                error_msg = "Bad Gateway (502) - OpenRouter service temporarily unavailable"
                logger.warning(f"{error_msg}. Request will be retried with exponential backoff.")
                # Re-raise to trigger retry logic
                raise
            
            elif status_code == 503:
                error_msg = "Service Unavailable (503) - OpenRouter service temporarily down"
                logger.warning(f"{error_msg}. Request will be retried with exponential backoff.")
                # Re-raise to trigger retry logic
                raise
            
            elif status_code == 504:
                error_msg = "Gateway Timeout (504) - Request took too long"
                logger.warning(f"{error_msg}. Request will be retried with exponential backoff.")
                # Re-raise to trigger retry logic
                raise
            
            else:
                error_msg = f"GLM 4.5 Air API error: HTTP {status_code}"
                logger.error(f"{error_msg}: {e}")
                raise APIConnectionError(error_msg) from e
            
        except httpx.TimeoutException as e:
            error_msg = f"GLM 4.5 Air request timeout after {self.timeout}s"
            logger.warning(f"{error_msg}. Request will be retried with exponential backoff.")
            # Re-raise to trigger retry logic
            raise
            
        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to OpenRouter API: {str(e)}"
            logger.warning(f"{error_msg}. Request will be retried with exponential backoff.")
            # Re-raise to trigger retry logic
            raise
            
        except httpx.NetworkError as e:
            error_msg = f"Network error while calling GLM 4.5 Air: {str(e)}"
            logger.error(error_msg)
            raise APIConnectionError(error_msg) from e
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse GLM 4.5 Air response as JSON: {str(e)}"
            logger.error(error_msg)
            raise APIConnectionError(error_msg) from e
            
        except KeyError as e:
            error_msg = f"Unexpected response structure from GLM 4.5 Air: missing key {str(e)}"
            logger.error(error_msg)
            raise APIConnectionError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Unexpected error calling GLM 4.5 Air: {str(e)}"
            logger.error(error_msg)
            raise APIConnectionError(error_msg) from e
    
    def parse_qualification_response(self, response: str) -> Dict[str, Any]:
        """
        Parse qualification response from GLM 4.5 Air.
        
        Extracts structured data including:
        - qualification_percentage: Percentage of project qualifying for R&D credit
        - confidence_score: Confidence in the qualification (0-1)
        - reasoning: Explanation of the qualification decision
        - citations: IRS document references
        
        Args:
            response: Raw LLM response text
        
        Returns:
            Dict containing parsed qualification data
        
        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Try to parse as JSON first
            if response.strip().startswith("{"):
                data = json.loads(response)
                return self._validate_qualification_data(data)
            
            # Parse natural language response
            data = self._parse_natural_language_response(response)
            return self._validate_qualification_data(data)
            
        except Exception as e:
            logger.error(f"Failed to parse qualification response: {e}")
            raise ValueError(f"Invalid qualification response format: {str(e)}")
    
    def _parse_natural_language_response(self, response: str) -> Dict[str, Any]:
        """
        Parse natural language response into structured data.
        
        Args:
            response: Natural language response text
        
        Returns:
            Dict containing extracted data
        """
        data = {
            "qualification_percentage": 0.0,
            "confidence_score": 0.0,
            "reasoning": response,
            "citations": []
        }
        
        # Extract qualification percentage
        import re
        percentage_match = re.search(r'(\d+(?:\.\d+)?)\s*%', response)
        if percentage_match:
            data["qualification_percentage"] = float(percentage_match.group(1))
        
        # Extract confidence score
        confidence_match = re.search(r'confidence(?:\s+score)?(?:\s+is)?[:\s]+(\d+(?:\.\d+)?)', response, re.IGNORECASE)
        if confidence_match:
            confidence = float(confidence_match.group(1))
            # Normalize to 0-1 if given as percentage
            data["confidence_score"] = confidence / 100 if confidence > 1 else confidence
        
        # Extract citations (look for CFR, Form, Publication references)
        citation_patterns = [
            r'CFR\s+Title\s+\d+\s+§\s+[\d.]+',
            r'Form\s+\d+',
            r'Publication\s+\d+',
            r'§\s+[\d.]+'
        ]
        for pattern in citation_patterns:
            citations = re.findall(pattern, response, re.IGNORECASE)
            data["citations"].extend(citations)
        
        return data
    
    def _validate_qualification_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize qualification data.
        
        Args:
            data: Raw parsed data
        
        Returns:
            Dict with validated and normalized data
        """
        validated = {
            "qualification_percentage": float(data.get("qualification_percentage", 0)),
            "confidence_score": float(data.get("confidence_score", 0)),
            "reasoning": str(data.get("reasoning", "")),
            "citations": data.get("citations", [])
        }
        
        # Validate ranges
        if not 0 <= validated["qualification_percentage"] <= 100:
            logger.warning(
                f"Invalid qualification percentage: {validated['qualification_percentage']}, "
                "clamping to 0-100"
            )
            validated["qualification_percentage"] = max(0, min(100, validated["qualification_percentage"]))
        
        if not 0 <= validated["confidence_score"] <= 1:
            logger.warning(
                f"Invalid confidence score: {validated['confidence_score']}, "
                "clamping to 0-1"
            )
            validated["confidence_score"] = max(0, min(1, validated["confidence_score"]))
        
        return validated
    
    def parse_structured_response(self, response: str) -> Dict[str, Any]:
        """
        Parse any structured response from GLM 4.5 Air.
        
        Handles both JSON and natural language formats. Attempts multiple
        parsing strategies to extract structured data:
        1. Direct JSON parsing
        2. JSON extraction from markdown code blocks
        3. Key-value pair extraction from natural language
        4. Fallback to content wrapper
        
        Args:
            response: Raw LLM response text
        
        Returns:
            Dict containing parsed data. For natural language responses,
            returns {"content": response}. For structured responses,
            returns the parsed dictionary or list.
        
        Raises:
            ValueError: If response is empty or None
        
        Examples:
            >>> reasoner.parse_structured_response('{"key": "value"}')
            {'key': 'value'}
            
            >>> reasoner.parse_structured_response('This is text')
            {'content': 'This is text'}
            
            >>> reasoner.parse_structured_response('```json\\n{"key": "value"}\\n```')
            {'key': 'value'}
        """
        if not response:
            raise ValueError("Response cannot be empty or None")
        
        response = response.strip()
        
        try:
            # Strategy 1: Direct JSON parsing
            if response.startswith("{") or response.startswith("["):
                try:
                    parsed = json.loads(response)
                    logger.debug("Successfully parsed response as direct JSON")
                    return parsed
                except json.JSONDecodeError:
                    # Continue to next strategy
                    pass
            
            # Strategy 2: Extract JSON from markdown code blocks
            json_match = self._extract_json_from_markdown(response)
            if json_match:
                try:
                    parsed = json.loads(json_match)
                    logger.debug("Successfully extracted JSON from markdown code block")
                    return parsed
                except json.JSONDecodeError:
                    # Continue to next strategy
                    pass
            
            # Strategy 3: Extract key-value pairs from natural language
            structured_data = self._extract_key_value_pairs(response)
            if structured_data and len(structured_data) > 1:  # More than just content
                logger.debug("Successfully extracted key-value pairs from natural language")
                return structured_data
            
            # Strategy 4: Fallback to content wrapper
            logger.debug("Returning response as natural language content")
            return {"content": response}
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}, returning as text content")
            return {"content": response}
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return {"content": response}
    
    def _extract_json_from_markdown(self, text: str) -> Optional[str]:
        """
        Extract JSON from markdown code blocks.
        
        Looks for patterns like:
        ```json
        {"key": "value"}
        ```
        
        or
        
        ```
        {"key": "value"}
        ```
        
        Args:
            text: Text potentially containing markdown code blocks
        
        Returns:
            Extracted JSON string or None if not found
        """
        # Pattern for ```json ... ``` or ``` ... ```
        patterns = [
            r'```json\s*\n(.*?)\n```',
            r'```\s*\n(\{.*?\})\s*\n```',
            r'```\s*\n(\[.*?\])\s*\n```'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_key_value_pairs(self, text: str) -> Dict[str, Any]:
        """
        Extract key-value pairs from natural language text.
        
        Looks for common patterns like:
        - "key: value"
        - "key = value"
        - "key is value"
        
        Args:
            text: Natural language text
        
        Returns:
            Dict containing extracted key-value pairs
        """
        data = {"content": text}
        
        # Pattern for "key: value" or "key = value"
        # More restrictive: key must be at start of line or after whitespace
        # and value should not contain sentence-ending punctuation
        kv_pattern = r'^\s*(\w+(?:_\w+)?)\s*[:=]\s*([^\n]+?)(?:\n|$)'
        matches = re.findall(kv_pattern, text, re.MULTILINE)
        
        for key, value in matches:
            # Clean up key and value
            key = key.strip().lower().replace(' ', '_')
            value = value.strip()
            
            # Skip if value looks like a sentence (contains punctuation at end)
            if value.endswith(('.', '!', '?', ':')):
                continue
            
            # Try to convert value to appropriate type
            try:
                # Try integer
                if value.isdigit():
                    data[key] = int(value)
                # Try float
                elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                    data[key] = float(value)
                # Try boolean
                elif value.lower() in ('true', 'yes'):
                    data[key] = True
                elif value.lower() in ('false', 'no'):
                    data[key] = False
                # Keep as string
                else:
                    data[key] = value
            except (ValueError, AttributeError):
                data[key] = value
        
        return data
