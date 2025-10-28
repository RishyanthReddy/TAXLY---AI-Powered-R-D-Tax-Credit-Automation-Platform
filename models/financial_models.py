"""
Financial data models for R&D Tax Credit Automation Agent.

This module contains Pydantic models for financial data including employee time entries,
project costs, and payroll information. These models ensure data validation and type safety
throughout the application.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, computed_field
from decimal import Decimal
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.constants import CostType


class EmployeeTimeEntry(BaseModel):
    """
    Represents a single time entry for an employee working on a project.
    
    This model captures time tracking data from systems like Clockify and validates
    that the data meets requirements for R&D tax credit qualification analysis.
    
    Attributes:
        employee_id: Unique identifier for the employee (e.g., "EMP001")
        employee_name: Full name of the employee
        project_name: Name of the project the time was spent on
        task_description: Detailed description of the work performed
        hours_spent: Number of hours spent on the task (0-24)
        date: Date and time when the work was performed
        is_rd_classified: Whether this time entry is classified as R&D work
    
    Example:
        >>> entry = EmployeeTimeEntry(
        ...     employee_id="EMP001",
        ...     employee_name="Alice Johnson",
        ...     project_name="Alpha Development",
        ...     task_description="Implemented new authentication algorithm",
        ...     hours_spent=8.5,
        ...     date="2024-03-15T09:00:00",
        ...     is_rd_classified=True
        ... )
        >>> print(entry)
        EMP001 - Alice Johnson: 8.5 hours on Alpha Development (2024-03-15)
    """
    
    employee_id: str = Field(
        ...,
        description="Unique identifier for the employee",
        min_length=1
    )
    
    employee_name: str = Field(
        ...,
        description="Full name of the employee",
        min_length=1
    )
    
    project_name: str = Field(
        ...,
        description="Name of the project",
        min_length=1
    )
    
    task_description: str = Field(
        ...,
        description="Detailed description of the work performed",
        min_length=1
    )
    
    hours_spent: float = Field(
        ...,
        description="Number of hours spent on the task",
        gt=0,
        le=24
    )
    
    date: datetime = Field(
        ...,
        description="Date and time when the work was performed"
    )
    
    is_rd_classified: bool = Field(
        default=False,
        description="Whether this time entry is classified as R&D work"
    )
    
    @field_validator('hours_spent')
    @classmethod
    def validate_hours_spent(cls, v: float) -> float:
        """
        Validate that hours_spent is within valid range (0-24 hours).
        
        Args:
            v: The hours_spent value to validate
            
        Returns:
            The validated hours_spent value
            
        Raises:
            ValueError: If hours_spent is not between 0 and 24
        """
        if v <= 0:
            raise ValueError("hours_spent must be greater than 0")
        if v > 24:
            raise ValueError("hours_spent cannot exceed 24 hours in a single day")
        return v
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: datetime) -> datetime:
        """
        Validate that the date is not in the future.
        
        Args:
            v: The date value to validate
            
        Returns:
            The validated date value
            
        Raises:
            ValueError: If the date is in the future
        """
        if v > datetime.now():
            raise ValueError("date cannot be in the future")
        return v
    
    def __str__(self) -> str:
        """
        Return a human-readable string representation of the time entry.
        
        Returns:
            Formatted string with key information about the time entry
        """
        date_str = self.date.strftime("%Y-%m-%d")
        return f"{self.employee_id} - {self.employee_name}: {self.hours_spent} hours on {self.project_name} ({date_str})"
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "employee_id": "EMP001",
                "employee_name": "Alice Johnson",
                "project_name": "Alpha Development",
                "task_description": "Implemented new authentication algorithm with encryption",
                "hours_spent": 8.5,
                "date": "2024-03-15T09:00:00",
                "is_rd_classified": True
            }
        }


class ProjectCost(BaseModel):
    """
    Represents a cost entry associated with a project for R&D tax credit analysis.
    
    This model captures cost data from HRIS/payroll systems (via Unified.to) or expense
    tracking systems. It validates cost data and provides computed fields for analysis.
    
    Attributes:
        cost_id: Unique identifier for the cost entry
        cost_type: Type of cost (Payroll, Contractor, Materials, Cloud, Other)
        amount: Cost amount in dollars (must be positive)
        project_name: Name of the project this cost is associated with
        employee_id: Optional employee identifier (for payroll costs)
        date: Date when the cost was incurred
        is_rd_classified: Whether this cost is classified as R&D-related
        metadata: Optional dictionary containing additional cost information
    
    Example:
        >>> cost = ProjectCost(
        ...     cost_id="PAY001",
        ...     cost_type="Payroll",
        ...     amount=12500.00,
        ...     project_name="Alpha Development",
        ...     employee_id="EMP001",
        ...     date="2024-03-31T00:00:00",
        ...     is_rd_classified=True,
        ...     metadata={
        ...         "annual_salary": 150000.00,
        ...         "hourly_rate": 72.12,
        ...         "pay_period": "2024-03",
        ...         "department": "Engineering"
        ...     }
        ... )
        >>> print(cost.hourly_rate)
        72.12
    """
    
    cost_id: str = Field(
        ...,
        description="Unique identifier for the cost entry",
        min_length=1
    )
    
    cost_type: str = Field(
        ...,
        description="Type of cost (Payroll, Contractor, Materials, Cloud, Other)"
    )
    
    amount: float = Field(
        ...,
        description="Cost amount in dollars",
        gt=0
    )
    
    project_name: str = Field(
        ...,
        description="Name of the project this cost is associated with",
        min_length=1
    )
    
    employee_id: Optional[str] = Field(
        default=None,
        description="Employee identifier (required for payroll costs)"
    )
    
    date: datetime = Field(
        ...,
        description="Date when the cost was incurred"
    )
    
    is_rd_classified: bool = Field(
        default=False,
        description="Whether this cost is classified as R&D-related"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional cost information (e.g., annual_salary, hourly_rate, department)"
    )
    
    @field_validator('cost_type')
    @classmethod
    def validate_cost_type(cls, v: str) -> str:
        """
        Validate that cost_type is one of the allowed values.
        
        Args:
            v: The cost_type value to validate
            
        Returns:
            The validated cost_type value
            
        Raises:
            ValueError: If cost_type is not in the allowed list
        """
        allowed_types = [ct.value for ct in CostType]
        if v not in allowed_types:
            raise ValueError(
                f"cost_type must be one of {allowed_types}, got '{v}'"
            )
        return v
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """
        Validate that amount is positive.
        
        Args:
            v: The amount value to validate
            
        Returns:
            The validated amount value
            
        Raises:
            ValueError: If amount is not positive
        """
        if v <= 0:
            raise ValueError("amount must be positive (greater than 0)")
        return v
    
    @computed_field
    @property
    def hourly_rate(self) -> Optional[float]:
        """
        Calculate or retrieve hourly rate from metadata.
        
        This computed field retrieves the hourly_rate from metadata if available,
        or calculates it from annual_salary and annual_hours (assuming 2080 hours/year).
        Useful for converting annual compensation to hourly rates for time-based R&D calculations.
        
        Returns:
            Hourly rate rounded to 2 decimal places, or None if not calculable
            
        Example:
            >>> cost = ProjectCost(
            ...     cost_id="PAY001",
            ...     cost_type="Payroll",
            ...     amount=12500.00,
            ...     project_name="Alpha Development",
            ...     employee_id="EMP001",
            ...     date="2024-03-31T00:00:00",
            ...     metadata={"annual_salary": 150000.00, "hourly_rate": 72.12}
            ... )
            >>> cost.hourly_rate
            72.12
        """
        if self.metadata:
            # First try to get hourly_rate directly from metadata
            if 'hourly_rate' in self.metadata:
                return round(float(self.metadata['hourly_rate']), 2)
            
            # Otherwise calculate from annual_salary if available
            if 'annual_salary' in self.metadata:
                annual_salary = float(self.metadata['annual_salary'])
                # Use annual_hours from metadata or default to 2080 (40 hours/week * 52 weeks)
                annual_hours = float(self.metadata.get('annual_hours', 2080.0))
                return round(annual_salary / annual_hours, 2)
        
        return None
    
    def __str__(self) -> str:
        """
        Return a human-readable string representation of the cost entry.
        
        Returns:
            Formatted string with key information about the cost
        """
        date_str = self.date.strftime("%Y-%m-%d")
        employee_info = f" (Employee: {self.employee_id})" if self.employee_id else ""
        return f"{self.cost_id} - {self.cost_type}: ${self.amount:.2f} on {self.project_name} ({date_str}){employee_info}"
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "cost_id": "PAY001",
                "cost_type": "Payroll",
                "amount": 12500.00,
                "project_name": "Alpha Development",
                "employee_id": "EMP001",
                "date": "2024-03-31T00:00:00",
                "is_rd_classified": True,
                "metadata": {
                    "annual_salary": 150000.00,
                    "hourly_rate": 72.12,
                    "pay_period": "2024-03",
                    "department": "Engineering"
                }
            }
        }
