"""
Unit Tests for Status Broadcaster

Tests the status broadcasting functionality including:
- Status update broadcasting
- Error notification broadcasting
- Progress update broadcasting
- Convenience functions
- Connection monitoring
- Custom message broadcasting
- Error handling

Requirements: 5.2, 5.3
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from utils.status_broadcaster import (
    send_status_update,
    send_error_notification,
    send_progress_update,
    send_agent_started,
    send_agent_completed,
    send_agent_error,
    get_active_connection_count,
    broadcast_custom_message
)
from models.websocket_models import (
    AgentStage,
    AgentStatus,
    ErrorType,
    StatusUpdateMessage,
    ErrorMessage,
    ProgressMessage
)


@pytest.fixture
def mock_connection_manager():
    """Mock the connection manager"""
    with patch('utils.status_broadcaster.connection_manager') as mock_manager:
        mock_manager.broadcast_status_update = AsyncMock()
        mock_manager.broadcast_error = AsyncMock()
        mock_manager.broadcast_progress = AsyncMock()
        mock_manager.broadcast = AsyncMock()
        mock_manager.get_connection_count = MagicMock(return_value=3)
        yield mock_manager


@pytest.mark.asyncio
class TestSendStatusUpdate:
    """Tests for send_status_update function"""
    
    async def test_send_valid_status_update(self, mock_connection_manager):
        """Test sending a valid status update"""
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.IN_PROGRESS,
            details="Analyzing project: Alpha Development"
        )
        
        # Verify broadcast was called
        mock_connection_manager.broadcast_status_update.assert_called_once()
        
        # Verify the message structure
        call_args = mock_connection_manager.broadcast_status_update.call_args[0][0]
        assert isinstance(call_args, StatusUpdateMessage)
        assert call_args.stage == AgentStage.QUALIFICATION
        assert call_args.status == AgentStatus.IN_PROGRESS
        assert call_args.details == "Analyzing project: Alpha Development"
    
    async def test_send_status_update_all_stages(self, mock_connection_manager):
        """Test status updates for all agent stages"""
        stages = [
            AgentStage.DATA_INGESTION,
            AgentStage.QUALIFICATION,
            AgentStage.AUDIT_TRAIL
        ]
        
        for stage in stages:
            await send_status_update(
                stage=stage,
                status=AgentStatus.IN_PROGRESS,
                details=f"Processing {stage.value}"
            )
        
        assert mock_connection_manager.broadcast_status_update.call_count == len(stages)
    
    async def test_send_status_update_all_statuses(self, mock_connection_manager):
        """Test status updates for all status types"""
        statuses = [
            AgentStatus.PENDING,
            AgentStatus.IN_PROGRESS,
            AgentStatus.COMPLETED,
            AgentStatus.ERROR
        ]
        
        for status in statuses:
            await send_status_update(
                stage=AgentStage.DATA_INGESTION,
                status=status,
                details=f"Status: {status.value}"
            )
        
        assert mock_connection_manager.broadcast_status_update.call_count == len(statuses)
    
    async def test_send_status_update_empty_details(self, mock_connection_manager):
        """Test that empty details raises ValueError"""
        with pytest.raises(ValueError, match="Details field cannot be empty"):
            await send_status_update(
                stage=AgentStage.DATA_INGESTION,
                status=AgentStatus.IN_PROGRESS,
                details=""
            )
    
    async def test_send_status_update_whitespace_details(self, mock_connection_manager):
        """Test that whitespace-only details raises ValueError"""
        with pytest.raises(ValueError, match="Details field cannot be empty"):
            await send_status_update(
                stage=AgentStage.DATA_INGESTION,
                status=AgentStatus.IN_PROGRESS,
                details="   "
            )
    
    async def test_send_status_update_broadcast_error(self, mock_connection_manager):
        """Test that broadcast errors are handled gracefully"""
        mock_connection_manager.broadcast_status_update.side_effect = Exception("Broadcast failed")
        
        # Should not raise exception
        await send_status_update(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.IN_PROGRESS,
            details="Test message"
        )


@pytest.mark.asyncio
class TestSendErrorNotification:
    """Tests for send_error_notification function"""
    
    async def test_send_valid_error_notification(self, mock_connection_manager):
        """Test sending a valid error notification"""
        await send_error_notification(
            error_type=ErrorType.API_CONNECTION,
            message="Failed to connect to Clockify API",
            traceback="Traceback (most recent call last):\n  File..."
        )
        
        # Verify broadcast was called
        mock_connection_manager.broadcast_error.assert_called_once()
        
        # Verify the message structure
        call_args = mock_connection_manager.broadcast_error.call_args[0][0]
        assert isinstance(call_args, ErrorMessage)
        assert call_args.error_type == ErrorType.API_CONNECTION
        assert call_args.message == "Failed to connect to Clockify API"
        assert call_args.traceback == "Traceback (most recent call last):\n  File..."
    
    async def test_send_error_notification_without_traceback(self, mock_connection_manager):
        """Test sending error notification without traceback"""
        await send_error_notification(
            error_type=ErrorType.VALIDATION,
            message="Invalid data format"
        )
        
        call_args = mock_connection_manager.broadcast_error.call_args[0][0]
        assert call_args.traceback is None
    
    async def test_send_error_notification_all_types(self, mock_connection_manager):
        """Test error notifications for all error types"""
        error_types = [
            ErrorType.API_CONNECTION,
            ErrorType.VALIDATION,
            ErrorType.RAG_RETRIEVAL,
            ErrorType.AGENT_EXECUTION,
            ErrorType.PDF_GENERATION,
            ErrorType.UNKNOWN
        ]
        
        for error_type in error_types:
            await send_error_notification(
                error_type=error_type,
                message=f"Error: {error_type.value}"
            )
        
        assert mock_connection_manager.broadcast_error.call_count == len(error_types)
    
    async def test_send_error_notification_empty_message(self, mock_connection_manager):
        """Test that empty message is handled gracefully"""
        # The function logs the error but doesn't raise
        # This is by design to prevent error notifications from breaking agent execution
        await send_error_notification(
            error_type=ErrorType.UNKNOWN,
            message=""
        )
        
        # Verify broadcast was NOT called due to validation error
        mock_connection_manager.broadcast_error.assert_not_called()


@pytest.mark.asyncio
class TestSendProgressUpdate:
    """Tests for send_progress_update function"""
    
    async def test_send_valid_progress_update(self, mock_connection_manager):
        """Test sending a valid progress update"""
        await send_progress_update(
            current_step=15,
            total_steps=50,
            description="Processing project 15 of 50"
        )
        
        # Verify broadcast was called
        mock_connection_manager.broadcast_progress.assert_called_once()
        
        # Verify the message structure
        call_args = mock_connection_manager.broadcast_progress.call_args[0][0]
        assert isinstance(call_args, ProgressMessage)
        assert call_args.current_step == 15
        assert call_args.total_steps == 50
        assert call_args.percentage == 30.0
        assert call_args.description == "Processing project 15 of 50"
    
    async def test_send_progress_update_without_description(self, mock_connection_manager):
        """Test progress update without description"""
        await send_progress_update(
            current_step=25,
            total_steps=100
        )
        
        call_args = mock_connection_manager.broadcast_progress.call_args[0][0]
        assert call_args.description is None
        assert call_args.percentage == 25.0
    
    async def test_send_progress_update_percentage_calculation(self, mock_connection_manager):
        """Test that percentage is calculated correctly"""
        test_cases = [
            (0, 100, 0.0),
            (50, 100, 50.0),
            (100, 100, 100.0),
            (1, 3, 33.333333333333336),
            (2, 3, 66.66666666666667)
        ]
        
        for current, total, expected_pct in test_cases:
            await send_progress_update(
                current_step=current,
                total_steps=total
            )
            
            call_args = mock_connection_manager.broadcast_progress.call_args[0][0]
            assert abs(call_args.percentage - expected_pct) < 0.01
    
    async def test_send_progress_update_zero_total_steps(self, mock_connection_manager):
        """Test progress update with zero total steps"""
        # Should handle gracefully with 0% progress
        await send_progress_update(
            current_step=0,
            total_steps=0
        )
        
        # Validation will catch this
        # The function calculates 0% but Pydantic validation should fail
        # because total_steps must be > 0


@pytest.mark.asyncio
class TestConvenienceFunctions:
    """Tests for convenience functions"""
    
    async def test_send_agent_started(self, mock_connection_manager):
        """Test send_agent_started convenience function"""
        await send_agent_started(
            stage=AgentStage.DATA_INGESTION,
            details="Starting data ingestion"
        )
        
        call_args = mock_connection_manager.broadcast_status_update.call_args[0][0]
        assert call_args.stage == AgentStage.DATA_INGESTION
        assert call_args.status == AgentStatus.IN_PROGRESS
        assert call_args.details == "Starting data ingestion"
    
    async def test_send_agent_completed(self, mock_connection_manager):
        """Test send_agent_completed convenience function"""
        await send_agent_completed(
            stage=AgentStage.QUALIFICATION,
            details="Successfully qualified 15 projects"
        )
        
        call_args = mock_connection_manager.broadcast_status_update.call_args[0][0]
        assert call_args.stage == AgentStage.QUALIFICATION
        assert call_args.status == AgentStatus.COMPLETED
        assert call_args.details == "Successfully qualified 15 projects"
    
    async def test_send_agent_error(self, mock_connection_manager):
        """Test send_agent_error convenience function"""
        await send_agent_error(
            stage=AgentStage.AUDIT_TRAIL,
            details="Failed to generate PDF report"
        )
        
        call_args = mock_connection_manager.broadcast_status_update.call_args[0][0]
        assert call_args.stage == AgentStage.AUDIT_TRAIL
        assert call_args.status == AgentStatus.ERROR
        assert call_args.details == "Failed to generate PDF report"


@pytest.mark.asyncio
class TestConnectionMonitoring:
    """Tests for connection monitoring functions"""
    
    def test_get_active_connection_count(self, mock_connection_manager):
        """Test getting active connection count"""
        mock_connection_manager.get_connection_count.return_value = 5
        
        count = get_active_connection_count()
        
        assert count == 5
        mock_connection_manager.get_connection_count.assert_called_once()
    
    def test_get_active_connection_count_zero(self, mock_connection_manager):
        """Test getting connection count when no clients connected"""
        mock_connection_manager.get_connection_count.return_value = 0
        
        count = get_active_connection_count()
        
        assert count == 0


@pytest.mark.asyncio
class TestBroadcastCustomMessage:
    """Tests for broadcast_custom_message function"""
    
    async def test_broadcast_custom_message(self, mock_connection_manager):
        """Test broadcasting a custom message"""
        await broadcast_custom_message(
            message_type="credit_calculation",
            total_credit=125000.50,
            qualified_projects=15
        )
        
        # Verify broadcast was called
        mock_connection_manager.broadcast.assert_called_once()
        
        # Verify the message structure
        call_args = mock_connection_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "credit_calculation"
        assert call_args["total_credit"] == 125000.50
        assert call_args["qualified_projects"] == 15
        assert "timestamp" in call_args
    
    async def test_broadcast_custom_message_multiple_fields(self, mock_connection_manager):
        """Test broadcasting custom message with multiple fields"""
        await broadcast_custom_message(
            message_type="workflow_complete",
            total_credit=125000.50,
            qualified_projects=15,
            qualified_hours=2340.5,
            tax_year=2024,
            report_path="/outputs/reports/rd_tax_credit_2024.pdf"
        )
        
        call_args = mock_connection_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "workflow_complete"
        assert call_args["total_credit"] == 125000.50
        assert call_args["qualified_projects"] == 15
        assert call_args["qualified_hours"] == 2340.5
        assert call_args["tax_year"] == 2024
        assert call_args["report_path"] == "/outputs/reports/rd_tax_credit_2024.pdf"
    
    async def test_broadcast_custom_message_error_handling(self, mock_connection_manager):
        """Test that custom message broadcast errors are handled"""
        mock_connection_manager.broadcast.side_effect = Exception("Broadcast failed")
        
        # Should not raise exception
        await broadcast_custom_message(
            message_type="test",
            data="test_data"
        )


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for complete workflows"""
    
    async def test_complete_agent_workflow(self, mock_connection_manager):
        """Test a complete agent workflow with multiple status updates"""
        # Start agent
        await send_agent_started(
            stage=AgentStage.DATA_INGESTION,
            details="Starting data ingestion"
        )
        
        # Send progress updates
        for i in range(1, 4):
            await send_progress_update(
                current_step=i,
                total_steps=3,
                description=f"Processing step {i}"
            )
        
        # Complete agent
        await send_agent_completed(
            stage=AgentStage.DATA_INGESTION,
            details="Data ingestion completed"
        )
        
        # Verify all broadcasts were called
        assert mock_connection_manager.broadcast_status_update.call_count == 2  # start + complete
        assert mock_connection_manager.broadcast_progress.call_count == 3
    
    async def test_error_workflow(self, mock_connection_manager):
        """Test error handling workflow"""
        # Start agent
        await send_agent_started(
            stage=AgentStage.QUALIFICATION,
            details="Starting qualification"
        )
        
        # Send error notification
        await send_error_notification(
            error_type=ErrorType.API_CONNECTION,
            message="API connection failed"
        )
        
        # Update agent status to error
        await send_agent_error(
            stage=AgentStage.QUALIFICATION,
            details="Qualification failed due to API error"
        )
        
        # Verify broadcasts
        assert mock_connection_manager.broadcast_status_update.call_count == 2
        assert mock_connection_manager.broadcast_error.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
