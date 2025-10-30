"""
You.com API client for search, agent, and content capabilities.

This module provides a client for interacting with You.com APIs:
- Search API: Search for IRS guidance and compliance information
- Agent API: Expert R&D qualification reasoning
- Contents API: Fetch narrative templates and content
- Express Agent API: Quick compliance reviews

API Documentation: https://documentation.you.com/
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from tools.api_connectors import BaseAPIConnector
from tools.youcom_rate_limiter import YouComRateLimiter, RateLimitConfig
from utils.exceptions import APIConnectionError
from utils.logger import get_tool_logger


# Get logger for You.com client
logger = get_tool_logger("you_com_client")


class YouComClient(BaseAPIConnector):
    """
    Client for You.com APIs.
    
    Provides methods to interact with You.com's suite of APIs for:
    - Searching IRS guidance and compliance information
    - Running AI agents for R&D qualification reasoning
    - Fetching content and narrative templates
    - Quick compliance reviews with Express Agent
    
    All methods handle authentication, rate limiting, and error handling
    through the BaseAPIConnector class.
    
    API Documentation: https://documentation.you.com/
    """
    
    def __init__(
        self,
        api_key: str,
        enable_cache: bool = True,
        search_cache_ttl: int = 3600,  # 1 hour for search results
        content_cache_ttl: int = 86400,  # 24 hours for narrative templates
        custom_rate_limits: Optional[Dict[str, RateLimitConfig]] = None,
        enable_backoff_warnings: bool = True
    ):
        """
        Initialize You.com API client.
        
        Args:
            api_key: You.com API key (ydc-sk-... format)
            enable_cache: Enable caching for Search and Contents APIs (default: True)
            search_cache_ttl: Time-to-live for search results cache in seconds (default: 3600 = 1 hour)
            content_cache_ttl: Time-to-live for content/template cache in seconds (default: 86400 = 24 hours)
            custom_rate_limits: Optional custom rate limit configurations per endpoint
                               Format: {'endpoint_name': RateLimitConfig(...)}
            enable_backoff_warnings: Enable warnings when rate limits are approached (default: True)
        
        Raises:
            ValueError: If api_key is empty or invalid format
        
        Example:
            >>> from utils.config import get_config
            >>> config = get_config()
            >>> client = YouComClient(api_key=config.youcom_api_key)
            >>> 
            >>> # With custom cache settings
            >>> client = YouComClient(
            ...     api_key=config.youcom_api_key,
            ...     enable_cache=True,
            ...     search_cache_ttl=1800,  # 30 minutes
            ...     content_cache_ttl=43200  # 12 hours
            ... )
            >>> 
            >>> # With custom rate limits
            >>> from tools.youcom_rate_limiter import RateLimitConfig
            >>> custom_limits = {
            ...     'agent': RateLimitConfig(requests_per_minute=5, burst_size=5)
            ... }
            >>> client = YouComClient(
            ...     api_key=config.youcom_api_key,
            ...     custom_rate_limits=custom_limits
            ... )
        
        Note:
            Caching is applied to:
            - Search API: Caches search results to avoid repeated queries (1 hour TTL)
            - Contents API: Caches fetched templates and content (24 hour TTL)
            
            Agent API and Express Agent API are NOT cached as they require
            fresh reasoning for each request.
            
            Rate limiting is applied per endpoint:
            - Search API: 10 requests per minute (default)
            - Agent API: 10 requests per minute (default)
            - Contents API: 10 requests per minute (default)
            - Express Agent API: 10 requests per minute (default)
            - News API: 10 requests per minute (default)
        """
        if not api_key:
            raise ValueError("You.com API key cannot be empty")
        
        if not api_key.startswith("ydc-sk-"):
            logger.warning(
                "You.com API key does not start with 'ydc-sk-'. "
                "This may indicate an invalid key format."
            )
        
        # Initialize base connector with You.com-specific settings
        # 60 second timeout for agent runs which can take 10-30 seconds
        # Note: We pass rate_limit=None to disable base class rate limiting
        # since we're using the more sophisticated YouComRateLimiter
        super().__init__(
            api_name="You.com",
            rate_limit=None,  # Disable base class rate limiting
            timeout=60.0,  # 60 second timeout for agent runs
            max_retries=3  # Retry up to 3 times with exponential backoff
        )
        
        self.api_key = api_key
        
        # Initialize You.com-specific rate limiter with per-endpoint limits
        self.rate_limiter = YouComRateLimiter(
            custom_limits=custom_rate_limits,
            enable_backoff_warnings=enable_backoff_warnings
        )
        
        # Cache configuration
        self.enable_cache = enable_cache
        self.search_cache_ttl = search_cache_ttl
        self.content_cache_ttl = content_cache_ttl
        
        # Cache storage
        # Format: {cache_key: {'result': data, 'timestamp': datetime, 'ttl': int}}
        self.search_cache: Dict[str, Dict[str, Any]] = {}
        self.content_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            "Initialized You.com API client "
            f"(timeout=60s, max_retries=3, per-endpoint rate limiting enabled, "
            f"cache_enabled={enable_cache}, "
            f"search_ttl={search_cache_ttl}s, content_ttl={content_cache_ttl}s)"
        )
    
    def _generate_cache_key(self, prefix: str, **params) -> str:
        """
        Generate a unique cache key for a request with its parameters.
        
        Args:
            prefix: Cache key prefix (e.g., "search", "content")
            **params: Request parameters to include in the cache key
        
        Returns:
            MD5 hash of the parameters as cache key
        
        Example:
            >>> key = self._generate_cache_key("search", query="IRS R&D", count=10)
        """
        # Create a dictionary with all parameters
        cache_params = {"prefix": prefix}
        cache_params.update(params)
        
        # Generate hash
        params_str = json.dumps(cache_params, sort_keys=True)
        cache_key = hashlib.md5(params_str.encode()).hexdigest()
        
        return cache_key
    
    def _get_cached_result(
        self,
        cache_dict: Dict[str, Dict[str, Any]],
        cache_key: str
    ) -> Optional[Any]:
        """
        Retrieve a cached result if available and not expired.
        
        Args:
            cache_dict: The cache dictionary to check (search_cache or content_cache)
            cache_key: The cache key for the request
        
        Returns:
            Cached result if available and valid, None otherwise
        """
        if not self.enable_cache:
            return None
        
        if cache_key not in cache_dict:
            return None
        
        cached_entry = cache_dict[cache_key]
        cached_time = cached_entry['timestamp']
        cached_result = cached_entry['result']
        ttl = cached_entry['ttl']
        
        # Check if cache entry has expired
        age = (datetime.now() - cached_time).total_seconds()
        if age > ttl:
            # Remove expired entry
            del cache_dict[cache_key]
            logger.debug(f"Cache entry expired (age: {age:.1f}s, ttl: {ttl}s)")
            return None
        
        logger.info(f"Cache hit! Retrieved result from cache (age: {age:.1f}s, ttl: {ttl}s)")
        return cached_result
    
    def _store_cached_result(
        self,
        cache_dict: Dict[str, Dict[str, Any]],
        cache_key: str,
        result: Any,
        ttl: int
    ) -> None:
        """
        Store a result in the cache.
        
        Args:
            cache_dict: The cache dictionary to store in (search_cache or content_cache)
            cache_key: The cache key for the request
            result: The result to cache
            ttl: Time-to-live for this cache entry in seconds
        """
        if not self.enable_cache:
            return
        
        cache_dict[cache_key] = {
            'result': result,
            'timestamp': datetime.now(),
            'ttl': ttl
        }
        
        logger.debug(f"Stored result in cache (ttl: {ttl}s)")
    
    def clear_search_cache(self) -> int:
        """
        Clear all cached search results.
        
        Returns:
            Number of cache entries cleared
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> # ... make some search calls ...
            >>> cleared = client.clear_search_cache()
            >>> print(f"Cleared {cleared} search cache entries")
        """
        count = len(self.search_cache)
        self.search_cache.clear()
        logger.info(f"Cleared {count} search cache entries")
        return count
    
    def clear_content_cache(self) -> int:
        """
        Clear all cached content/templates.
        
        Returns:
            Number of cache entries cleared
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> # ... fetch some content ...
            >>> cleared = client.clear_content_cache()
            >>> print(f"Cleared {cleared} content cache entries")
        """
        count = len(self.content_cache)
        self.content_cache.clear()
        logger.info(f"Cleared {count} content cache entries")
        return count
    
    def clear_all_caches(self) -> Dict[str, int]:
        """
        Clear all caches (search and content).
        
        Returns:
            Dictionary with counts of cleared entries:
                - search: Number of search cache entries cleared
                - content: Number of content cache entries cleared
                - total: Total number of entries cleared
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> # ... make various API calls ...
            >>> cleared = client.clear_all_caches()
            >>> print(f"Cleared {cleared['total']} total cache entries")
        """
        search_count = self.clear_search_cache()
        content_count = self.clear_content_cache()
        
        result = {
            'search': search_count,
            'content': content_count,
            'total': search_count + content_count
        }
        
        logger.info(f"Cleared all caches: {result['total']} total entries")
        return result
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about cache usage.
        
        Returns:
            Dictionary with cache statistics:
                - enabled: Whether caching is enabled
                - search_cache_size: Number of search results cached
                - content_cache_size: Number of content items cached
                - total_cache_size: Total number of cached items
                - search_ttl: TTL for search cache in seconds
                - content_ttl: TTL for content cache in seconds
                - search_hit_rate: Percentage of search requests served from cache (if tracked)
                - content_hit_rate: Percentage of content requests served from cache (if tracked)
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> # ... make some API calls ...
            >>> stats = client.get_cache_statistics()
            >>> print(f"Search cache: {stats['search_cache_size']} entries")
            >>> print(f"Content cache: {stats['content_cache_size']} entries")
        """
        # Clean up expired entries before reporting statistics
        self._cleanup_expired_entries()
        
        stats = {
            'enabled': self.enable_cache,
            'search_cache_size': len(self.search_cache),
            'content_cache_size': len(self.content_cache),
            'total_cache_size': len(self.search_cache) + len(self.content_cache),
            'search_ttl': self.search_cache_ttl,
            'content_ttl': self.content_cache_ttl
        }
        
        return stats
    
    def _cleanup_expired_entries(self) -> Dict[str, int]:
        """
        Remove expired entries from all caches.
        
        Returns:
            Dictionary with counts of removed entries:
                - search: Number of expired search entries removed
                - content: Number of expired content entries removed
                - total: Total number of expired entries removed
        """
        now = datetime.now()
        
        # Clean search cache
        search_expired = []
        for key, entry in self.search_cache.items():
            age = (now - entry['timestamp']).total_seconds()
            if age > entry['ttl']:
                search_expired.append(key)
        
        for key in search_expired:
            del self.search_cache[key]
        
        # Clean content cache
        content_expired = []
        for key, entry in self.content_cache.items():
            age = (now - entry['timestamp']).total_seconds()
            if age > entry['ttl']:
                content_expired.append(key)
        
        for key in content_expired:
            del self.content_cache[key]
        
        if search_expired or content_expired:
            logger.debug(
                f"Cleaned up {len(search_expired)} expired search entries "
                f"and {len(content_expired)} expired content entries"
            )
        
        return {
            'search': len(search_expired),
            'content': len(content_expired),
            'total': len(search_expired) + len(content_expired)
        }
    
    def _get_base_url(self) -> str:
        """
        Get the base URL for You.com API.
        
        Returns:
            Base URL string
        """
        return "https://api.you.com"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for You.com API.
        
        You.com uses X-API-Key header for authentication.
        
        Returns:
            Dictionary with authentication headers
        """
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _handle_youcom_error(
        self,
        error: APIConnectionError,
        endpoint: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Handle You.com-specific API errors with detailed logging.
        
        This method provides enhanced error handling and logging for You.com API
        errors, including specific guidance for common error scenarios.
        
        Args:
            error: The APIConnectionError that was raised
            endpoint: The API endpoint that was called
            context: Optional context dictionary with additional error details
                    (e.g., query parameters, request payload info)
        
        Raises:
            APIConnectionError: Re-raises the error after logging
        
        Note:
            This method logs comprehensive error information including:
            - Error type and status code
            - Endpoint and request context
            - Suggested remediation steps
            - Full error details for debugging
        """
        status_code = error.status_code
        
        # Build context string for logging
        context_str = ""
        if context:
            context_items = [f"{k}={v}" for k, v in context.items()]
            context_str = f" ({', '.join(context_items)})"
        
        # Handle specific error codes with detailed logging
        if status_code == 401:
            logger.error(
                f"[You.com] 401 Unauthorized on {endpoint}{context_str}\n"
                f"Error: {error.message}\n"
                f"Cause: Invalid or expired API key\n"
                f"Remediation: Verify YOUCOM_API_KEY in environment variables\n"
                f"  - Check that the key starts with 'ydc-sk-'\n"
                f"  - Verify the key is active in You.com dashboard\n"
                f"  - Ensure the key has not expired\n"
                f"Details: {error.details}"
            )
        
        elif status_code == 429:
            logger.error(
                f"[You.com] 429 Rate Limit Exceeded on {endpoint}{context_str}\n"
                f"Error: {error.message}\n"
                f"Cause: Too many requests to You.com API\n"
                f"Rate Limit: 10 requests per minute\n"
                f"Remediation: Wait before retrying or reduce request frequency\n"
                f"  - Current rate limiter should handle this automatically\n"
                f"  - If error persists, consider increasing delay between requests\n"
                f"  - Check if multiple instances are using the same API key\n"
                f"Details: {error.details}"
            )
        
        elif status_code == 500:
            logger.error(
                f"[You.com] 500 Internal Server Error on {endpoint}{context_str}\n"
                f"Error: {error.message}\n"
                f"Cause: You.com API server error\n"
                f"Remediation: Retry the request (automatic retry in progress)\n"
                f"  - This is a temporary server-side issue\n"
                f"  - Request will be retried with exponential backoff\n"
                f"  - If error persists, check You.com status page\n"
                f"Details: {error.details}"
            )
        
        elif status_code == 503:
            logger.error(
                f"[You.com] 503 Service Unavailable on {endpoint}{context_str}\n"
                f"Error: {error.message}\n"
                f"Cause: You.com API temporarily unavailable\n"
                f"Remediation: Retry the request after a delay\n"
                f"  - Service may be under maintenance\n"
                f"  - Request will be retried with exponential backoff\n"
                f"  - Check You.com status page for maintenance windows\n"
                f"Details: {error.details}"
            )
        
        elif status_code == 400:
            logger.error(
                f"[You.com] 400 Bad Request on {endpoint}{context_str}\n"
                f"Error: {error.message}\n"
                f"Cause: Invalid request parameters or payload\n"
                f"Remediation: Check request parameters and payload format\n"
                f"  - Verify all required parameters are provided\n"
                f"  - Check parameter types and value ranges\n"
                f"  - Review API documentation for endpoint requirements\n"
                f"Details: {error.details}"
            )
        
        elif status_code == 403:
            logger.error(
                f"[You.com] 403 Forbidden on {endpoint}{context_str}\n"
                f"Error: {error.message}\n"
                f"Cause: API key lacks permission for this endpoint\n"
                f"Remediation: Verify API key permissions\n"
                f"  - Check that your API key has access to this endpoint\n"
                f"  - Some endpoints may require specific subscription tiers\n"
                f"  - Contact You.com support if access should be granted\n"
                f"Details: {error.details}"
            )
        
        elif status_code and status_code >= 500:
            logger.error(
                f"[You.com] {status_code} Server Error on {endpoint}{context_str}\n"
                f"Error: {error.message}\n"
                f"Cause: You.com API server error\n"
                f"Remediation: Retry the request (automatic retry in progress)\n"
                f"Details: {error.details}"
            )
        
        else:
            logger.error(
                f"[You.com] HTTP {status_code} Error on {endpoint}{context_str}\n"
                f"Error: {error.message}\n"
                f"Details: {error.details}"
            )
        
        # Re-raise the error after logging
        raise error
    
    def test_authentication(self) -> bool:
        """
        Test authentication by making a simple API call.
        
        This method attempts to call a lightweight endpoint to verify
        that the API key is valid and the connection is working.
        
        Returns:
            True if authentication succeeds, False otherwise
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> if client.test_authentication():
            ...     print("Authentication successful!")
            ... else:
            ...     print("Authentication failed!")
        
        Note:
            This method does not raise exceptions. It returns False for any
            error condition and logs the error details. Use this for validation
            checks where you want to handle authentication failures gracefully.
        """
        logger.info("Testing You.com authentication...")
        
        try:
            # Try a simple search query to test authentication
            # Using a minimal query to avoid consuming quota
            # Use the correct base URL for search endpoint
            response = self._make_request(
                method="GET",
                endpoint="/search",
                params={"query": "test", "num_web_results": 1},
                retry=False,  # Don't retry auth test
                base_url="https://api.ydc-index.io/v1"
            )
            
            logger.info("You.com authentication successful!")
            return True
            
        except APIConnectionError as e:
            if e.status_code == 401:
                logger.error(
                    "[You.com] Authentication failed: Invalid API key\n"
                    "Remediation: Check YOUCOM_API_KEY environment variable\n"
                    f"Details: {e.details}"
                )
            else:
                logger.error(
                    f"[You.com] Authentication test failed with status {e.status_code}\n"
                    f"Error: {e.message}\n"
                    f"Details: {e.details}"
                )
            return False
        
        except Exception as e:
            logger.error(
                f"[You.com] Unexpected error during authentication test\n"
                f"Error: {str(e)}\n"
                f"Type: {type(e).__name__}"
            )
            return False
    
    def get_rate_limiter_statistics(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics for all endpoints.
        
        Returns:
            Dictionary mapping endpoint names to their rate limiter statistics
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> # ... make some API calls ...
            >>> rate_stats = client.get_rate_limiter_statistics()
            >>> for endpoint, stats in rate_stats.items():
            ...     print(f"{endpoint}: {stats['total_requests']} requests")
        """
        return self.rate_limiter.get_statistics()
    
    def log_rate_limiter_statistics(self):
        """
        Log rate limiter statistics for all endpoints.
        
        This method logs a summary of rate limiter usage for all endpoints,
        including request counts, wait times, and backoff events.
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> # ... make some API calls ...
            >>> client.log_rate_limiter_statistics()
        """
        self.rate_limiter.log_statistics()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get client statistics including API usage, cache performance, and rate limiting.
        
        Returns:
            Dictionary with statistics:
                - api_name: Name of the API
                - request_count: Total number of requests made
                - error_count: Total number of errors encountered
                - error_rate: Percentage of requests that failed
                - total_wait_time: Total time spent waiting for rate limits
                - rate_limit: Rate limit description
                - cache: Cache statistics (enabled, sizes, TTLs)
                - rate_limiter: Per-endpoint rate limiter statistics
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> # ... make some API calls ...
            >>> stats = client.get_statistics()
            >>> print(f"Made {stats['request_count']} requests")
            >>> print(f"Error rate: {stats['error_rate']:.2%}")
            >>> print(f"Search cache: {stats['cache']['search_cache_size']} entries")
            >>> print(f"Search rate limiter: {stats['rate_limiter']['search']['total_requests']} requests")
        """
        stats = super().get_statistics()
        
        # Add You.com-specific statistics
        stats['rate_limit'] = "10 requests per minute per endpoint (configurable)"
        
        # Add cache statistics
        stats['cache'] = self.get_cache_statistics()
        
        # Add rate limiter statistics
        stats['rate_limiter'] = self.get_rate_limiter_statistics()
        
        return stats
    
    def search(
        self, 
        query: str, 
        count: int = 10,
        offset: int = 0,
        freshness: Optional[str] = None,
        country: str = "US",
        safesearch: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """
        Search for IRS guidance and compliance information using You.com Search API.
        
        This method searches for recent IRS rulings, precedents, and guidance that may
        not yet be indexed in the local RAG system. It's particularly useful for
        finding very recent tax year updates and compliance information.
        
        The API returns unified search results from both web and news sources.
        
        Args:
            query: Search query string (e.g., "IRS R&D tax credit software development new rulings 2025")
                  Can include search operators to refine results
            count: Maximum number of results to return per section (web/news) (default: 10, max: 100)
            offset: Offset for pagination in multiples of count (default: 0, max: 9)
            freshness: Time filter for results - "day", "week", "month", or "year" (optional)
            country: Country code for geographical focus (default: "US")
            safesearch: Content moderation level - "off", "moderate", or "strict" (default: "moderate")
        
        Returns:
            List of search result dictionaries, each containing:
                - title: Title of the search result
                - url: URL of the source document
                - description: Description/summary of the content
                - snippets: List of relevant text snippets
                - thumbnail_url: URL of thumbnail image (if available)
                - page_age: Publication date (if available)
                - authors: List of authors (if available)
                - favicon_url: URL of site favicon (if available)
                - source_type: "web" or "news" indicating result type
        
        Raises:
            APIConnectionError: If the API request fails
            ValueError: If query is empty or parameters are invalid
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> results = client.search(
            ...     query="IRS R&D tax credit software development 2025",
            ...     count=5,
            ...     freshness="year"
            ... )
            >>> for result in results:
            ...     print(f"Title: {result['title']}")
            ...     print(f"URL: {result['url']}")
            ...     print(f"Description: {result['description']}")
            ...     print(f"Snippets: {result['snippets']}")
        
        Note:
            This method is used by the Qualification Agent to perform final
            compliance checks before finalizing R&D qualification decisions.
            It helps identify recent IRS guidance that may affect qualification.
            
            API Documentation: https://documentation.you.com/api-reference/search
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")
        
        if count < 1 or count > 100:
            raise ValueError("Count must be between 1 and 100")
        
        if offset < 0 or offset > 9:
            raise ValueError("Offset must be between 0 and 9")
        
        if freshness and freshness not in ["day", "week", "month", "year"]:
            raise ValueError("Freshness must be one of: day, week, month, year")
        
        if safesearch not in ["off", "moderate", "strict"]:
            raise ValueError("Safesearch must be one of: off, moderate, strict")
        
        logger.info(
            f"Searching You.com for: '{query}' "
            f"(count={count}, offset={offset}, freshness={freshness})"
        )
        
        # Generate cache key for this search request
        cache_key = self._generate_cache_key(
            "search",
            query=query.strip(),
            count=count,
            offset=offset,
            country=country,
            safesearch=safesearch,
            freshness=freshness
        )
        
        # Check cache first
        cached_result = self._get_cached_result(self.search_cache, cache_key)
        if cached_result is not None:
            logger.info(f"Returning {len(cached_result)} cached search results")
            return cached_result
        
        # Apply rate limiting for search endpoint
        wait_time = self.rate_limiter.acquire('search')
        if wait_time > 0:
            logger.debug(f"Rate limited: waited {wait_time:.2f}s before search request")
        
        try:
            # Prepare query parameters
            params = {
                "query": query.strip(),
                "count": count,  # Number of results per section (web/news)
                "offset": offset,
                "country": country,
                "safesearch": safesearch
            }
            
            # Add optional freshness parameter
            if freshness:
                params["freshness"] = freshness
            
            # Make API request to the correct base URL
            # You.com uses api.ydc-index.io for search endpoint
            # Use /v1/search for the Search API
            response = self._make_request(
                method="GET",
                endpoint="/v1/search",
                params=params,
                base_url="https://api.ydc-index.io"
            )
            
            # Parse and structure results
            results = self._parse_search_results(response)
            
            logger.info(f"Retrieved {len(results)} search results from API")
            
            # Store in cache
            self._store_cached_result(
                self.search_cache,
                cache_key,
                results,
                self.search_cache_ttl
            )
            
            return results
            
        except APIConnectionError as e:
            # Use enhanced error handling with context
            self._handle_youcom_error(
                error=e,
                endpoint="/v1/search",
                context={
                    "query": query[:100],  # First 100 chars of query
                    "count": count,
                    "freshness": freshness
                }
            )
        
        except Exception as e:
            logger.error(
                f"[You.com] Unexpected error during search\n"
                f"Endpoint: /v1/search\n"
                f"Query: {query[:100]}\n"
                f"Error: {str(e)}\n"
                f"Type: {type(e).__name__}"
            )
            raise APIConnectionError(
                message=f"Unexpected error during search: {str(e)}",
                api_name=self.api_name,
                endpoint="/v1/search",
                details={"error": str(e), "type": type(e).__name__}
            )
    
    def news(
        self,
        query: str,
        count: int = 10,
        offset: int = 0,
        freshness: Optional[str] = None,
        country: str = "US"
    ) -> List[Dict[str, Any]]:
        """
        Search for recent news articles using You.com Live News API.
        
        This method searches specifically for news articles about IRS updates,
        tax credit changes, and compliance announcements. It's useful for finding
        breaking news and recent developments that may affect R&D tax credit qualification.
        
        Args:
            query: Search query string (e.g., "IRS R&D tax credit new ruling")
            count: Maximum number of news results to return (default: 10, max: 100)
            offset: Offset for pagination in multiples of count (default: 0, max: 9)
            freshness: Time filter - "day", "week", "month", or "year" (optional)
            country: Country code for geographical focus (default: "US")
        
        Returns:
            List of news result dictionaries, each containing:
                - title: Title of the news article
                - url: URL of the article
                - description: Article summary
                - page_age: Publication date
                - thumbnail_url: Article image (if available)
                - source_type: Always "news"
        
        Raises:
            APIConnectionError: If the API request fails
            ValueError: If query is empty or parameters are invalid
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> news = client.news(
            ...     query="IRS R&D tax credit updates",
            ...     count=5,
            ...     freshness="month"
            ... )
            >>> for article in news:
            ...     print(f"Title: {article['title']}")
            ...     print(f"Published: {article.get('page_age', 'Unknown')}")
            ...     print(f"URL: {article['url']}")
        
        Note:
            The Live News API is available on the basic tier and provides
            access to recent news articles from various sources.
            
            API Documentation: https://documentation.you.com/api-reference/news
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("News query cannot be empty")
        
        if count < 1 or count > 100:
            raise ValueError("Count must be between 1 and 100")
        
        if offset < 0 or offset > 9:
            raise ValueError("Offset must be between 0 and 9")
        
        if freshness and freshness not in ["day", "week", "month", "year"]:
            raise ValueError("Freshness must be one of: day, week, month, year")
        
        logger.info(
            f"Searching You.com News for: '{query}' "
            f"(count={count}, offset={offset}, freshness={freshness})"
        )
        
        # Generate cache key for this news request
        cache_key = self._generate_cache_key(
            "news",
            query=query.strip(),
            count=count,
            offset=offset,
            country=country,
            freshness=freshness
        )
        
        # Check cache first
        cached_result = self._get_cached_result(self.search_cache, cache_key)
        if cached_result is not None:
            logger.info(f"Returning {len(cached_result)} cached news results")
            return cached_result
        
        # Apply rate limiting for news endpoint
        wait_time = self.rate_limiter.acquire('news')
        if wait_time > 0:
            logger.debug(f"Rate limited: waited {wait_time:.2f}s before news request")
        
        try:
            # Prepare query parameters for news endpoint
            params = {
                "q": query.strip(),  # News API uses 'q' instead of 'query'
                "count": count,
                "offset": offset,
                "country": country
            }
            
            # Add optional freshness parameter
            if freshness:
                params["freshness"] = freshness
            
            # Make API request to news endpoint
            # You.com uses api.ydc-index.io for news endpoint
            # Use /livenews for the Live News API
            response = self._make_request(
                method="GET",
                endpoint="/livenews",
                params=params,
                base_url="https://api.ydc-index.io"
            )
            
            # Parse news results
            results = self._parse_news_results(response)
            
            logger.info(f"Retrieved {len(results)} news results from API")
            
            # Store in cache
            self._store_cached_result(
                self.search_cache,
                cache_key,
                results,
                self.search_cache_ttl
            )
            
            return results
            
        except APIConnectionError as e:
            # Use enhanced error handling with context
            self._handle_youcom_error(
                error=e,
                endpoint="/news",
                context={
                    "query": query[:100],
                    "count": count,
                    "freshness": freshness
                }
            )
        
        except Exception as e:
            logger.error(
                f"[You.com] Unexpected error during news search\n"
                f"Endpoint: /news\n"
                f"Query: {query[:100]}\n"
                f"Error: {str(e)}\n"
                f"Type: {type(e).__name__}"
            )
            raise APIConnectionError(
                message=f"Unexpected error during news search: {str(e)}",
                api_name=self.api_name,
                endpoint="/news",
                details={"error": str(e), "type": type(e).__name__}
            )
    
    def _parse_news_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse You.com News API response into structured results.
        
        Args:
            response: Raw API response dictionary
        
        Returns:
            List of structured news result dictionaries
        """
        results = []
        
        # Extract news results from the response
        news_items = response.get('news', {}).get('results', [])
        
        for item in news_items:
            result = {
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'description': item.get('description', ''),
                'source_type': 'news'
            }
            
            # Add optional fields
            if 'age' in item:
                result['page_age'] = item['age']
            
            if 'thumbnail' in item and item['thumbnail']:
                result['thumbnail_url'] = item['thumbnail'].get('original', '')
            
            results.append(result)
        
        return results
    
    def _parse_search_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse You.com Search API response into structured results.
        
        The API returns results in a nested structure:
        {
            "results": {
                "web": [...],
                "news": [...]
            },
            "metadata": {...}
        }
        
        Args:
            response: Raw API response dictionary
        
        Returns:
            List of structured search result dictionaries combining web and news results
        """
        results = []
        
        # Extract results from the response
        results_data = response.get('results', {})
        
        # Process web results
        web_results = results_data.get('web', [])
        for item in web_results:
            result = {
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'description': item.get('description', ''),
                'snippets': item.get('snippets', []),
                'source_type': 'web'
            }
            
            # Add optional fields
            if 'thumbnail_url' in item:
                result['thumbnail_url'] = item['thumbnail_url']
            
            if 'page_age' in item:
                result['page_age'] = item['page_age']
            
            if 'authors' in item:
                result['authors'] = item['authors']
            
            if 'favicon_url' in item:
                result['favicon_url'] = item['favicon_url']
            
            results.append(result)
        
        # Process news results
        news_results = results_data.get('news', [])
        for item in news_results:
            result = {
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'description': item.get('description', ''),
                'snippets': [],  # News results may not have snippets field
                'source_type': 'news'
            }
            
            # Add optional fields
            if 'thumbnail_url' in item:
                result['thumbnail_url'] = item['thumbnail_url']
            
            if 'page_age' in item:
                result['page_age'] = item['page_age']
            
            results.append(result)
        
        return results
    
    def agent_run(
        self,
        prompt: str,
        agent_mode: str = "express",
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Run You.com Agent API for expert R&D qualification reasoning.
        
        The Agent API provides advanced AI reasoning capabilities for complex tasks
        like R&D tax credit qualification. It combines web search, knowledge retrieval,
        and LLM reasoning to provide expert-level analysis.
        
        This method is used by the Qualification Agent to determine R&D qualification
        percentages and confidence scores based on IRS guidance and project data.
        
        Args:
            prompt: Detailed prompt with RAG context and project data for qualification analysis.
                   Should include:
                   - IRS document context from RAG system
                   - Project name and description
                   - Technical activities and challenges
                   - Total hours and costs
                   - Instructions for qualification analysis
            agent_mode: Agent mode configuration (default: "express")
                       Options: "express", "custom", "advanced"
                       - express: Fast responses with web search (max 1 search)
                       - custom: Custom agent with specific instructions
                       - advanced: More comprehensive analysis
            stream: Whether to stream the response using SSE (default: False)
                   When True, returns streaming response
            tools: Optional list of tools the agent can use (e.g., web search tool)
                  Example: [{"type": "web_search"}]
        
        Returns:
            Dictionary containing agent response:
                - output: List of output items with type, text, content, and agent info
                  Each output item contains:
                  - type: Type of output (e.g., "web_search.results, chat_node.answer")
                  - text: The agent's response text
                  - content: Original input content
                  - agent: Agent mode used
        
        Raises:
            APIConnectionError: If the API request fails
            ValueError: If prompt is empty or parameters are invalid
        
        Example:
            >>> from tools.rd_knowledge_tool import RD_Knowledge_Tool
            >>> from tools.prompt_templates import populate_rag_inference_prompt
            >>> 
            >>> # Get RAG context
            >>> rag_tool = RD_Knowledge_Tool()
            >>> rag_context = rag_tool.query("R&D tax credit software development")
            >>> 
            >>> # Create prompt with RAG context and project data
            >>> prompt = populate_rag_inference_prompt(
            ...     rag_context=rag_context.format_for_llm_prompt(),
            ...     project_name="API Optimization",
            ...     project_description="Improve API response times through algorithm optimization",
            ...     technical_activities="Algorithm research, caching strategies, performance testing",
            ...     total_hours=120.5,
            ...     total_cost=15000.00
            ... )
            >>> 
            >>> # Run agent for qualification
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> response = client.agent_run(prompt=prompt, agent_mode="express")
            >>> 
            >>> # Extract answer from response
            >>> answer_text = response['output'][0]['text']
            >>> parsed = client._parse_agent_response(answer_text)
            >>> print(f"Qualification: {parsed['qualification_percentage']}%")
            >>> print(f"Confidence: {parsed['confidence_score']}")
        
        Note:
            The Agent API may take 10-30 seconds to complete as it performs
            comprehensive research and reasoning. The timeout is set to 60 seconds
            to accommodate this.
            
            The response format depends on how the prompt is structured. For
            R&D qualification, the prompt should request JSON output with specific
            fields (qualification_percentage, confidence_score, reasoning, citations).
            
            API Documentation: https://documentation.you.com/api-reference/express
        """
        # Validate inputs
        if not prompt or not prompt.strip():
            raise ValueError("Agent prompt cannot be empty")
        
        if agent_mode not in ["express", "custom", "advanced"]:
            raise ValueError("Agent mode must be one of: express, custom, advanced")
        
        logger.info(
            f"Running You.com Agent API "
            f"(mode={agent_mode}, stream={stream}, prompt_length={len(prompt)})"
        )
        
        # Apply rate limiting for agent endpoint
        # Use 'express_agent' for express mode, 'agent' for others
        endpoint = 'express_agent' if agent_mode == 'express' else 'agent'
        wait_time = self.rate_limiter.acquire(endpoint)
        if wait_time > 0:
            logger.debug(f"Rate limited: waited {wait_time:.2f}s before agent request")
        
        try:
            # Prepare request payload according to You.com API spec
            payload = {
                "agent": agent_mode,
                "input": prompt.strip(),
                "stream": stream
            }
            
            # Add optional tools if specified
            if tools is not None:
                payload["tools"] = tools
            
            # Agent API uses Bearer token authentication instead of X-API-Key
            # Override the default headers for this specific endpoint
            agent_headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request
            # You.com Agent API uses the main api.you.com base URL
            response = self._make_request(
                method="POST",
                endpoint="/v1/agents/runs",
                json_data=payload,
                headers=agent_headers
            )
            
            logger.info("Agent API call successful")
            
            return response
            
        except APIConnectionError as e:
            # Use enhanced error handling with context
            self._handle_youcom_error(
                error=e,
                endpoint="/v1/agents/runs",
                context={
                    "agent_mode": agent_mode,
                    "prompt_length": len(prompt),
                    "stream": stream,
                    "has_tools": tools is not None
                }
            )
        
        except Exception as e:
            logger.error(
                f"[You.com] Unexpected error during agent run\n"
                f"Endpoint: /v1/agents/runs\n"
                f"Agent Mode: {agent_mode}\n"
                f"Prompt Length: {len(prompt)}\n"
                f"Error: {str(e)}\n"
                f"Type: {type(e).__name__}"
            )
            raise APIConnectionError(
                message=f"Unexpected error during agent run: {str(e)}",
                api_name=self.api_name,
                endpoint="/v1/agents/runs",
                details={"error": str(e), "type": type(e).__name__}
            )
    
    def _parse_agent_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse You.com Agent API response to extract structured qualification data.
        
        The agent response may be in JSON format or natural language. This method
        attempts to extract structured data including qualification percentage,
        confidence score, reasoning, and citations.
        
        Args:
            response_text: The agent's response text (from response['output'][0]['text'])
        
        Returns:
            Dictionary with extracted data:
                - qualification_percentage: Percentage of project qualifying (0-100)
                - confidence_score: Confidence in qualification (0-1)
                - reasoning: Detailed explanation of the qualification decision
                - citations: List of IRS document references
                - four_part_test_results: Results of the four-part test (optional)
                - technical_details: Technical uncertainties and experimentation (optional)
        
        Raises:
            ValueError: If response cannot be parsed or required fields are missing
        
        Example:
            >>> response = client.agent_run(prompt=qualification_prompt)
            >>> answer_text = response['output'][0]['text']
            >>> parsed = client._parse_agent_response(answer_text)
            >>> print(f"Qualification: {parsed['qualification_percentage']}%")
        
        Note:
            This method handles both JSON and natural language responses. If the
            response is JSON, it extracts fields directly. If it's natural language,
            it attempts to extract key information using pattern matching.
        """
        import json
        import re
        
        logger.info("Parsing agent response for qualification data")
        
        # Try to parse as JSON first
        try:
            # Look for JSON block in markdown code fence
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                logger.info("Successfully parsed JSON from markdown code fence")
            else:
                # Try to parse entire response as JSON
                data = json.loads(response_text)
                logger.info("Successfully parsed response as JSON")
            
            # Validate required fields
            required_fields = ['qualification_percentage', 'confidence_score', 'reasoning']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                raise ValueError(f"Missing required fields in response: {missing_fields}")
            
            # Validate field types and ranges
            qual_pct = data['qualification_percentage']
            if not isinstance(qual_pct, (int, float)) or qual_pct < 0 or qual_pct > 100:
                raise ValueError(
                    f"qualification_percentage must be between 0-100, got {qual_pct}"
                )
            
            conf_score = data['confidence_score']
            if not isinstance(conf_score, (int, float)) or conf_score < 0 or conf_score > 1:
                raise ValueError(
                    f"confidence_score must be between 0-1, got {conf_score}"
                )
            
            # Ensure citations is a list
            if 'citations' in data and not isinstance(data['citations'], list):
                data['citations'] = [data['citations']]
            elif 'citations' not in data:
                data['citations'] = []
            
            logger.info(
                f"Parsed qualification: {qual_pct}% "
                f"(confidence: {conf_score:.2f})"
            )
            
            return data
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse as JSON: {e}. Attempting natural language parsing.")
        
        except ValueError as e:
            # If it's a validation error (not a JSON decode error), re-raise it
            # These are errors like "confidence_score must be between 0-1"
            if "must be between" in str(e) or "Missing required fields" in str(e):
                raise
            # Otherwise, try natural language parsing
            logger.warning(f"JSON validation failed: {e}. Attempting natural language parsing.")
        
        # Fallback: Try to extract information from natural language
        result = {
            'qualification_percentage': 0.0,
            'confidence_score': 0.0,
            'reasoning': response_text,
            'citations': []
        }
        
        # Try to extract qualification percentage
        qual_patterns = [
            r'qualification\s+(?:percentage\s+)?(?:of\s+)?(\d+(?:\.\d+)?)\s*%',
            r'qualification[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'qualifies[:\s]+(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s+qualif',
            r'qualification\s+is\s+(\d+(?:\.\d+)?)\s*%',
        ]
        for pattern in qual_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                result['qualification_percentage'] = float(match.group(1))
                break
        
        # Try to extract confidence score
        conf_patterns = [
            r'confidence\s+score\s+(?:of\s+)?(\d+(?:\.\d+)?)',
            r'confidence[:\s]+(\d+(?:\.\d+)?)',
            r'with\s+confidence[:\s]+(\d+(?:\.\d+)?)',
        ]
        for pattern in conf_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                conf_value = float(match.group(1))
                # If value is > 1, assume it's a percentage and convert
                if conf_value > 1:
                    conf_value = conf_value / 100.0
                result['confidence_score'] = conf_value
                break
        
        # Try to extract citations
        citation_patterns = [
            r'(?:CFR|Form|Publication|§)\s+[\w\s\d\-\.]+',
            r'IRS\s+[\w\s\d\-\.]+',
        ]
        citations = set()
        for pattern in citation_patterns:
            matches = re.findall(pattern, response_text)
            citations.update(matches)
        result['citations'] = list(citations)
        
        if result['qualification_percentage'] == 0.0 and result['confidence_score'] == 0.0:
            logger.error("Could not extract qualification data from natural language response")
            raise ValueError(
                "Unable to parse agent response. Response must be in JSON format "
                "or contain extractable qualification percentage and confidence score."
            )
        
        logger.info(
            f"Extracted from natural language: {result['qualification_percentage']}% "
            f"(confidence: {result['confidence_score']:.2f})"
        )
        
        return result
    
    def fetch_content(
        self,
        url: str,
        format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Fetch R&D project narrative templates from known URLs using You.com Contents API.
        
        The Contents API extracts and converts web content into structured formats
        (Markdown or HTML). This is particularly useful for fetching R&D project
        narrative templates from authoritative sources that can be used to generate
        audit-ready documentation.
        
        Args:
            url: URL of the content to fetch (e.g., IRS guidance pages, template repositories)
                Must be a valid HTTP/HTTPS URL
            format: Output format - "markdown" or "html" (default: "markdown")
                   - markdown: Clean, structured Markdown format (recommended)
                   - html: Preserved HTML structure
        
        Returns:
            Dictionary containing:
                - content: Extracted content in requested format (Markdown or HTML)
                - url: Original URL that was fetched
                - title: Page title (if available)
                - description: Page description/meta description (if available)
                - author: Content author (if available)
                - published_date: Publication date (if available)
                - word_count: Number of words in the content
                - format: Format of the returned content ("markdown" or "html")
        
        Raises:
            APIConnectionError: If the API request fails
            ValueError: If URL is invalid or format is not supported
        
        Example:
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> 
            >>> # Fetch R&D narrative template
            >>> result = client.fetch_content(
            ...     url="https://example.com/rd-narrative-template",
            ...     format="markdown"
            ... )
            >>> 
            >>> # Extract template content
            >>> template_text = result['content']
            >>> print(f"Title: {result['title']}")
            >>> print(f"Word count: {result['word_count']}")
            >>> print(f"Content:\\n{template_text}")
            >>> 
            >>> # Use template for narrative generation
            >>> # ... populate template with project-specific data ...
        
        Note:
            This method is used by the Audit Trail Agent to fetch narrative
            templates that can be populated with project-specific data to
            generate comprehensive R&D project descriptions.
            
            The Contents API is optimized for extracting clean, readable content
            from web pages, removing navigation, ads, and other non-content elements.
            
            Common template sources:
            - IRS guidance documents
            - Tax professional resources
            - R&D documentation best practices
            
            API Documentation: https://documentation.you.com/api-reference/contents
        """
        # Validate inputs
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")
        
        # Basic URL validation
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        
        if format not in ["markdown", "html"]:
            raise ValueError("Format must be 'markdown' or 'html'")
        
        logger.info(
            f"Fetching content from URL: {url} "
            f"(format={format})"
        )
        
        # Generate cache key for this content request
        cache_key = self._generate_cache_key(
            "content",
            url=url,
            format=format
        )
        
        # Check cache first
        cached_result = self._get_cached_result(self.content_cache, cache_key)
        if cached_result is not None:
            logger.info(
                f"Returning cached content from {url} "
                f"(word_count={cached_result.get('word_count', 0)})"
            )
            return cached_result
        
        # Apply rate limiting for contents endpoint
        wait_time = self.rate_limiter.acquire('contents')
        if wait_time > 0:
            logger.debug(f"Rate limited: waited {wait_time:.2f}s before contents request")
        
        try:
            # Prepare request payload according to You.com Contents API spec
            # Note: Contents API expects "urls" as an array, not a single "url"
            payload = {
                "urls": [url],  # Must be an array
                "format": format
            }
            
            # Make API request
            # Contents API uses api.ydc-index.io base URL (not api.you.com)
            response = self._make_request(
                method="POST",
                endpoint="/v1/contents",
                json_data=payload,
                base_url="https://api.ydc-index.io"
            )
            
            # Parse and structure the response
            result = self._parse_content_response(response, url, format)
            
            logger.info(
                f"Successfully fetched content from {url} "
                f"(word_count={result.get('word_count', 0)})"
            )
            
            # Store in cache
            self._store_cached_result(
                self.content_cache,
                cache_key,
                result,
                self.content_cache_ttl
            )
            
            return result
            
        except APIConnectionError as e:
            # Use enhanced error handling with context
            self._handle_youcom_error(
                error=e,
                endpoint="/v1/contents",
                context={
                    "url": url[:100],  # First 100 chars of URL
                    "format": format
                }
            )
        
        except Exception as e:
            logger.error(
                f"[You.com] Unexpected error fetching content\n"
                f"Endpoint: /v1/contents\n"
                f"URL: {url}\n"
                f"Format: {format}\n"
                f"Error: {str(e)}\n"
                f"Type: {type(e).__name__}"
            )
            raise APIConnectionError(
                message=f"Unexpected error fetching content: {str(e)}",
                api_name=self.api_name,
                endpoint="/v1/contents",
                details={"error": str(e), "type": type(e).__name__, "url": url}
            )
    
    def _parse_content_response(
        self,
        response: Dict[str, Any],
        url: str,
        format: str
    ) -> Dict[str, Any]:
        """
        Parse You.com Contents API response into structured format.
        
        Args:
            response: Raw API response (array of content objects)
            url: Original URL that was fetched
            format: Format that was requested ("markdown" or "html")
        
        Returns:
            Dictionary with structured content data
        """
        # The Contents API returns an array of results
        # Since we only request one URL, we take the first result
        if isinstance(response, list) and len(response) > 0:
            content_obj = response[0]
        elif isinstance(response, dict):
            # Fallback for single object response
            content_obj = response
        else:
            logger.warning(f"Unexpected response format from Contents API: {type(response)}")
            content_obj = {}
        
        # Extract content based on format
        if format == "markdown":
            content = content_obj.get('markdown', '')
        elif format == "html":
            content = content_obj.get('html', '')
        else:
            # Fallback: try both
            content = content_obj.get('markdown', content_obj.get('html', ''))
        
        if not content:
            logger.warning(f"No content extracted from {url}")
        
        # Build structured result
        result = {
            'content': content,
            'url': content_obj.get('url', url),
            'format': format
        }
        
        # Add optional metadata fields if present
        if 'title' in content_obj:
            result['title'] = content_obj['title']
        
        if 'description' in content_obj:
            result['description'] = content_obj['description']
        
        if 'author' in content_obj:
            result['author'] = content_obj['author']
        
        if 'published_date' in content_obj:
            result['published_date'] = content_obj['published_date']
        
        # Calculate word count
        if content:
            # Simple word count (split on whitespace)
            word_count = len(content.split())
            result['word_count'] = word_count
        else:
            result['word_count'] = 0
        
        return result
    
    def express_agent(
        self,
        narrative_text: str,
        compliance_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run You.com Express Agent API for quick compliance reviews.
        
        The Express Agent API provides fast AI-powered reviews for specific tasks
        like compliance checking. This method is used by the Audit Trail Agent to
        perform final narrative compliance reviews before report generation.
        
        Express Agent is optimized for speed and uses a streamlined reasoning process
        compared to the full Agent API, making it ideal for quick validation checks.
        
        Args:
            narrative_text: The technical narrative text to review for compliance
                           Should be a complete R&D project narrative with all required sections
            compliance_prompt: Optional custom compliance review prompt
                              If not provided, uses the default COMPLIANCE_REVIEW_PROMPT
                              from prompt_templates module
        
        Returns:
            Dictionary containing review results:
                - compliance_status: "compliant", "needs_revision", or "non_compliant"
                - completeness_score: Score between 0-1 indicating completeness
                - missing_elements: List of missing required elements
                - suggestions: List of specific suggestions for improvement
                - strengths: List of strong points in the narrative
                - overall_assessment: Summary of the review
                - raw_response: Full response text from the agent
        
        Raises:
            APIConnectionError: If the API request fails
            ValueError: If narrative_text is empty or response cannot be parsed
        
        Example:
            >>> from tools.prompt_templates import populate_compliance_review_prompt
            >>> 
            >>> client = YouComClient(api_key="ydc-sk-...")
            >>> 
            >>> # Generate narrative for a project
            >>> narrative = '''
            ... Project Overview: This project aimed to develop a new caching algorithm...
            ... Technical Uncertainties: We faced uncertainty about optimal cache eviction...
            ... Process of Experimentation: We systematically tested multiple approaches...
            ... '''
            >>> 
            >>> # Review narrative for compliance
            >>> review = client.express_agent(
            ...     narrative_text=narrative
            ... )
            >>> 
            >>> # Check results
            >>> print(f"Status: {review['compliance_status']}")
            >>> print(f"Completeness: {review['completeness_score']:.1%}")
            >>> 
            >>> if review['missing_elements']:
            ...     print("Missing elements:")
            ...     for element in review['missing_elements']:
            ...         print(f"  - {element}")
            >>> 
            >>> if review['suggestions']:
            ...     print("Suggestions:")
            ...     for suggestion in review['suggestions']:
            ...         print(f"  - {suggestion}")
        
        Note:
            This method uses the Express Agent mode which is faster than the full
            Agent API but still provides comprehensive compliance analysis.
            
            The default compliance prompt checks for:
            - Technical uncertainties clearly identified
            - Process of experimentation documented
            - Technological nature demonstrated
            - Qualified purpose described
            - Documentation quality and specificity
            
            If the response cannot be parsed as JSON, the method will attempt to
            extract key information from natural language and return a structured
            result with available data.
            
            API Documentation: https://documentation.you.com/api-reference/express
        """
        # Validate inputs
        if not narrative_text or not narrative_text.strip():
            raise ValueError("Narrative text cannot be empty")
        
        logger.info(
            f"Running Express Agent for compliance review "
            f"(narrative_length={len(narrative_text)})"
        )
        
        try:
            # Use default compliance prompt if not provided
            if compliance_prompt is None:
                from tools.prompt_templates import populate_compliance_review_prompt
                compliance_prompt = populate_compliance_review_prompt(narrative_text)
            
            # Run agent with express mode for quick review
            # Express Agent is optimized for fast responses
            agent_response = self.agent_run(
                prompt=compliance_prompt,
                agent_mode="express",
                stream=False
            )
            
            # Extract response text from agent output
            # The response structure is: {'output': [{'text': '...', ...}]}
            if 'output' not in agent_response or not agent_response['output']:
                raise ValueError("Invalid agent response: missing output field")
            
            response_text = agent_response['output'][0].get('text', '')
            
            if not response_text:
                raise ValueError("Invalid agent response: empty response text")
            
            # Parse the compliance review response
            review_result = self._parse_compliance_review_response(response_text)
            
            # Add raw response for debugging/audit trail
            review_result['raw_response'] = response_text
            
            logger.info(
                f"Compliance review completed: {review_result['compliance_status']} "
                f"(completeness: {review_result['completeness_score']:.2f})"
            )
            
            return review_result
            
        except APIConnectionError as e:
            # Use enhanced error handling with context
            self._handle_youcom_error(
                error=e,
                endpoint="/v1/agents/runs (express)",
                context={
                    "agent_mode": "express",
                    "narrative_length": len(narrative_text),
                    "has_custom_prompt": compliance_prompt is not None
                }
            )
        
        except ValueError as e:
            logger.error(
                f"[You.com] Failed to parse compliance review response\n"
                f"Endpoint: /v1/agents/runs (express)\n"
                f"Error: {str(e)}\n"
                f"Narrative Length: {len(narrative_text)}"
            )
            raise
        
        except Exception as e:
            logger.error(
                f"[You.com] Unexpected error during compliance review\n"
                f"Endpoint: /v1/agents/runs (express)\n"
                f"Narrative Length: {len(narrative_text)}\n"
                f"Error: {str(e)}\n"
                f"Type: {type(e).__name__}"
            )
            raise APIConnectionError(
                message=f"Unexpected error during compliance review: {str(e)}",
                api_name=self.api_name,
                endpoint="/v1/agents/runs (express)",
                details={"error": str(e), "type": type(e).__name__}
            )
    
    def _parse_compliance_review_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Express Agent compliance review response.
        
        The agent response should be in JSON format with compliance review data.
        If JSON parsing fails, attempts to extract key information from natural language.
        
        Args:
            response_text: The agent's response text
        
        Returns:
            Dictionary with compliance review data:
                - compliance_status: "compliant", "needs_revision", or "non_compliant"
                - completeness_score: Score between 0-1
                - missing_elements: List of missing elements
                - suggestions: List of suggestions
                - strengths: List of strengths
                - overall_assessment: Summary text
        
        Raises:
            ValueError: If response cannot be parsed and key data cannot be extracted
        
        Example:
            >>> response = client.express_agent(narrative_text=narrative)
            >>> # Response is already parsed, but this shows the internal parsing
        """
        import json
        import re
        
        logger.info("Parsing compliance review response")
        
        # Try to parse as JSON first
        try:
            # Look for JSON block in markdown code fence
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                logger.info("Successfully parsed JSON from markdown code fence")
            else:
                # Try to parse entire response as JSON
                data = json.loads(response_text)
                logger.info("Successfully parsed response as JSON")
            
            # Validate required fields
            required_fields = ['compliance_status', 'completeness_score']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                raise ValueError(f"Missing required fields in response: {missing_fields}")
            
            # Validate compliance_status
            valid_statuses = ['compliant', 'needs_revision', 'non_compliant']
            if data['compliance_status'] not in valid_statuses:
                raise ValueError(
                    f"compliance_status must be one of {valid_statuses}, "
                    f"got {data['compliance_status']}"
                )
            
            # Validate completeness_score
            score = data['completeness_score']
            if not isinstance(score, (int, float)) or score < 0 or score > 1:
                raise ValueError(
                    f"completeness_score must be between 0-1, got {score}"
                )
            
            # Ensure list fields are lists
            for field in ['missing_elements', 'suggestions', 'strengths']:
                if field in data and not isinstance(data[field], list):
                    data[field] = [data[field]] if data[field] else []
                elif field not in data:
                    data[field] = []
            
            # Ensure overall_assessment exists
            if 'overall_assessment' not in data:
                data['overall_assessment'] = "Review completed successfully."
            
            logger.info(
                f"Parsed compliance review: {data['compliance_status']} "
                f"(score: {score:.2f})"
            )
            
            return data
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse as JSON: {e}. Attempting natural language parsing.")
        
        except ValueError as e:
            # If it's a validation error, re-raise it
            if "must be" in str(e) or "Missing required fields" in str(e):
                raise
            # Otherwise, try natural language parsing
            logger.warning(f"JSON validation failed: {e}. Attempting natural language parsing.")
        
        # Fallback: Try to extract information from natural language
        result = {
            'compliance_status': 'needs_revision',  # Default to needs_revision
            'completeness_score': 0.5,  # Default to medium score
            'missing_elements': [],
            'suggestions': [],
            'strengths': [],
            'overall_assessment': response_text[:500]  # Use first 500 chars as summary
        }
        
        # Try to extract compliance status
        status_patterns = [
            (r'compliance[_\s]+status[:\s]+["\']?(compliant|needs_revision|non_compliant)["\']?', 1),
            (r'status[:\s]+["\']?(compliant|needs_revision|non_compliant)["\']?', 1),
            (r'\b(compliant|needs_revision|non_compliant)\b', 1),
        ]
        for pattern, group in status_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                status = match.group(group).lower().replace(' ', '_')
                if status in ['compliant', 'needs_revision', 'non_compliant']:
                    result['compliance_status'] = status
                    break
        
        # Try to extract completeness score
        score_patterns = [
            r'completeness[_\s]+score[:\s]+(\d+(?:\.\d+)?)',
            r'score[:\s]+(\d+(?:\.\d+)?)',
            r'completeness[:\s]+(\d+(?:\.\d+)?)',
        ]
        for pattern in score_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                score_value = float(match.group(1))
                # If value is > 1, assume it's a percentage and convert
                if score_value > 1:
                    score_value = score_value / 100.0
                result['completeness_score'] = min(max(score_value, 0.0), 1.0)
                break
        
        # Try to extract missing elements (look for bullet points or lists)
        missing_section = re.search(
            r'missing[_\s]+elements?[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)',
            response_text,
            re.IGNORECASE | re.DOTALL
        )
        if missing_section:
            missing_text = missing_section.group(1)
            # Extract bullet points or numbered items
            items = re.findall(r'[-*•]\s*(.+?)(?:\n|$)', missing_text)
            if not items:
                items = re.findall(r'\d+\.\s*(.+?)(?:\n|$)', missing_text)
            result['missing_elements'] = [item.strip() for item in items if item.strip()]
        
        # Try to extract suggestions
        suggestions_section = re.search(
            r'suggestions?[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)',
            response_text,
            re.IGNORECASE | re.DOTALL
        )
        if suggestions_section:
            suggestions_text = suggestions_section.group(1)
            items = re.findall(r'[-*•]\s*(.+?)(?:\n|$)', suggestions_text)
            if not items:
                items = re.findall(r'\d+\.\s*(.+?)(?:\n|$)', suggestions_text)
            result['suggestions'] = [item.strip() for item in items if item.strip()]
        
        # Try to extract strengths
        strengths_section = re.search(
            r'strengths?[:\s]+(.*?)(?:\n\n|\n[A-Z]|$)',
            response_text,
            re.IGNORECASE | re.DOTALL
        )
        if strengths_section:
            strengths_text = strengths_section.group(1)
            items = re.findall(r'[-*•]\s*(.+?)(?:\n|$)', strengths_text)
            if not items:
                items = re.findall(r'\d+\.\s*(.+?)(?:\n|$)', strengths_text)
            result['strengths'] = [item.strip() for item in items if item.strip()]
        
        logger.info(
            f"Extracted from natural language: {result['compliance_status']} "
            f"(score: {result['completeness_score']:.2f})"
        )
        
        return result
