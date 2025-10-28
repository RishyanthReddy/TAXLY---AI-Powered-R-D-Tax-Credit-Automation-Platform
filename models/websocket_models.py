"""
WebSocket Message Models

This module defines Pydantic models for real-time communication between
the backend agents and frontend UI via WebSocket connections.

These models ensure type safety and validation for status updates,
error messages, and progress tracking during agent execution.

Requirements: 5.2, 5.3
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class AgentStage(str, Enum):
    """
    Enumeration of agent pipeline stages.
    
    Used to identify which stage of the workflow is currently executing.
    """
    INGESTION = "ingestion"
    QUALIFICATION = "qualification"
    AUDIT_TRAIL = "audit_trail"


class MessageStatus(str, Enum):
    """
    Enumeration of message status types.
    
    Indicates the current state of an agent or operation.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class StatusUpdateMessage(BaseModel):
    """
    WebSocket message for agent status updates.
    
    Sent during agent execution to provide real-time visibility into
    the workflow progress. Used to update the React Flow visualization
    and inform users of current operations.
    
    Requirements: 5.2, 5.3
    
    Example:
        {
            "stage": "qualification",
            "status": "in_progress",
            "details": "Analyzing project: Alpha Development",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    stage: AgentStage = Field(..., description="Pipeline stage (ingestion, qualification, audit_trail)")
    status: MessageStatus = Field(..., description="Current status of the stage")
    details: str = Field(..., description="Human-readable description of current operation")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of status update")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('details')
    def validate_details_not_empty(cls, v):
        """Ensure details field is not empty"""
        if not v or not v.strip():
            raise ValueError('Details field cannot be empty')
        return v.strip()
    
    def to_dict(self) -> dict:
        """
        Convert message to dictionary for JSON serialization.
        
        Returns:
            dict: Message as dictionary with ISO format timestamp
        """
        return {
            'stage': self.stage.value,
            'status': self.status.value,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class ErrorMessage(BaseModel):
    """
    WebSocket message for error notifications.
    
    Sent when an error occurs during agent execution. Provides detailed
    error information to help users understand and resolve issues.
    
    Requirements: 5.2, 5.3
    
    Example:
        {
            "error_type": "APIConnectionError",
            "message": "Failed to connect to Clockify API",
            "traceback": "Traceback (most recent call last):\\n...",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    error_type: str = Field(..., description="Error class name (e.g., APIConnectionError, ValidationError)")
    message: str = Field(..., description="Human-readable error message")
    traceback: Optional[str] = Field(None, description="Full error traceback for debugging")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of error occurrence")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('error_type')
    def validate_error_type_not_empty(cls, v):
        """Ensure error_type is not empty"""
        if not v or not v.strip():
            raise ValueError('Error type cannot be empty')
        return v.strip()
    
    @validator('message')
    def validate_message_not_empty(cls, v):
        """Ensure message is not empty"""
        if not v or not v.strip():
            raise ValueError('Error message cannot be empty')
        return v.strip()
    
    def to_dict(self) -> dict:
        """
        Convert message to dictionary for JSON serialization.
        
        Returns:
            dict: Message as dictionary with ISO format timestamp
        """
        return {
            'error_type': self.error_type,
            'message': self.message,
            'traceback': self.traceback,
            'timestamp': self.timestamp.isoformat()
        }


class ProgressMessage(BaseModel):
    """
    WebSocket message for progress tracking.
    
    Sent during long-running operations to show progress to users.
    Useful for operations like batch processing of projects or
    generating multiple narratives.
    
    Requirements: 5.2, 5.3
    
    Example:
        {
            "current_step": 15,
            "total_steps": 50,
            "percentage": 30.0,
            "description": "Qualifying project 15 of 50",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    current_step: int = Field(..., ge=0, description="Current step number (0-indexed or 1-indexed)")
    total_steps: int = Field(..., gt=0, description="Total number of steps in operation")
    percentage: float = Field(..., ge=0, le=100, description="Completion percentage (0-100)")
    description: Optional[str] = Field(None, description="Optional description of current step")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of progress update")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('current_step')
    def validate_current_step(cls, v, values):
        """Ensure current_step doesn't exceed total_steps"""
        if 'total_steps' in values and v > values['total_steps']:
            raise ValueError('Current step cannot exceed total steps')
        return v
    
    @validator('percentage')
    def validate_percentage_matches_steps(cls, v, values):
        """
        Validate that percentage is consistent with step counts.
        
        Allows for small floating point discrepancies.
        """
        if 'current_step' in values and 'total_steps' in values:
            expected_percentage = (values['current_step'] / values['total_steps']) * 100
            # Allow 1% tolerance for rounding
            if abs(v - expected_percentage) > 1.0:
                raise ValueError(
                    f'Percentage {v}% does not match step ratio '
                    f'({values["current_step"]}/{values["total_steps"]} = {expected_percentage:.1f}%)'
                )
        return v
    
    def to_dict(self) -> dict:
        """
        Convert message to dictionary for JSON serialization.
        
        Returns:
            dict: Message as dictionary with ISO format timestamp
        """
        return {
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'percentage': self.percentage,
            'description': self.description,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_steps(cls, current_step: int, total_steps: int, description: Optional[str] = None) -> 'ProgressMessage':
        """
        Create ProgressMessage from step counts, automatically calculating percentage.
        
        Args:
            current_step: Current step number
            total_steps: Total number of steps
            description: Optional description of current step
        
        Returns:
            ProgressMessage: New progress message instance
        
        Example:
            >>> msg = ProgressMessage.from_steps(15, 50, "Processing project 15")
            >>> msg.percentage
            30.0
        """
        percentage = (current_step / total_steps) * 100 if total_steps > 0 else 0.0
        return cls(
            current_step=current_step,
            total_steps=total_steps,
            percentage=round(percentage, 2),
            description=description
        )
