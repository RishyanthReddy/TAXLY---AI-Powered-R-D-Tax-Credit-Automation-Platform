"""
Status Update Broadcaster

This module provides a high-level interface for broadcasting status updates
to all connected WebSocket clients. It simplifies the process of sending
status updates, error messages, and progress notifications from agents.

Key Features:
- Convenient send_status_update() function
- Automatic message formatting
- Integration with WebSocket manager
- Comprehensive logging
- Type-safe message construction

Requirements: 5.2, 5.3
"""

import logging
from typing import Optional
from datetime import datetime

from utils.logger import AgentLogger
from utils.websocket_manager import connection_manager
from models.websocket_models import (
    StatusUpdateMessage,
    ErrorMessage,
    ProgressMessage,
    AgentStage,
    AgentStatus,
    ErrorType
)

# Initialize logger
logger = AgentLogger.get_logger(__name__)


async def send_status_update(
    stage: AgentStage,
    status: AgentStatus,
    details: str
) -> None:
    """
    Send a status update to all connected WebSocket clients.
    
    This is the primary function for broadcasting agent status changes.
    It creates a StatusUpdateMessage, logs it, and broadcasts to all clients.
    
    Args:
        stage: The agent pipeline stage (data_ingestion, qualification, audit_trail)
        status: The current execution status (pending, in_progress, completed, error)
        details: Human-readable description of the current status
        
    Raises:
        ValueError: If details is empty or invalid
        
    Example:
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.IN_PROGRESS,
            details="Analyzing project: Alpha Development"
        )
        
    Requirements: 5.2, 5.3
    """
    try:
        # Create StatusUpdateMessage (validates inputs)
        status_message = StatusUpdateMessage(
            stage=stage,
            status=status,
            details=details
        )
        
        # Log the status update
        logger.info(
            f"Status Update - Stage: {stage.value}, "
            f"Status: {status.value}, Details: {details}"
        )
        
        # Broadcast to all connected clients
        await connection_manager.broadcast_status_update(status_message)
        
        logger.debug(
            f"Status update broadcast successful to "
            f"{connection_manager.get_connection_count()} clients"
        )
        
    except ValueError as e:
        logger.error(f"Invalid status update parameters: {e}")
        raise
        
    except Exception as e:
        logger.error(
            f"Error broadcasting status update: {e}",
            exc_info=True
        )
        # Don't raise - we don't want status update failures to break agent execution
        # The error is logged for debugging


async def send_error_notification(
    error_type: ErrorType,
    message: str,
    traceback: Optional[str] = None
) -> None:
    """
    Send an error notification to all connected WebSocket clients.
    
    Use this function when an error occurs during agent execution that
    should be communicated to the frontend.
    
    Args:
        error_type: Category of error (api_connection, validation, etc.)
        message: Human-readable error message
        traceback: Optional full error traceback for debugging
        
    Example:
        await send_error_notification(
            error_type=ErrorType.API_CONNECTION,
            message="Failed to connect to Clockify API after 3 retries",
            traceback=traceback.format_exc()
        )
        
    Requirements: 5.3
    """
    try:
        # Create ErrorMessage (validates inputs)
        error_message = ErrorMessage(
            error_type=error_type,
            message=message,
            traceback=traceback
        )
        
        # Log the error
        logger.error(
            f"Error Notification - Type: {error_type.value}, Message: {message}"
        )
        
        # Broadcast to all connected clients
        await connection_manager.broadcast_error(error_message)
        
        logger.debug(
            f"Error notification broadcast successful to "
            f"{connection_manager.get_connection_count()} clients"
        )
        
    except ValueError as e:
        logger.error(f"Invalid error notification parameters: {e}")
        
    except Exception as e:
        logger.error(
            f"Error broadcasting error notification: {e}",
            exc_info=True
        )


async def send_progress_update(
    current_step: int,
    total_steps: int,
    description: Optional[str] = None
) -> None:
    """
    Send a progress update to all connected WebSocket clients.
    
    Use this function during long-running operations to show incremental progress.
    The percentage is automatically calculated from current_step and total_steps.
    
    Args:
        current_step: Current step number (0-indexed or 1-indexed)
        total_steps: Total number of steps
        description: Optional human-readable progress description
        
    Example:
        await send_progress_update(
            current_step=15,
            total_steps=50,
            description="Processing project 15 of 50"
        )
        
    Requirements: 5.2, 5.3
    """
    try:
        # Calculate percentage
        percentage = (current_step / total_steps) * 100 if total_steps > 0 else 0
        
        # Create ProgressMessage (validates inputs)
        progress_message = ProgressMessage(
            current_step=current_step,
            total_steps=total_steps,
            percentage=percentage,
            description=description
        )
        
        # Log the progress update
        logger.info(
            f"Progress Update - {current_step}/{total_steps} "
            f"({percentage:.1f}%){f': {description}' if description else ''}"
        )
        
        # Broadcast to all connected clients
        await connection_manager.broadcast_progress(progress_message)
        
        logger.debug(
            f"Progress update broadcast successful to "
            f"{connection_manager.get_connection_count()} clients"
        )
        
    except ValueError as e:
        logger.error(f"Invalid progress update parameters: {e}")
        
    except Exception as e:
        logger.error(
            f"Error broadcasting progress update: {e}",
            exc_info=True
        )


async def send_agent_started(stage: AgentStage, details: str) -> None:
    """
    Convenience function to send an agent started status update.
    
    Args:
        stage: The agent pipeline stage
        details: Description of what the agent is starting
        
    Example:
        await send_agent_started(
            stage=AgentStage.DATA_INGESTION,
            details="Starting data ingestion from Clockify and Unified.to"
        )
    """
    await send_status_update(
        stage=stage,
        status=AgentStatus.IN_PROGRESS,
        details=details
    )


async def send_agent_completed(stage: AgentStage, details: str) -> None:
    """
    Convenience function to send an agent completed status update.
    
    Args:
        stage: The agent pipeline stage
        details: Description of what the agent completed
        
    Example:
        await send_agent_completed(
            stage=AgentStage.DATA_INGESTION,
            details="Successfully ingested 1,234 time entries"
        )
    """
    await send_status_update(
        stage=stage,
        status=AgentStatus.COMPLETED,
        details=details
    )


async def send_agent_error(stage: AgentStage, details: str) -> None:
    """
    Convenience function to send an agent error status update.
    
    Args:
        stage: The agent pipeline stage
        details: Description of the error
        
    Example:
        await send_agent_error(
            stage=AgentStage.DATA_INGESTION,
            details="Failed to connect to Clockify API"
        )
    """
    await send_status_update(
        stage=stage,
        status=AgentStatus.ERROR,
        details=details
    )


def get_active_connection_count() -> int:
    """
    Get the number of active WebSocket connections.
    
    Useful for checking if there are any clients listening before
    performing expensive operations for status updates.
    
    Returns:
        int: Number of active WebSocket connections
        
    Example:
        if get_active_connection_count() > 0:
            # Perform expensive status update preparation
            await send_status_update(...)
    """
    return connection_manager.get_connection_count()


async def broadcast_custom_message(message_type: str, **kwargs) -> None:
    """
    Broadcast a custom message to all connected clients.
    
    Use this for application-specific messages that don't fit the standard
    status/error/progress categories.
    
    Args:
        message_type: Type identifier for the message
        **kwargs: Additional key-value pairs to include in the message
        
    Example:
        await broadcast_custom_message(
            message_type="credit_calculation",
            total_credit=125000.50,
            qualified_projects=15
        )
    """
    try:
        message = {
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        logger.info(f"Broadcasting custom message: {message_type}")
        await connection_manager.broadcast(message)
        
        logger.debug(
            f"Custom message broadcast successful to "
            f"{connection_manager.get_connection_count()} clients"
        )
        
    except Exception as e:
        logger.error(
            f"Error broadcasting custom message: {e}",
            exc_info=True
        )
