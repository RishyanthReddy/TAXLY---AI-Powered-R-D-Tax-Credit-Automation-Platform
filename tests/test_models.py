"""
Unit tests for EmployeeTimeEntry model.

This test module focuses on validating the EmployeeTimeEntry Pydantic model
to ensure proper validation, serialization, and data integrity for R&D tax
credit time tracking data.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import ValidationError
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.financial_models import EmployeeTimeEntry, ProjectCost
from models.tax_models import QualifiedProject


class TestEmployeeTimeEntry:
    """Test suite for EmployeeTimeEntry model validation and functionality."""
    
    def test_valid_entry_creation(self):
        """Test creating a valid EmployeeTimeEntry with all required fields."""
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
        assert entry.task_description == "Implemented new authentication algorithm"
        assert entry.hours_spent == 8.5
        assert entry.is_rd_classified is True
        assert isinstance(entry.date, datetime)
    
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
        
        # Verify the error is for hours_spent field
        error_str = str(exc_info.value)
        assert "hours_spent" in error_str
        assert "24" in error_str or "exceed" in error_str.lower()
    
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
        
        # Verify the error is for hours_spent field
        error_str = str(exc_info.value)
        assert "hours_spent" in error_str
        assert "greater than 0" in error_str or "positive" in error_str.lower()
    
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
        
        # Verify the error is for hours_spent field
        error_str = str(exc_info.value)
        assert "hours_spent" in error_str
        assert "greater than 0" in error_str or "positive" in error_str.lower()
    
    def test_hours_spent_validation_boundary_valid(self):
        """Test that hours_spent at boundary values (0.1 and 24.0) are valid."""
        # Test minimum valid value
        entry_min = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=0.1,
            date="2024-03-15T09:00:00"
        )
        assert entry_min.hours_spent == 0.1
        
        # Test maximum valid value
        entry_max = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=24.0,
            date="2024-03-15T09:00:00"
        )
        assert entry_max.hours_spent == 24.0
    
    def test_date_validation_future_date(self):
        """Test that future dates raise ValidationError."""
        # Create a date far in the future
        future_date = datetime.now() + timedelta(days=365)
        
        with pytest.raises(ValidationError) as exc_info:
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Test Project",
                task_description="Test task",
                hours_spent=8.0,
                date=future_date
            )
        
        error_str = str(exc_info.value)
        assert "date" in error_str.lower()
        assert "future" in error_str.lower()
    
    def test_date_validation_current_date(self):
        """Test that current date is valid."""
        current_date = datetime.now()
        
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=8.0,
            date=current_date
        )
        
        assert entry.date <= datetime.now()
    
    def test_date_validation_past_date(self):
        """Test that past dates are valid."""
        past_date = datetime.now() - timedelta(days=30)
        
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=8.0,
            date=past_date
        )
        
        assert entry.date < datetime.now()
    
    def test_is_rd_classified_default_value(self):
        """Test that is_rd_classified defaults to False when not provided."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=8.0,
            date="2024-03-15T09:00:00"
        )
        
        assert entry.is_rd_classified is False
    
    def test_is_rd_classified_explicit_true(self):
        """Test that is_rd_classified can be explicitly set to True."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=8.0,
            date="2024-03-15T09:00:00",
            is_rd_classified=True
        )
        
        assert entry.is_rd_classified is True
    
    def test_is_rd_classified_explicit_false(self):
        """Test that is_rd_classified can be explicitly set to False."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=8.0,
            date="2024-03-15T09:00:00",
            is_rd_classified=False
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
        
        # Serialize to JSON string
        json_str = entry.model_dump_json()
        
        # Verify JSON contains expected data
        assert isinstance(json_str, str)
        assert "EMP001" in json_str
        assert "Alice Johnson" in json_str
        assert "Alpha Development" in json_str
        assert "8.5" in json_str
        assert "true" in json_str.lower()  # is_rd_classified
        
        # Verify it's valid JSON
        json_dict = json.loads(json_str)
        assert json_dict["employee_id"] == "EMP001"
        assert json_dict["hours_spent"] == 8.5
    
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
        
        # Deserialize from dictionary
        entry = EmployeeTimeEntry(**json_data)
        
        # Verify all fields are correctly deserialized
        assert entry.employee_id == "EMP001"
        assert entry.employee_name == "Alice Johnson"
        assert entry.project_name == "Alpha Development"
        assert entry.task_description == "Implemented new authentication algorithm"
        assert entry.hours_spent == 8.5
        assert entry.is_rd_classified is True
        assert isinstance(entry.date, datetime)
    
    def test_json_round_trip(self):
        """Test that serialization and deserialization preserve data integrity."""
        original_entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Implemented new authentication algorithm",
            hours_spent=8.5,
            date="2024-03-15T09:00:00",
            is_rd_classified=True
        )
        
        # Serialize to JSON
        json_str = original_entry.model_dump_json()
        
        # Deserialize back to object
        json_dict = json.loads(json_str)
        restored_entry = EmployeeTimeEntry(**json_dict)
        
        # Verify all fields match
        assert restored_entry.employee_id == original_entry.employee_id
        assert restored_entry.employee_name == original_entry.employee_name
        assert restored_entry.project_name == original_entry.project_name
        assert restored_entry.task_description == original_entry.task_description
        assert restored_entry.hours_spent == original_entry.hours_spent
        assert restored_entry.is_rd_classified == original_entry.is_rd_classified
        assert restored_entry.date == original_entry.date
    
    def test_model_dump(self):
        """Test model_dump() returns dictionary with correct structure."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Test task",
            hours_spent=8.5,
            date="2024-03-15T09:00:00",
            is_rd_classified=True
        )
        
        data_dict = entry.model_dump()
        
        assert isinstance(data_dict, dict)
        assert data_dict["employee_id"] == "EMP001"
        assert data_dict["employee_name"] == "Alice Johnson"
        assert data_dict["project_name"] == "Alpha Development"
        assert data_dict["hours_spent"] == 8.5
        assert data_dict["is_rd_classified"] is True
        assert isinstance(data_dict["date"], datetime)
    
    def test_required_fields_validation(self):
        """Test that missing required fields raise ValidationError."""
        # Missing employee_id
        with pytest.raises(ValidationError):
            EmployeeTimeEntry(
                employee_name="Alice Johnson",
                project_name="Test Project",
                task_description="Test task",
                hours_spent=8.0,
                date="2024-03-15T09:00:00"
            )
        
        # Missing employee_name
        with pytest.raises(ValidationError):
            EmployeeTimeEntry(
                employee_id="EMP001",
                project_name="Test Project",
                task_description="Test task",
                hours_spent=8.0,
                date="2024-03-15T09:00:00"
            )
        
        # Missing project_name
        with pytest.raises(ValidationError):
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                task_description="Test task",
                hours_spent=8.0,
                date="2024-03-15T09:00:00"
            )
        
        # Missing hours_spent
        with pytest.raises(ValidationError):
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Test Project",
                task_description="Test task",
                date="2024-03-15T09:00:00"
            )
        
        # Missing date
        with pytest.raises(ValidationError):
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Test Project",
                task_description="Test task",
                hours_spent=8.0
            )
    
    def test_str_representation(self):
        """Test the __str__ method returns a formatted string."""
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Test task",
            hours_spent=8.5,
            date="2024-03-15T09:00:00"
        )
        
        str_repr = str(entry)
        
        # Verify string contains key information
        assert "EMP001" in str_repr
        assert "Alice Johnson" in str_repr
        assert "8.5" in str_repr
        assert "Alpha Development" in str_repr
        assert "2024-03-15" in str_repr



class TestProjectCost:
    """Test suite for ProjectCost model validation and functionality."""
    
    def test_valid_cost_creation(self):
        """Test creating a valid ProjectCost with all required fields."""
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
        assert isinstance(cost.date, datetime)
        assert cost.metadata is not None
        assert cost.metadata["annual_salary"] == 150000.00
    
    def test_cost_type_validation_valid_types(self):
        """Test that all valid cost types are accepted."""
        valid_types = ["Payroll", "Contractor", "Materials", "Cloud", "Other"]
        
        for cost_type in valid_types:
            cost = ProjectCost(
                cost_id="COST001",
                cost_type=cost_type,
                amount=1000.00,
                project_name="Test Project",
                date="2024-03-31T00:00:00"
            )
            assert cost.cost_type == cost_type
    
    def test_cost_type_validation_invalid_type(self):
        """Test that invalid cost_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCost(
                cost_id="COST001",
                cost_type="InvalidType",
                amount=1000.00,
                project_name="Test Project",
                date="2024-03-31T00:00:00"
            )
        
        error_str = str(exc_info.value)
        assert "cost_type" in error_str
        assert "InvalidType" in error_str or "must be one of" in error_str
    
    def test_cost_type_validation_case_sensitive(self):
        """Test that cost_type validation is case-sensitive."""
        with pytest.raises(ValidationError):
            ProjectCost(
                cost_id="COST001",
                cost_type="payroll",  # lowercase should fail
                amount=1000.00,
                project_name="Test Project",
                date="2024-03-31T00:00:00"
            )
    
    def test_amount_validation_negative(self):
        """Test that negative amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=-1000.00,
                project_name="Test Project",
                date="2024-03-31T00:00:00"
            )
        
        error_str = str(exc_info.value)
        assert "amount" in error_str
        assert "positive" in error_str.lower() or "greater than 0" in error_str
    
    def test_amount_validation_zero(self):
        """Test that zero amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=0.0,
                project_name="Test Project",
                date="2024-03-31T00:00:00"
            )
        
        error_str = str(exc_info.value)
        assert "amount" in error_str
        assert "positive" in error_str.lower() or "greater than 0" in error_str
    
    def test_amount_validation_positive(self):
        """Test that positive amounts are valid."""
        # Test small positive amount
        cost_small = ProjectCost(
            cost_id="COST001",
            cost_type="Materials",
            amount=0.01,
            project_name="Test Project",
            date="2024-03-31T00:00:00"
        )
        assert cost_small.amount == 0.01
        
        # Test large positive amount
        cost_large = ProjectCost(
            cost_id="COST002",
            cost_type="Cloud",
            amount=999999.99,
            project_name="Test Project",
            date="2024-03-31T00:00:00"
        )
        assert cost_large.amount == 999999.99
    
    def test_optional_employee_id_none(self):
        """Test that employee_id can be None for non-payroll costs."""
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Materials",
            amount=5000.00,
            project_name="Test Project",
            date="2024-03-31T00:00:00"
        )
        
        assert cost.employee_id is None
    
    def test_optional_employee_id_provided(self):
        """Test that employee_id can be provided when needed."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Test Project",
            employee_id="EMP001",
            date="2024-03-31T00:00:00"
        )
        
        assert cost.employee_id == "EMP001"
    
    def test_optional_employee_id_empty_string(self):
        """Test that empty string employee_id is accepted."""
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Contractor",
            amount=8000.00,
            project_name="Test Project",
            employee_id="",
            date="2024-03-31T00:00:00"
        )
        
        assert cost.employee_id == ""
    
    def test_hourly_rate_computation_from_metadata(self):
        """Test that hourly_rate is retrieved from metadata when provided."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Test Project",
            employee_id="EMP001",
            date="2024-03-31T00:00:00",
            metadata={"hourly_rate": 72.12}
        )
        
        assert cost.hourly_rate == 72.12
    
    def test_hourly_rate_computation_from_annual_salary(self):
        """Test that hourly_rate is calculated from annual_salary."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Test Project",
            employee_id="EMP001",
            date="2024-03-31T00:00:00",
            metadata={"annual_salary": 150000.00}
        )
        
        # 150000 / 2080 = 72.115... rounded to 72.12
        assert cost.hourly_rate == 72.12
    
    def test_hourly_rate_computation_with_custom_annual_hours(self):
        """Test that hourly_rate calculation uses custom annual_hours if provided."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Test Project",
            employee_id="EMP001",
            date="2024-03-31T00:00:00",
            metadata={
                "annual_salary": 100000.00,
                "annual_hours": 2000.0
            }
        )
        
        # 100000 / 2000 = 50.00
        assert cost.hourly_rate == 50.00
    
    def test_hourly_rate_computation_no_metadata(self):
        """Test that hourly_rate returns None when metadata is not provided."""
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Materials",
            amount=5000.00,
            project_name="Test Project",
            date="2024-03-31T00:00:00"
        )
        
        assert cost.hourly_rate is None
    
    def test_hourly_rate_computation_empty_metadata(self):
        """Test that hourly_rate returns None when metadata is empty."""
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Cloud",
            amount=3000.00,
            project_name="Test Project",
            date="2024-03-31T00:00:00",
            metadata={}
        )
        
        assert cost.hourly_rate is None
    
    def test_hourly_rate_computation_priority(self):
        """Test that hourly_rate from metadata takes priority over calculation."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Test Project",
            employee_id="EMP001",
            date="2024-03-31T00:00:00",
            metadata={
                "hourly_rate": 80.00,
                "annual_salary": 150000.00  # Would calculate to 72.12
            }
        )
        
        # Should use the explicit hourly_rate, not calculate from annual_salary
        assert cost.hourly_rate == 80.00
    
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
            metadata={"hourly_rate": 72.12}
        )
        
        json_str = cost.model_dump_json()
        
        assert isinstance(json_str, str)
        assert "PAY001" in json_str
        assert "Payroll" in json_str
        assert "12500" in json_str
        assert "Alpha Development" in json_str
        assert "EMP001" in json_str
        
        # Verify it's valid JSON
        json_dict = json.loads(json_str)
        assert json_dict["cost_id"] == "PAY001"
        assert json_dict["amount"] == 12500.00
    
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
            "metadata": {"hourly_rate": 72.12}
        }
        
        cost = ProjectCost(**json_data)
        
        assert cost.cost_id == "PAY001"
        assert cost.cost_type == "Payroll"
        assert cost.amount == 12500.00
        assert cost.project_name == "Alpha Development"
        assert cost.employee_id == "EMP001"
        assert cost.is_rd_classified is True
        assert isinstance(cost.date, datetime)
        assert cost.metadata["hourly_rate"] == 72.12
    
    def test_required_fields_validation(self):
        """Test that missing required fields raise ValidationError."""
        # Missing cost_id
        with pytest.raises(ValidationError):
            ProjectCost(
                cost_type="Payroll",
                amount=1000.00,
                project_name="Test Project",
                date="2024-03-31T00:00:00"
            )
        
        # Missing cost_type
        with pytest.raises(ValidationError):
            ProjectCost(
                cost_id="COST001",
                amount=1000.00,
                project_name="Test Project",
                date="2024-03-31T00:00:00"
            )
        
        # Missing amount
        with pytest.raises(ValidationError):
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                project_name="Test Project",
                date="2024-03-31T00:00:00"
            )
        
        # Missing project_name
        with pytest.raises(ValidationError):
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=1000.00,
                date="2024-03-31T00:00:00"
            )
        
        # Missing date
        with pytest.raises(ValidationError):
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=1000.00,
                project_name="Test Project"
            )
    
    def test_str_representation(self):
        """Test the __str__ method returns a formatted string."""
        cost = ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Alpha Development",
            employee_id="EMP001",
            date="2024-03-31T00:00:00"
        )
        
        str_repr = str(cost)
        
        # Verify string contains key information
        assert "PAY001" in str_repr
        assert "Payroll" in str_repr
        assert "12500.00" in str_repr
        assert "Alpha Development" in str_repr
        assert "EMP001" in str_repr
        assert "2024-03-31" in str_repr
    
    def test_str_representation_without_employee_id(self):
        """Test __str__ method when employee_id is None."""
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Materials",
            amount=5000.00,
            project_name="Test Project",
            date="2024-03-31T00:00:00"
        )
        
        str_repr = str(cost)
        
        # Verify string contains key information but not employee_id
        assert "COST001" in str_repr
        assert "Materials" in str_repr
        assert "5000.00" in str_repr
        assert "Test Project" in str_repr
        # Should not contain employee reference when None
        assert "Employee:" not in str_repr or "None" not in str_repr
    
    def test_is_rd_classified_default_value(self):
        """Test that is_rd_classified defaults to False when not provided."""
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Cloud",
            amount=3000.00,
            project_name="Test Project",
            date="2024-03-31T00:00:00"
        )
        
        assert cost.is_rd_classified is False
    
    def test_metadata_optional(self):
        """Test that metadata is optional and defaults to None."""
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Contractor",
            amount=8000.00,
            project_name="Test Project",
            date="2024-03-31T00:00:00"
        )
        
        assert cost.metadata is None



class TestQualifiedProject:
    """Test suite for QualifiedProject model validation and functionality."""
    
    def test_valid_qualified_project_creation(self):
        """Test creating a valid QualifiedProject with all required fields."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="The project involves developing a new authentication algorithm...",
            reasoning="This project clearly meets the four-part test...",
            irs_source="CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research"
        )
        
        assert project.project_name == "Alpha Development"
        assert project.qualified_hours == 14.5
        assert project.qualified_cost == 1045.74
        assert project.confidence_score == 0.92
        assert project.qualification_percentage == 95.0
        assert project.flagged_for_review is False
        assert project.estimated_credit == 209.15
    
    def test_confidence_score_validation_valid_range(self):
        """Test that confidence_score within 0-1 range is valid."""
        # Test minimum valid value
        project_min = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.0,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_min.confidence_score == 0.0
        
        # Test maximum valid value
        project_max = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=1.0,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_max.confidence_score == 1.0
        
        # Test mid-range value
        project_mid = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.5,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_mid.confidence_score == 0.5
    
    def test_confidence_score_validation_below_range(self):
        """Test that confidence_score < 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=-0.1,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "confidence_score" in error_str
    
    def test_confidence_score_validation_above_range(self):
        """Test that confidence_score > 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=1.5,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "confidence_score" in error_str
    
    def test_auto_flagging_low_confidence(self):
        """Test that projects with confidence < 0.7 are automatically flagged."""
        # Test with confidence = 0.69 (should be flagged)
        project_low = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.69,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_low.flagged_for_review is True
        
        # Test with confidence = 0.5 (should be flagged)
        project_very_low = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.5,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_very_low.flagged_for_review is True
    
    def test_auto_flagging_high_confidence(self):
        """Test that projects with confidence >= 0.7 are not auto-flagged."""
        # Test with confidence = 0.7 (should NOT be flagged)
        project_threshold = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.7,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_threshold.flagged_for_review is False
        
        # Test with confidence = 0.9 (should NOT be flagged)
        project_high = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.9,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_high.flagged_for_review is False
    
    def test_manual_flagging_overrides_auto_flag(self):
        """Test that explicitly setting flagged_for_review=True works even with high confidence."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.95,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source",
            flagged_for_review=True
        )
        assert project.flagged_for_review is True
    
    def test_qualification_percentage_validation_valid_range(self):
        """Test that qualification_percentage within 0-100 range is valid."""
        # Test minimum valid value
        project_min = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=0.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_min.qualification_percentage == 0.0
        
        # Test maximum valid value
        project_max = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=100.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_max.qualification_percentage == 100.0
        
        # Test mid-range value
        project_mid = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_mid.qualification_percentage == 50.0
    
    def test_qualification_percentage_validation_below_range(self):
        """Test that qualification_percentage < 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=-5.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "qualification_percentage" in error_str
    
    def test_qualification_percentage_validation_above_range(self):
        """Test that qualification_percentage > 100 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=105.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "qualification_percentage" in error_str
    
    def test_estimated_credit_computation(self):
        """Test that estimated_credit is correctly calculated as 20% of qualified_cost."""
        # Test with $1000 cost (should be $200 credit)
        project1 = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project1.estimated_credit == 200.0
        
        # Test with $1045.74 cost (should be $209.15 credit)
        project2 = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project2.estimated_credit == 209.15
        
        # Test with $5000 cost (should be $1000 credit)
        project3 = QualifiedProject(
            project_name="Test Project",
            qualified_hours=50.0,
            qualified_cost=5000.0,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project3.estimated_credit == 1000.0
    
    def test_estimated_credit_computation_zero_cost(self):
        """Test that estimated_credit is 0 when qualified_cost is 0."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=0.0,
            qualified_cost=0.0,
            confidence_score=0.8,
            qualification_percentage=0.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project.estimated_credit == 0.0
    
    def test_estimated_credit_rounding(self):
        """Test that estimated_credit is properly rounded to 2 decimal places."""
        # Test with cost that results in repeating decimal
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=333.33,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        # 333.33 * 0.20 = 66.666, should round to 66.67
        assert project.estimated_credit == 66.67
    
    def test_json_serialization(self):
        """Test JSON serialization of QualifiedProject."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="The project involves developing a new authentication algorithm...",
            reasoning="This project clearly meets the four-part test...",
            irs_source="CFR Title 26 § 1.41-4(a)(1)"
        )
        
        json_str = project.model_dump_json()
        
        assert isinstance(json_str, str)
        assert "Alpha Development" in json_str
        assert "14.5" in json_str
        assert "1045.74" in json_str
        assert "0.92" in json_str
        assert "95" in json_str
        
        # Verify it's valid JSON
        json_dict = json.loads(json_str)
        assert json_dict["project_name"] == "Alpha Development"
        assert json_dict["confidence_score"] == 0.92
    
    def test_json_deserialization(self):
        """Test JSON deserialization into QualifiedProject."""
        json_data = {
            "project_name": "Alpha Development",
            "qualified_hours": 14.5,
            "qualified_cost": 1045.74,
            "confidence_score": 0.92,
            "qualification_percentage": 95.0,
            "supporting_citation": "The project involves developing a new authentication algorithm...",
            "reasoning": "This project clearly meets the four-part test...",
            "irs_source": "CFR Title 26 § 1.41-4(a)(1)"
        }
        
        project = QualifiedProject(**json_data)
        
        assert project.project_name == "Alpha Development"
        assert project.qualified_hours == 14.5
        assert project.qualified_cost == 1045.74
        assert project.confidence_score == 0.92
        assert project.qualification_percentage == 95.0
        assert project.estimated_credit == 209.15
    
    def test_str_representation(self):
        """Test the __str__ method returns a formatted string."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        str_repr = str(project)
        
        # Verify string contains key information
        assert "Alpha Development" in str_repr
        assert "14.5" in str_repr
        assert "1045.74" in str_repr
        assert "95" in str_repr
        assert "0.92" in str_repr
        assert "FLAGGED" not in str_repr  # High confidence, not flagged
    
    def test_str_representation_flagged(self):
        """Test __str__ method includes flag indicator for flagged projects."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.65,  # Low confidence, will be auto-flagged
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        str_repr = str(project)
        
        # Verify string contains flag indicator
        assert "FLAGGED FOR REVIEW" in str_repr
    
    def test_technical_details_optional(self):
        """Test that technical_details is optional and defaults to None."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        assert project.technical_details is None
    
    def test_technical_details_provided(self):
        """Test that technical_details can be provided with custom data."""
        technical_info = {
            "technological_uncertainty": "Uncertainty about encryption methods",
            "experimentation_process": "Tested multiple algorithms",
            "business_component": "Authentication System"
        }
        
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source",
            technical_details=technical_info
        )
        
        assert project.technical_details is not None
        assert project.technical_details["technological_uncertainty"] == "Uncertainty about encryption methods"
        assert project.technical_details["business_component"] == "Authentication System"
    
    def test_required_fields_validation(self):
        """Test that missing required fields raise ValidationError."""
        # Missing project_name
        with pytest.raises(ValidationError):
            QualifiedProject(
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        # Missing confidence_score
        with pytest.raises(ValidationError):
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        # Missing supporting_citation
        with pytest.raises(ValidationError):
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=50.0,
                reasoning="Test reasoning",
                irs_source="Test source"
            )

c
lass TestQualifiedProject:
    """Test suite for QualifiedProject model validation and functionality."""
    
    def test_valid_qualified_project_creation(self):
        """Test creating a valid QualifiedProject with all required fields."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="The project involves developing a new authentication algorithm...",
            reasoning="This project clearly meets the four-part test...",
            irs_source="CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research"
        )
        
        assert project.project_name == "Alpha Development"
        assert project.qualified_hours == 14.5
        assert project.qualified_cost == 1045.74
        assert project.confidence_score == 0.92
        assert project.qualification_percentage == 95.0
        assert project.flagged_for_review is False
        assert project.estimated_credit == 209.15
    
    def test_confidence_score_validation_valid_range(self):
        """Test that confidence_score within 0-1 range is valid."""
        # Test minimum valid value
        project_min = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.0,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_min.confidence_score == 0.0
        
        # Test maximum valid value
        project_max = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=1.0,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_max.confidence_score == 1.0
        
        # Test mid-range value
        project_mid = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.5,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_mid.confidence_score == 0.5
    
    def test_confidence_score_validation_below_range(self):
        """Test that confidence_score < 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=-0.1,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "confidence_score" in error_str
    
    def test_confidence_score_validation_above_range(self):
        """Test that confidence_score > 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=1.5,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "confidence_score" in error_str
    
    def test_auto_flagging_low_confidence(self):
        """Test that projects with confidence < 0.7 are automatically flagged."""
        # Test with confidence = 0.69 (should be flagged)
        project_low = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.69,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_low.flagged_for_review is True
        
        # Test with confidence = 0.5 (should be flagged)
        project_very_low = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.5,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_very_low.flagged_for_review is True
    
    def test_auto_flagging_high_confidence(self):
        """Test that projects with confidence >= 0.7 are not auto-flagged."""
        # Test with confidence = 0.7 (should NOT be flagged)
        project_threshold = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.7,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_threshold.flagged_for_review is False
        
        # Test with confidence = 0.9 (should NOT be flagged)
        project_high = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.9,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_high.flagged_for_review is False
    
    def test_manual_flagging_overrides_auto_flag(self):
        """Test that explicitly setting flagged_for_review=True works even with high confidence."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.95,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source",
            flagged_for_review=True
        )
        assert project.flagged_for_review is True
    
    def test_qualification_percentage_validation_valid_range(self):
        """Test that qualification_percentage within 0-100 range is valid."""
        # Test minimum valid value
        project_min = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=0.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_min.qualification_percentage == 0.0
        
        # Test maximum valid value
        project_max = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=100.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_max.qualification_percentage == 100.0
        
        # Test mid-range value
        project_mid = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_mid.qualification_percentage == 50.0
    
    def test_qualification_percentage_validation_below_range(self):
        """Test that qualification_percentage < 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=-5.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "qualification_percentage" in error_str
    
    def test_qualification_percentage_validation_above_range(self):
        """Test that qualification_percentage > 100 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=105.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "qualification_percentage" in error_str
    
    def test_estimated_credit_computation(self):
        """Test that estimated_credit is correctly calculated as 20% of qualified_cost."""
        # Test with $1000 cost (should be $200 credit)
        project1 = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project1.estimated_credit == 200.0
        
        # Test with $1045.74 cost (should be $209.15 credit)
        project2 = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project2.estimated_credit == 209.15
        
        # Test with $5000 cost (should be $1000 credit)
        project3 = QualifiedProject(
            project_name="Test Project",
            qualified_hours=50.0,
            qualified_cost=5000.0,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project3.estimated_credit == 1000.0
    
    def test_estimated_credit_computation_zero_cost(self):
        """Test that estimated_credit is 0 when qualified_cost is 0."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=0.0,
            qualified_cost=0.0,
            confidence_score=0.8,
            qualification_percentage=0.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project.estimated_credit == 0.0
    
    def test_estimated_credit_rounding(self):
        """Test that estimated_credit is properly rounded to 2 decimal places."""
        # Test with cost that results in repeating decimal
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=333.33,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        # 333.33 * 0.20 = 66.666, should round to 66.67
        assert project.estimated_credit == 66.67
    
    def test_json_serialization(self):
        """Test JSON serialization of QualifiedProject."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="The project involves developing a new authentication algorithm...",
            reasoning="This project clearly meets the four-part test...",
            irs_source="CFR Title 26 § 1.41-4(a)(1)"
        )
        
        json_str = project.model_dump_json()
        
        assert isinstance(json_str, str)
        assert "Alpha Development" in json_str
        assert "14.5" in json_str
        assert "1045.74" in json_str
        assert "0.92" in json_str
        assert "95" in json_str
        
        # Verify it's valid JSON
        json_dict = json.loads(json_str)
        assert json_dict["project_name"] == "Alpha Development"
        assert json_dict["confidence_score"] == 0.92
    
    def test_json_deserialization(self):
        """Test JSON deserialization into QualifiedProject."""
        json_data = {
            "project_name": "Alpha Development",
            "qualified_hours": 14.5,
            "qualified_cost": 1045.74,
            "confidence_score": 0.92,
            "qualification_percentage": 95.0,
            "supporting_citation": "The project involves developing a new authentication algorithm...",
            "reasoning": "This project clearly meets the four-part test...",
            "irs_source": "CFR Title 26 § 1.41-4(a)(1)"
        }
        
        project = QualifiedProject(**json_data)
        
        assert project.project_name == "Alpha Development"
        assert project.qualified_hours == 14.5
        assert project.qualified_cost == 1045.74
        assert project.confidence_score == 0.92
        assert project.qualification_percentage == 95.0
        assert project.estimated_credit == 209.15
    
    def test_str_representation(self):
        """Test the __str__ method returns a formatted string."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        str_repr = str(project)
        
        # Verify string contains key information
        assert "Alpha Development" in str_repr
        assert "14.5" in str_repr
        assert "1045.74" in str_repr
        assert "95" in str_repr
        assert "0.92" in str_repr
        assert "FLAGGED" not in str_repr  # High confidence, not flagged
    
    def test_str_representation_flagged(self):
        """Test __str__ method includes flag indicator for flagged projects."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.65,  # Low confidence, will be auto-flagged
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        str_repr = str(project)
        
        # Verify string contains flag indicator
        assert "FLAGGED FOR REVIEW" in str_repr
    
    def test_technical_details_optional(self):
        """Test that technical_details is optional and defaults to None."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        assert project.technical_details is None
    
    def test_technical_details_provided(self):
        """Test that technical_details can be provided with custom data."""
        technical_info = {
            "technological_uncertainty": "Uncertainty about encryption methods",
            "experimentation_process": "Tested multiple algorithms",
            "business_component": "Authentication System"
        }
        
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source",
            technical_details=technical_info
        )
        
        assert project.technical_details is not None
        assert project.technical_details["technological_uncertainty"] == "Uncertainty about encryption methods"
        assert project.technical_details["business_component"] == "Authentication System"
    
    def test_required_fields_validation(self):
        """Test that missing required fields raise ValidationError."""
        # Missing project_name
        with pytest.raises(ValidationError):
            QualifiedProject(
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        # Missing confidence_score
        with pytest.raises(ValidationError):
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        # Missing supporting_citation
        with pytest.raises(ValidationError):
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=50.0,
                reasoning="Test reasoning",
                irs_source="Test source"
            )
