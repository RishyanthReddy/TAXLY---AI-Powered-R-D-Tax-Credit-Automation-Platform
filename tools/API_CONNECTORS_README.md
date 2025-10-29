# API Connectors Documentation

## Overview

This document provides comprehensive documentation for all API connector classes in the R&D Tax Credit Automation system. The connectors provide interfaces to external APIs for data ingestion, AI reasoning, and compliance checking.

## Table of Contents

1. [BaseAPIConnector](#baseapiconnector)
2. [RateLimiter](#ratelimiter)
3. [ClockifyConnector](#clockifyconnector)
4. [UnifiedToConnector](#unifiedtoconnector)
5. [GLMReasoner](#glmreasoner)
6. [YouComClient](#youcomclient)
7. [Error Handling](#error-handling)
8. [Rate Limiting Best Practices](#rate-limiting-best-practices)
9. [Usage Examples](#usage-examples)

---

## BaseAPIConnector

Abstract base class providing common functionality for all API connectors.

### Features

- HTTP request handling with retry logic
- Rate limiting support
- Error handling and logging
- Request/response logging
- Statistics tracking

### Constructor

```python
BaseAPIConnector(
    api_name: str,
    rate_limit: Optional[float] = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    rate_limit_burst_size: Optional[int] = None,
    rate_limit_backoff_threshold: float = 0.2,
    enable_backoff_warnings: bool = True
)
```

### Parameters

- `api_name`: Name of the API (for logging and error messages)
- `rate_limit`: Maximum requests per second (None for no limit)
- `timeout`: Request timeout in seconds (default: 30.0)
- `max_retries`: Maximum number of retry attempts (default: 3)
- `rate_limit_burst_size`: Maximum burst size for rate limiter (defaults to rate_limit)
- `rate_limit_backoff_threshold`: Token threshold (0-1) below which to apply backoff (default: 0.2)
- `enable_backoff_warnings`: Enable warning logs when approaching rate limits (default: True)

### Methods

#### `get_statistics() -> Dict[str, Any]`

Get connector statistics including request counts, error rates, and rate limiter stats.

**Returns:**
- Dictionary with statistics:
  - `api_name`: Name of the API
  - `request_count`: Total number of requests made
  - `error_count`: Total number of errors encountered
  - `error_rate`: Percentage of requests that failed
  - `total_wait_time`: Total time spent waiting for rate limits
  - `rate_limiter`: Per-endpoint rate limiter statistics (if applicable)

**Example:**
```python
connector = ClockifyConnector(api_key="...", workspace_id="...")
# ... make some requests ...
stats = connector.get_statistics()
print(f"Requests: {stats['request_count']}")
print(f"Error rate: {stats['error_rate']:.1%}")
```

#### `close()`

Close the HTTP client and release resources.

**Example:**
```python
connector = ClockifyConnector(api_key="...", workspace_id="...")
# ... use connector ...
connector.close()

# Or use as context manager:
with ClockifyConnector(api_key="...", workspace_id="...") as connector:
    # ... use connector ...
    pass  # Automatically closed
```

---

## RateLimiter

Token bucket rate limiter for API calls.

### Features

- Token bucket algorithm for smooth rate limiting
- Automatic backoff when approaching rate limits
- Configurable burst size for handling traffic spikes
- Warning logs when rate limits are approached
- Statistics tracking

### Constructor

```python
RateLimiter(
    requests_per_second: float,
    burst_size: Optional[int] = None,
    backoff_threshold: float = 0.2,
    enable_backoff_warnings: bool = True
)
```

### Parameters

- `requests_per_second`: Maximum number of requests per second
- `burst_size`: Maximum burst size (defaults to requests_per_second)
- `backoff_threshold`: Token threshold (0-1) below which to apply backoff (default: 0.2)
- `enable_backoff_warnings`: Enable warning logs when approaching limits (default: True)

### Methods

#### `acquire() -> float`

Acquire a token for making an API call. Implements automatic backoff when token count falls below threshold.

**Returns:** Time waited in seconds (0 if no wait was needed)

**Example:**
```python
limiter = RateLimiter(requests_per_second=10.0)
wait_time = limiter.acquire()
if wait_time > 0:
    print(f"Rate limited: waited {wait_time:.2f}s")
```

#### `get_statistics() -> Dict[str, Any]`

Get rate limiter statistics.

**Returns:**
- Dictionary with statistics:
  - `total_requests`: Total number of requests processed
  - `total_wait_time`: Total time spent waiting (seconds)
  - `backoff_count`: Number of times backoff was applied
  - `current_tokens`: Current token count
  - `token_percentage`: Current token percentage (0-1)
  - `requests_per_second`: Configured rate limit
  - `burst_size`: Configured burst size
  - `backoff_threshold`: Configured backoff threshold

---

## ClockifyConnector

Connector for Clockify time tracking API.

### Features

- Fetch time entries with pagination
- Transform raw API data to EmployeeTimeEntry models
- Parse ISO 8601 duration strings
- Automatic authentication testing
- Rate limiting: 10 requests per second

### Constructor

```python
ClockifyConnector(api_key: str, workspace_id: str)
```

### Parameters

- `api_key`: Clockify API key (X-Api-Key header)
- `workspace_id`: Clockify workspace ID

### Methods

#### `test_authentication() -> Dict[str, Any]`

Test authentication by fetching current user information.

**Returns:** User information dictionary with fields:
- `id`: User ID
- `email`: User email
- `name`: User name
- `activeWorkspace`: Active workspace ID
- `status`: Account status

**Raises:** `APIConnectionError` if authentication fails

**Example:**
```python
connector = ClockifyConnector(api_key="...", workspace_id="...")
user_info = connector.test_authentication()
print(f"Authenticated as: {user_info['email']}")
```

#### `fetch_time_entries(start_date: datetime, end_date: datetime, page_size: int = 50) -> List[Dict[str, Any]]`

Fetch time entries from Clockify for a given date range.

**Parameters:**
- `start_date`: Start date for time entries (inclusive)
- `end_date`: End date for time entries (inclusive)
- `page_size`: Number of entries per page (default: 50, max: 50)

**Returns:** List of time entry dictionaries with fields:
- `id`: Time entry ID
- `description`: Task description
- `userId`: User ID who logged the time
- `projectId`: Project ID
- `timeInterval`: Dict with start and end timestamps
- `duration`: Duration in ISO 8601 format (e.g., "PT8H30M")

**Raises:**
- `APIConnectionError`: If request fails
- `ValueError`: If date range is invalid or page_size is out of range

**Example:**
```python
from datetime import datetime
connector = ClockifyConnector(api_key="...", workspace_id="...")
entries = connector.fetch_time_entries(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31)
)
print(f"Fetched {len(entries)} time entries")
```

### API Documentation

https://docs.clockify.me/

### Rate Limits

- 10 requests per second
- Automatic pagination for large result sets
- Exponential backoff on rate limit errors

---

## UnifiedToConnector

Connector for Unified.to HRIS/Payroll API.

### Features

- OAuth 2.0 authentication with automatic token refresh
- Fetch employee data from 190+ HRIS systems
- Fetch payslip data with compensation details
- Transform payslip data to ProjectCost models
- Rate limiting: 5 requests per second (conservative)

### Constructor

```python
UnifiedToConnector(api_key: str, workspace_id: str)
```

### Parameters

- `api_key`: Unified.to API key for OAuth 2.0 authentication
- `workspace_id`: Unified.to workspace ID

### OAuth 2.0 Token Management

The connector automatically manages OAuth 2.0 tokens:
- Tokens are refreshed automatically when expired
- 60-second buffer before expiration for proactive refresh
- Handles token refresh failures gracefully
- Stores access token, expiration time, and refresh token

### Methods

#### `fetch_employees(connection_id: str) -> List[Dict[str, Any]]`

Fetch employee profiles from connected HRIS system.

**Parameters:**
- `connection_id`: Unified.to connection ID for the HRIS system

**Returns:** List of employee dictionaries with fields:
- Employee profiles with job titles, departments, compensation
- Varies by HRIS system

**Raises:** `APIConnectionError` if request fails

**Example:**
```python
connector = UnifiedToConnector(api_key="...", workspace_id="...")
employees = connector.fetch_employees(connection_id="conn_123")
print(f"Fetched {len(employees)} employees")
```

#### `fetch_payslips(connection_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]`

Fetch payslip data from connected HRIS system.

**Parameters:**
- `connection_id`: Unified.to connection ID for the HRIS system
- `start_date`: Start date for payslips (inclusive)
- `end_date`: End date for payslips (inclusive)

**Returns:** List of payslip dictionaries with fields:
- `gross_pay`: Gross pay amount
- `net_pay`: Net pay amount
- `deductions`: List of deductions
- `taxes`: Tax withholdings
- Employee ID and pay period information

**Raises:** `APIConnectionError` if request fails

**Example:**
```python
from datetime import datetime
connector = UnifiedToConnector(api_key="...", workspace_id="...")
payslips = connector.fetch_payslips(
    connection_id="conn_123",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31)
)
print(f"Fetched {len(payslips)} payslips")
```

### API Documentation

https://docs.unified.to/

### Rate Limits

- 5 requests per second (conservative)
- OAuth 2.0 token refresh handled automatically
- Exponential backoff on rate limit errors

### Error Handling

The connector handles various OAuth 2.0 error scenarios:
- **401 Unauthorized**: Invalid API key - provides remediation steps
- **403 Forbidden**: Insufficient permissions - suggests checking API key permissions
- **429 Rate Limit**: Automatic retry with backoff
- **Token Expiration**: Automatic token refresh before requests

---

## GLMReasoner

GLM 4.5 Air reasoner for PydanticAI agent reasoning via OpenRouter.

### Features

- RAG-augmented inference with IRS document context
- Agent decision-making for PydanticAI workflows
- Structured response parsing for qualification logic
- Comprehensive error handling with retry logic
- Timeout handling (30 seconds default)

### Model Configuration

- **Model**: `z-ai/glm-4.5-air:free`
- **Provider**: OpenRouter (https://openrouter.ai/api/v1)
- **Authentication**: Bearer token (OpenRouter API key)
- **Timeout**: 30 seconds (configurable)
- **Max Retries**: 3 attempts with exponential backoff

### Constructor

```python
GLMReasoner(api_key: Optional[str] = None, timeout: int = 30)
```

### Parameters

- `api_key`: OpenRouter API key (defaults to config)
- `timeout`: Request timeout in seconds (default: 30)

### Methods

#### `async reason(prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 2000) -> str`

Call GLM 4.5 Air for reasoning with comprehensive error handling.

**Parameters:**
- `prompt`: User prompt for reasoning
- `system_prompt`: Optional system prompt for context
- `temperature`: Sampling temperature (0.0-1.0, default: 0.2)
- `max_tokens`: Maximum tokens in response (default: 2000)

**Returns:** LLM response text

**Raises:** `APIConnectionError` if API call fails after retries

**Example:**
```python
import asyncio
from tools.glm_reasoner import GLMReasoner

async def main():
    reasoner = GLMReasoner()
    response = await reasoner.reason(
        prompt="What qualifies as R&D under IRS guidelines?",
        system_prompt="You are an expert in R&D tax credit qualification."
    )
    print(response)

asyncio.run(main())
```

#### `parse_qualification_response(response: str) -> Dict[str, Any]`

Parse qualification response from GLM 4.5 Air.

**Parameters:**
- `response`: Raw LLM response text

**Returns:** Dictionary containing:
- `qualification_percentage`: Percentage of project qualifying for R&D credit (0-100)
- `confidence_score`: Confidence in the qualification (0-1)
- `reasoning`: Explanation of the qualification decision
- `citations`: IRS document references

**Raises:** `ValueError` if response cannot be parsed

**Example:**
```python
reasoner = GLMReasoner()
response = await reasoner.reason(qualification_prompt)
parsed = reasoner.parse_qualification_response(response)
print(f"Qualification: {parsed['qualification_percentage']}%")
print(f"Confidence: {parsed['confidence_score']}")
```

#### `parse_structured_response(response: str) -> Dict[str, Any]`

Parse any structured response from GLM 4.5 Air.

Handles both JSON and natural language formats with multiple parsing strategies:
1. Direct JSON parsing
2. JSON extraction from markdown code blocks
3. Key-value pair extraction from natural language
4. Fallback to content wrapper

**Parameters:**
- `response`: Raw LLM response text

**Returns:** Dictionary containing parsed data

**Example:**
```python
reasoner = GLMReasoner()
response = await reasoner.reason(prompt)
parsed = reasoner.parse_structured_response(response)
```

### Error Handling

The GLMReasoner implements comprehensive error handling:

- **401 Unauthorized**: Invalid API key - no retry, immediate failure
- **429 Rate Limit Exceeded**: Retries with exponential backoff (max 3 attempts)
- **500 Internal Server Error**: Retries with exponential backoff
- **502 Bad Gateway**: Retries with exponential backoff
- **503 Service Unavailable**: Retries with exponential backoff
- **504 Gateway Timeout**: Retries with exponential backoff
- **Timeout**: Retries with exponential backoff (30s default timeout)
- **Connection Errors**: Retries with exponential backoff

### Retry Logic

- **Max Attempts**: 3
- **Initial Delay**: 2 seconds
- **Maximum Delay**: 10 seconds
- **Multiplier**: 1 (linear backoff)

### API Documentation

https://openrouter.ai/docs

---

## YouComClient

Client for You.com APIs (Search, Agent, Contents, Express Agent, News).

### Features

- Search API: Search for IRS guidance and compliance information
- Agent API: Expert R&D qualification reasoning
- Contents API: Fetch narrative templates and content
- Express Agent API: Quick compliance reviews
- News API: Search for recent news articles
- Per-endpoint rate limiting
- Caching for Search and Contents APIs
- Comprehensive error handling

### API Configuration

- **Search API**: 10 requests per minute (default)
- **Agent API**: 10 requests per minute (default)
- **Contents API**: 10 requests per minute (default)
- **Express Agent API**: 10 requests per minute (default)
- **News API**: 10 requests per minute (default)
- **Timeout**: 60 seconds (for agent runs which can take 10-30 seconds)
- **Max Retries**: 3 attempts with exponential backoff

### Constructor

```python
YouComClient(
    api_key: str,
    enable_cache: bool = True,
    search_cache_ttl: int = 3600,
    content_cache_ttl: int = 86400,
    custom_rate_limits: Optional[Dict[str, RateLimitConfig]] = None,
    enable_backoff_warnings: bool = True
)
```

### Parameters

- `api_key`: You.com API key (ydc-sk-... format)
- `enable_cache`: Enable caching for Search and Contents APIs (default: True)
- `search_cache_ttl`: Time-to-live for search results cache in seconds (default: 3600 = 1 hour)
- `content_cache_ttl`: Time-to-live for content/template cache in seconds (default: 86400 = 24 hours)
- `custom_rate_limits`: Optional custom rate limit configurations per endpoint
- `enable_backoff_warnings`: Enable warnings when rate limits are approached (default: True)

### Caching

Caching is applied to:
- **Search API**: Caches search results to avoid repeated queries (1 hour TTL)
- **Contents API**: Caches fetched templates and content (24 hour TTL)

Agent API and Express Agent API are NOT cached as they require fresh reasoning for each request.

### Methods

#### `test_authentication() -> bool`

Test authentication by making a simple API call.

**Returns:** True if authentication succeeds, False otherwise

**Example:**
```python
client = YouComClient(api_key="ydc-sk-...")
if client.test_authentication():
    print("Authentication successful!")
else:
    print("Authentication failed!")
```

#### `search(query: str, count: int = 10, offset: int = 0, freshness: Optional[str] = None, country: str = "US", safesearch: str = "moderate") -> List[Dict[str, Any]]`

Search for IRS guidance and compliance information using You.com Search API.

**Parameters:**
- `query`: Search query string (e.g., "IRS R&D tax credit software development new rulings 2025")
- `count`: Maximum number of results to return per section (web/news) (default: 10, max: 100)
- `offset`: Offset for pagination in multiples of count (default: 0, max: 9)
- `freshness`: Time filter for results - "day", "week", "month", or "year" (optional)
- `country`: Country code for geographical focus (default: "US")
- `safesearch`: Content moderation level - "off", "moderate", or "strict" (default: "moderate")

**Returns:** List of search result dictionaries, each containing:
- `title`: Title of the search result
- `url`: URL of the source document
- `description`: Description/summary of the content
- `snippets`: List of relevant text snippets
- `thumbnail_url`: URL of thumbnail image (if available)
- `page_age`: Publication date (if available)
- `authors`: List of authors (if available)
- `favicon_url`: URL of site favicon (if available)
- `source_type`: "web" or "news" indicating result type

**Example:**
```python
client = YouComClient(api_key="ydc-sk-...")
results = client.search(
    query="IRS R&D tax credit software development 2025",
    count=5,
    freshness="year"
)
for result in results:
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
    print(f"Description: {result['description']}")
```

#### `news(query: str, count: int = 10, offset: int = 0, freshness: Optional[str] = None, country: str = "US") -> List[Dict[str, Any]]`

Search for recent news articles using You.com Live News API.

**Parameters:**
- `query`: Search query string (e.g., "IRS R&D tax credit new ruling")
- `count`: Maximum number of news results to return (default: 10, max: 100)
- `offset`: Offset for pagination in multiples of count (default: 0, max: 9)
- `freshness`: Time filter - "day", "week", "month", or "year" (optional)
- `country`: Country code for geographical focus (default: "US")

**Returns:** List of news result dictionaries

**Example:**
```python
client = YouComClient(api_key="ydc-sk-...")
news = client.news(
    query="IRS R&D tax credit updates",
    count=5,
    freshness="month"
)
for article in news:
    print(f"Title: {article['title']}")
    print(f"Published: {article.get('page_age', 'Unknown')}")
```

#### `agent_run(prompt: str, agent_mode: str = "express", stream: bool = False, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]`

Run You.com Agent API for expert R&D qualification reasoning.

The Agent API provides advanced AI reasoning capabilities for complex tasks like R&D tax credit qualification. It combines web search, knowledge retrieval, and LLM reasoning to provide expert-level analysis.

**Parameters:**
- `prompt`: Detailed prompt with RAG context and project data for qualification analysis
- `agent_mode`: Agent mode configuration (default: "express")
  - `express`: Fast responses with web search (max 1 search)
  - `custom`: Custom agent with specific instructions
  - `advanced`: More comprehensive analysis
- `stream`: Whether to stream the response using SSE (default: False)
- `tools`: Optional list of tools the agent can use (e.g., [{"type": "web_search"}])

**Returns:** Dictionary containing agent response:
- `output`: List of output items with type, text, content, and agent info

**Example:**
```python
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.prompt_templates import populate_rag_inference_prompt

# Get RAG context
rag_tool = RD_Knowledge_Tool()
rag_context = rag_tool.query("R&D tax credit software development")

# Create prompt with RAG context and project data
prompt = populate_rag_inference_prompt(
    rag_context=rag_context.format_for_llm_prompt(),
    project_name="API Optimization",
    project_description="Improve API response times through algorithm optimization",
    technical_activities="Algorithm research, caching strategies, performance testing",
    total_hours=120.5,
    total_cost=15000.00
)

# Run agent for qualification
client = YouComClient(api_key="ydc-sk-...")
response = client.agent_run(prompt=prompt, agent_mode="express")

# Extract answer from response
answer_text = response['output'][0]['text']
parsed = client._parse_agent_response(answer_text)
print(f"Qualification: {parsed['qualification_percentage']}%")
print(f"Confidence: {parsed['confidence_score']}")
```

**Note:** The Agent API may take 10-30 seconds to complete as it performs comprehensive research and reasoning.

#### `_parse_agent_response(response_text: str) -> Dict[str, Any]`

Parse You.com Agent API response to extract structured qualification data.

**Parameters:**
- `response_text`: The agent's response text (from response['output'][0]['text'])

**Returns:** Dictionary with extracted data:
- `qualification_percentage`: Percentage of project qualifying (0-100)
- `confidence_score`: Confidence in qualification (0-1)
- `reasoning`: Detailed explanation of the qualification decision
- `citations`: List of IRS document references

**Example:**
```python
response = client.agent_run(prompt=qualification_prompt)
answer_text = response['output'][0]['text']
parsed = client._parse_agent_response(answer_text)
print(f"Qualification: {parsed['qualification_percentage']}%")
```

#### `fetch_content(url: str, format: str = "markdown") -> Dict[str, Any]`

Fetch R&D project narrative templates from known URLs using You.com Contents API.

**Parameters:**
- `url`: URL of the content to fetch
- `format`: Output format - "markdown" or "html" (default: "markdown")

**Returns:** Dictionary containing:
- `content`: Extracted content in requested format
- `url`: Original URL that was fetched
- `title`: Page title (if available)
- `description`: Page description (if available)
- `word_count`: Number of words in the content
- `format`: Format of the returned content

**Example:**
```python
client = YouComClient(api_key="ydc-sk-...")
result = client.fetch_content(
    url="https://example.com/rd-narrative-template",
    format="markdown"
)
print(f"Fetched {result['word_count']} words")
print(result['content'])
```

### Cache Management

#### `clear_search_cache() -> int`

Clear all cached search results.

**Returns:** Number of cache entries cleared

#### `clear_content_cache() -> int`

Clear all cached content/templates.

**Returns:** Number of cache entries cleared

#### `clear_all_caches() -> Dict[str, int]`

Clear all caches (search and content).

**Returns:** Dictionary with counts of cleared entries

#### `get_cache_statistics() -> Dict[str, Any]`

Get statistics about cache usage.

**Returns:** Dictionary with cache statistics

### Rate Limiter Statistics

#### `get_rate_limiter_statistics() -> Dict[str, Any]`

Get rate limiter statistics for all endpoints.

**Returns:** Dictionary mapping endpoint names to their rate limiter statistics

#### `log_rate_limiter_statistics()`

Log rate limiter statistics for all endpoints.

### API Documentation

https://documentation.you.com/

---

## Error Handling

All API connectors implement comprehensive error handling with specific strategies for different error types.

### Common Error Scenarios

#### 401 Unauthorized

**Cause:** Invalid API key or expired credentials

**Handling:**
- ClockifyConnector: Immediate failure with clear error message
- UnifiedToConnector: Automatic token refresh attempt, then failure
- GLMReasoner: Immediate failure (no retry)
- YouComClient: Immediate failure with remediation steps

**Remediation:**
- Verify API key in environment variables
- Check that the key is active and not expired
- Ensure the key has correct format (e.g., ydc-sk-... for You.com)

#### 429 Rate Limit Exceeded

**Cause:** Too many requests to the API

**Handling:**
- Automatic retry with exponential backoff
- Wait time extracted from retry-after header if available
- Rate limiter automatically slows down requests

**Remediation:**
- Wait before retrying (handled automatically)
- Reduce request frequency
- Check if multiple instances are using the same API key

#### 500 Internal Server Error

**Cause:** API server error (temporary)

**Handling:**
- Automatic retry with exponential backoff (max 3 attempts)
- Logged as warning (not error) since it's transient

**Remediation:**
- Retry the request (handled automatically)
- If error persists, check API status page

#### Timeout Errors

**Cause:** Request took too long to complete

**Handling:**
- Automatic retry with exponential backoff
- Configurable timeout per connector

**Remediation:**
- Increase timeout if needed
- Check network connectivity
- Verify API endpoint is responsive

### Error Logging

All connectors log errors with comprehensive context:
- Error type and status code
- Endpoint and request context
- Suggested remediation steps
- Full error details for debugging

**Example Error Log:**
```
[You.com] 401 Unauthorized on /v1/search (query=IRS R&D, count=10)
Error: Invalid API key
Cause: Invalid or expired API key
Remediation: Verify YOUCOM_API_KEY in environment variables
  - Check that the key starts with 'ydc-sk-'
  - Verify the key is active in You.com dashboard
  - Ensure the key has not expired
Details: {'error': 'Invalid credentials'}
```

---

## Rate Limiting Best Practices

### Per-Connector Rate Limits

| Connector | Rate Limit | Burst Size | Backoff Threshold |
|-----------|------------|------------|-------------------|
| ClockifyConnector | 10 req/s | 10 | 0.2 (20%) |
| UnifiedToConnector | 5 req/s | 5 | 0.2 (20%) |
| GLMReasoner | N/A (uses retry logic) | N/A | N/A |
| YouComClient (Search) | 10 req/min | 10 | 0.2 (20%) |
| YouComClient (Agent) | 10 req/min | 10 | 0.2 (20%) |
| YouComClient (Contents) | 10 req/min | 10 | 0.2 (20%) |
| YouComClient (Express) | 10 req/min | 10 | 0.2 (20%) |
| YouComClient (News) | 10 req/min | 10 | 0.2 (20%) |

### Automatic Backoff

All rate limiters implement automatic backoff when token count falls below the threshold (default: 20% of burst size). This helps prevent hitting rate limits by proactively slowing down when approaching the limit.

**Backoff Calculation:**
```python
backoff_factor = (threshold - token_percentage) / threshold
backoff_wait = backoff_factor * (1.0 / requests_per_second)
```

### Custom Rate Limits

You can configure custom rate limits for You.com APIs:

```python
from tools.youcom_rate_limiter import RateLimitConfig

custom_limits = {
    'agent': RateLimitConfig(requests_per_minute=5, burst_size=5),
    'search': RateLimitConfig(requests_per_minute=20, burst_size=20)
}

client = YouComClient(
    api_key="ydc-sk-...",
    custom_rate_limits=custom_limits
)
```

### Monitoring Rate Limits

Monitor rate limiter statistics to optimize performance:

```python
# Get statistics for a specific connector
stats = connector.get_statistics()
print(f"Total requests: {stats['request_count']}")
print(f"Total wait time: {stats['total_wait_time']:.2f}s")

# For You.com client, get per-endpoint statistics
rate_stats = client.get_rate_limiter_statistics()
for endpoint, stats in rate_stats.items():
    print(f"{endpoint}: {stats['total_requests']} requests, "
          f"{stats['backoff_count']} backoffs")
```

---

## Usage Examples

### Example 1: Fetch Time Entries from Clockify

```python
from datetime import datetime
from tools.api_connectors import ClockifyConnector
from utils.config import get_config

# Initialize connector
config = get_config()
connector = ClockifyConnector(
    api_key=config.clockify_api_key,
    workspace_id=config.clockify_workspace_id
)

# Test authentication
try:
    user_info = connector.test_authentication()
    print(f"Authenticated as: {user_info['email']}")
except Exception as e:
    print(f"Authentication failed: {e}")
    exit(1)

# Fetch time entries for January 2024
entries = connector.fetch_time_entries(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    page_size=50
)

print(f"Fetched {len(entries)} time entries")

# Get statistics
stats = connector.get_statistics()
print(f"Total requests: {stats['request_count']}")
print(f"Error rate: {stats['error_rate']:.1%}")
print(f"Total wait time: {stats['total_wait_time']:.2f}s")

# Close connector
connector.close()
```

### Example 2: Fetch Payroll Data from Unified.to

```python
from datetime import datetime
from tools.api_connectors import UnifiedToConnector
from utils.config import get_config

# Initialize connector
config = get_config()
connector = UnifiedToConnector(
    api_key=config.unified_to_api_key,
    workspace_id=config.unified_to_workspace_id
)

# Fetch employees
connection_id = "conn_123"  # Your HRIS connection ID
employees = connector.fetch_employees(connection_id=connection_id)
print(f"Fetched {len(employees)} employees")

# Fetch payslips for Q1 2024
payslips = connector.fetch_payslips(
    connection_id=connection_id,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 3, 31)
)
print(f"Fetched {len(payslips)} payslips")

# Get statistics
stats = connector.get_statistics()
print(f"Total requests: {stats['request_count']}")
print(f"Error rate: {stats['error_rate']:.1%}")

# Close connector
connector.close()
```

### Example 3: GLM 4.5 Air Reasoning for R&D Qualification

```python
import asyncio
from tools.glm_reasoner import GLMReasoner
from tools.rd_knowledge_tool import RD_Knowledge_Tool

async def qualify_project():
    # Initialize reasoner
    reasoner = GLMReasoner()
    
    # Get RAG context from IRS documents
    rag_tool = RD_Knowledge_Tool()
    rag_context = rag_tool.query(
        "What qualifies as R&D for software development under IRS guidelines?"
    )
    
    # Create system prompt with RAG context
    system_prompt = f"""You are an expert in R&D tax credit qualification.
    
Use the following IRS guidance to inform your analysis:

{rag_context.format_for_llm_prompt()}

Provide your response in JSON format with the following fields:
- qualification_percentage: Percentage of project qualifying (0-100)
- confidence_score: Confidence in qualification (0-1)
- reasoning: Detailed explanation
- citations: List of IRS document references
"""
    
    # Create user prompt with project details
    user_prompt = """Analyze the following project for R&D tax credit qualification:

Project: API Performance Optimization
Description: Developed new caching algorithms to reduce API response times by 50%
Technical Activities:
- Researched various caching strategies and algorithms
- Experimented with different data structures for cache storage
- Conducted performance testing and benchmarking
- Resolved technical uncertainties around cache invalidation

Total Hours: 120.5
Total Cost: $15,000

Determine the qualification percentage and confidence score."""
    
    # Call GLM 4.5 Air for reasoning
    response = await reasoner.reason(
        prompt=user_prompt,
        system_prompt=system_prompt,
        temperature=0.2
    )
    
    # Parse response
    parsed = reasoner.parse_qualification_response(response)
    
    print(f"Qualification: {parsed['qualification_percentage']}%")
    print(f"Confidence: {parsed['confidence_score']:.2f}")
    print(f"Reasoning: {parsed['reasoning']}")
    print(f"Citations: {', '.join(parsed['citations'])}")

# Run async function
asyncio.run(qualify_project())
```

### Example 4: You.com Search for IRS Guidance

```python
from tools.you_com_client import YouComClient
from utils.config import get_config

# Initialize client
config = get_config()
client = YouComClient(
    api_key=config.youcom_api_key,
    enable_cache=True,
    search_cache_ttl=3600  # 1 hour
)

# Test authentication
if not client.test_authentication():
    print("Authentication failed!")
    exit(1)

# Search for recent IRS guidance
results = client.search(
    query="IRS R&D tax credit software development new rulings 2025",
    count=10,
    freshness="year",
    country="US"
)

print(f"Found {len(results)} search results")

for i, result in enumerate(results, 1):
    print(f"\n{i}. {result['title']}")
    print(f"   URL: {result['url']}")
    print(f"   Type: {result['source_type']}")
    print(f"   Description: {result['description'][:200]}...")
    if result.get('page_age'):
        print(f"   Published: {result['page_age']}")

# Get cache statistics
cache_stats = client.get_cache_statistics()
print(f"\nCache Statistics:")
print(f"Search cache size: {cache_stats['search_cache_size']} entries")
print(f"Content cache size: {cache_stats['content_cache_size']} entries")

# Get rate limiter statistics
client.log_rate_limiter_statistics()

# Close client
client.close()
```

### Example 5: You.com Agent API for R&D Qualification

```python
from tools.you_com_client import YouComClient
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.prompt_templates import YOUCOM_QUALIFICATION_PROMPT
from utils.config import get_config

# Initialize client
config = get_config()
client = YouComClient(api_key=config.youcom_api_key)

# Get RAG context from IRS documents
rag_tool = RD_Knowledge_Tool()
rag_context = rag_tool.query(
    "R&D tax credit qualification for software development"
)

# Populate prompt template with RAG context and project data
prompt = YOUCOM_QUALIFICATION_PROMPT.format(
    rag_context=rag_context.format_for_llm_prompt(),
    project_name="Machine Learning Model Optimization",
    project_description="Developed novel algorithms to improve ML model training speed",
    technical_activities="""
    - Researched state-of-the-art optimization techniques
    - Experimented with gradient descent variants
    - Resolved technical uncertainties around convergence
    - Conducted extensive performance benchmarking
    """,
    total_hours=250.0,
    total_cost=35000.00
)

# Run You.com Agent API for expert qualification
response = client.agent_run(
    prompt=prompt,
    agent_mode="express"
)

# Extract and parse agent response
answer_text = response['output'][0]['text']
parsed = client._parse_agent_response(answer_text)

print(f"Project: Machine Learning Model Optimization")
print(f"Qualification: {parsed['qualification_percentage']}%")
print(f"Confidence: {parsed['confidence_score']:.2f}")
print(f"\nReasoning:")
print(parsed['reasoning'])
print(f"\nCitations:")
for citation in parsed['citations']:
    print(f"  - {citation}")

# Get statistics
stats = client.get_statistics()
print(f"\nAPI Statistics:")
print(f"Total requests: {stats['request_count']}")
print(f"Error rate: {stats['error_rate']:.1%}")

# Close client
client.close()
```

### Example 6: You.com Contents API for Narrative Templates

```python
from tools.you_com_client import YouComClient
from utils.config import get_config

# Initialize client with caching enabled
config = get_config()
client = YouComClient(
    api_key=config.youcom_api_key,
    enable_cache=True,
    content_cache_ttl=86400  # 24 hours
)

# Fetch R&D narrative template from a known URL
template_url = "https://example.com/rd-narrative-template"

result = client.fetch_content(
    url=template_url,
    format="markdown"
)

print(f"Fetched template: {result['title']}")
print(f"Word count: {result['word_count']}")
print(f"Format: {result['format']}")
print(f"\nContent preview:")
print(result['content'][:500])
print("...")

# Use template for narrative generation
# (This would be used by the Audit Trail Agent)

# Get cache statistics
cache_stats = client.get_cache_statistics()
print(f"\nCache Statistics:")
print(f"Content cache size: {cache_stats['content_cache_size']} entries")

# Close client
client.close()
```

### Example 7: Context Manager Usage

```python
from datetime import datetime
from tools.api_connectors import ClockifyConnector
from utils.config import get_config

config = get_config()

# Use connector as context manager (automatically closes)
with ClockifyConnector(
    api_key=config.clockify_api_key,
    workspace_id=config.clockify_workspace_id
) as connector:
    # Test authentication
    user_info = connector.test_authentication()
    print(f"Authenticated as: {user_info['email']}")
    
    # Fetch time entries
    entries = connector.fetch_time_entries(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31)
    )
    
    print(f"Fetched {len(entries)} time entries")
    
    # Get statistics
    stats = connector.get_statistics()
    print(f"Total requests: {stats['request_count']}")
    print(f"Error rate: {stats['error_rate']:.1%}")

# Connector is automatically closed here
```

### Example 8: Error Handling

```python
from tools.you_com_client import YouComClient
from utils.exceptions import APIConnectionError
from utils.config import get_config

config = get_config()
client = YouComClient(api_key=config.youcom_api_key)

try:
    # Attempt to search
    results = client.search(
        query="IRS R&D tax credit",
        count=10
    )
    print(f"Found {len(results)} results")
    
except APIConnectionError as e:
    # Handle API errors with detailed information
    print(f"API Error: {e.message}")
    print(f"API: {e.api_name}")
    print(f"Status Code: {e.status_code}")
    print(f"Endpoint: {e.endpoint}")
    print(f"Details: {e.details}")
    
    # Take appropriate action based on error type
    if e.status_code == 401:
        print("Authentication failed. Please check your API key.")
    elif e.status_code == 429:
        print("Rate limit exceeded. Please wait before retrying.")
    elif e.status_code >= 500:
        print("Server error. Please retry later.")
    else:
        print("Unexpected error occurred.")

except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected error: {e}")

finally:
    # Always close the client
    client.close()
```

---

## Summary

This documentation covers all API connectors in the R&D Tax Credit Automation system:

1. **BaseAPIConnector**: Abstract base class with common functionality
2. **RateLimiter**: Token bucket rate limiter with automatic backoff
3. **ClockifyConnector**: Time tracking data from Clockify API
4. **UnifiedToConnector**: HRIS/payroll data from 190+ systems via Unified.to
5. **GLMReasoner**: GLM 4.5 Air reasoning via OpenRouter for PydanticAI agents
6. **YouComClient**: Search, Agent, Contents, Express Agent, and News APIs

All connectors implement:
- Comprehensive error handling with retry logic
- Rate limiting to prevent API throttling
- Statistics tracking for monitoring
- Context manager support for resource cleanup
- Detailed logging for debugging

For more information, see:
- Individual README files for each tool
- Usage examples in the `examples/` directory
- Test files in the `tests/` directory
- API documentation links provided for each connector
