"""
FastAPI Application for R&D Tax Credit Automation Agent

This module provides the main FastAPI application with:
- RESTful API endpoints for agent orchestration
- WebSocket support for real-time status updates
- CORS middleware for frontend communication
- Comprehensive exception handling
- Startup and shutdown event handlers

Requirements: 5.3, 8.4
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils.config import get_config, ConfigurationError
from utils.exceptions import (
    RDTaxAgentError,
    APIConnectionError,
    ValidationError,
    RAGRetrievalError,
    AgentExecutionError
)
from utils.logger import AgentLogger
from utils.websocket_manager import connection_manager

# Initialize logger
logger = AgentLogger.get_logger(__name__)


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events.
    
    Startup:
    - Load and validate configuration
    - Initialize logging
    - Verify knowledge base exists
    - Check API health (optional)
    
    Shutdown:
    - Close database connections (if any)
    - Clean up temporary files
    - Log shutdown event
    """
    # Startup
    logger.info("Starting R&D Tax Credit Automation Agent API")
    
    try:
        # Load configuration
        config = get_config()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"Knowledge base path: {config.knowledge_base_path}")
        logger.info(f"Log level: {config.log_level}")
        
        # Verify knowledge base exists
        if not config.knowledge_base_path.exists():
            logger.warning(
                f"Knowledge base directory not found at {config.knowledge_base_path}. "
                f"RAG functionality may not work correctly."
            )
        
        # Create output directories if they don't exist
        config.output_dir.mkdir(parents=True, exist_ok=True)
        (config.output_dir / "reports").mkdir(exist_ok=True)
        (config.output_dir / "temp").mkdir(exist_ok=True)
        logger.info(f"Output directories verified at {config.output_dir}")
        
        # Log API configuration status
        logger.info("API Keys configured:")
        logger.info(f"  - OpenRouter: {'✓' if config.openrouter_api_key else '✗'}")
        logger.info(f"  - Clockify: {'✓' if config.clockify_api_key else '✗'}")
        logger.info(f"  - Unified.to: {'✓' if config.unified_to_api_key else '✗'}")
        logger.info(f"  - You.com: {'✓' if config.youcom_api_key else '✗'}")
        logger.info(f"  - Thesys: {'✓' if config.thesys_api_key else '✗'}")
        
        logger.info("Application startup complete")
        
    except ConfigurationError as e:
        logger.error(f"Configuration error during startup: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during startup: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down R&D Tax Credit Automation Agent API")
    
    try:
        # Clean up temporary files
        temp_dir = get_config().output_dir / "temp"
        if temp_dir.exists():
            import shutil
            for item in temp_dir.iterdir():
                if item.is_file():
                    item.unlink()
            logger.info("Temporary files cleaned up")
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


# Initialize FastAPI application
app = FastAPI(
    title="R&D Tax Credit Automation Agent",
    description=(
        "AI-powered enterprise solution for automating R&D Tax Credit documentation. "
        "This API orchestrates three specialized agents (Data Ingestion, Qualification, "
        "and Audit Trail) to collect employee time data, determine R&D qualification "
        "using IRS guidance, and generate audit-ready PDF reports."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:5173",  # Vite development server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Exception Handlers

@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request, exc: ConfigurationError):
    """
    Handle configuration errors.
    
    Returns 500 Internal Server Error with configuration guidance.
    """
    logger.error(f"Configuration error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Configuration Error",
            "message": str(exc),
            "details": "Please check your .env file and ensure all required API keys are set.",
            "type": "configuration_error"
        }
    )


@app.exception_handler(APIConnectionError)
async def api_connection_error_handler(request, exc: APIConnectionError):
    """
    Handle external API connection errors.
    
    Returns 502 Bad Gateway for upstream service failures.
    """
    logger.error(
        f"API connection error: {exc.message} | "
        f"API: {exc.api_name} | Status: {exc.status_code} | "
        f"Endpoint: {exc.endpoint} | Retries: {exc.retry_count}"
    )
    return JSONResponse(
        status_code=502,
        content={
            "error": "API Connection Error",
            "message": exc.message,
            "api_name": exc.api_name,
            "status_code": exc.status_code,
            "endpoint": exc.endpoint,
            "retry_count": exc.retry_count,
            "type": "api_connection_error"
        }
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """
    Handle data validation errors.
    
    Returns 422 Unprocessable Entity for invalid input data.
    """
    logger.warning(
        f"Validation error: {exc.message} | "
        f"Field: {exc.field_name} | Value: {exc.invalid_value}"
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": exc.message,
            "field_name": exc.field_name,
            "invalid_value": str(exc.invalid_value) if exc.invalid_value is not None else None,
            "validation_rule": exc.validation_rule,
            "type": "validation_error"
        }
    )


@app.exception_handler(RAGRetrievalError)
async def rag_retrieval_error_handler(request, exc: RAGRetrievalError):
    """
    Handle RAG knowledge base retrieval errors.
    
    Returns 500 Internal Server Error for RAG system failures.
    """
    logger.error(
        f"RAG retrieval error: {exc.message} | "
        f"Query: {exc.query} | KB Path: {exc.knowledge_base_path}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "RAG Retrieval Error",
            "message": exc.message,
            "query": exc.query,
            "knowledge_base_path": exc.knowledge_base_path,
            "error_type": exc.error_type,
            "type": "rag_retrieval_error"
        }
    )


@app.exception_handler(AgentExecutionError)
async def agent_execution_error_handler(request, exc: AgentExecutionError):
    """
    Handle agent runtime execution errors.
    
    Returns 500 Internal Server Error for agent failures.
    """
    logger.error(
        f"Agent execution error: {exc.message} | "
        f"Agent: {exc.agent_name} | Stage: {exc.stage} | Tool: {exc.tool_name}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Agent Execution Error",
            "message": exc.message,
            "agent_name": exc.agent_name,
            "stage": exc.stage,
            "tool_name": exc.tool_name,
            "state": exc.state,
            "type": "agent_execution_error"
        }
    )


@app.exception_handler(RDTaxAgentError)
async def generic_agent_error_handler(request, exc: RDTaxAgentError):
    """
    Handle generic agent errors not caught by specific handlers.
    
    Returns 500 Internal Server Error.
    """
    logger.error(f"Agent error: {exc.message} | Details: {exc.details}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Agent Error",
            "message": exc.message,
            "details": exc.details,
            "type": "agent_error"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """
    Handle FastAPI HTTP exceptions.
    
    Returns the appropriate HTTP status code with error details.
    """
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "type": "http_error"
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    """
    Handle unexpected exceptions.
    
    Returns 500 Internal Server Error for unhandled exceptions.
    """
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please check the server logs.",
            "type": "internal_error"
        }
    )


# Health Check Endpoint

@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns application status and configuration information.
    
    Returns:
        dict: Health status information
    """
    try:
        config = get_config()
        
        return {
            "status": "healthy",
            "version": "1.0.0",
            "configuration": {
                "knowledge_base_exists": config.knowledge_base_path.exists(),
                "output_dir_exists": config.output_dir.exists(),
                "log_level": config.log_level,
            },
            "api_keys_configured": {
                "openrouter": bool(config.openrouter_api_key),
                "clockify": bool(config.clockify_api_key),
                "unified_to": bool(config.unified_to_api_key),
                "youcom": bool(config.youcom_api_key),
                "thesys": bool(config.thesys_api_key),
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Root Endpoint

@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """
    Root endpoint.
    
    Returns welcome message and API documentation links.
    """
    return {
        "message": "R&D Tax Credit Automation Agent API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/health"
    }


# API Endpoints

from pydantic import BaseModel as PydanticBaseModel, Field, validator
from agents.data_ingestion_agent import DataIngestionAgent
from tools.api_connectors import ClockifyConnector, UnifiedToConnector
from utils.status_broadcaster import send_status_update
from models.websocket_models import AgentStage, AgentStatus


class DataIngestionRequest(PydanticBaseModel):
    """
    Request model for data ingestion endpoint.
    
    Attributes:
        start_date: Start date for data collection (ISO 8601 format)
        end_date: End date for data collection (ISO 8601 format)
        clockify_api_key: Optional Clockify API key (overrides env var)
        clockify_workspace_id: Optional Clockify workspace ID (overrides env var)
        unified_to_api_key: Optional Unified.to API key (overrides env var)
        unified_to_workspace_id: Optional Unified.to workspace ID (overrides env var)
        connection_id: Optional Unified.to connection ID for HRIS system
    """
    
    start_date: str = Field(
        ...,
        description="Start date for data collection (ISO 8601 format: YYYY-MM-DD)",
        example="2024-01-01"
    )
    
    end_date: str = Field(
        ...,
        description="End date for data collection (ISO 8601 format: YYYY-MM-DD)",
        example="2024-01-31"
    )
    
    clockify_api_key: Optional[str] = Field(
        None,
        description="Optional Clockify API key (overrides environment variable)"
    )
    
    clockify_workspace_id: Optional[str] = Field(
        None,
        description="Optional Clockify workspace ID (overrides environment variable)"
    )
    
    unified_to_api_key: Optional[str] = Field(
        None,
        description="Optional Unified.to API key (overrides environment variable)"
    )
    
    unified_to_workspace_id: Optional[str] = Field(
        None,
        description="Optional Unified.to workspace ID (overrides environment variable)"
    )
    
    connection_id: Optional[str] = Field(
        None,
        description="Optional Unified.to connection ID for specific HRIS system"
    )
    
    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate date format is ISO 8601 (YYYY-MM-DD)."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(
                f"Invalid date format: {v}. Expected ISO 8601 format (YYYY-MM-DD)"
            )


class DataIngestionResponse(PydanticBaseModel):
    """
    Response model for data ingestion endpoint.
    
    Attributes:
        success: Whether ingestion completed successfully
        time_entries: List of ingested time entries
        costs: List of ingested costs
        validation_errors: List of validation error messages
        deduplication_count: Number of duplicate entries removed
        execution_time_seconds: Total execution time
        summary: Human-readable summary
    """
    
    success: bool = Field(
        ...,
        description="Whether ingestion completed successfully"
    )
    
    time_entries: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of ingested time entries"
    )
    
    costs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of ingested costs"
    )
    
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation error messages"
    )
    
    deduplication_count: int = Field(
        default=0,
        description="Number of duplicate entries removed"
    )
    
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total execution time in seconds"
    )
    
    summary: str = Field(
        default="",
        description="Human-readable summary of ingestion results"
    )


@app.post("/api/ingest", tags=["Data Ingestion"], response_model=DataIngestionResponse)
async def ingest_data(request: DataIngestionRequest) -> DataIngestionResponse:
    """
    Data ingestion endpoint.
    
    Collects employee time tracking data from Clockify and payroll/HRIS data
    from Unified.to for the specified date range. Validates, deduplicates, and
    performs quality checks on all ingested data.
    
    The endpoint sends real-time status updates via WebSocket to connected clients,
    allowing the frontend to visualize the ingestion progress.
    
    Args:
        request: DataIngestionRequest with date range and optional API credentials
        
    Returns:
        DataIngestionResponse with ingested data and metadata
        
    Raises:
        HTTPException 400: If request parameters are invalid
        HTTPException 500: If configuration is missing or ingestion fails
        HTTPException 502: If external API connection fails
        
    Example Request:
        POST /api/ingest
        {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "connection_id": "conn_123"
        }
        
    Example Response:
        {
            "success": true,
            "time_entries": [...],
            "costs": [...],
            "validation_errors": [],
            "deduplication_count": 5,
            "execution_time_seconds": 12.5,
            "summary": "Successfully ingested 1,234 time entries..."
        }
        
    Requirements: 1.5, 5.2
    """
    logger.info(
        f"Received data ingestion request: {request.start_date} to {request.end_date}"
    )
    
    try:
        # Parse dates
        try:
            start_date = datetime.fromisoformat(request.start_date)
            end_date = datetime.fromisoformat(request.end_date)
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {e}"
            )
        
        # Validate date range
        if start_date > end_date:
            logger.error("start_date must be before or equal to end_date")
            raise HTTPException(
                status_code=400,
                detail="start_date must be before or equal to end_date"
            )
        
        # Get configuration
        config = get_config()
        
        # Use provided API keys or fall back to config
        clockify_api_key = request.clockify_api_key or config.clockify_api_key
        clockify_workspace_id = request.clockify_workspace_id or config.clockify_workspace_id
        unified_to_api_key = request.unified_to_api_key or config.unified_to_api_key
        unified_to_workspace_id = request.unified_to_workspace_id or config.unified_to_workspace_id
        
        # Validate required credentials
        if not clockify_api_key:
            logger.error("Clockify API key not provided")
            raise HTTPException(
                status_code=500,
                detail="Clockify API key not configured. Please set CLOCKIFY_API_KEY in environment or provide in request."
            )
        
        if not clockify_workspace_id:
            logger.error("Clockify workspace ID not provided")
            raise HTTPException(
                status_code=500,
                detail="Clockify workspace ID not configured. Please set CLOCKIFY_WORKSPACE_ID in environment or provide in request."
            )
        
        if not unified_to_api_key:
            logger.error("Unified.to API key not provided")
            raise HTTPException(
                status_code=500,
                detail="Unified.to API key not configured. Please set UNIFIED_TO_API_KEY in environment or provide in request."
            )
        
        if not unified_to_workspace_id:
            logger.error("Unified.to workspace ID not provided")
            raise HTTPException(
                status_code=500,
                detail="Unified.to workspace ID not configured. Please set UNIFIED_TO_WORKSPACE_ID in environment or provide in request."
            )
        
        # Send initial status update
        await send_status_update(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.IN_PROGRESS,
            details=f"Starting data ingestion for {request.start_date} to {request.end_date}"
        )
        
        # Initialize API connectors
        logger.info("Initializing API connectors...")
        
        clockify_connector = ClockifyConnector(
            api_key=clockify_api_key,
            workspace_id=clockify_workspace_id
        )
        
        unified_to_connector = UnifiedToConnector(
            api_key=unified_to_api_key,
            workspace_id=unified_to_workspace_id
        )
        
        # Define status callback for real-time updates
        # Note: The agent calls this synchronously, so we need to handle async send_status_update
        # by creating a task in the event loop
        import asyncio
        
        def status_callback(status_message):
            """Callback to send status updates during agent execution."""
            try:
                # Get the current event loop and create a task for the async send_status_update
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a task
                    asyncio.create_task(send_status_update(
                        stage=status_message.stage,
                        status=status_message.status,
                        details=status_message.details
                    ))
                else:
                    # If loop is not running, run it synchronously (shouldn't happen in FastAPI)
                    loop.run_until_complete(send_status_update(
                        stage=status_message.stage,
                        status=status_message.status,
                        details=status_message.details
                    ))
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")
        
        # Initialize Data Ingestion Agent
        logger.info("Initializing Data Ingestion Agent...")
        
        agent = DataIngestionAgent(
            clockify_connector=clockify_connector,
            unified_to_connector=unified_to_connector,
            status_callback=status_callback
        )
        
        # Run data ingestion
        logger.info("Running data ingestion...")
        
        result = agent.run(
            start_date=start_date,
            end_date=end_date,
            connection_id=request.connection_id
        )
        
        # Send completion status update
        await send_status_update(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.COMPLETED,
            details=result.summary
        )
        
        # Convert Pydantic models to dictionaries for JSON response
        time_entries_dict = [entry.model_dump() for entry in result.time_entries]
        costs_dict = [cost.model_dump() for cost in result.costs]
        
        # Build response
        response = DataIngestionResponse(
            success=True,
            time_entries=time_entries_dict,
            costs=costs_dict,
            validation_errors=result.validation_errors,
            deduplication_count=result.deduplication_count,
            execution_time_seconds=result.execution_time_seconds,
            summary=result.summary
        )
        
        logger.info(
            f"Data ingestion completed successfully: "
            f"{len(result.time_entries)} time entries, "
            f"{len(result.costs)} costs"
        )
        
        return response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except APIConnectionError as e:
        # Handle API connection errors
        error_msg = f"API connection failed: {e.message}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=502,
            detail=error_msg
        )
    
    except ConfigurationError as e:
        # Handle configuration errors
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
    
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error during data ingestion: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        await send_status_update(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


class QualificationRequest(PydanticBaseModel):
    """
    Request model for qualification endpoint.
    
    Attributes:
        time_entries: List of time entry dictionaries (from ingestion)
        costs: List of cost dictionaries (from ingestion)
        tax_year: Optional tax year for checking recent IRS guidance
    """
    
    time_entries: List[Dict[str, Any]] = Field(
        ...,
        description="List of time entry dictionaries with user classifications"
    )
    
    costs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of cost dictionaries with user classifications"
    )
    
    tax_year: Optional[int] = Field(
        None,
        description="Optional tax year for checking recent IRS guidance (e.g., 2024)",
        example=2024
    )
    
    @validator('tax_year')
    def validate_tax_year(cls, v):
        """Validate tax year is reasonable."""
        if v is not None:
            current_year = datetime.now().year
            if v < 2000 or v > current_year + 1:
                raise ValueError(
                    f"Tax year must be between 2000 and {current_year + 1}"
                )
        return v


class QualificationResponse(PydanticBaseModel):
    """
    Response model for qualification endpoint.
    
    Attributes:
        success: Whether qualification completed successfully
        qualified_projects: List of qualified project dictionaries
        total_qualified_hours: Sum of all qualified hours
        total_qualified_cost: Sum of all qualified costs
        estimated_credit: Estimated tax credit (20% of qualified costs)
        average_confidence: Average confidence score across all projects
        flagged_projects: List of project names flagged for review
        execution_time_seconds: Total execution time
        summary: Human-readable summary
    """
    
    success: bool = Field(
        ...,
        description="Whether qualification completed successfully"
    )
    
    qualified_projects: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of qualified project dictionaries"
    )
    
    total_qualified_hours: float = Field(
        default=0.0,
        description="Sum of all qualified hours"
    )
    
    total_qualified_cost: float = Field(
        default=0.0,
        description="Sum of all qualified costs"
    )
    
    estimated_credit: float = Field(
        default=0.0,
        description="Estimated tax credit (20% of qualified costs)"
    )
    
    average_confidence: float = Field(
        default=0.0,
        description="Average confidence score across all projects"
    )
    
    flagged_projects: List[str] = Field(
        default_factory=list,
        description="List of project names flagged for review"
    )
    
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total execution time in seconds"
    )
    
    summary: str = Field(
        default="",
        description="Human-readable summary of qualification results"
    )


@app.post("/api/qualify", tags=["Qualification"], response_model=QualificationResponse)
async def qualify_projects(request: QualificationRequest) -> QualificationResponse:
    """
    Qualification endpoint.
    
    Determines which projects and costs qualify for R&D tax credits using:
    - RAG system (local IRS documents) for authoritative guidance
    - You.com Agent API for expert reasoning and qualification decisions
    - GLM 4.5 Air via OpenRouter for RAG inference
    - Recent IRS guidance checks via You.com Search API
    
    The endpoint sends real-time status updates via WebSocket to connected clients,
    allowing the frontend to visualize the qualification progress.
    
    Args:
        request: QualificationRequest with ingested data and user classifications
        
    Returns:
        QualificationResponse with qualified projects and metadata
        
    Raises:
        HTTPException 400: If request parameters are invalid
        HTTPException 500: If configuration is missing or qualification fails
        HTTPException 502: If external API connection fails
        
    Example Request:
        POST /api/qualify
        {
            "time_entries": [
                {
                    "employee_id": "EMP001",
                    "employee_name": "John Doe",
                    "project_name": "API Optimization",
                    "task_description": "Implemented caching layer",
                    "hours_spent": 8.5,
                    "date": "2024-01-15T00:00:00",
                    "is_rd_classified": true
                }
            ],
            "costs": [
                {
                    "cost_id": "COST001",
                    "cost_type": "Payroll",
                    "amount": 1500.00,
                    "project_name": "API Optimization",
                    "employee_id": "EMP001",
                    "date": "2024-01-15T00:00:00",
                    "is_rd_classified": true
                }
            ],
            "tax_year": 2024
        }
        
    Example Response:
        {
            "success": true,
            "qualified_projects": [...],
            "total_qualified_hours": 120.5,
            "total_qualified_cost": 15000.00,
            "estimated_credit": 3000.00,
            "average_confidence": 0.85,
            "flagged_projects": [],
            "execution_time_seconds": 45.2,
            "summary": "Successfully qualified 5 projects..."
        }
        
    Requirements: 3.5, 5.2
    """
    logger.info(
        f"Received qualification request: {len(request.time_entries)} time entries, "
        f"{len(request.costs)} costs"
    )
    
    try:
        # Validate request data
        if not request.time_entries:
            logger.error("time_entries cannot be empty")
            raise HTTPException(
                status_code=400,
                detail="time_entries cannot be empty"
            )
        
        # Get configuration
        config = get_config()
        
        # Validate required API keys
        if not config.openrouter_api_key:
            logger.error("OpenRouter API key not configured")
            raise HTTPException(
                status_code=500,
                detail="OpenRouter API key not configured. Please set OPENROUTER_API_KEY in environment."
            )
        
        if not config.youcom_api_key:
            logger.error("You.com API key not configured")
            raise HTTPException(
                status_code=500,
                detail="You.com API key not configured. Please set YOUCOM_API_KEY in environment."
            )
        
        # Validate knowledge base exists
        if not config.knowledge_base_path.exists():
            logger.error(f"Knowledge base not found at {config.knowledge_base_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Knowledge base not found at {config.knowledge_base_path}. Please run indexing pipeline first."
            )
        
        # Send initial status update
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.IN_PROGRESS,
            details="Starting R&D qualification process"
        )
        
        # Parse time entries and costs from dictionaries to Pydantic models
        logger.info("Parsing time entries and costs...")
        
        from models.financial_models import EmployeeTimeEntry, ProjectCost
        
        try:
            time_entries = [
                EmployeeTimeEntry(**entry) for entry in request.time_entries
            ]
            logger.info(f"Parsed {len(time_entries)} time entries")
        except Exception as e:
            logger.error(f"Failed to parse time entries: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time entry data: {str(e)}"
            )
        
        try:
            costs = [
                ProjectCost(**cost) for cost in request.costs
            ]
            logger.info(f"Parsed {len(costs)} costs")
        except Exception as e:
            logger.error(f"Failed to parse costs: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cost data: {str(e)}"
            )
        
        # Initialize tools
        logger.info("Initializing qualification tools...")
        
        from tools.rd_knowledge_tool import RD_Knowledge_Tool
        from tools.you_com_client import YouComClient
        from tools.glm_reasoner import GLMReasoner
        from agents.qualification_agent import QualificationAgent
        
        # Initialize RAG tool
        rag_tool = RD_Knowledge_Tool(
            knowledge_base_path=str(config.knowledge_base_path)
        )
        logger.info("RAG tool initialized")
        
        # Initialize You.com client
        youcom_client = YouComClient(
            api_key=config.youcom_api_key
        )
        logger.info("You.com client initialized")
        
        # Initialize GLM reasoner
        glm_reasoner = GLMReasoner(
            api_key=config.openrouter_api_key
        )
        logger.info("GLM reasoner initialized")
        
        # Define status callback for real-time updates
        import asyncio
        
        def status_callback(status_message):
            """Callback to send status updates during agent execution."""
            try:
                # Get the current event loop and create a task for the async send_status_update
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a task
                    asyncio.create_task(send_status_update(
                        stage=status_message.stage,
                        status=status_message.status,
                        details=status_message.details
                    ))
                else:
                    # If loop is not running, run it synchronously (shouldn't happen in FastAPI)
                    loop.run_until_complete(send_status_update(
                        stage=status_message.stage,
                        status=status_message.status,
                        details=status_message.details
                    ))
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")
        
        # Initialize Qualification Agent
        logger.info("Initializing Qualification Agent...")
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            status_callback=status_callback
        )
        
        # Run qualification
        logger.info("Running qualification...")
        
        result = agent.run(
            time_entries=time_entries,
            costs=costs,
            tax_year=request.tax_year
        )
        
        # Send completion status update
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.COMPLETED,
            details=result.summary
        )
        
        # Convert Pydantic models to dictionaries for JSON response
        qualified_projects_dict = [
            project.model_dump() for project in result.qualified_projects
        ]
        
        # Build response
        response = QualificationResponse(
            success=True,
            qualified_projects=qualified_projects_dict,
            total_qualified_hours=result.total_qualified_hours,
            total_qualified_cost=result.total_qualified_cost,
            estimated_credit=result.estimated_credit,
            average_confidence=result.average_confidence,
            flagged_projects=result.flagged_projects,
            execution_time_seconds=result.execution_time_seconds,
            summary=result.summary
        )
        
        logger.info(
            f"Qualification completed successfully: "
            f"{len(result.qualified_projects)} projects qualified, "
            f"estimated credit: ${result.estimated_credit:,.2f}"
        )
        
        return response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except RAGRetrievalError as e:
        # Handle RAG retrieval errors
        error_msg = f"RAG retrieval failed: {str(e)}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
    
    except APIConnectionError as e:
        # Handle API connection errors
        error_msg = f"API connection failed: {e.message}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=502,
            detail=error_msg
        )
    
    except ConfigurationError as e:
        # Handle configuration errors
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
    
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error during qualification: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


class ReportGenerationRequest(PydanticBaseModel):
    """
    Request model for report generation endpoint.
    
    Attributes:
        qualified_projects: List of qualified project dictionaries (from qualification)
        tax_year: Tax year for the report
        company_name: Optional company name for report header
    """
    
    qualified_projects: List[Dict[str, Any]] = Field(
        ...,
        description="List of qualified project dictionaries from qualification endpoint"
    )
    
    tax_year: int = Field(
        ...,
        description="Tax year for the report (e.g., 2024)",
        example=2024
    )
    
    company_name: Optional[str] = Field(
        None,
        description="Optional company name for report header",
        example="Acme Corporation"
    )
    
    @validator('tax_year')
    def validate_tax_year(cls, v):
        """Validate tax year is reasonable."""
        current_year = datetime.now().year
        if v < 2000 or v > current_year + 1:
            raise ValueError(
                f"Tax year must be between 2000 and {current_year + 1}"
            )
        return v


class ReportGenerationResponse(PydanticBaseModel):
    """
    Response model for report generation endpoint.
    
    Attributes:
        success: Whether report generation completed successfully
        report_id: Unique identifier for the generated report
        pdf_path: Path to generated PDF file (relative to outputs directory)
        report_metadata: Metadata about the generated report
        execution_time_seconds: Total execution time
        summary: Human-readable summary
    """
    
    success: bool = Field(
        ...,
        description="Whether report generation completed successfully"
    )
    
    report_id: str = Field(
        ...,
        description="Unique identifier for the generated report"
    )
    
    pdf_path: str = Field(
        ...,
        description="Path to generated PDF file (relative to outputs directory)"
    )
    
    report_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the generated report"
    )
    
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total execution time in seconds"
    )
    
    summary: str = Field(
        default="",
        description="Human-readable summary of report generation"
    )


@app.post("/api/generate-report", tags=["Report Generation"], response_model=ReportGenerationResponse)
async def generate_report(request: ReportGenerationRequest) -> ReportGenerationResponse:
    """
    Report generation endpoint.
    
    Generates comprehensive audit-ready PDF documentation for qualified R&D projects using:
    - You.com Agent API for technical narrative generation
    - You.com Express Agent for compliance review
    - GLM 4.5 Air via OpenRouter for agent reasoning
    - PDFGenerator for professional report creation
    
    The endpoint sends real-time status updates via WebSocket to connected clients,
    allowing the frontend to visualize the report generation progress.
    
    Args:
        request: ReportGenerationRequest with qualified projects and metadata
        
    Returns:
        ReportGenerationResponse with report metadata and file path
        
    Raises:
        HTTPException 400: If request parameters are invalid
        HTTPException 500: If configuration is missing or generation fails
        HTTPException 502: If external API connection fails
        
    Example Request:
        POST /api/generate-report
        {
            "qualified_projects": [
                {
                    "project_name": "API Optimization",
                    "qualified_hours": 120.5,
                    "qualified_cost": 15000.00,
                    "confidence_score": 0.85,
                    "qualification_percentage": 80.0,
                    "supporting_citation": "CFR Title 26 § 1.41-4(a)(1)",
                    "reasoning": "Project involves systematic experimentation...",
                    "irs_source": "CFR Title 26 § 1.41-4",
                    "flagged_for_review": false
                }
            ],
            "tax_year": 2024,
            "company_name": "Acme Corporation"
        }
        
    Example Response:
        {
            "success": true,
            "report_id": "report_20240115_123456",
            "pdf_path": "reports/report_20240115_123456.pdf",
            "report_metadata": {
                "generation_date": "2024-01-15T12:34:56",
                "tax_year": 2024,
                "total_qualified_hours": 120.5,
                "total_qualified_cost": 15000.00,
                "estimated_credit": 3000.00,
                "project_count": 1
            },
            "execution_time_seconds": 45.8,
            "summary": "Successfully generated audit report for 1 project..."
        }
        
    Requirements: 4.5, 5.2
    """
    logger.info(
        f"Received report generation request: {len(request.qualified_projects)} projects, "
        f"tax year: {request.tax_year}"
    )
    
    try:
        # Validate request data
        if not request.qualified_projects:
            logger.error("qualified_projects cannot be empty")
            raise HTTPException(
                status_code=400,
                detail="qualified_projects cannot be empty"
            )
        
        # Get configuration
        config = get_config()
        
        # Validate required API keys
        if not config.openrouter_api_key:
            logger.error("OpenRouter API key not configured")
            raise HTTPException(
                status_code=500,
                detail="OpenRouter API key not configured. Please set OPENROUTER_API_KEY in environment."
            )
        
        if not config.youcom_api_key:
            logger.error("You.com API key not configured")
            raise HTTPException(
                status_code=500,
                detail="You.com API key not configured. Please set YOUCOM_API_KEY in environment."
            )
        
        # Send initial status update
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.IN_PROGRESS,
            details="Starting audit report generation"
        )
        
        # Parse qualified projects from dictionaries to Pydantic models
        logger.info("Parsing qualified projects...")
        
        from models.tax_models import QualifiedProject
        
        try:
            qualified_projects = [
                QualifiedProject(**project) for project in request.qualified_projects
            ]
            logger.info(f"Parsed {len(qualified_projects)} qualified projects")
        except Exception as e:
            logger.error(f"Failed to parse qualified projects: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid qualified project data: {str(e)}"
            )
        
        # Initialize tools
        logger.info("Initializing audit trail tools...")
        
        from tools.you_com_client import YouComClient
        from tools.glm_reasoner import GLMReasoner
        from agents.audit_trail_agent import AuditTrailAgent
        
        # Initialize You.com client
        youcom_client = YouComClient(
            api_key=config.youcom_api_key
        )
        logger.info("You.com client initialized")
        
        # Initialize GLM reasoner
        glm_reasoner = GLMReasoner(
            api_key=config.openrouter_api_key
        )
        logger.info("GLM reasoner initialized")
        
        # Define status callback for real-time updates
        import asyncio
        
        def status_callback(status_message):
            """Callback to send status updates during agent execution."""
            try:
                # Get the current event loop and create a task for the async send_status_update
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a task
                    asyncio.create_task(send_status_update(
                        stage=status_message.stage,
                        status=status_message.status,
                        details=status_message.details
                    ))
                else:
                    # If loop is not running, run it synchronously (shouldn't happen in FastAPI)
                    loop.run_until_complete(send_status_update(
                        stage=status_message.stage,
                        status=status_message.status,
                        details=status_message.details
                    ))
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")
        
        # Initialize PDF Generator
        from utils.pdf_generator import PDFGenerator
        
        pdf_generator = PDFGenerator()
        logger.info("PDF generator initialized")
        
        # Initialize Audit Trail Agent
        logger.info("Initializing Audit Trail Agent...")
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            pdf_generator=pdf_generator,
            status_callback=status_callback
        )
        
        # Run report generation
        logger.info("Running report generation...")
        
        result = agent.run(
            qualified_projects=qualified_projects,
            tax_year=request.tax_year,
            company_name=request.company_name
        )
        
        # Send completion status update
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.COMPLETED,
            details=result.summary
        )
        
        # Generate report ID from PDF path or create one
        if result.pdf_path:
            # Extract filename from path
            import os
            report_id = os.path.splitext(os.path.basename(result.pdf_path))[0]
        else:
            # Generate report ID if PDF path not available
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build report metadata
        report_metadata = {}
        if result.report:
            report_metadata = {
                "generation_date": result.report.generation_date.isoformat() if result.report.generation_date else None,
                "tax_year": result.report.tax_year,
                "total_qualified_hours": result.report.total_qualified_hours,
                "total_qualified_cost": result.report.total_qualified_cost,
                "estimated_credit": result.report.estimated_credit,
                "project_count": len(result.report.projects)
            }
        
        # Build response
        response = ReportGenerationResponse(
            success=True,
            report_id=report_id,
            pdf_path=result.pdf_path or "",
            report_metadata=report_metadata,
            execution_time_seconds=result.execution_time_seconds,
            summary=result.summary
        )
        
        logger.info(
            f"Report generation completed successfully: "
            f"report_id={report_id}, "
            f"pdf_path={result.pdf_path}"
        )
        
        return response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except APIConnectionError as e:
        # Handle API connection errors
        error_msg = f"API connection failed: {e.message}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=502,
            detail=error_msg
        )
    
    except ConfigurationError as e:
        # Handle configuration errors
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
    
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error during report generation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


# Report Download Endpoint

from fastapi.responses import FileResponse
from pathlib import Path


@app.get("/api/download/report/{report_id}", tags=["Report Download"])
async def download_report(report_id: str) -> FileResponse:
    """
    Report download endpoint.
    
    Downloads a generated PDF report by its unique report ID. The endpoint locates
    the PDF file in the outputs/reports/ directory and returns it as a streaming
    file response with appropriate headers for browser download.
    
    Args:
        report_id: Unique identifier for the report (e.g., "report_20240115_123456")
        
    Returns:
        FileResponse: Streaming PDF file response
        
    Raises:
        HTTPException 400: If report_id is invalid or empty
        HTTPException 404: If report file not found
        HTTPException 500: If file access error occurs
        
    Example Request:
        GET /api/download/report/report_20240115_123456
        
    Example Response:
        Content-Type: application/pdf
        Content-Disposition: attachment; filename="report_20240115_123456.pdf"
        [PDF file content]
        
    Requirements: 4.5
    """
    logger.info(f"Received report download request: report_id={report_id}")
    
    try:
        # Validate report_id parameter
        if not report_id or not report_id.strip():
            logger.error("report_id parameter is empty")
            raise HTTPException(
                status_code=400,
                detail="report_id parameter cannot be empty"
            )
        
        # Sanitize report_id to prevent path traversal attacks
        # Remove any path separators and parent directory references
        sanitized_report_id = report_id.replace('/', '').replace('\\', '').replace('..', '')
        
        if sanitized_report_id != report_id:
            logger.warning(
                f"Potentially malicious report_id detected: {report_id}. "
                f"Sanitized to: {sanitized_report_id}"
            )
        
        # Get configuration
        config = get_config()
        
        # Construct path to reports directory
        reports_dir = config.output_dir / "reports"
        
        # Try to locate the PDF file
        # The report_id might be just the ID or might include the full filename
        pdf_path = None
        
        # Case 1: report_id is the exact filename (with .pdf extension)
        if sanitized_report_id.endswith('.pdf'):
            potential_path = reports_dir / sanitized_report_id
            if potential_path.exists() and potential_path.is_file():
                pdf_path = potential_path
        
        # Case 2: report_id is the ID without extension
        if pdf_path is None:
            potential_path = reports_dir / f"{sanitized_report_id}.pdf"
            if potential_path.exists() and potential_path.is_file():
                pdf_path = potential_path
        
        # Case 3: Search for files matching the report_id pattern
        # This handles cases where the filename includes additional suffixes
        if pdf_path is None:
            # Search in reports directory and subdirectories
            for file_path in reports_dir.rglob(f"*{sanitized_report_id}*.pdf"):
                if file_path.is_file():
                    pdf_path = file_path
                    logger.info(f"Found matching report file: {file_path}")
                    break
        
        # If still not found, raise 404
        if pdf_path is None:
            logger.error(f"Report file not found for report_id: {report_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Report not found: {report_id}. Please verify the report ID and try again."
            )
        
        # Verify the file is within the reports directory (security check)
        try:
            pdf_path_resolved = pdf_path.resolve()
            reports_dir_resolved = reports_dir.resolve()
            
            if not str(pdf_path_resolved).startswith(str(reports_dir_resolved)):
                logger.error(
                    f"Security violation: Attempted to access file outside reports directory. "
                    f"Path: {pdf_path_resolved}"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Invalid file path"
                )
        except Exception as e:
            logger.error(f"Error resolving file path: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error accessing report file"
            )
        
        # Verify file is readable
        if not pdf_path.exists():
            logger.error(f"Report file does not exist: {pdf_path}")
            raise HTTPException(
                status_code=404,
                detail=f"Report file not found: {report_id}"
            )
        
        if not pdf_path.is_file():
            logger.error(f"Report path is not a file: {pdf_path}")
            raise HTTPException(
                status_code=500,
                detail="Invalid report file"
            )
        
        # Get file size for logging
        file_size = pdf_path.stat().st_size
        logger.info(
            f"Serving report file: {pdf_path.name} "
            f"(size: {file_size:,} bytes)"
        )
        
        # Return file as streaming response
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=pdf_path.name,
            headers={
                "Content-Disposition": f'attachment; filename="{pdf_path.name}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error during report download: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


# Report List Endpoint

@app.get("/api/reports/list", tags=["Reports"])
async def list_reports() -> Dict[str, Any]:
    """
    List all available PDF reports.
    
    Scans the outputs/reports/ directory and returns metadata for all PDF files.
    Includes file size, modification date, and parsed metadata from filenames.
    
    Returns:
        dict: List of report metadata
        
    Example Response:
        {
            "reports": [
                {
                    "id": "2024_20251030_143000",
                    "filename": "rd_tax_credit_report_2024_20251030_143000.pdf",
                    "fileSize": 87654,
                    "generationDate": "2024-10-30T14:30:00",
                    "taxYear": 2024,
                    "companyName": "Acme Corporation",
                    "status": "complete"
                }
            ],
            "total": 1
        }
        
    Requirements: 4.5, 5.4
    """
    logger.info("Received request to list all reports")
    
    try:
        config = get_config()
        reports_dir = config.output_dir / "reports"
        
        if not reports_dir.exists():
            logger.warning(f"Reports directory does not exist: {reports_dir}")
            return {
                "reports": [],
                "total": 0
            }
        
        reports = []
        
        # Scan for PDF files in reports directory and subdirectories
        for pdf_path in reports_dir.rglob("*.pdf"):
            if not pdf_path.is_file():
                continue
            
            try:
                # Get file stats
                file_stats = pdf_path.stat()
                file_size = file_stats.st_size
                modification_time = datetime.fromtimestamp(file_stats.st_mtime)
                
                # Parse filename to extract metadata
                filename = pdf_path.name
                report_id = filename.replace('.pdf', '')
                
                # Try to parse standard format: rd_tax_credit_report_{tax_year}_{timestamp}
                tax_year = None
                generation_date = modification_time.isoformat()
                
                # Pattern 1: rd_tax_credit_report_{tax_year}_{YYYYMMDD}_{HHMMSS}.pdf
                import re
                match = re.match(r'rd_tax_credit_report_(\d{4})_(\d{8})_(\d{6})\.pdf', filename)
                if match:
                    tax_year = int(match.group(1))
                    date_str = match.group(2)
                    time_str = match.group(3)
                    
                    year = date_str[0:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    hour = time_str[0:2]
                    minute = time_str[2:4]
                    second = time_str[4:6]
                    
                    generation_date = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
                    report_id = f"{tax_year}_{date_str}_{time_str}"
                
                # Pattern 2: rd_tax_credit_report_{custom_id}_{YYYYMMDD}_{HHMMSS}.pdf
                else:
                    match = re.match(r'rd_tax_credit_report_(.+?)_(\d{8})_(\d{6})\.pdf', filename)
                    if match:
                        custom_id = match.group(1)
                        date_str = match.group(2)
                        time_str = match.group(3)
                        
                        year = date_str[0:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        hour = time_str[0:2]
                        minute = time_str[2:4]
                        second = time_str[4:6]
                        
                        generation_date = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
                        report_id = custom_id
                        tax_year = int(year)
                
                # Default values if parsing fails
                if tax_year is None:
                    tax_year = datetime.now().year
                
                reports.append({
                    "id": report_id,
                    "filename": filename,
                    "fileSize": file_size,
                    "generationDate": generation_date,
                    "taxYear": tax_year,
                    "companyName": "Acme Corporation",  # Default, could be enhanced
                    "totalQualifiedHours": 320.0,  # Default values
                    "totalQualifiedCost": 23040.00,
                    "estimatedCredit": 4608.00,
                    "projectCount": 10,
                    "pageCount": 12,  # Default, could be calculated from PDF
                    "status": "complete"
                })
                
            except Exception as e:
                logger.error(f"Error processing report file {pdf_path}: {e}")
                continue
        
        # Sort by generation date (newest first)
        reports.sort(key=lambda r: r["generationDate"], reverse=True)
        
        logger.info(f"Found {len(reports)} reports")
        
        return {
            "reports": reports,
            "total": len(reports)
        }
    
    except Exception as e:
        error_msg = f"Error listing reports: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


# Complete Pipeline Endpoint

class CompletePipelineRequest(PydanticBaseModel):
    """
    Request model for complete pipeline endpoint.
    
    Attributes:
        use_sample_data: Whether to use sample data from fixtures (default: True)
        tax_year: Tax year for the report
        company_name: Optional company name for report header
    """
    
    use_sample_data: bool = Field(
        default=True,
        description="Whether to use sample data from fixtures (default: True)"
    )
    
    tax_year: int = Field(
        default=2024,
        description="Tax year for the report (e.g., 2024)",
        example=2024
    )
    
    company_name: Optional[str] = Field(
        default="Acme Corporation",
        description="Optional company name for report header",
        example="Acme Corporation"
    )
    
    @validator('tax_year')
    def validate_tax_year(cls, v):
        """Validate tax year is reasonable."""
        current_year = datetime.now().year
        if v < 2000 or v > current_year + 1:
            raise ValueError(
                f"Tax year must be between 2000 and {current_year + 1}"
            )
        return v


class CompletePipelineResponse(PydanticBaseModel):
    """
    Response model for complete pipeline endpoint.
    
    Attributes:
        success: Whether pipeline completed successfully
        report_id: Unique identifier for the generated report
        pdf_path: Path to generated PDF file
        total_qualified_hours: Sum of all qualified hours
        total_qualified_cost: Sum of all qualified costs
        estimated_credit: Estimated tax credit
        project_count: Number of projects processed
        execution_time_seconds: Total execution time
        summary: Human-readable summary
    """
    
    success: bool = Field(
        ...,
        description="Whether pipeline completed successfully"
    )
    
    report_id: str = Field(
        ...,
        description="Unique identifier for the generated report"
    )
    
    pdf_path: str = Field(
        ...,
        description="Path to generated PDF file"
    )
    
    total_qualified_hours: float = Field(
        default=0.0,
        description="Sum of all qualified hours"
    )
    
    total_qualified_cost: float = Field(
        default=0.0,
        description="Sum of all qualified costs"
    )
    
    estimated_credit: float = Field(
        default=0.0,
        description="Estimated tax credit (20% of qualified costs)"
    )
    
    project_count: int = Field(
        default=0,
        description="Number of projects processed"
    )
    
    execution_time_seconds: float = Field(
        default=0.0,
        description="Total execution time in seconds"
    )
    
    summary: str = Field(
        default="",
        description="Human-readable summary of pipeline execution"
    )


@app.post("/api/run-pipeline", tags=["Pipeline"], response_model=CompletePipelineResponse)
async def run_complete_pipeline(request: CompletePipelineRequest) -> CompletePipelineResponse:
    """
    Run complete pipeline endpoint.
    
    Executes the complete R&D tax credit automation pipeline from start to finish:
    1. Load sample qualified projects from fixtures (5 projects)
    2. Run Audit Trail Agent to generate narratives and compliance reviews
    3. Generate audit-ready PDF report
    4. Send real-time WebSocket updates throughout execution
    
    This endpoint is designed for demonstration and testing purposes, using
    pre-qualified sample data to showcase the complete workflow in 60-120 seconds.
    
    Args:
        request: CompletePipelineRequest with configuration options
        
    Returns:
        CompletePipelineResponse with report metadata and execution details
        
    Raises:
        HTTPException 400: If request parameters are invalid
        HTTPException 500: If configuration is missing or pipeline fails
        HTTPException 502: If external API connection fails
        
    Example Request:
        POST /api/run-pipeline
        {
            "use_sample_data": true,
            "tax_year": 2024,
            "company_name": "Acme Corporation"
        }
        
    Example Response:
        {
            "success": true,
            "report_id": "2024_20251030_143000",
            "pdf_path": "outputs/reports/rd_tax_credit_report_2024_20251030_143000.pdf",
            "total_qualified_hours": 320.0,
            "total_qualified_cost": 23040.00,
            "estimated_credit": 4608.00,
            "project_count": 5,
            "execution_time_seconds": 75.3,
            "summary": "Successfully generated audit report for 5 projects..."
        }
        
    Requirements: 5.2, 5.3
    """
    logger.info(
        f"Received complete pipeline request: "
        f"use_sample_data={request.use_sample_data}, "
        f"tax_year={request.tax_year}, "
        f"company_name={request.company_name}"
    )
    
    start_time = datetime.now()
    
    try:
        # Get configuration
        config = get_config()
        
        # Validate required API keys
        if not config.openrouter_api_key:
            logger.error("OpenRouter API key not configured")
            raise HTTPException(
                status_code=500,
                detail="OpenRouter API key not configured. Please set OPENROUTER_API_KEY in environment."
            )
        
        if not config.youcom_api_key:
            logger.error("You.com API key not configured")
            raise HTTPException(
                status_code=500,
                detail="You.com API key not configured. Please set YOUCOM_API_KEY in environment."
            )
        
        # Send initial status update
        await send_status_update(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.IN_PROGRESS,
            details="Loading sample qualified projects from fixtures"
        )
        
        # Load sample qualified projects from fixtures
        logger.info("Loading sample qualified projects...")
        
        import json
        from models.tax_models import QualifiedProject
        
        fixture_path = Path('tests/fixtures/sample_qualified_projects.json')
        
        if not fixture_path.exists():
            logger.error(f"Sample projects fixture not found: {fixture_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Sample projects fixture not found: {fixture_path}. Please ensure test fixtures are available."
            )
        
        with open(fixture_path, 'r') as f:
            projects_data = json.load(f)
        
        # Select 5 projects for the pipeline
        selected_projects_data = projects_data[:5]
        
        try:
            qualified_projects = [
                QualifiedProject(**project) for project in selected_projects_data
            ]
            logger.info(f"Loaded {len(qualified_projects)} sample projects")
        except Exception as e:
            logger.error(f"Failed to parse qualified projects: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Invalid qualified project data in fixtures: {str(e)}"
            )
        
        # Send data ingestion completion
        await send_status_update(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.COMPLETED,
            details=f"Loaded {len(qualified_projects)} qualified projects from fixtures"
        )
        
        # Send qualification start (simulated - data is already qualified)
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.IN_PROGRESS,
            details="Validating qualified projects"
        )
        
        # Brief delay to simulate qualification
        import asyncio
        await asyncio.sleep(1)
        
        # Send qualification completion
        total_hours = sum(p.qualified_hours for p in qualified_projects)
        total_cost = sum(p.qualified_cost for p in qualified_projects)
        estimated_credit = total_cost * 0.20
        
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.COMPLETED,
            details=f"Validated {len(qualified_projects)} projects: {total_hours:.1f}h, ${total_cost:,.2f}"
        )
        
        # Initialize tools for audit trail
        logger.info("Initializing audit trail tools...")
        
        from tools.you_com_client import YouComClient
        from tools.glm_reasoner import GLMReasoner
        from agents.audit_trail_agent import AuditTrailAgent
        from utils.pdf_generator import PDFGenerator
        
        # Initialize You.com client
        youcom_client = YouComClient(
            api_key=config.youcom_api_key
        )
        logger.info("You.com client initialized")
        
        # Initialize GLM reasoner
        glm_reasoner = GLMReasoner(
            api_key=config.openrouter_api_key
        )
        logger.info("GLM reasoner initialized")
        
        # Initialize PDF Generator
        pdf_generator = PDFGenerator()
        logger.info("PDF generator initialized")
        
        # Define status callback for real-time updates
        def status_callback(status_message):
            """Callback to send status updates during agent execution."""
            try:
                # Since we're in a thread pool, we need to schedule the coroutine in the main loop
                # Use asyncio.run_coroutine_threadsafe to schedule from another thread
                try:
                    main_loop = asyncio.get_event_loop()
                except RuntimeError:
                    # No event loop in current thread, skip status update
                    logger.debug("No event loop available for status update")
                    return
                
                # Schedule the coroutine in the main event loop
                asyncio.run_coroutine_threadsafe(
                    send_status_update(
                        stage=status_message.stage,
                        status=status_message.status,
                        details=status_message.details
                    ),
                    main_loop
                )
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")
        
        # Initialize Audit Trail Agent
        logger.info("Initializing Audit Trail Agent...")
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            pdf_generator=pdf_generator,
            status_callback=status_callback
        )
        
        # Send audit trail start
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.IN_PROGRESS,
            details="Starting audit report generation"
        )
        
        # Run audit trail agent
        logger.info("Running audit trail agent...")
        
        # Run the agent in a thread pool to avoid event loop conflicts
        import concurrent.futures
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool,
                agent.run,
                qualified_projects,
                request.tax_year,
                request.company_name
            )
        
        # Send completion status update
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.COMPLETED,
            details=result.summary
        )
        
        # Calculate execution time
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Generate report ID from PDF path or create one
        if result.pdf_path:
            # Extract filename from path
            import os
            report_id = os.path.splitext(os.path.basename(result.pdf_path))[0]
        else:
            # Generate report ID if PDF path not available
            report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build response
        response = CompletePipelineResponse(
            success=True,
            report_id=report_id,
            pdf_path=result.pdf_path or "",
            total_qualified_hours=total_hours,
            total_qualified_cost=total_cost,
            estimated_credit=estimated_credit,
            project_count=len(qualified_projects),
            execution_time_seconds=execution_time,
            summary=f"Successfully generated audit report for {len(qualified_projects)} projects in {execution_time:.1f}s"
        )
        
        logger.info(
            f"Complete pipeline executed successfully: "
            f"report_id={report_id}, "
            f"execution_time={execution_time:.1f}s"
        )
        
        return response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except APIConnectionError as e:
        # Handle API connection errors
        error_msg = f"API connection failed: {e.message}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=502,
            detail=error_msg
        )
    
    except ConfigurationError as e:
        # Handle configuration errors
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
    
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error during pipeline execution: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.ERROR,
            details=error_msg
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )


# WebSocket Endpoint

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional communication.
    
    Accepts client connections and registers them with the ConnectionManager.
    Handles incoming messages and broadcasts to all connected clients.
    Gracefully handles disconnections.
    
    Requirements: 5.2, 5.3
    
    Usage:
        // Frontend JavaScript
        const ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onopen = () => {
            console.log('Connected to R&D Tax Agent');
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received:', data);
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        ws.onclose = () => {
            console.log('Disconnected from R&D Tax Agent');
        };
    """
    # Accept and register the connection
    await connection_manager.connect(websocket)
    
    try:
        # Keep the connection alive and handle incoming messages
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            
            logger.info(f"Received message from client {id(websocket)}: {data}")
            
            # Echo the message back to the sender (for testing)
            # In production, you might want to process the message differently
            await connection_manager.send_personal_message(
                {
                    "type": "echo",
                    "message": f"Server received: {data}",
                    "timestamp": datetime.now().isoformat()
                },
                websocket
            )
            
    except WebSocketDisconnect:
        # Client disconnected normally
        logger.info(f"Client {id(websocket)} disconnected")
        connection_manager.disconnect(websocket)
        
    except Exception as e:
        # Unexpected error occurred
        logger.error(
            f"Error in WebSocket connection {id(websocket)}: {e}",
            exc_info=True
        )
        connection_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
