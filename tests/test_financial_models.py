"""
Unit tests for financial data models.

Tests the EmployeeTimeEntry and ProjectCost Pydantic models to ensure proper
validation, serialization, and integration with Phase 1 JSON fixtures.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.financial_models import EmployeeTimeEntry, ProjectCost


class TestEmployeeTimeEntry:
    """Test suite for EmployeeTimeEntry model."""
    
    def test_valid_entry_creation(self):
        """Test creating a valid EmployeeTimeEntry."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Implemented new authentication algorithm",
            hours_spent=8.5,
            date="2024-03-15T09:00:00",
            is_rd_classified=True
        )
        
        assert entry.employee_id == "EMP001"
        assert entry.employee_name == "Alice Johnson"
        assert entry.project_name == "Alpha Development"
        assert entry.hours_spent == 8.5
        assert entry.is_rd_classified is True
    
    def test_hours_spent_validation_exceeds_24(self):
        """Test that hours_spent > 24 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Test Project",
                task_description="Test task",
                hours_spent=25.0,
                date="2024-03-15T09:00:00"
            )
        
        # Check that validation error is raised for hours_spent field
        assert "hours_spent" in str(exc_info.value)
    
    def test_hours_spent_validation_negative(self):
        """Test that negative hours_spent raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Test Project",
                task_description="Test task",
                hours_spent=-1.0,
                date="2024-03-15T09:00:00"
            )
        
        # Check that validation error is raised for hours_spent field
        assert "hours_spent" in str(exc_info.value)
        assert "greater than 0" in str(exc_info.value)
    
    def test_hours_spent_validation_zero(self):
        """Test that zero hours_spent raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Test Project",
                task_description="Test task",
                hours_spent=0.0,
                date="2024-03-15T09:00:00"
            )
        
        # Check that validation error is raised for hours_spent field
        assert "hours_spent" in str(exc_info.value)
        assert "greater than 0" in str(exc_info.value)
    
    def test_date_validation_future_date(self):
        """Test that future dates raise ValidationError."""
        future_date = "2030-12-31T09:00:00"
        
        with pytest.raises(ValidationError) as exc_info:
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Test Project",
                task_description="Test task",
                hours_spent=8.0,
                date=future_date
            )
        
        assert "date cannot be in the future" in str(exc_info.value)
    
    def test_is_rd_classified_default_value(self):
        """Test that is_rd_classified defaults to False."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=8.0,
            date="2024-03-15T09:00:00"
        )
        
        assert entry.is_rd_classified is False
    
    def test_json_serialization(self):
        """Test JSON serialization of EmployeeTimeEntry."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Implemented new authentication algorithm",
            hours_spent=8.5,
            date="2024-03-15T09:00:00",
            is_rd_classified=True
        )
        
        json_str = entry.model_dump_json()
        assert "EMP001" in json_str
        assert "Alice Johnson" in json_str
        assert "8.5" in json_str
    
    def test_json_deserialization(self):
        """Test JSON deserialization into EmployeeTimeEntry."""
        json_data = {
            "employee_id": "EMP001",
            "employee_name": "Alice Johnson",
            "project_name": "Alpha Development",
            "task_description": "Implemented new authentication algorithm",
            "hours_spent": 8.5,
            "date": "2024-03-15T09:00:00",
            "is_rd_classified": True
        }
        
        entry = EmployeeTimeEntry(**json_data)
        
        assert entry.employee_id == "EMP001"
        assert entry.employee_name == "Alice Johnson"
        assert entry.hours_spent == 8.5
        assert entry.is_rd_classified is True
    
    def test_str_method(self):
        """Test the __str__ method returns formatted string."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Test task",
            hours_spent=8.5,
            date="2024-03-15T09:00:00"
        )
        
        str_repr = str(entry)
        assert "EMP001" in str_repr
        assert "Alice Johnson" in str_repr
        assert "8.5" in str_repr
        assert "Alpha Development" in str_repr
        assert "2024-03-15" in str_repr
    
    def test_phase1_fixture_compatibility(self):
        """Test that the model is compatible with Phase 1 sample_time_entries.json."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_time_entries.json"
        
        # Load the Phase 1 fixture
        with open(fixture_path, 'r') as f:
            time_entries_data = json.load(f)
        
        # Validate that all entries can be parsed
        entries = []
        for entry_data in time_entries_data:
            entry = EmployeeTimeEntry(**entry_data)
            entries.append(entry)
        
        # Verify we loaded all entries
        assert len(entries) == len(time_entries_data)
        
        # Spot check first entry
        first_entry = entries[0]
        assert first_entry.employee_id == "EMP001"
        assert first_entry.employee_name == "Alice Johnson"
        assert first_entry.project_name == "Alpha Development"
        assert first_entry.hours_spent == 8.5
        assert first_entry.is_rd_classified is True
    
    def test_phase1_fixture_round_trip(self):
        """Test that we can load Phase 1 fixture, convert to models, and serialize back."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_time_entries.json"
        
        # Load the Phase 1 fixture
        with open(fixture_path, 'r') as f:
            original_data = json.load(f)
        
        # Convert to Pydantic models
        entries = [EmployeeTimeEntry(**entry_data) for entry_data in original_data]
        
        # Serialize back to JSON
        serialized_data = [json.loads(entry.model_dump_json()) for entry in entries]
        
        # Verify key fields match
        for original, serialized in zip(original_data, serialized_data):
            assert original["employee_id"] == serialized["employee_id"]
            assert original["employee_name"] == serialized["employee_name"]
            assert original["project_name"] == serialized["project_name"]
            assert original["hours_spent"] == serialized["hours_spent"]
            assert original["is_rd_classified"] == serialized["is_rd_classified"]



class TestProjectCost:
    """Test suite for ProjectCost model."""
    
    def test_valid_cost_creation(self):
        """Test creating a valid ProjectCost."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Alpha Development",
            employee_id="EMP001",
            date="2024-03-31T00:00:00",
            is_rd_classified=True,
            metadata={
                "annual_salary": 150000.00,
                "hourly_rate": 72.12,
                "pay_period": "2024-03",
                "department": "Engineering"
            }
        )
        
        assert cost.cost_id == "PAY001"
        assert cost.cost_type == "Payroll"
        assert cost.amount == 12500.00
        assert cost.project_name == "Alpha Development"
        assert cost.employee_id == "EMP001"
        assert cost.is_rd_classified is True
        assert cost.metadata["annual_salary"] == 150000.00
    
    def test_cost_type_validation_invalid(self):
        """Test that invalid cost_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCost(
                cost_id="COST001",
                cost_type="InvalidType",
                amount=1000.00,
                project_name="Test Project",
                date="2024-03-15T00:00:00"
            )
        
        assert "cost_type must be one of" in str(exc_info.value)
    
    def test_cost_type_validation_valid_types(self):
        """Test that all valid cost types are accepted."""
        valid_types = ["Payroll", "Contractor", "Materials", "Cloud", "Other"]
        
        for cost_type in valid_types:
            cost = ProjectCost(
                cost_id=f"COST_{cost_type}",
                cost_type=cost_type,
                amount=1000.00,
                project_name="Test Project",
                date="2024-03-15T00:00:00"
            )
            assert cost.cost_type == cost_type
    
    def test_amount_validation_negative(self):
        """Test that negative amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=-1000.00,
                project_name="Test Project",
                date="2024-03-15T00:00:00"
            )
        
        assert "amount" in str(exc_info.value)
        assert "greater than 0" in str(exc_info.value)
    
    def test_amount_validation_zero(self):
        """Test that zero amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=0.0,
                project_name="Test Project",
                date="2024-03-15T00:00:00"
            )
        
        assert "amount" in str(exc_info.value)
        assert "greater than 0" in str(exc_info.value)
    
    def test_optional_employee_id(self):
        """Test that employee_id is optional (for non-payroll costs)."""
        cost = ProjectCost(
            cost_id="MAT001",
            cost_type="Materials",
            amount=5000.00,
            project_name="Beta Infrastructure",
            date="2024-03-10T00:00:00"
        )
        
        assert cost.employee_id is None
    
    def test_hourly_rate_computation_from_metadata(self):
        """Test hourly_rate computed field retrieves from metadata."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Alpha Development",
            employee_id="EMP001",
            date="2024-03-31T00:00:00",
            metadata={
                "annual_salary": 150000.00,
                "hourly_rate": 72.12
            }
        )
        
        assert cost.hourly_rate == 72.12
    
    def test_hourly_rate_computation_from_annual_salary(self):
        """Test hourly_rate computed field calculates from annual_salary."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Alpha Development",
            employee_id="EMP001",
            date="2024-03-31T00:00:00",
            metadata={
                "annual_salary": 120000.00
            }
        )
        
        # 120000 / 2080 = 57.69
        assert cost.hourly_rate == 57.69
    
    def test_hourly_rate_none_without_metadata(self):
        """Test hourly_rate returns None when metadata is not provided."""
        cost = ProjectCost(
            cost_id="MAT001",
            cost_type="Materials",
            amount=5000.00,
            project_name="Beta Infrastructure",
            date="2024-03-10T00:00:00"
        )
        
        assert cost.hourly_rate is None
    
    def test_is_rd_classified_default_value(self):
        """Test that is_rd_classified defaults to False."""
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Payroll",
            amount=1000.00,
            project_name="Test Project",
            date="2024-03-15T00:00:00"
        )
        
        assert cost.is_rd_classified is False
    
    def test_json_serialization(self):
        """Test JSON serialization of ProjectCost."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Alpha Development",
            employee_id="EMP001",
            date="2024-03-31T00:00:00",
            is_rd_classified=True,
            metadata={"annual_salary": 150000.00}
        )
        
        json_str = cost.model_dump_json()
        assert "PAY001" in json_str
        assert "Payroll" in json_str
        assert "12500" in json_str
    
    def test_json_deserialization(self):
        """Test JSON deserialization into ProjectCost."""
        json_data = {
            "cost_id": "PAY001",
            "cost_type": "Payroll",
            "amount": 12500.00,
            "project_name": "Alpha Development",
            "employee_id": "EMP001",
            "date": "2024-03-31T00:00:00",
            "is_rd_classified": True,
            "metadata": {
                "annual_salary": 150000.00,
                "hourly_rate": 72.12
            }
        }
        
        cost = ProjectCost(**json_data)
        
        assert cost.cost_id == "PAY001"
        assert cost.cost_type == "Payroll"
        assert cost.amount == 12500.00
        assert cost.is_rd_classified is True
        assert cost.hourly_rate == 72.12
    
    def test_str_method(self):
        """Test the __str__ method returns formatted string."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Alpha Development",
            employee_id="EMP001",
            date="2024-03-31T00:00:00"
        )
        
        str_repr = str(cost)
        assert "PAY001" in str_repr
        assert "Payroll" in str_repr
        assert "12500.00" in str_repr
        assert "Alpha Development" in str_repr
        assert "2024-03-31" in str_repr
        assert "EMP001" in str_repr
    
    def test_str_method_without_employee(self):
        """Test __str__ method for non-payroll costs without employee_id."""
        cost = ProjectCost(
            cost_id="MAT001",
            cost_type="Materials",
            amount=5000.00,
            project_name="Beta Infrastructure",
            date="2024-03-10T00:00:00"
        )
        
        str_repr = str(cost)
        assert "MAT001" in str_repr
        assert "Materials" in str_repr
        assert "5000.00" in str_repr
        assert "Beta Infrastructure" in str_repr
        # Should not contain employee info
        assert "Employee:" not in str_repr
    
    def test_phase1_fixture_compatibility(self):
        """Test that the model is compatible with Phase 1 sample_payroll_data.json."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_payroll_data.json"
        
        # Load the Phase 1 fixture
        with open(fixture_path, 'r') as f:
            payroll_data = json.load(f)
        
        # Validate that all entries can be parsed
        costs = []
        for cost_data in payroll_data:
            cost = ProjectCost(**cost_data)
            costs.append(cost)
        
        # Verify we loaded all entries
        assert len(costs) == len(payroll_data)
        
        # Spot check first entry (payroll)
        first_cost = costs[0]
        assert first_cost.cost_id == "PAY001"
        assert first_cost.cost_type == "Payroll"
        assert first_cost.amount == 12500.00
        assert first_cost.project_name == "Alpha Development"
        assert first_cost.employee_id == "EMP001"
        assert first_cost.is_rd_classified is True
        assert first_cost.hourly_rate == 72.12
        
        # Spot check contractor entry (no employee_id)
        contractor_cost = costs[7]
        assert contractor_cost.cost_id == "CONT001"
        assert contractor_cost.cost_type == "Contractor"
        assert contractor_cost.employee_id is None
    
    def test_phase1_fixture_round_trip(self):
        """Test that we can load Phase 1 fixture, convert to models, and serialize back."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_payroll_data.json"
        
        # Load the Phase 1 fixture
        with open(fixture_path, 'r') as f:
            original_data = json.load(f)
        
        # Convert to Pydantic models
        costs = [ProjectCost(**cost_data) for cost_data in original_data]
        
        # Serialize back to JSON
        serialized_data = [json.loads(cost.model_dump_json()) for cost in costs]
        
        # Verify key fields match
        for original, serialized in zip(original_data, serialized_data):
            assert original["cost_id"] == serialized["cost_id"]
            assert original["cost_type"] == serialized["cost_type"]
            assert original["amount"] == serialized["amount"]
            assert original["project_name"] == serialized["project_name"]
            assert original["is_rd_classified"] == serialized["is_rd_classified"]
            
            # employee_id can be None
            assert original.get("employee_id") == serialized.get("employee_id")
