"""
WebSocket Message Models

This module defines Pydantic models for real-time communication between
the backend agents and the frontend UI via WebSocket or Server-Sent Events.

These models ensure type-safe, structured messaging for:
- Agent status updates
- Error notifications
- Progress tracking

Requirements: 5.2, 5.3
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class AgentStage(str, Enum):
    """Enumeration of agent pipeline stages"""
    DATA_INGESTION = "data_ingestion"
    QUALIFICATION = "qualification"
    AUDIT_TRAIL = "audit_trail"


class AgentStatus(str, Enum):
    """Enumeration of agent execution statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class ErrorType(str, Enum):
    """Enumeration of error categories"""
    API_CONNECTION = "api_connection"
    VALIDATION = "validation"
    RAG_RETRIEVAL = "rag_retrieval"
    AGENT_EXECUTION = "agent_execution"
    PDF_GENERATION = "pdf_generation"
    UNKNOWN = "unknown"


class StatusUpdateMessage(BaseModel):
    """
    Message model for agent status updates.
    
    Sent when an agent transitions between states or completes a significant action.
    Used to update the React Flow visualization in real-time.
    
    Requirements: 5.2
    
    Example:
        {
            "stage": "qualification",
            "status": "in_progress",
            "details": "Analyzing project: Alpha Development",
            "timestamp": "2025-01-15T10:30:45.123456"
        }
    """
    stage: AgentStage = Field(..., description="Agent pipeline stage")
    status: AgentStatus = Field(..., description="Current execution status")
    details: str = Field(..., description="Human-readable status description")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    
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


class ErrorMessage(BaseModel):
    """
    Message model for error notifications.
    
    Sent when an error occurs during agent execution.
    Provides context for debugging and user notification.
    
    Requirements: 5.3
    
    Example:
        {
            "error_type": "api_connection",
            "message": "Failed to connect to Clockify API after 3 retries",
            "traceback": "Traceback (most recent call last):\\n  File...",
            "timestamp": "2025-01-15T10:30:45.123456"
        }
    """
    error_type: ErrorType = Field(..., description="Category of error")
    message: str = Field(..., description="Human-readable error message")
    traceback: Optional[str] = Field(None, description="Full error traceback for debugging")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('message')
    def validate_message_not_empty(cls, v):
        """Ensure message field is not empty"""
        if not v or not v.strip():
            raise ValueError('Message field cannot be empty')
        return v.strip()


class ProgressMessage(BaseModel):
    """
    Message model for progress tracking.
    
    Sent during long-running operations to show incremental progress.
    Used for operations like batch processing, RAG indexing, or PDF generation.
    
    Requirements: 5.2, 5.3
    
    Example:
        {
            "current_step": 15,
            "total_steps": 50,
            "percentage": 30.0,
            "description": "Processing project 15 of 50",
            "timestamp": "2025-01-15T10:30:45.123456"
        }
    """
    current_step: int = Field(..., ge=0, description="Current step number (0-indexed or 1-indexed)")
    total_steps: int = Field(..., gt=0, description="Total number of steps")
    percentage: float = Field(..., ge=0, le=100, description="Completion percentage (0-100)")
    description: Optional[str] = Field(None, description="Optional progress description")
    timestamp: datetime = Field(default_factory=datetime.now, description="Progress timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('current_step')
    def validate_current_step(cls, v, values):
        """Ensure current_step doesn't exceed total_steps"""
        if 'total_steps' in values and v > values['total_steps']:
            raise ValueError('current_step cannot exceed total_steps')
        return v
    
    @validator('percentage')
    def validate_percentage_consistency(cls, v, values):
        """Ensure percentage is consistent with step counts"""
        if 'current_step' in values and 'total_steps' in values:
            expected_percentage = (values['current_step'] / values['total_steps']) * 100
            # Allow 1% tolerance for rounding
            if abs(v - expected_percentage) > 1.0:
                raise ValueError(
                    f'Percentage {v} inconsistent with steps '
                    f'({values["current_step"]}/{values["total_steps"]} = {expected_percentage:.1f}%)'
                )
        return v
