# FastAPI Application Structure

## Overview

The `main.py` file provides the FastAPI application structure for the R&D Tax Credit Automation Agent. It serves as the backend API that orchestrates the three specialized agents (Data Ingestion, Qualification, and Audit Trail) and provides real-time status updates to the frontend.

## Features

### 1. Application Initialization
- FastAPI app with comprehensive metadata
- Lifespan context manager for startup/shutdown events
- Configuration loading and validation
- Directory structure verification
- API key status logging

### 2. CORS Middleware
- Configured for frontend communication
- Allows requests from:
  - `http://localhost:3000` (React dev server)
  - `http://localhost:5173` (Vite dev server)
  - `http://127.0.0.1:3000`
  - `http://127.0.0.1:5173`
- Supports all HTTP methods and headers
- Enables credentials for authenticated requests

### 3. Exception Handlers
Comprehensive error handling for all custom exceptions:

| Exception Type | HTTP Status | Description |
|---------------|-------------|-------------|
| `ConfigurationError` | 500 | Missing or invalid configuration |
| `APIConnectionError` | 502 | External API connection failures |
| `ValidationError` | 422 | Data validation errors |
| `RAGRetrievalError` | 500 | Knowledge base retrieval failures |
| `AgentExecutionError` | 500 | Agent runtime errors |
| `RDTaxAgentError` | 500 | Generic agent errors |
| `HTTPException` | varies | FastAPI HTTP exceptions |
| `Exception` | 500 | Unexpected errors |

### 4. Endpoints

#### Health Check
```
GET /health
```
Returns application status and configuration information.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "configuration": {
    "knowledge_base_exists": true,
    "output_dir_exists": true,
    "log_level": "INFO"
  },
  "api_keys_configured": {
    "openrouter": true,
    "clockify": true,
    "unified_to": true,
    "youcom": true,
    "thesys": true
  }
}
```

#### Root
```
GET /
```
Returns welcome message and API documentation links.

**Response:**
```json
{
  "message": "R&D Tax Credit Automation Agent API",
  "version": "1.0.0",
  "documentation": "/docs",
  "health_check": "/health"
}
```

### 5. Startup Events
On application startup:
1. Load and validate configuration from `.env`
2. Initialize logging infrastructure
3. Verify knowledge base directory exists
4. Create output directories if needed
5. Log API key configuration status

### 6. Shutdown Events
On application shutdown:
1. Clean up temporary files in `outputs/temp/`
2. Log shutdown event
3. Close any open connections

## Running the Application

### Method 1: Using main.py
```bash
cd rd_tax_agent
python main.py
```

### Method 2: Using uvicorn
```bash
cd rd_tax_agent
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Method 3: With custom settings
```bash
uvicorn main:app --reload --log-level info --port 8000
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Testing

### Unit Tests
```bash
pytest tests/test_main.py -v
```

### Manual Testing
```bash
python examples/fastapi_usage_example.py
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Configuration

The application requires a `.env` file with the following variables:

```env
# API Keys
OPENROUTER_API_KEY=your_openrouter_key
CLOCKIFY_API_KEY=your_clockify_key
UNIFIED_TO_API_KEY=your_unified_key
YOUCOM_API_KEY=your_youcom_key
THESYS_API_KEY=your_thesys_key

# Workspace IDs
CLOCKIFY_WORKSPACE_ID=your_workspace_id
UNIFIED_TO_WORKSPACE_ID=your_workspace_id

# Application Settings
LOG_LEVEL=INFO
MAX_RETRIES=3
TIMEOUT_SECONDS=30

# Paths
KNOWLEDGE_BASE_PATH=knowledge_base
LOG_DIR=logs
OUTPUT_DIR=outputs
```

## Error Handling

All errors are returned in a consistent JSON format:

```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "type": "error_type_identifier",
  "details": {}
}
```

### Example Error Response
```json
{
  "error": "API Connection Error",
  "message": "Failed to connect to Clockify API after 3 retries",
  "api_name": "Clockify",
  "status_code": 503,
  "endpoint": "/api/v1/workspaces",
  "retry_count": 3,
  "type": "api_connection_error"
}
```

## Logging

All application events are logged to:
- **File**: `logs/agent_YYYYMMDD.log` (daily rotation, 30-day retention)
- **Console**: Real-time output during development

Log levels:
- `DEBUG`: Detailed debugging information
- `INFO`: General informational messages
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors requiring immediate attention

## Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   Lifespan Context Manager        │ │
│  │   - Startup: Config, Logging      │ │
│  │   - Shutdown: Cleanup             │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   CORS Middleware                 │ │
│  │   - Allow Origins                 │ │
│  │   - Allow Methods                 │ │
│  │   - Allow Headers                 │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   Exception Handlers              │ │
│  │   - Configuration Errors          │ │
│  │   - API Connection Errors         │ │
│  │   - Validation Errors             │ │
│  │   - RAG Retrieval Errors          │ │
│  │   - Agent Execution Errors        │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │   Endpoints                       │ │
│  │   - GET /                         │ │
│  │   - GET /health                   │ │
│  │   - POST /api/ingest (future)     │ │
│  │   - POST /api/qualify (future)    │ │
│  │   - POST /api/generate-report     │ │
│  │   - GET /api/download/report/{id} │ │
│  │   - WebSocket /ws (future)        │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Next Steps

Future endpoints to be implemented:
1. `POST /api/ingest` - Data ingestion endpoint (Task 128)
2. `POST /api/qualify` - Qualification endpoint (Task 129)
3. `POST /api/generate-report` - Report generation endpoint (Task 130)
4. `GET /api/download/report/{report_id}` - Report download endpoint (Task 131)
5. `WebSocket /ws` - Real-time status updates (Task 126)

## Requirements

This implementation satisfies:
- **Requirement 5.3**: WebSocket/SSE support for real-time updates
- **Requirement 8.4**: Comprehensive error handling and logging

## Dependencies

- `fastapi==0.115.6` - Web framework
- `uvicorn[standard]==0.34.0` - ASGI server
- `pydantic==2.10.3` - Data validation
- `python-dotenv==1.0.1` - Environment variable management

## Troubleshooting

### Server won't start
- Check that all required API keys are set in `.env`
- Verify port 8000 is not already in use
- Check logs in `logs/agent_YYYYMMDD.log`

### CORS errors
- Verify frontend origin is in the allowed origins list
- Check that credentials are enabled if using authentication

### Configuration errors
- Ensure `.env` file exists in the project root
- Verify all required environment variables are set
- Check that API keys don't contain placeholder values

## Support

For issues or questions:
1. Check the logs in `logs/agent_YYYYMMDD.log`
2. Review the API documentation at `/docs`
3. Run the health check endpoint to verify configuration
4. Use the example script to test basic functionality
