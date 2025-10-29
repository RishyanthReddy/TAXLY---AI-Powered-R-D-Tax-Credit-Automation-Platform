"""
Tests for API health check module.

Tests cover:
- Individual API health checks (Clockify, Unified.to, You.com, GLM)
- Health check result formatting
- Overall health status calculation
- Startup health check functionality
- Error handling and timeout scenarios
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from tools.health_check import (
    HealthStatus,
    HealthCheckResult,
    check_clockify_health,
    check_unified_to_health,
    check_youcom_health,
    check_glm_health,
    check_api_health,
    check_all_apis,
    check_all_apis_async,
    get_overall_health_status,
    startup_health_check,
    print_health_report
)
from utils.exceptions import APIConnectionError


class TestHealthCheckResult:
    """Tests for HealthCheckResult class."""
    
    def test_health_check_result_creation(self):
        """Test creating a health check result."""
        result = HealthCheckResult(
            api_name="TestAPI",
            status=HealthStatus.HEALTHY,
            response_time=0.5,
            message="API is healthy"
        )
        
        assert result.api_name == "TestAPI"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time == 0.5
        assert result.message == "API is healthy"
        assert result.details == {}
        assert result.error is None
        assert isinstance(result.timestamp, datetime)
    
    def test_health_check_result_with_details(self):
        """Test health check result with additional details."""
        details = {'user_id': '123', 'workspace': 'test'}
        result = HealthCheckResult(
            api_name="TestAPI",
            status=HealthStatus.HEALTHY,
            response_time=0.5,
            message="API is healthy",
            details=details
        )
        
        assert result.details == details
    
    def test_health_check_result_with_error(self):
        """Test health check result with error."""
        result = HealthCheckResult(
            api_name="TestAPI",
            status=HealthStatus.DOWN,
            response_time=1.0,
            message="API is down",
            error="Connection refused"
        )
        
        assert result.status == HealthStatus.DOWN
        assert result.error == "Connection refused"
    
    def test_health_check_result_to_dict(self):
        """Test converting health check result to dictionary."""
        result = HealthCheckResult(
            api_name="TestAPI",
            status=HealthStatus.HEALTHY,
            response_time=0.5,
            message="API is healthy",
            details={'key': 'value'}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['api_name'] == "TestAPI"
        assert result_dict['status'] == HealthStatus.HEALTHY
        assert result_dict['response_time_ms'] == 500.0
        assert result_dict['message'] == "API is healthy"
        assert result_dict['details'] == {'key': 'value'}
        assert 'timestamp' in result_dict
        assert 'error' not in result_dict  # No error in this case
    
    def test_health_check_result_repr(self):
        """Test string representation of health check result."""
        result = HealthCheckResult(
            api_name="TestAPI",
            status=HealthStatus.HEALTHY,
            response_time=0.5,
            message="API is healthy"
        )
        
        repr_str = repr(result)
        assert "TestAPI" in repr_str
        assert "healthy" in repr_str
        assert "0.500" in repr_str


class TestClockifyHealthCheck:
    """Tests for Clockify health check."""
    
    @patch('tools.health_check.ClockifyConnector')
    def test_clockify_health_check_success(self, mock_connector_class):
        """Test successful Clockify health check."""
        # Mock connector
        mock_connector = Mock()
        mock_connector.test_authentication.return_value = {
            'id': 'user123',
            'email': 'test@example.com'
        }
        mock_connector_class.return_value = mock_connector
        
        # Run health check
        result = check_clockify_health(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        assert result.api_name == "Clockify"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time > 0
        assert "healthy" in result.message.lower()
        assert result.details['user_id'] == 'user123'
        assert result.details['user_email'] == 'test@example.com'
    
    @patch('tools.health_check.ClockifyConnector')
    def test_clockify_health_check_slow_response(self, mock_connector_class):
        """Test Clockify health check with slow response."""
        # Mock connector with slow response
        mock_connector = Mock()
        
        def slow_auth():
            import time
            time.sleep(6)  # Simulate slow response
            return {'id': 'user123', 'email': 'test@example.com'}
        
        mock_connector.test_authentication = slow_auth
        mock_connector_class.return_value = mock_connector
        
        # Run health check
        result = check_clockify_health(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        assert result.status == HealthStatus.DEGRADED
        assert "slow" in result.message.lower()
        assert result.response_time > 5.0
    
    @patch('tools.health_check.ClockifyConnector')
    def test_clockify_health_check_auth_failure(self, mock_connector_class):
        """Test Clockify health check with authentication failure."""
        # Mock connector that raises 401 error
        mock_connector = Mock()
        mock_connector.test_authentication.side_effect = APIConnectionError(
            message="Invalid API key",
            api_name="Clockify",
            status_code=401,
            endpoint="/user"
        )
        mock_connector_class.return_value = mock_connector
        
        # Run health check
        result = check_clockify_health(
            api_key="invalid_key",
            workspace_id="test_workspace"
        )
        
        assert result.status == HealthStatus.DOWN
        assert "authentication failed" in result.message.lower()
        assert result.error is not None


class TestUnifiedToHealthCheck:
    """Tests for Unified.to health check."""
    
    @patch('tools.health_check.UnifiedToConnector')
    def test_unified_to_health_check_success(self, mock_connector_class):
        """Test successful Unified.to health check."""
        # Mock connector
        mock_connector = Mock()
        mock_connector.test_authentication.return_value = {
            'id': 'workspace123',
            'name': 'Test Workspace'
        }
        mock_connector_class.return_value = mock_connector
        
        # Run health check
        result = check_unified_to_health(
            api_key="test_key",
            workspace_id="test_workspace"
        )
        
        assert result.api_name == "Unified.to"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time > 0
        assert "healthy" in result.message.lower()
        assert result.details['workspace_name'] == 'Test Workspace'
    
    @patch('tools.health_check.UnifiedToConnector')
    def test_unified_to_health_check_not_found(self, mock_connector_class):
        """Test Unified.to health check with workspace not found."""
        # Mock connector that raises 404 error
        mock_connector = Mock()
        mock_connector.test_authentication.side_effect = APIConnectionError(
            message="Workspace not found",
            api_name="Unified.to",
            status_code=404,
            endpoint="/workspace"
        )
        mock_connector_class.return_value = mock_connector
        
        # Run health check
        result = check_unified_to_health(
            api_key="test_key",
            workspace_id="invalid_workspace"
        )
        
        assert result.status == HealthStatus.DOWN
        assert "not found" in result.message.lower()


class TestYouComHealthCheck:
    """Tests for You.com health check."""
    
    @patch('tools.health_check.YouComClient')
    def test_youcom_health_check_success(self, mock_client_class):
        """Test successful You.com health check."""
        # Mock client
        mock_client = Mock()
        mock_client.test_authentication.return_value = True
        mock_client_class.return_value = mock_client
        
        # Run health check
        result = check_youcom_health(api_key="ydc-sk-test_key")
        
        assert result.api_name == "You.com"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time > 0
        assert "healthy" in result.message.lower()
    
    @patch('tools.health_check.YouComClient')
    def test_youcom_health_check_auth_failure(self, mock_client_class):
        """Test You.com health check with authentication failure."""
        # Mock client that returns False for auth
        mock_client = Mock()
        mock_client.test_authentication.return_value = False
        mock_client_class.return_value = mock_client
        
        # Run health check
        result = check_youcom_health(api_key="invalid_key")
        
        assert result.status == HealthStatus.DOWN
        assert "authentication failed" in result.message.lower()


class TestGLMHealthCheck:
    """Tests for GLM 4.5 Air health check."""
    
    @pytest.mark.asyncio
    @patch('tools.health_check.GLMReasoner')
    async def test_glm_health_check_success(self, mock_reasoner_class):
        """Test successful GLM health check."""
        # Mock reasoner
        mock_reasoner = Mock()
        
        # Create async mock function
        async def mock_reason(*args, **kwargs):
            return "OK"
        
        mock_reasoner.reason = mock_reason
        mock_reasoner.model = "z-ai/glm-4.5-air:free"
        mock_reasoner_class.return_value = mock_reasoner
        
        # Run health check
        result = await check_glm_health(api_key="test_key")
        
        assert result.api_name == "GLM 4.5 Air"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time > 0
        assert "healthy" in result.message.lower()
        assert result.details['model'] == "z-ai/glm-4.5-air:free"
    
    @pytest.mark.asyncio
    @patch('tools.health_check.GLMReasoner')
    async def test_glm_health_check_empty_response(self, mock_reasoner_class):
        """Test GLM health check with empty response."""
        # Mock reasoner that returns empty string
        mock_reasoner = Mock()
        
        # Create async mock function
        async def mock_reason(*args, **kwargs):
            return ""
        
        mock_reasoner.reason = mock_reason
        mock_reasoner_class.return_value = mock_reasoner
        
        # Run health check
        result = await check_glm_health(api_key="test_key")
        
        assert result.status == HealthStatus.DOWN
        assert "empty response" in result.message.lower()
    
    @pytest.mark.asyncio
    @patch('tools.health_check.GLMReasoner')
    async def test_glm_health_check_api_error(self, mock_reasoner_class):
        """Test GLM health check with API error."""
        # Mock reasoner that raises error
        mock_reasoner = Mock()
        
        # Create async mock function that raises error
        async def mock_reason(*args, **kwargs):
            raise APIConnectionError("Invalid API key")
        
        mock_reasoner.reason = mock_reason
        mock_reasoner_class.return_value = mock_reasoner
        
        # Run health check
        result = await check_glm_health(api_key="invalid_key")
        
        assert result.status == HealthStatus.DOWN
        assert result.error is not None


class TestCheckAPIHealth:
    """Tests for check_api_health function."""
    
    @patch('tools.health_check.check_clockify_health')
    def test_check_api_health_clockify(self, mock_check):
        """Test checking Clockify health by name."""
        mock_check.return_value = HealthCheckResult(
            api_name="Clockify",
            status=HealthStatus.HEALTHY,
            response_time=0.5,
            message="Healthy"
        )
        
        result = check_api_health('clockify')
        
        assert result.api_name == "Clockify"
        assert result.status == HealthStatus.HEALTHY
        mock_check.assert_called_once()
    
    @patch('tools.health_check.check_youcom_health')
    def test_check_api_health_youcom(self, mock_check):
        """Test checking You.com health by name."""
        mock_check.return_value = HealthCheckResult(
            api_name="You.com",
            status=HealthStatus.HEALTHY,
            response_time=0.5,
            message="Healthy"
        )
        
        result = check_api_health('youcom')
        
        assert result.api_name == "You.com"
        mock_check.assert_called_once()
    
    def test_check_api_health_invalid_name(self):
        """Test checking health with invalid API name."""
        with pytest.raises(ValueError, match="Unknown API name"):
            check_api_health('invalid_api')


class TestCheckAllAPIs:
    """Tests for check_all_apis function."""
    
    @patch('tools.health_check.check_clockify_health')
    @patch('tools.health_check.check_unified_to_health')
    @patch('tools.health_check.check_youcom_health')
    @patch('tools.health_check.check_glm_health')
    def test_check_all_apis_success(
        self,
        mock_glm,
        mock_youcom,
        mock_unified,
        mock_clockify
    ):
        """Test checking all APIs successfully."""
        # Mock all health checks
        mock_clockify.return_value = HealthCheckResult(
            "Clockify", HealthStatus.HEALTHY, 0.5, "Healthy"
        )
        mock_unified.return_value = HealthCheckResult(
            "Unified.to", HealthStatus.HEALTHY, 0.5, "Healthy"
        )
        mock_youcom.return_value = HealthCheckResult(
            "You.com", HealthStatus.HEALTHY, 0.5, "Healthy"
        )
        
        # Mock async GLM check
        async def mock_glm_check(*args, **kwargs):
            return HealthCheckResult(
                "GLM 4.5 Air", HealthStatus.HEALTHY, 0.5, "Healthy"
            )
        mock_glm.side_effect = mock_glm_check
        
        # Run check
        results = check_all_apis()
        
        assert len(results) == 4
        assert all(result.status == HealthStatus.HEALTHY for result in results.values())
    
    @patch('tools.health_check.check_clockify_health')
    @patch('tools.health_check.check_youcom_health')
    def test_check_all_apis_specific(self, mock_youcom, mock_clockify):
        """Test checking specific APIs only."""
        mock_clockify.return_value = HealthCheckResult(
            "Clockify", HealthStatus.HEALTHY, 0.5, "Healthy"
        )
        mock_youcom.return_value = HealthCheckResult(
            "You.com", HealthStatus.HEALTHY, 0.5, "Healthy"
        )
        
        # Check only Clockify and You.com
        results = check_all_apis(include_apis=['clockify', 'youcom'])
        
        assert len(results) == 2
        assert 'clockify' in results
        assert 'youcom' in results


class TestOverallHealthStatus:
    """Tests for get_overall_health_status function."""
    
    def test_overall_health_all_healthy(self):
        """Test overall health when all APIs are healthy."""
        results = {
            'api1': HealthCheckResult("API1", HealthStatus.HEALTHY, 0.5, "OK"),
            'api2': HealthCheckResult("API2", HealthStatus.HEALTHY, 0.5, "OK"),
        }
        
        status = get_overall_health_status(results)
        assert status == HealthStatus.HEALTHY
    
    def test_overall_health_one_degraded(self):
        """Test overall health when one API is degraded."""
        results = {
            'api1': HealthCheckResult("API1", HealthStatus.HEALTHY, 0.5, "OK"),
            'api2': HealthCheckResult("API2", HealthStatus.DEGRADED, 6.0, "Slow"),
        }
        
        status = get_overall_health_status(results)
        assert status == HealthStatus.DEGRADED
    
    def test_overall_health_one_down(self):
        """Test overall health when one API is down."""
        results = {
            'api1': HealthCheckResult("API1", HealthStatus.HEALTHY, 0.5, "OK"),
            'api2': HealthCheckResult("API2", HealthStatus.DOWN, 1.0, "Error"),
        }
        
        status = get_overall_health_status(results)
        assert status == HealthStatus.DOWN
    
    def test_overall_health_empty_results(self):
        """Test overall health with empty results."""
        status = get_overall_health_status({})
        assert status == HealthStatus.DOWN


class TestStartupHealthCheck:
    """Tests for startup_health_check function."""
    
    @patch('tools.health_check.check_all_apis')
    @patch('tools.health_check.print_health_report')
    def test_startup_health_check_success(self, mock_print, mock_check_all):
        """Test successful startup health check."""
        mock_check_all.return_value = {
            'clockify': HealthCheckResult("Clockify", HealthStatus.HEALTHY, 0.5, "OK"),
            'youcom': HealthCheckResult("You.com", HealthStatus.HEALTHY, 0.5, "OK"),
        }
        
        result = startup_health_check()
        
        assert result is True
        mock_check_all.assert_called_once()
        mock_print.assert_called_once()
    
    @patch('tools.health_check.check_all_apis')
    @patch('tools.health_check.print_health_report')
    def test_startup_health_check_failure(self, mock_print, mock_check_all):
        """Test startup health check with failures."""
        mock_check_all.return_value = {
            'clockify': HealthCheckResult("Clockify", HealthStatus.HEALTHY, 0.5, "OK"),
            'youcom': HealthCheckResult("You.com", HealthStatus.DOWN, 1.0, "Error"),
        }
        
        result = startup_health_check()
        
        assert result is False
    
    @patch('tools.health_check.check_all_apis')
    @patch('tools.health_check.print_health_report')
    def test_startup_health_check_fail_on_error(self, mock_print, mock_check_all):
        """Test startup health check with fail_on_error=True."""
        mock_check_all.return_value = {
            'clockify': HealthCheckResult("Clockify", HealthStatus.DOWN, 1.0, "Error"),
        }
        
        with pytest.raises(RuntimeError, match="Startup health check failed"):
            startup_health_check(fail_on_error=True)


class TestPrintHealthReport:
    """Tests for print_health_report function."""
    
    def test_print_health_report_all_healthy(self, capsys):
        """Test printing health report with all healthy APIs."""
        results = {
            'clockify': HealthCheckResult("Clockify", HealthStatus.HEALTHY, 0.125, "OK"),
            'youcom': HealthCheckResult("You.com", HealthStatus.HEALTHY, 0.456, "OK"),
        }
        
        print_health_report(results)
        
        captured = capsys.readouterr()
        assert "API Health Check Report" in captured.out
        assert "Clockify" in captured.out
        assert "You.com" in captured.out
        assert "All systems operational" in captured.out
    
    def test_print_health_report_with_issues(self, capsys):
        """Test printing health report with issues."""
        results = {
            'clockify': HealthCheckResult("Clockify", HealthStatus.HEALTHY, 0.5, "OK"),
            'youcom': HealthCheckResult("You.com", HealthStatus.DOWN, 1.0, "Error", error="Connection failed"),
        }
        
        print_health_report(results)
        
        captured = capsys.readouterr()
        assert "Some systems experiencing issues" in captured.out
        assert "Error: Connection failed" in captured.out
