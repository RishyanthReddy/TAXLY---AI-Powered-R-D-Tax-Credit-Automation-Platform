# GLM Reasoner

## Overview

The `GLMReasoner` class provides an interface to GLM 4.5 Air via OpenRouter for PydanticAI agent reasoning in the R&D Tax Credit Automation system. GLM 4.5 Air is used as the core reasoning engine for RAG-augmented inference and agent decision-making.

## Purpose

GLM 4.5 Air (via OpenRouter) serves as the primary LLM for:
- **RAG-augmented inference**: Reasoning with IRS document context
- **Agent decision-making**: PydanticAI workflow logic
- **Structured response parsing**: Extracting qualification data

## Features

- ✅ Async API calls with retry logic
- ✅ Automatic error handling and recovery
- ✅ Structured response parsing (JSON and natural language)
- ✅ Qualification-specific data extraction
- ✅ Citation extraction from responses
- ✅ Configurable temperature and token limits

## Installation

The GLMReasoner requires:
```bash
pip install httpx tenacity
```

## Configuration

Set your OpenRouter API key in `.env`:
```bash
OPENROUTER_API_KEY=your_openrouter_key_here
```

## Usage

### Basic Reasoning

```python
from rd_tax_agent.tools.glm_reasoner import GLMReasoner
import asyncio

async def main():
    reasoner = GLMReasoner()
    
    prompt = "Analyze if this software development project qualifies for R&D tax credit..."
    system_prompt = "You are an expert in IRS R&D tax credit regulations."
    
    response = await reasoner.reason(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.2
    )
    
    print(response)

asyncio.run(main())
```

### RAG-Augmented Reasoning

```python
from rd_tax_agent.tools.glm_reasoner import GLMReasoner
from rd_tax_agent.tools.rd_knowledge_tool import RD_Knowledge_Tool
import asyncio

async def main():
    # Initialize tools
    reasoner = GLMReasoner()
    rag_tool = RD_Knowledge_Tool()
    
    # Query RAG system
    question = "What are the four-part test requirements for R&D qualification?"
    rag_context = rag_tool.query(question, top_k=3)
    
    # Format context for LLM
    context_text = "\n\n".join([
        f"Source: {ctx['source']}, Page: {ctx['page']}\n{ctx['text']}"
        for ctx in rag_context
    ])
    
    # Reason with context
    prompt = f"""Based on the following IRS guidance:

{context_text}

Question: {question}

Provide a detailed answer with citations."""
    
    response = await reasoner.reason(prompt=prompt)
    print(response)

asyncio.run(main())
```

### Qualification Response Parsing

```python
from rd_tax_agent.tools.glm_reasoner import GLMReasoner
import asyncio

async def main():
    reasoner = GLMReasoner()
    
    # Get qualification reasoning
    prompt = """Analyze this project for R&D qualification:
    
Project: Machine Learning Model Development
Description: Developed novel neural network architecture for image recognition...

Provide:
1. Qualification percentage (0-100%)
2. Confidence score (0-1)
3. Reasoning
4. IRS citations
"""
    
    response = await reasoner.reason(prompt=prompt)
    
    # Parse structured data
    qualification_data = reasoner.parse_qualification_response(response)
    
    print(f"Qualification: {qualification_data['qualification_percentage']}%")
    print(f"Confidence: {qualification_data['confidence_score']}")
    print(f"Reasoning: {qualification_data['reasoning']}")
    print(f"Citations: {qualification_data['citations']}")

asyncio.run(main())
```

## API Reference

### GLMReasoner

#### `__init__(api_key: Optional[str] = None, timeout: int = 30)`

Initialize the GLM reasoner.

**Parameters:**
- `api_key` (str, optional): OpenRouter API key (defaults to config)
- `timeout` (int): Request timeout in seconds (default: 30)

**Raises:**
- `ValueError`: If API key is not provided

#### `async reason(prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 2000) -> str`

Call GLM 4.5 Air for reasoning.

**Parameters:**
- `prompt` (str): User prompt for reasoning
- `system_prompt` (str, optional): System prompt for context
- `temperature` (float): Sampling temperature 0.0-1.0 (default: 0.2)
- `max_tokens` (int): Maximum tokens in response (default: 2000)

**Returns:**
- `str`: LLM response text

**Raises:**
- `APIConnectionError`: If API call fails after retries

**Features:**
- Automatic retry with exponential backoff (3 attempts)
- Handles 401 (invalid key), 429 (rate limit), 500 (server error)
- Timeout handling

#### `parse_qualification_response(response: str) -> Dict[str, Any]`

Parse qualification response from GLM 4.5 Air.

**Parameters:**
- `response` (str): Raw LLM response text

**Returns:**
- `Dict` containing:
  - `qualification_percentage` (float): 0-100
  - `confidence_score` (float): 0-1
  - `reasoning` (str): Explanation
  - `citations` (list): IRS document references

**Raises:**
- `ValueError`: If response cannot be parsed

**Supported Formats:**
- JSON: `{"qualification_percentage": 85, "confidence_score": 0.9, ...}`
- Natural language: Extracts data using regex patterns

#### `parse_structured_response(response: str) -> Dict[str, Any]`

Parse any structured response from GLM 4.5 Air with intelligent format detection.

**Parameters:**
- `response` (str): Raw LLM response text

**Returns:**
- `Dict` or `List`: Parsed structured data, or `{"content": response}` for plain text

**Raises:**
- `ValueError`: If response is empty or None

**Parsing Strategies:**

The method attempts multiple parsing strategies in order:

1. **Direct JSON Parsing**: Detects and parses JSON objects/arrays
   ```python
   response = '{"key": "value", "number": 42}'
   result = reasoner.parse_structured_response(response)
   # Returns: {'key': 'value', 'number': 42}
   ```

2. **Markdown Code Block Extraction**: Extracts JSON from markdown
   ```python
   response = '''Here's the data:
   ```json
   {"status": "success"}
   ```'''
   result = reasoner.parse_structured_response(response)
   # Returns: {'status': 'success'}
   ```

3. **Key-Value Pair Extraction**: Parses natural language patterns
   ```python
   response = '''
   name: John Doe
   age: 30
   active: yes
   '''
   result = reasoner.parse_structured_response(response)
   # Returns: {'name': 'John Doe', 'age': 30, 'active': True, 'content': '...'}
   ```

4. **Fallback to Content Wrapper**: Returns text as-is
   ```python
   response = "This is plain text"
   result = reasoner.parse_structured_response(response)
   # Returns: {'content': 'This is plain text'}
   ```

**Type Conversion:**

The method automatically converts values to appropriate types:
- Integers: `"42"` → `42`
- Floats: `"3.14"` → `3.14`
- Booleans: `"yes"`, `"true"` → `True`; `"no"`, `"false"` → `False`
- Strings: Everything else

**Examples:**

```python
# Example 1: Parse JSON response
json_response = '{"project": "Alpha", "score": 95}'
result = reasoner.parse_structured_response(json_response)
print(result['project'])  # "Alpha"
print(result['score'])    # 95

# Example 2: Parse markdown JSON
markdown = '''Analysis complete:
```json
{"qualified": true, "percentage": 85.5}
```'''
result = reasoner.parse_structured_response(markdown)
print(result['qualified'])   # True
print(result['percentage'])  # 85.5

# Example 3: Parse key-value pairs
kv_text = '''
status: complete
confidence: 0.92
approved: yes
'''
result = reasoner.parse_structured_response(kv_text)
print(result['status'])      # "complete"
print(result['confidence'])  # 0.92
print(result['approved'])    # True

# Example 4: Parse JSON array
array = '[{"id": 1}, {"id": 2}]'
result = reasoner.parse_structured_response(array)
print(len(result))  # 2
print(result[0])    # {'id': 1}

# Example 5: Handle plain text
text = "This project qualifies for R&D credit."
result = reasoner.parse_structured_response(text)
print(result['content'])  # "This project qualifies for R&D credit."
```

## Model Configuration

**Model:** `z-ai/glm-4.5-air:free`
**Provider:** OpenRouter
**Base URL:** `https://openrouter.ai/api/v1`

**Model Characteristics:**
- Free tier available
- Excellent reasoning capabilities
- Good for structured output
- Supports system prompts
- Max context: ~8K tokens

## Error Handling

The GLMReasoner implements comprehensive error handling with automatic retry logic for transient failures.

### Error Types and Handling

| Error Type | Status Code | Retry? | Handling Strategy |
|------------|-------------|--------|-------------------|
| **Invalid API Key** | 401 | ❌ No | Raises `APIConnectionError` immediately with clear message |
| **Rate Limit Exceeded** | 429 | ✅ Yes | Retries with exponential backoff (3 attempts) |
| **Internal Server Error** | 500 | ✅ Yes | Retries with exponential backoff (3 attempts) |
| **Bad Gateway** | 502 | ✅ Yes | Retries with exponential backoff (3 attempts) |
| **Service Unavailable** | 503 | ✅ Yes | Retries with exponential backoff (3 attempts) |
| **Gateway Timeout** | 504 | ✅ Yes | Retries with exponential backoff (3 attempts) |
| **Request Timeout** | N/A | ✅ Yes | Retries with exponential backoff (3 attempts) |
| **Connection Error** | N/A | ✅ Yes | Retries with exponential backoff (3 attempts) |
| **Network Error** | N/A | ❌ No | Raises `APIConnectionError` immediately |
| **Invalid JSON Response** | N/A | ❌ No | Raises `APIConnectionError` with parse error details |
| **Malformed Response** | N/A | ❌ No | Raises `APIConnectionError` with validation error |

### Retry Configuration

The retry logic uses exponential backoff with the following parameters:

- **Maximum Attempts:** 3
- **Initial Delay:** 2 seconds
- **Maximum Delay:** 10 seconds
- **Multiplier:** 1 (linear backoff)

**Example Retry Timeline:**
1. First attempt fails → Wait 2 seconds
2. Second attempt fails → Wait 2 seconds
3. Third attempt fails → Raise exception

### Error Messages

All errors include detailed, actionable messages:

```python
# 401 Unauthorized
"Invalid OpenRouter API key (401 Unauthorized). Please check your OPENROUTER_API_KEY environment variable."

# 429 Rate Limit
"Rate limit exceeded for GLM 4.5 Air (429 Too Many Requests). Request will be retried with exponential backoff."

# 500 Server Error
"GLM 4.5 Air internal server error (500). Request will be retried with exponential backoff."

# Timeout
"GLM 4.5 Air request timeout after 30s. Request will be retried with exponential backoff."

# Connection Error
"Failed to connect to OpenRouter API: [details]. Request will be retried with exponential backoff."

# Invalid Response
"Invalid API response: missing 'choices' field"
```

### Logging

All errors are logged with appropriate severity levels:

- **ERROR:** Non-retryable errors (401, network errors, parse errors)
- **WARNING:** Retryable errors before retry attempts
- **INFO:** Successful responses

**Example Log Output:**
```
2025-10-29 08:10:05 [ WARNING] tools.glm_reasoner - Rate limit exceeded for GLM 4.5 Air (429 Too Many Requests). Request will be retried with exponential backoff.
2025-10-29 08:10:05 [ WARNING] tools.glm_reasoner - Retrying tools.glm_reasoner.GLMReasoner.reason in 2.0 seconds as it raised HTTPStatusError: Rate limit.
2025-10-29 08:10:07 [    INFO] tools.glm_reasoner - GLM 4.5 Air response received (length: 1234)
```

### Response Validation

The reasoner validates all API responses to ensure data integrity:

1. **Structure Validation:**
   - Checks for `choices` field
   - Validates `choices` array is not empty
   - Verifies `message` field exists
   - Confirms `content` field is present

2. **Type Validation:**
   - Ensures response is valid JSON
   - Validates field types match expected schema

3. **Content Validation:**
   - For qualification responses: validates percentage (0-100) and confidence (0-1)
   - Clamps out-of-range values with warnings

### Error Handling Examples

**Example 1: Handling Rate Limits**
```python
import asyncio
from rd_tax_agent.tools.glm_reasoner import GLMReasoner
from rd_tax_agent.utils.exceptions import APIConnectionError

async def main():
    reasoner = GLMReasoner()
    
    try:
        response = await reasoner.reason("Analyze this project...")
        print(response)
    except APIConnectionError as e:
        if "Rate limit" in str(e):
            print("Rate limit hit. The request was retried but still failed.")
            print("Consider implementing request queuing or upgrading your plan.")
        else:
            print(f"API error: {e}")

asyncio.run(main())
```

**Example 2: Handling Timeouts**
```python
async def main():
    # Use longer timeout for complex queries
    reasoner = GLMReasoner(timeout=60)
    
    try:
        response = await reasoner.reason(
            prompt="Complex analysis requiring more time...",
            max_tokens=4000
        )
        print(response)
    except APIConnectionError as e:
        if "timeout" in str(e):
            print("Request timed out even after retries.")
            print("Consider breaking the query into smaller parts.")
        else:
            print(f"API error: {e}")

asyncio.run(main())
```

**Example 3: Handling Invalid API Keys**
```python
async def main():
    try:
        reasoner = GLMReasoner(api_key="invalid_key")
        response = await reasoner.reason("Test prompt")
    except APIConnectionError as e:
        if "401" in str(e) or "Invalid" in str(e):
            print("API key is invalid. Please check your credentials.")
            print("Set OPENROUTER_API_KEY in your .env file.")
        else:
            print(f"API error: {e}")

asyncio.run(main())
```

**Example 4: Graceful Degradation**
```python
async def reason_with_fallback(prompt: str, fallback_response: str = None):
    """Attempt reasoning with fallback on failure"""
    reasoner = GLMReasoner()
    
    try:
        return await reasoner.reason(prompt)
    except APIConnectionError as e:
        logger.error(f"GLM reasoning failed: {e}")
        if fallback_response:
            logger.info("Using fallback response")
            return fallback_response
        else:
            raise

# Usage
response = await reason_with_fallback(
    "Analyze project...",
    fallback_response="Unable to analyze at this time. Please try again later."
)
```

### Best Practices for Error Handling

1. **Always use try-except blocks:**
   ```python
   try:
       response = await reasoner.reason(prompt)
   except APIConnectionError as e:
       logger.error(f"Reasoning failed: {e}")
       # Handle error appropriately
   ```

2. **Monitor retry attempts:**
   - Check logs for frequent retries
   - May indicate rate limiting or service issues

3. **Implement circuit breakers for production:**
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(stop=stop_after_attempt(5), wait=wait_exponential(min=4, max=60))
   async def robust_reasoning(prompt: str):
       reasoner = GLMReasoner()
       return await reasoner.reason(prompt)
   ```

4. **Set appropriate timeouts:**
   - Short queries: 30s (default)
   - Complex analysis: 60-90s
   - Batch processing: Consider per-item timeout

5. **Handle specific error types:**
   ```python
   try:
       response = await reasoner.reason(prompt)
   except APIConnectionError as e:
       if "401" in str(e):
           # Handle authentication error
           notify_admin("Invalid API key")
       elif "429" in str(e):
           # Handle rate limit
           queue_for_later(prompt)
       else:
           # Handle other errors
           log_error(e)
   ```

## Best Practices

1. **Use appropriate temperature:**
   - 0.0-0.3: Deterministic, factual responses
   - 0.4-0.7: Balanced creativity and accuracy
   - 0.8-1.0: Creative, varied responses

2. **Provide clear system prompts:**
   ```python
   system_prompt = "You are an expert in IRS R&D tax credit regulations. Provide precise, citation-backed answers."
   ```

3. **Structure your prompts:**
   - Include context first
   - Ask specific questions
   - Request structured output format

4. **Handle async properly:**
   ```python
   # Use asyncio.run() for top-level
   asyncio.run(main())
   
   # Use await in async functions
   response = await reasoner.reason(prompt)
   ```

5. **Parse responses defensively:**
   ```python
   try:
       data = reasoner.parse_qualification_response(response)
   except ValueError as e:
       logger.error(f"Failed to parse: {e}")
       # Fallback logic
   ```

## Integration with PydanticAI

The GLMReasoner is designed to work seamlessly with PydanticAI agents:

```python
from pydantic_ai import Agent
from rd_tax_agent.tools.glm_reasoner import GLMReasoner

# Initialize reasoner
reasoner = GLMReasoner()

# Use in PydanticAI agent
agent = Agent(
    model="openrouter:z-ai/glm-4.5-air:free",
    # ... agent configuration
)

# The reasoner can be used for custom reasoning steps
async def custom_reasoning_step(context: str, question: str):
    return await reasoner.reason(
        prompt=f"Context: {context}\n\nQuestion: {question}",
        temperature=0.2
    )
```

## Performance Considerations

- **Latency:** ~2-5 seconds per request
- **Rate Limits:** Check OpenRouter free tier limits
- **Token Usage:** Monitor with max_tokens parameter
- **Caching:** Consider caching responses for repeated queries

## Troubleshooting

### "Invalid OpenRouter API key"
- Check `.env` file has correct `OPENROUTER_API_KEY`
- Verify key is active on OpenRouter dashboard

### "Rate limit exceeded"
- Wait for rate limit reset
- Consider upgrading OpenRouter plan
- Implement request queuing

### "Request timeout"
- Increase timeout parameter
- Check network connectivity
- Verify OpenRouter service status

### "Failed to parse qualification response"
- Check prompt asks for structured output
- Review response format in logs
- Adjust parsing logic if needed

## Related Components

- **RD_Knowledge_Tool**: RAG system for IRS documents
- **QualificationAgent**: Uses GLMReasoner for project qualification
- **AuditTrailAgent**: Uses GLMReasoner for narrative generation

## Testing

See `tests/test_glm_reasoner.py` for comprehensive test suite.

Run tests:
```bash
pytest tests/test_glm_reasoner.py -v
```

## License

Part of the R&D Tax Credit Automation Agent project.
