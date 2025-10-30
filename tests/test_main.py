"""
Unit tests for FastAPI application structure.

Tests:
- Application initialization
- CORS middleware configuration
- Exception handlers
- Health check endpoint
- Root endpoint

Requirements: Testing, 5.3, 8.4
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from utils.exceptions import (
    ConfigurationError,
    APIConnectionError,
    ValidationError,
    RAGRetrievalError,
    AgentExecutionError,
    RDTaxAgentError
)


# Test client
client = TestClient(app)


class TestApplicationInitialization:
    """Test FastAPI application initialization"""
    
    def test_app_metadata(self):
        """Test that application has correct metadata"""
        assert app.title == "R&D Tax Credit Automation Agent"
        assert app.version == "1.0.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"
    
    def test_cors_middleware_configured(self):
        """Test that CORS middleware is configured"""
        # Check that CORS middleware is in the middleware stack
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        assert 'CORSMiddleware' in middleware_types


class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root_endpoint(self):
        """Test GET / returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "R&D Tax Credit Automation Agent API" in data["message"]
        assert data["version"] == "1.0.0"
        assert data["documentation"] == "/docs"
        assert data["health_check"] == "/health"


class TestHealthCheckEndpoint:
    """Test health check endpoint"""
    
    @patch('main.get_config')
    def test_health_check_healthy(self, mock_get_config):
        """Test health check returns healthy status"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_config.output_dir.exists.return_value = True
        mock_config.log_level = "INFO"
        mock_config.openrouter_api_key = "test_key"
        mock_config.clockify_api_key = "test_key"
        mock_config.unified_to_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_config.thesys_api_key = "test_key"
        mock_get_config.return_value = mock_config
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "configuration" in data
        assert "api_keys_configured" in data
        assert data["configuration"]["knowledge_base_exists"] is True
        assert data["configuration"]["output_dir_exists"] is True
    
    @patch('main.get_config')
    def test_health_check_unhealthy(self, mock_get_config):
        """Test health check handles errors gracefully"""
        # Mock configuration error
        mock_get_config.side_effect = Exception("Configuration failed")
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data


class TestExceptionHandlers:
    """Test exception handlers"""
    
    def test_configuration_error_handler(self):
        """Test ConfigurationError handler"""
        # Create a test endpoint that raises ConfigurationError
        @app.get("/test/config-error")
        async def test_config_error():
            raise ConfigurationError("Missing API key")
        
        response = client.get("/test/config-error")
        assert response.status_code == 500
        
        data = response.json()
        assert data["error"] == "Configuration Error"
        assert "Missing API key" in data["message"]
        assert data["type"] == "configuration_error"
    
    def test_api_connection_error_handler(self):
        """Test APIConnectionError handler"""
        @app.get("/test/api-error")
        async def test_api_error():
            raise APIConnectionError(
                message="Connection failed",
                api_name="Clockify",
                status_code=503,
                endpoint="/api/v1/workspaces",
                retry_count=3
            )
        
        response = client.get("/test/api-error")
        assert response.status_code == 502
        
        data = response.json()
        assert data["error"] == "API Connection Error"
        assert data["api_name"] == "Clockify"
        assert data["status_code"] == 503
        assert data["retry_count"] == 3
        assert data["type"] == "api_connection_error"
    
    def test_validation_error_handler(self):
        """Test ValidationError handler"""
        @app.get("/test/validation-error")
        async def test_validation_error():
            raise ValidationError(
                message="Invalid hours",
                field_name="hours_spent",
                invalid_value=25,
                validation_rule="hours must be <= 24"
            )
        
        response = client.get("/test/validation-error")
        assert response.status_code == 422
        
        data = response.json()
        assert data["error"] == "Validation Error"
        assert data["field_name"] == "hours_spent"
        assert data["invalid_value"] == "25"
        assert data["type"] == "validation_error"
    
    def test_rag_retrieval_error_handler(self):
        """Test RAGRetrievalError handler"""
        @app.get("/test/rag-error")
        async def test_rag_error():
            raise RAGRetrievalError(
                message="No documents found",
                query="R&D qualification criteria",
                knowledge_base_path="/path/to/kb",
                error_type="query"
            )
        
        response = client.get("/test/rag-error")
        assert response.status_code == 500
        
        data = response.json()
        assert data["error"] == "RAG Retrieval Error"
        assert data["query"] == "R&D qualification criteria"
        assert data["error_type"] == "query"
        assert data["type"] == "rag_retrieval_error"
    
    def test_agent_execution_error_handler(self):
        """Test AgentExecutionError handler"""
        @app.get("/test/agent-error")
        async def test_agent_error():
            raise AgentExecutionError(
                message="Agent failed",
                agent_name="DataIngestionAgent",
                stage="data_collection",
                tool_name="ClockifyConnector",
                state={"progress": 50}
            )
        
        response = client.get("/test/agent-error")
        assert response.status_code == 500
        
        data = response.json()
        assert data["error"] == "Agent Execution Error"
        assert data["agent_name"] == "DataIngestionAgent"
        assert data["stage"] == "data_collection"
        assert data["tool_name"] == "ClockifyConnector"
        assert data["type"] == "agent_execution_error"
    
    def test_generic_agent_error_handler(self):
        """Test generic RDTaxAgentError handler"""
        @app.get("/test/generic-error")
        async def test_generic_error():
            raise RDTaxAgentError(
                message="Something went wrong",
                details={"context": "test"}
            )
        
        response = client.get("/test/generic-error")
        assert response.status_code == 500
        
        data = response.json()
        assert data["error"] == "Agent Error"
        assert "Something went wrong" in data["message"]
        assert data["type"] == "agent_error"
    
    def test_http_exception_handler(self):
        """Test HTTPException handler"""
        # Test 404 Not Found
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert data["error"] == "HTTP Error"
        assert data["status_code"] == 404
        assert data["type"] == "http_error"
    
    def test_generic_exception_handler(self):
        """Test generic Exception handler"""
        @app.get("/test/unexpected-error")
        async def test_unexpected_error():
            raise ValueError("Unexpected error")
        
        response = client.get("/test/unexpected-error")
        assert response.status_code == 500
        
        data = response.json()
        assert data["error"] == "Internal Server Error"
        assert data["type"] == "internal_error"


class TestCORSConfiguration:
    """Test CORS configuration"""
    
    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses"""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers


class TestWebSocketEndpoint:
    """Test WebSocket endpoint"""
    
    def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        with client.websocket_connect("/ws") as websocket:
            # Receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert "Connected to R&D Tax Credit Automation Agent" in data["message"]
            assert "timestamp" in data
            assert "connection_id" in data
    
    def test_websocket_echo_message(self):
        """Test WebSocket echo functionality"""
        with client.websocket_connect("/ws") as websocket:
            # Receive welcome message
            welcome = websocket.receive_json()
            assert welcome["type"] == "connection_established"
            
            # Send a test message
            test_message = "Hello, WebSocket!"
            websocket.send_text(test_message)
            
            # Receive echo response
            response = websocket.receive_json()
            assert response["type"] == "echo"
            assert f"Server received: {test_message}" in response["message"]
            assert "timestamp" in response
    
    def test_websocket_multiple_messages(self):
        """Test sending multiple messages through WebSocket"""
        with client.websocket_connect("/ws") as websocket:
            # Receive welcome message
            welcome = websocket.receive_json()
            assert welcome["type"] == "connection_established"
            
            # Send multiple messages
            messages = ["Message 1", "Message 2", "Message 3"]
            for msg in messages:
                websocket.send_text(msg)
                response = websocket.receive_json()
                assert response["type"] == "echo"
                assert f"Server received: {msg}" in response["message"]
    
    def test_websocket_disconnection(self):
        """Test WebSocket disconnection handling"""
        with client.websocket_connect("/ws") as websocket:
            # Receive welcome message
            welcome = websocket.receive_json()
            assert welcome["type"] == "connection_established"
            
            # Connection should close gracefully when context exits
        
        # Connection is now closed, verify by attempting to connect again
        with client.websocket_connect("/ws") as websocket:
            # Should be able to establish a new connection
            welcome = websocket.receive_json()
            assert welcome["type"] == "connection_established"


class TestDataIngestionEndpoint:
    """Test data ingestion endpoint"""
    
    @patch('main.get_config')
    @patch('main.ClockifyConnector')
    @patch('main.UnifiedToConnector')
    @patch('main.DataIngestionAgent')
    @patch('main.send_status_update')
    def test_ingest_data_success(
        self,
        mock_send_status,
        mock_agent_class,
        mock_unified_to_class,
        mock_clockify_class,
        mock_get_config
    ):
        """Test successful data ingestion"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.clockify_api_key = "test_clockify_key"
        mock_config.clockify_workspace_id = "test_workspace"
        mock_config.unified_to_api_key = "test_unified_key"
        mock_config.unified_to_workspace_id = "test_unified_workspace"
        mock_get_config.return_value = mock_config
        
        # Mock connectors
        mock_clockify = MagicMock()
        mock_unified_to = MagicMock()
        mock_clockify_class.return_value = mock_clockify
        mock_unified_to_class.return_value = mock_unified_to
        
        # Mock agent and result
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.time_entries = []
        mock_result.costs = []
        mock_result.validation_errors = []
        mock_result.deduplication_count = 0
        mock_result.execution_time_seconds = 5.0
        mock_result.summary = "Successfully ingested 0 time entries and 0 costs"
        
        mock_agent.run.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        
        # Make request
        response = client.post(
            "/api/ingest",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "time_entries" in data
        assert "costs" in data
        assert "summary" in data
        
        # Verify agent was called correctly
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        assert call_args[1]["connection_id"] is None
    
    @patch('main.get_config')
    def test_ingest_data_invalid_date_format(self, mock_get_config):
        """Test data ingestion with invalid date format"""
        mock_config = MagicMock()
        mock_config.clockify_api_key = "test_key"
        mock_config.clockify_workspace_id = "test_workspace"
        mock_config.unified_to_api_key = "test_key"
        mock_config.unified_to_workspace_id = "test_workspace"
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/ingest",
            json={
                "start_date": "invalid-date",
                "end_date": "2024-01-31"
            }
        )
        
        # Pydantic validation returns 422 Unprocessable Entity
        assert response.status_code == 422
        data = response.json()
        # Pydantic validation error format
        assert "detail" in data
    
    @patch('main.get_config')
    def test_ingest_data_invalid_date_range(self, mock_get_config):
        """Test data ingestion with invalid date range"""
        mock_config = MagicMock()
        mock_config.clockify_api_key = "test_key"
        mock_config.clockify_workspace_id = "test_workspace"
        mock_config.unified_to_api_key = "test_key"
        mock_config.unified_to_workspace_id = "test_workspace"
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/ingest",
            json={
                "start_date": "2024-01-31",
                "end_date": "2024-01-01"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "start_date must be before or equal to end_date" in data["message"]
    
    @patch('main.get_config')
    def test_ingest_data_missing_clockify_key(self, mock_get_config):
        """Test data ingestion with missing Clockify API key"""
        mock_config = MagicMock()
        mock_config.clockify_api_key = None
        mock_config.clockify_workspace_id = "test_workspace"
        mock_config.unified_to_api_key = "test_key"
        mock_config.unified_to_workspace_id = "test_workspace"
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/ingest",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "Clockify API key not configured" in data["message"]
    
    @patch('main.get_config')
    def test_ingest_data_missing_unified_to_key(self, mock_get_config):
        """Test data ingestion with missing Unified.to API key"""
        mock_config = MagicMock()
        mock_config.clockify_api_key = "test_key"
        mock_config.clockify_workspace_id = "test_workspace"
        mock_config.unified_to_api_key = None
        mock_config.unified_to_workspace_id = "test_workspace"
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/ingest",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "Unified.to API key not configured" in data["message"]
    
    @patch('main.get_config')
    @patch('main.ClockifyConnector')
    @patch('main.UnifiedToConnector')
    @patch('main.DataIngestionAgent')
    @patch('main.send_status_update')
    def test_ingest_data_with_custom_credentials(
        self,
        mock_send_status,
        mock_agent_class,
        mock_unified_to_class,
        mock_clockify_class,
        mock_get_config
    ):
        """Test data ingestion with custom API credentials"""
        # Mock configuration with no keys
        mock_config = MagicMock()
        mock_config.clockify_api_key = None
        mock_config.clockify_workspace_id = None
        mock_config.unified_to_api_key = None
        mock_config.unified_to_workspace_id = None
        mock_get_config.return_value = mock_config
        
        # Mock connectors
        mock_clockify = MagicMock()
        mock_unified_to = MagicMock()
        mock_clockify_class.return_value = mock_clockify
        mock_unified_to_class.return_value = mock_unified_to
        
        # Mock agent and result
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.time_entries = []
        mock_result.costs = []
        mock_result.validation_errors = []
        mock_result.deduplication_count = 0
        mock_result.execution_time_seconds = 5.0
        mock_result.summary = "Successfully ingested 0 time entries and 0 costs"
        
        mock_agent.run.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        
        # Make request with custom credentials
        response = client.post(
            "/api/ingest",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "clockify_api_key": "custom_clockify_key",
                "clockify_workspace_id": "custom_workspace",
                "unified_to_api_key": "custom_unified_key",
                "unified_to_workspace_id": "custom_unified_workspace",
                "connection_id": "conn_123"
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify connectors were initialized with custom credentials
        mock_clockify_class.assert_called_once_with(
            api_key="custom_clockify_key",
            workspace_id="custom_workspace"
        )
        mock_unified_to_class.assert_called_once_with(
            api_key="custom_unified_key",
            workspace_id="custom_unified_workspace"
        )
        
        # Verify agent was called with connection_id
        call_args = mock_agent.run.call_args
        assert call_args[1]["connection_id"] == "conn_123"
    
    @patch('main.get_config')
    @patch('main.ClockifyConnector')
    @patch('main.UnifiedToConnector')
    @patch('main.DataIngestionAgent')
    @patch('main.send_status_update')
    def test_ingest_data_api_connection_error(
        self,
        mock_send_status,
        mock_agent_class,
        mock_unified_to_class,
        mock_clockify_class,
        mock_get_config
    ):
        """Test data ingestion with API connection error"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.clockify_api_key = "test_key"
        mock_config.clockify_workspace_id = "test_workspace"
        mock_config.unified_to_api_key = "test_key"
        mock_config.unified_to_workspace_id = "test_workspace"
        mock_get_config.return_value = mock_config
        
        # Mock connectors
        mock_clockify = MagicMock()
        mock_unified_to = MagicMock()
        mock_clockify_class.return_value = mock_clockify
        mock_unified_to_class.return_value = mock_unified_to
        
        # Mock agent to raise APIConnectionError
        mock_agent = MagicMock()
        mock_agent.run.side_effect = APIConnectionError(
            message="Connection failed",
            api_name="Clockify",
            status_code=503,
            endpoint="/api/v1/workspaces",
            retry_count=3
        )
        mock_agent_class.return_value = mock_agent
        
        # Make request
        response = client.post(
            "/api/ingest",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            }
        )
        
        # Verify error response
        assert response.status_code == 502
        data = response.json()
        assert "API connection failed" in data["message"]


class TestQualificationEndpoint:
    """Test qualification endpoint"""
    
    @patch('main.get_config')
    @patch('agents.qualification_agent.QualificationAgent')
    @patch('tools.glm_reasoner.GLMReasoner')
    @patch('tools.you_com_client.YouComClient')
    @patch('tools.rd_knowledge_tool.RD_Knowledge_Tool')
    @patch('main.send_status_update')
    def test_qualify_projects_success(
        self,
        mock_send_status,
        mock_rag_class,
        mock_youcom_class,
        mock_glm_class,
        mock_agent_class,
        mock_get_config
    ):
        """Test successful project qualification"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_openrouter_key"
        mock_config.youcom_api_key = "test_youcom_key"
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_get_config.return_value = mock_config
        
        # Mock tools
        mock_rag = MagicMock()
        mock_youcom = MagicMock()
        mock_glm = MagicMock()
        mock_rag_class.return_value = mock_rag
        mock_youcom_class.return_value = mock_youcom
        mock_glm_class.return_value = mock_glm
        
        # Mock agent and result
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.qualified_projects = []
        mock_result.total_qualified_hours = 0.0
        mock_result.total_qualified_cost = 0.0
        mock_result.estimated_credit = 0.0
        mock_result.average_confidence = 0.0
        mock_result.flagged_projects = []
        mock_result.execution_time_seconds = 10.0
        mock_result.summary = "Successfully qualified 0 projects"
        
        mock_agent.run.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        
        # Make request
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [
                    {
                        "employee_id": "EMP001",
                        "employee_name": "John Doe",
                        "project_name": "API Optimization",
                        "task_description": "Implemented caching",
                        "hours_spent": 8.5,
                        "date": "2024-01-15T00:00:00",
                        "is_rd_classified": True
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
                        "is_rd_classified": True
                    }
                ],
                "tax_year": 2024
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "qualified_projects" in data
        assert "total_qualified_hours" in data
        assert "total_qualified_cost" in data
        assert "estimated_credit" in data
        assert "summary" in data
        
        # Verify agent was called correctly
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        assert call_args[1]["tax_year"] == 2024
    
    @patch('main.get_config')
    def test_qualify_projects_empty_time_entries(self, mock_get_config):
        """Test qualification with empty time entries"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [],
                "costs": []
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "time_entries cannot be empty" in data["message"]
    
    @patch('main.get_config')
    def test_qualify_projects_missing_openrouter_key(self, mock_get_config):
        """Test qualification with missing OpenRouter API key"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = None
        mock_config.youcom_api_key = "test_key"
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [
                    {
                        "employee_id": "EMP001",
                        "employee_name": "John Doe",
                        "project_name": "Test Project",
                        "hours_spent": 8.0,
                        "date": "2024-01-15T00:00:00",
                        "is_rd_classified": True
                    }
                ]
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "OpenRouter API key not configured" in data["message"]
    
    @patch('main.get_config')
    def test_qualify_projects_missing_youcom_key(self, mock_get_config):
        """Test qualification with missing You.com API key"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = None
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [
                    {
                        "employee_id": "EMP001",
                        "employee_name": "John Doe",
                        "project_name": "Test Project",
                        "hours_spent": 8.0,
                        "date": "2024-01-15T00:00:00",
                        "is_rd_classified": True
                    }
                ]
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "You.com API key not configured" in data["message"]
    
    @patch('main.get_config')
    def test_qualify_projects_missing_knowledge_base(self, mock_get_config):
        """Test qualification with missing knowledge base"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = False
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [
                    {
                        "employee_id": "EMP001",
                        "employee_name": "John Doe",
                        "project_name": "Test Project",
                        "hours_spent": 8.0,
                        "date": "2024-01-15T00:00:00",
                        "is_rd_classified": True
                    }
                ]
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "Knowledge base not found" in data["message"]
    
    @patch('main.get_config')
    def test_qualify_projects_invalid_time_entry(self, mock_get_config):
        """Test qualification with invalid time entry data"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [
                    {
                        "employee_id": "EMP001",
                        "employee_name": "John Doe",
                        "project_name": "Test Project",
                        "hours_spent": 25,  # Invalid: > 24
                        "date": "2024-01-15T00:00:00",
                        "is_rd_classified": True
                    }
                ]
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid time entry data" in data["message"]
    
    @patch('main.get_config')
    def test_qualify_projects_invalid_tax_year(self, mock_get_config):
        """Test qualification with invalid tax year"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [
                    {
                        "employee_id": "EMP001",
                        "employee_name": "John Doe",
                        "project_name": "Test Project",
                        "hours_spent": 8.0,
                        "date": "2024-01-15T00:00:00",
                        "is_rd_classified": True
                    }
                ],
                "tax_year": 1999  # Invalid: < 2000
            }
        )
        
        # Pydantic validation returns 422 Unprocessable Entity
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @patch('main.get_config')
    @patch('agents.qualification_agent.QualificationAgent')
    @patch('tools.glm_reasoner.GLMReasoner')
    @patch('tools.you_com_client.YouComClient')
    @patch('tools.rd_knowledge_tool.RD_Knowledge_Tool')
    @patch('main.send_status_update')
    def test_qualify_projects_rag_retrieval_error(
        self,
        mock_send_status,
        mock_rag_class,
        mock_youcom_class,
        mock_glm_class,
        mock_agent_class,
        mock_get_config
    ):
        """Test qualification with RAG retrieval error"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_get_config.return_value = mock_config
        
        # Mock tools
        mock_rag = MagicMock()
        mock_youcom = MagicMock()
        mock_glm = MagicMock()
        mock_rag_class.return_value = mock_rag
        mock_youcom_class.return_value = mock_youcom
        mock_glm_class.return_value = mock_glm
        
        # Mock agent to raise RAGRetrievalError
        mock_agent = MagicMock()
        mock_agent.run.side_effect = RAGRetrievalError(
            message="No documents found",
            query="R&D qualification",
            knowledge_base_path="/path/to/kb",
            error_type="query"
        )
        mock_agent_class.return_value = mock_agent
        
        # Make request
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [
                    {
                        "employee_id": "EMP001",
                        "employee_name": "John Doe",
                        "project_name": "Test Project",
                        "task_description": "Testing",
                        "hours_spent": 8.0,
                        "date": "2024-01-15T00:00:00",
                        "is_rd_classified": True
                    }
                ]
            }
        )
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "RAG retrieval failed" in data["message"]
    
    @patch('main.get_config')
    @patch('agents.qualification_agent.QualificationAgent')
    @patch('tools.glm_reasoner.GLMReasoner')
    @patch('tools.you_com_client.YouComClient')
    @patch('tools.rd_knowledge_tool.RD_Knowledge_Tool')
    @patch('main.send_status_update')
    def test_qualify_projects_api_connection_error(
        self,
        mock_send_status,
        mock_rag_class,
        mock_youcom_class,
        mock_glm_class,
        mock_agent_class,
        mock_get_config
    ):
        """Test qualification with API connection error"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_config.knowledge_base_path = MagicMock()
        mock_config.knowledge_base_path.exists.return_value = True
        mock_get_config.return_value = mock_config
        
        # Mock tools
        mock_rag = MagicMock()
        mock_youcom = MagicMock()
        mock_glm = MagicMock()
        mock_rag_class.return_value = mock_rag
        mock_youcom_class.return_value = mock_youcom
        mock_glm_class.return_value = mock_glm
        
        # Mock agent to raise APIConnectionError
        mock_agent = MagicMock()
        mock_agent.run.side_effect = APIConnectionError(
            message="Connection failed",
            api_name="You.com",
            status_code=503,
            endpoint="/v1/agent/run",
            retry_count=3
        )
        mock_agent_class.return_value = mock_agent
        
        # Make request
        response = client.post(
            "/api/qualify",
            json={
                "time_entries": [
                    {
                        "employee_id": "EMP001",
                        "employee_name": "John Doe",
                        "project_name": "Test Project",
                        "task_description": "Testing",
                        "hours_spent": 8.0,
                        "date": "2024-01-15T00:00:00",
                        "is_rd_classified": True
                    }
                ]
            }
        )
        
        # Verify error response
        assert response.status_code == 502
        data = response.json()
        assert "API connection failed" in data["message"]


class TestReportGenerationEndpoint:
    """Test report generation endpoint"""
    
    @patch('agents.audit_trail_agent.AuditTrailAgent')
    @patch('main.send_status_update')
    @patch('main.get_config')
    def test_generate_report_success(
        self,
        mock_get_config,
        mock_send_status,
        mock_agent_class
    ):
        """Test successful report generation"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_openrouter_key"
        mock_config.youcom_api_key = "test_youcom_key"
        mock_get_config.return_value = mock_config
        
        # Mock agent result
        from models.tax_models import AuditReport, QualifiedProject
        from datetime import datetime
        
        mock_result = MagicMock()
        mock_result.pdf_path = "reports/report_20240115_123456.pdf"
        mock_result.execution_time_seconds = 45.8
        mock_result.summary = "Successfully generated audit report for 1 project"
        
        # Mock report
        mock_report = MagicMock()
        mock_report.generation_date = datetime(2024, 1, 15, 12, 34, 56)
        mock_report.tax_year = 2024
        mock_report.total_qualified_hours = 120.5
        mock_report.total_qualified_cost = 15000.0
        mock_report.estimated_credit = 3000.0
        mock_report.projects = []
        mock_result.report = mock_report
        
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.run.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        
        # Make request
        response = client.post(
            "/api/generate-report",
            json={
                "qualified_projects": [
                    {
                        "project_name": "API Optimization",
                        "qualified_hours": 120.5,
                        "qualified_cost": 15000.0,
                        "confidence_score": 0.85,
                        "qualification_percentage": 80.0,
                        "supporting_citation": "CFR Title 26 § 1.41-4(a)(1)",
                        "reasoning": "Project involves systematic experimentation",
                        "irs_source": "CFR Title 26 § 1.41-4",
                        "flagged_for_review": False
                    }
                ],
                "tax_year": 2024,
                "company_name": "Acme Corporation"
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["report_id"] == "report_20240115_123456"
        assert data["pdf_path"] == "reports/report_20240115_123456.pdf"
        assert data["execution_time_seconds"] == 45.8
        assert "Successfully generated" in data["summary"]
        
        # Verify report metadata
        assert "report_metadata" in data
        metadata = data["report_metadata"]
        assert metadata["tax_year"] == 2024
        assert metadata["total_qualified_hours"] == 120.5
        assert metadata["total_qualified_cost"] == 15000.0
        assert metadata["estimated_credit"] == 3000.0
        assert metadata["project_count"] == 0
        
        # Verify agent was called correctly
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        assert call_args[1]["tax_year"] == 2024
        assert call_args[1]["company_name"] == "Acme Corporation"
        assert len(call_args[1]["qualified_projects"]) == 1
    
    @patch('main.get_config')
    def test_generate_report_empty_projects(self, mock_get_config):
        """Test report generation with empty projects list"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/generate-report",
            json={
                "qualified_projects": [],
                "tax_year": 2024
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "message" in data or "detail" in data
    
    @patch('main.get_config')
    def test_generate_report_missing_openrouter_key(self, mock_get_config):
        """Test report generation with missing OpenRouter API key"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = None
        mock_config.youcom_api_key = "test_key"
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/generate-report",
            json={
                "qualified_projects": [
                    {
                        "project_name": "Test Project",
                        "qualified_hours": 100.0,
                        "qualified_cost": 10000.0,
                        "confidence_score": 0.8,
                        "qualification_percentage": 75.0,
                        "supporting_citation": "Test citation",
                        "reasoning": "Test reasoning",
                        "irs_source": "Test source",
                        "flagged_for_review": False
                    }
                ],
                "tax_year": 2024
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data or "message" in data or "detail" in data
    
    @patch('main.get_config')
    def test_generate_report_missing_youcom_key(self, mock_get_config):
        """Test report generation with missing You.com API key"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = None
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/generate-report",
            json={
                "qualified_projects": [
                    {
                        "project_name": "Test Project",
                        "qualified_hours": 100.0,
                        "qualified_cost": 10000.0,
                        "confidence_score": 0.8,
                        "qualification_percentage": 75.0,
                        "supporting_citation": "Test citation",
                        "reasoning": "Test reasoning",
                        "irs_source": "Test source",
                        "flagged_for_review": False
                    }
                ],
                "tax_year": 2024
            }
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data or "message" in data or "detail" in data
    
    @patch('main.get_config')
    def test_generate_report_invalid_project_data(self, mock_get_config):
        """Test report generation with invalid project data"""
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/generate-report",
            json={
                "qualified_projects": [
                    {
                        "project_name": "Test Project",
                        # Missing required fields
                    }
                ],
                "tax_year": 2024
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "message" in data or "detail" in data
    
    @patch('main.get_config')
    def test_generate_report_invalid_tax_year(self, mock_get_config):
        """Test report generation with invalid tax year"""
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        
        response = client.post(
            "/api/generate-report",
            json={
                "qualified_projects": [
                    {
                        "project_name": "Test Project",
                        "qualified_hours": 100.0,
                        "qualified_cost": 10000.0,
                        "confidence_score": 0.8,
                        "qualification_percentage": 75.0,
                        "supporting_citation": "Test citation",
                        "reasoning": "Test reasoning",
                        "irs_source": "Test source",
                        "flagged_for_review": False
                    }
                ],
                "tax_year": 1999  # Invalid year
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @patch('agents.audit_trail_agent.AuditTrailAgent')
    @patch('main.send_status_update')
    @patch('main.get_config')
    def test_generate_report_api_connection_error(
        self,
        mock_get_config,
        mock_send_status,
        mock_agent_class
    ):
        """Test report generation with API connection error"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_get_config.return_value = mock_config
        
        # Mock agent to raise APIConnectionError
        from utils.exceptions import APIConnectionError
        
        mock_agent = MagicMock()
        mock_agent.run.side_effect = APIConnectionError(
            message="You.com API connection failed",
            api_name="You.com",
            endpoint="/v1/agents/runs",
            status_code=503
        )
        mock_agent_class.return_value = mock_agent
        
        # Make request
        response = client.post(
            "/api/generate-report",
            json={
                "qualified_projects": [
                    {
                        "project_name": "Test Project",
                        "qualified_hours": 100.0,
                        "qualified_cost": 10000.0,
                        "confidence_score": 0.8,
                        "qualification_percentage": 75.0,
                        "supporting_citation": "Test citation",
                        "reasoning": "Test reasoning",
                        "irs_source": "Test source",
                        "flagged_for_review": False
                    }
                ],
                "tax_year": 2024
            }
        )
        
        # Verify error response
        assert response.status_code == 502
        data = response.json()
        assert "error" in data or "message" in data or "detail" in data
    
    @patch('agents.audit_trail_agent.AuditTrailAgent')
    @patch('main.send_status_update')
    @patch('main.get_config')
    def test_generate_report_without_pdf_path(
        self,
        mock_get_config,
        mock_send_status,
        mock_agent_class
    ):
        """Test report generation when PDF path is not available"""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.openrouter_api_key = "test_key"
        mock_config.youcom_api_key = "test_key"
        mock_get_config.return_value = mock_config
        
        # Mock agent result without PDF path
        mock_result = MagicMock()
        mock_result.pdf_path = None
        mock_result.execution_time_seconds = 30.0
        mock_result.summary = "Report generated but PDF not available"
        mock_result.report = None
        
        mock_agent = MagicMock()
        mock_agent.run.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        
        # Make request
        response = client.post(
            "/api/generate-report",
            json={
                "qualified_projects": [
                    {
                        "project_name": "Test Project",
                        "qualified_hours": 100.0,
                        "qualified_cost": 10000.0,
                        "confidence_score": 0.8,
                        "qualification_percentage": 75.0,
                        "supporting_citation": "Test citation",
                        "reasoning": "Test reasoning",
                        "irs_source": "Test source",
                        "flagged_for_review": False
                    }
                ],
                "tax_year": 2024
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["pdf_path"] == ""
        # Report ID should be generated from timestamp
        assert data["report_id"].startswith("report_")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
