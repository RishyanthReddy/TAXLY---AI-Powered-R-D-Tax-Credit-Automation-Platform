"""
Unit tests for UnifiedToConnector payslip fetching and transformation (Task 62).

Tests cover:
- Fetching payslips from Unified.to API with pagination
- Handling multiple pay periods per employee
- Transforming payslip data to ProjectCost models
- Error handling for invalid data
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from tools.api_connectors import UnifiedToConnector
from utils.exceptions import APIConnectionError


class TestUnifiedToPayslipFetching:
    """Test cases for UnifiedToConnector payslip fetching (Task 62)."""
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_single_page(self, mock_request, mock_post):
        """Test fetching payslips with single page of results."""
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock payslips response
        mock_payslips_response = Mock()
        mock_payslips_response.status_code = 200
        mock_payslips_response.json.return_value = [
            {
                "id": "PAY001",
                "employee_id": "EMP001",
                "pay_period_start": "2024-03-01T00:00:00Z",
                "pay_period_end": "2024-03-31T00:00:00Z",
                "pay_date": "2024-03-31T00:00:00Z",
                "gross_pay": 12500.00,
                "net_pay": 9375.00,
                "deductions": 1875.00,
                "taxes": 1250.00,
                "currency": "USD",
                "employee_name": "Alice Johnson",
                "department": "Engineering"
            },
            {
                "id": "PAY002",
                "employee_id": "EMP002",
                "pay_period_start": "2024-03-01T00:00:00Z",
                "pay_period_end": "2024-03-31T00:00:00Z",
                "pay_date": "2024-03-31T00:00:00Z",
                "gross_pay": 13750.00,
                "net_pay": 10312.50,
                "deductions": 2062.50,
                "taxes": 1375.00,
                "currency": "USD",
                "employee_name": "Bob Smith",
                "department": "Engineering"
            }
        ]
        mock_request.return_value = mock_payslips_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        payslips = connector.fetch_payslips(
            connection_id="conn_123",
            start_date=datetime(2024, 3, 1),
            end_date=datetime(2024, 3, 31)
        )
        
        assert len(payslips) == 2
        assert payslips[0]["id"] == "PAY001"
        assert payslips[0]["employee_id"] == "EMP001"
        assert payslips[0]["gross_pay"] == 12500.00
        assert payslips[1]["id"] == "PAY002"
        assert payslips[1]["employee_id"] == "EMP002"
        assert payslips[1]["gross_pay"] == 13750.00
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_multiple_pages(self, mock_request, mock_post):
        """Test fetching payslips with pagination."""
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock paginated responses
        page1_payslips = [
            {
                "id": f"PAY{str(i).zfill(3)}",
                "employee_id": f"EMP{str(i).zfill(3)}",
                "pay_period_start": "2024-01-01T00:00:00Z",
                "pay_period_end": "2024-01-31T00:00:00Z",
                "pay_date": "2024-01-31T00:00:00Z",
                "gross_pay": 10000.00 + (i * 100),
                "net_pay": 7500.00 + (i * 75),
                "deductions": 1500.00,
                "taxes": 1000.00,
                "currency": "USD"
            }
            for i in range(1, 101)  # 100 payslips
        ]
        
        page2_payslips = [
            {
                "id": f"PAY{str(i).zfill(3)}",
                "employee_id": f"EMP{str(i).zfill(3)}",
                "pay_period_start": "2024-01-01T00:00:00Z",
                "pay_period_end": "2024-01-31T00:00:00Z",
                "pay_date": "2024-01-31T00:00:00Z",
                "gross_pay": 10000.00 + (i * 100),
                "net_pay": 7500.00 + (i * 75),
                "deductions": 1500.00,
                "taxes": 1000.00,
                "currency": "USD"
            }
            for i in range(101, 151)  # 50 payslips
        ]
        
        mock_response_page1 = Mock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = page1_payslips
        
        mock_response_page2 = Mock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = page2_payslips
        
        mock_request.side_effect = [mock_response_page1, mock_response_page2]
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        payslips = connector.fetch_payslips(
            connection_id="conn_123",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            page_size=100
        )
        
        assert len(payslips) == 150
        assert payslips[0]["id"] == "PAY001"
        assert payslips[149]["id"] == "PAY150"
        assert mock_request.call_count == 2
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_empty_result(self, mock_request, mock_post):
        """Test fetching payslips with no results."""
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock empty response
        mock_payslips_response = Mock()
        mock_payslips_response.status_code = 200
        mock_payslips_response.json.return_value = []
        mock_request.return_value = mock_payslips_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        payslips = connector.fetch_payslips(
            connection_id="conn_123",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert len(payslips) == 0
        assert mock_request.call_count == 1
    
    def test_fetch_payslips_invalid_date_range(self):
        """Test fetch_payslips with invalid date range."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_payslips(
                connection_id="conn_123",
                start_date=datetime(2024, 3, 31),
                end_date=datetime(2024, 3, 1)
            )
        
        assert "start_date must be before or equal to end_date" in str(exc_info.value)
    
    def test_fetch_payslips_invalid_page_size(self):
        """Test fetch_payslips with invalid page size."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Test page_size too small
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_payslips(
                connection_id="conn_123",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                page_size=0
            )
        
        assert "page_size must be between 1 and 200" in str(exc_info.value)
        
        # Test page_size too large
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_payslips(
                connection_id="conn_123",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                page_size=201
            )
        
        assert "page_size must be between 1 and 200" in str(exc_info.value)
    
    def test_fetch_payslips_empty_connection_id(self):
        """Test fetch_payslips with empty connection_id."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(ValueError) as exc_info:
            connector.fetch_payslips(
                connection_id="",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        assert "connection_id cannot be empty" in str(exc_info.value)
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_api_error(self, mock_request, mock_post):
        """Test fetch_payslips handles API errors."""
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock error response
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.json.return_value = {"error": "Internal server error"}
        mock_request.return_value = mock_error_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        with pytest.raises(APIConnectionError) as exc_info:
            connector.fetch_payslips(
                connection_id="conn_123",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31)
            )
        
        assert exc_info.value.status_code == 500
    
    @patch('httpx.Client.post')
    @patch('httpx.Client.request')
    def test_fetch_payslips_multiple_pay_periods(self, mock_request, mock_post):
        """Test fetching payslips handles multiple pay periods per employee."""
        # Mock token refresh
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_token_response
        
        # Mock payslips with multiple pay periods for same employee
        mock_payslips_response = Mock()
        mock_payslips_response.status_code = 200
        mock_payslips_response.json.return_value = [
            {
                "id": "PAY001_JAN",
                "employee_id": "EMP001",
                "pay_period_start": "2024-01-01T00:00:00Z",
                "pay_period_end": "2024-01-31T00:00:00Z",
                "pay_date": "2024-01-31T00:00:00Z",
                "gross_pay": 12500.00,
                "net_pay": 9375.00,
                "deductions": 1875.00,
                "taxes": 1250.00,
                "currency": "USD"
            },
            {
                "id": "PAY001_FEB",
                "employee_id": "EMP001",
                "pay_period_start": "2024-02-01T00:00:00Z",
                "pay_period_end": "2024-02-29T00:00:00Z",
                "pay_date": "2024-02-29T00:00:00Z",
                "gross_pay": 12500.00,
                "net_pay": 9375.00,
                "deductions": 1875.00,
                "taxes": 1250.00,
                "currency": "USD"
            },
            {
                "id": "PAY001_MAR",
                "employee_id": "EMP001",
                "pay_period_start": "2024-03-01T00:00:00Z",
                "pay_period_end": "2024-03-31T00:00:00Z",
                "pay_date": "2024-03-31T00:00:00Z",
                "gross_pay": 12500.00,
                "net_pay": 9375.00,
                "deductions": 1875.00,
                "taxes": 1250.00,
                "currency": "USD"
            }
        ]
        mock_request.return_value = mock_payslips_response
        
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        payslips = connector.fetch_payslips(
            connection_id="conn_123",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31)
        )
        
        # Should get all 3 pay periods for the same employee
        assert len(payslips) == 3
        assert all(p["employee_id"] == "EMP001" for p in payslips)
        assert payslips[0]["id"] == "PAY001_JAN"
        assert payslips[1]["id"] == "PAY001_FEB"
        assert payslips[2]["id"] == "PAY001_MAR"


class TestUnifiedToPayslipTransformation:
    """Test cases for UnifiedToConnector payslip transformation (Task 62)."""
    
    def test_transform_payslip_complete_data(self):
        """Test transforming payslip with all fields present."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_period_start": "2024-03-01T00:00:00Z",
            "pay_period_end": "2024-03-31T00:00:00Z",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00,
            "net_pay": 9375.00,
            "deductions": 1875.00,
            "taxes": 1250.00,
            "currency": "USD",
            "employee_name": "Alice Johnson",
            "department": "Engineering"
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip, "Alpha Development")
        
        assert cost is not None
        assert cost.cost_id == "PAYSLIP_PAY001"
        assert cost.cost_type == "Payroll"
        assert cost.amount == 12500.00
        assert cost.project_name == "Alpha Development"
        assert cost.employee_id == "EMP001"
        assert cost.date.year == 2024
        assert cost.date.month == 3
        assert cost.date.day == 31
        assert cost.is_rd_classified is False
        
        # Check metadata
        assert cost.metadata is not None
        assert cost.metadata["payslip_id"] == "PAY001"
        assert cost.metadata["gross_pay"] == 12500.00
        assert cost.metadata["net_pay"] == 9375.00
        assert cost.metadata["deductions"] == 1875.00
        assert cost.metadata["taxes"] == 1250.00
        assert cost.metadata["currency"] == "USD"
        assert cost.metadata["employee_name"] == "Alice Johnson"
        assert cost.metadata["department"] == "Engineering"
        
        # Check computed hourly rate (12500 / 173.33 ≈ 72.12)
        assert cost.metadata["hourly_rate"] is not None
        assert abs(cost.metadata["hourly_rate"] - 72.12) < 0.1
        
        # Check annual salary (12500 * 12 = 150000)
        assert cost.metadata["annual_salary"] == 150000.00
    
    def test_transform_payslip_missing_optional_fields(self):
        """Test transforming payslip with missing optional fields."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY002",
            "employee_id": "EMP002",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 13750.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        assert cost.cost_id == "PAYSLIP_PAY002"
        assert cost.cost_type == "Payroll"
        assert cost.amount == 13750.00
        assert cost.project_name == "General Operations"  # Default value
        assert cost.employee_id == "EMP002"
        
        # Check metadata has required fields but not optional ones
        assert cost.metadata is not None
        assert cost.metadata["payslip_id"] == "PAY002"
        assert cost.metadata["gross_pay"] == 13750.00
        assert "employee_name" not in cost.metadata
        assert "department" not in cost.metadata
    
    def test_transform_payslip_missing_id(self):
        """Test transforming payslip with missing id."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is None
    
    def test_transform_payslip_missing_employee_id(self):
        """Test transforming payslip with missing employee_id."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is None
    
    def test_transform_payslip_invalid_gross_pay(self):
        """Test transforming payslip with invalid gross_pay."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        # Test zero gross_pay
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 0
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        assert cost is None
        
        # Test negative gross_pay
        raw_payslip["gross_pay"] = -1000.00
        cost = connector._transform_payslip_to_cost(raw_payslip)
        assert cost is None
    
    def test_transform_payslip_missing_pay_date(self):
        """Test transforming payslip with missing pay_date."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is None
    
    def test_transform_payslip_hourly_rate_calculation(self):
        """Test hourly rate calculation from gross pay."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 10000.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        # Hourly rate = 10000 / 173.33 ≈ 57.69
        assert cost.metadata["hourly_rate"] is not None
        assert abs(cost.metadata["hourly_rate"] - 57.69) < 0.1
    
    def test_transform_payslip_annual_salary_calculation(self):
        """Test annual salary calculation from monthly gross pay."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 8333.33
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        # Annual salary = 8333.33 * 12 ≈ 100000
        assert cost.metadata["annual_salary"] is not None
        assert abs(cost.metadata["annual_salary"] - 99999.96) < 0.1
    
    def test_transform_payslip_custom_project_name(self):
        """Test transforming payslip with custom project name."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip, "Beta Project")
        
        assert cost is not None
        assert cost.project_name == "Beta Project"
    
    def test_transform_payslip_default_project_name(self):
        """Test transforming payslip with default project name."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        assert cost.project_name == "General Operations"
    
    def test_transform_payslip_computed_hourly_rate_from_metadata(self):
        """Test that ProjectCost.hourly_rate computed field works with metadata."""
        connector = UnifiedToConnector(
            api_key="test_key",
            workspace_id="workspace123"
        )
        
        raw_payslip = {
            "id": "PAY001",
            "employee_id": "EMP001",
            "pay_date": "2024-03-31T00:00:00Z",
            "gross_pay": 12500.00
        }
        
        cost = connector._transform_payslip_to_cost(raw_payslip)
        
        assert cost is not None
        # Test the computed field from ProjectCost model
        assert cost.hourly_rate is not None
        assert abs(cost.hourly_rate - 72.12) < 0.1
