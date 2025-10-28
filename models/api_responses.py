"""
API Response Models

This module defines Pydantic models for external API response schemas.
These models ensure type safety and validation for data received from:
- Clockify API (time tracking)
- Unified.to API (HRIS/payroll)
- OpenRouter API (LLM responses)
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class ClockifyTimeEntryResponse(BaseModel):
    """
    Response model for Clockify API time entry data.
    
    Maps to Clockify's time-entries endpoint response structure.
    Reference: https://docs.clockify.me/#tag/Time-entry
    
    Requirements: 1.1
    """
    id: str = Field(..., description="Unique time entry identifier")
    description: Optional[str] = Field(None, description="Task description")
    userId: str = Field(..., description="Employee/user identifier")
    workspaceId: str = Field(..., description="Workspace identifier")
    projectId: Optional[str] = Field(None, description="Project identifier")
    projectName: Optional[str] = Field(None, description="Project name")
    taskId: Optional[str] = Field(None, description="Task identifier")
    timeInterval: Dict[str, Any] = Field(..., description="Start and end time")
    duration: Optional[str] = Field(None, description="Duration in ISO 8601 format")
    billable: bool = Field(default=False, description="Whether entry is billable")
    userName: Optional[str] = Field(None, description="User's display name")
    
    @validator('timeInterval')
    def validate_time_interval(cls, v):
        """Ensure timeInterval has required start field"""
        if 'start' not in v:
            raise ValueError('timeInterval must contain start field')
        return v
    
    def get_hours_spent(self) -> float:
        """
        Calculate hours spent from duration or time interval.
        
        Returns:
            float: Hours spent (0-24)
        """
        if self.duration:
            # Parse ISO 8601 duration (e.g., "PT2H30M")
            duration_str = self.duration.replace('PT', '')
            hours = 0.0
            
            if 'H' in duration_str:
                hours_part = duration_str.split('H')[0]
                hours += float(hours_part)
                duration_str = duration_str.split('H')[1] if 'H' in duration_str else ''
            
            if 'M' in duration_str:
                minutes_part = duration_str.split('M')[0]
                hours += float(minutes_part) / 60
            
            return round(hours, 2)
        
        # Fallback: calculate from timeInterval
        if 'end' in self.timeInterval and self.timeInterval['end']:
            start = datetime.fromisoformat(self.timeInterval['start'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.timeInterval['end'].replace('Z', '+00:00'))
            duration_seconds = (end - start).total_seconds()
            return round(duration_seconds / 3600, 2)
        
        return 0.0
    
    def get_date(self) -> datetime:
        """
        Extract date from time interval start.
        
        Returns:
            datetime: Entry date
        """
        start_str = self.timeInterval['start']
        return datetime.fromisoformat(start_str.replace('Z', '+00:00'))


class UnifiedToEmployeeResponse(BaseModel):
    """
    Response model for Unified.to HRIS employee data.
    
    Maps to Unified.to's /hris/{connection_id}/employee endpoint.
    Reference: https://docs.unified.to/unified/api/hris/employee
    
    Requirements: 1.2
    """
    id: str = Field(..., description="Unique employee identifier")
    name: Optional[str] = Field(None, description="Employee full name")
    first_name: Optional[str] = Field(None, description="Employee first name")
    last_name: Optional[str] = Field(None, description="Employee last name")
    email: Optional[str] = Field(None, description="Employee email address")
    employee_number: Optional[str] = Field(None, description="Employee number/code")
    employment_status: Optional[str] = Field(None, description="Employment status (active, inactive)")
    employment_type: Optional[str] = Field(None, description="Employment type (full-time, part-time, contractor)")
    job_title: Optional[str] = Field(None, description="Job title")
    department: Optional[str] = Field(None, description="Department name")
    location: Optional[str] = Field(None, description="Work location")
    manager_id: Optional[str] = Field(None, description="Manager's employee ID")
    hire_date: Optional[str] = Field(None, description="Hire date (ISO 8601)")
    termination_date: Optional[str] = Field(None, description="Termination date (ISO 8601)")
    compensation: Optional[Dict[str, Any]] = Field(None, description="Compensation details")
    
    @validator('email')
    def validate_email_format(cls, v):
        """Basic email format validation"""
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    def get_annual_salary(self) -> Optional[float]:
        """
        Extract annual salary from compensation data.
        
        Returns:
            Optional[float]: Annual salary if available
        """
        if not self.compensation:
            return None
        
        # Handle various compensation structures
        if 'annual_salary' in self.compensation:
            return float(self.compensation['annual_salary'])
        
        if 'salary' in self.compensation:
            salary_data = self.compensation['salary']
            if isinstance(salary_data, dict):
                return float(salary_data.get('amount', 0))
            return float(salary_data)
        
        if 'amount' in self.compensation:
            return float(self.compensation['amount'])
        
        return None
    
    def get_hourly_rate(self, annual_hours: float = 2080) -> Optional[float]:
        """
        Calculate hourly rate from annual salary.
        
        Args:
            annual_hours: Standard work hours per year (default: 2080)
        
        Returns:
            Optional[float]: Hourly rate if salary available
        """
        annual_salary = self.get_annual_salary()
        if annual_salary:
            return round(annual_salary / annual_hours, 2)
        return None


class UnifiedToPayslipResponse(BaseModel):
    """
    Response model for Unified.to HRIS payslip data.
    
    Maps to Unified.to's /hris/{connection_id}/payslip endpoint.
    Reference: https://docs.unified.to/unified/api/hris/payslip
    
    Requirements: 1.2
    """
    id: str = Field(..., description="Unique payslip identifier")
    employee_id: str = Field(..., description="Employee identifier")
    pay_period_start: str = Field(..., description="Pay period start date (ISO 8601)")
    pay_period_end: str = Field(..., description="Pay period end date (ISO 8601)")
    pay_date: Optional[str] = Field(None, description="Payment date (ISO 8601)")
    gross_pay: float = Field(..., ge=0, description="Gross pay amount")
    net_pay: float = Field(..., ge=0, description="Net pay amount")
    currency: Optional[str] = Field(default="USD", description="Currency code")
    deductions: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Deduction items")
    earnings: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Earning items")
    taxes: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Tax items")
    
    @validator('net_pay')
    def validate_net_less_than_gross(cls, v, values):
        """Ensure net pay doesn't exceed gross pay"""
        if 'gross_pay' in values and v > values['gross_pay']:
            raise ValueError('Net pay cannot exceed gross pay')
        return v
    
    def get_pay_period_start_date(self) -> datetime:
        """Parse pay period start date"""
        return datetime.fromisoformat(self.pay_period_start.replace('Z', '+00:00'))
    
    def get_pay_period_end_date(self) -> datetime:
        """Parse pay period end date"""
        return datetime.fromisoformat(self.pay_period_end.replace('Z', '+00:00'))
    
    def get_total_deductions(self) -> float:
        """
        Calculate total deductions from deduction items.
        
        Returns:
            float: Total deduction amount
        """
        if not self.deductions:
            return 0.0
        
        total = 0.0
        for deduction in self.deductions:
            if 'amount' in deduction:
                total += float(deduction['amount'])
        
        return round(total, 2)
    
    def get_total_taxes(self) -> float:
        """
        Calculate total taxes from tax items.
        
        Returns:
            float: Total tax amount
        """
        if not self.taxes:
            return 0.0
        
        total = 0.0
        for tax in self.taxes:
            if 'amount' in tax:
                total += float(tax['amount'])
        
        return round(total, 2)


class OpenRouterChatResponse(BaseModel):
    """
    Response model for OpenRouter API chat completion.
    
    Maps to OpenRouter's /api/v1/chat/completions endpoint response.
    Used for DeepSeek Chat V3.1 and other LLM models via OpenRouter.
    Reference: https://openrouter.ai/docs
    
    Requirements: 2.3
    """
    id: str = Field(..., description="Unique response identifier")
    model: str = Field(..., description="Model used for completion")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    choices: List[Dict[str, Any]] = Field(..., description="Response choices")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")
    
    @validator('choices')
    def validate_choices_not_empty(cls, v):
        """Ensure at least one choice is returned"""
        if not v or len(v) == 0:
            raise ValueError('Response must contain at least one choice')
        return v
    
    def get_content(self, choice_index: int = 0) -> str:
        """
        Extract message content from response.
        
        Args:
            choice_index: Index of choice to extract (default: 0)
        
        Returns:
            str: Message content
        """
        if choice_index >= len(self.choices):
            raise IndexError(f'Choice index {choice_index} out of range')
        
        choice = self.choices[choice_index]
        
        # Handle different response structures
        if 'message' in choice:
            return choice['message'].get('content', '')
        
        if 'text' in choice:
            return choice['text']
        
        return ''
    
    def get_finish_reason(self, choice_index: int = 0) -> Optional[str]:
        """
        Get finish reason for a choice.
        
        Args:
            choice_index: Index of choice (default: 0)
        
        Returns:
            Optional[str]: Finish reason (stop, length, content_filter, etc.)
        """
        if choice_index >= len(self.choices):
            return None
        
        return self.choices[choice_index].get('finish_reason')
    
    def get_total_tokens(self) -> Optional[int]:
        """
        Get total token count from usage statistics.
        
        Returns:
            Optional[int]: Total tokens used
        """
        if not self.usage:
            return None
        
        return self.usage.get('total_tokens')
    
    def get_prompt_tokens(self) -> Optional[int]:
        """
        Get prompt token count from usage statistics.
        
        Returns:
            Optional[int]: Prompt tokens used
        """
        if not self.usage:
            return None
        
        return self.usage.get('prompt_tokens')
    
    def get_completion_tokens(self) -> Optional[int]:
        """
        Get completion token count from usage statistics.
        
        Returns:
            Optional[int]: Completion tokens used
        """
        if not self.usage:
            return None
        
        return self.usage.get('completion_tokens')
