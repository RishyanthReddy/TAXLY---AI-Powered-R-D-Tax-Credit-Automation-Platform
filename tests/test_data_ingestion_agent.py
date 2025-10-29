"""
Unit tests for Data Ingestion Agent.

Tests the DataIngestionAgent class structure, initialization, and basic functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from agents.data_ingestion_agent import (
    DataIngestionAgent,
    DataIngestionState,
    DataIngestionResult
)
from models.financial_models import EmployeeTimeEntry, ProjectCost
from models.websocket_models import AgentStatus, AgentStage, StatusUpdateMessage
from tools.api_connectors import ClockifyConnector, UnifiedToConnector
from utils.exceptions import APIConnectionError


class TestDataIngestionState:
    """Test DataIngestionState model."""
    
    def test_initial_state(self):
        """Test initial state values."""
        state = DataIngestionState()
        
        assert state.stage == "initializing"
        assert state.status == AgentStatus.PENDING
        assert state.time_entries_fetched == 0
        assert state.costs_fetched == 0
        assert state.validation_errors == 0
        assert state.deduplication_count == 0
        assert state.start_time is None
        assert state.end_time is None
        assert state.error_message is None
    
    def test_to_status_message(self):
        """Test conversion to StatusUpdateMessage."""
        state = DataIngestionState(
            stage="fetching_time_entries",
            status=AgentStatus.IN_PROGRESS,
            time_entries_fetched=100,
            costs_fetched=50
        )
        
        message = state.to_status_message()
        
        assert isinstance(message, StatusUpdateMessage)
        assert message.stage == AgentStage.DATA_INGESTION
        assert message.status == AgentStatus.IN_PROGRESS
        assert "100 time entries" in message.details
        assert "50 costs" in message.details
    
    def test_to_status_message_completed(self):
        """Test status message for completed state."""
        state = DataIngestionState(
            stage="completed",
            status=AgentStatus.COMPLETED,
            time_entries_fetched=200,
            costs_fetched=100
        )
        
        message = state.to_status_message()
        
        assert message.status == AgentStatus.COMPLETED
        assert "Successfully ingested" in message.details
    
    def test_to_status_message_error(self):
        """Test status message for error state."""
        state = DataIngestionState(
            stage="error",
            status=AgentStatus.ERROR,
            error_message="API connection failed"
        )
        
        message = state.to_status_message()
        
        assert message.status == AgentStatus.ERROR
        assert "API connection failed" in message.details


class TestDataIngestionResult:
    """Test DataIngestionResult model."""
    
    def test_empty_result(self):
        """Test empty result initialization."""
        result = DataIngestionResult()
        
        assert result.time_entries == []
        assert result.costs == []
        assert result.validation_errors == []
        assert result.deduplication_count == 0
        assert result.execution_time_seconds == 0.0
        assert result.summary == ""
    
    def test_result_with_data(self):
        """Test result with data."""
        time_entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime.now() - timedelta(days=1)
        )
        
        result = DataIngestionResult(
            time_entries=[time_entry],
            costs=[],
            validation_errors=["Error 1", "Error 2"],
            deduplication_count=5,
            execution_time_seconds=12.5,
            summary="Test summary"
        )
        
        assert len(result.time_entries) == 1
        assert len(result.validation_errors) == 2
        assert result.deduplication_count == 5
        assert result.execution_time_seconds == 12.5


class TestDataIngestionAgent:
    """Test DataIngestionAgent class."""
    
    @pytest.fixture
    def mock_clockify(self):
        """Create mock Clockify connector."""
        mock = Mock(spec=ClockifyConnector)
        mock.fetch_time_entries = Mock(return_value=[])
        mock._transform_time_entry = Mock(return_value=None)
        return mock
    
    @pytest.fixture
    def mock_unified_to(self):
        """Create mock Unified.to connector."""
        mock = Mock(spec=UnifiedToConnector)
        return mock
    
    @pytest.fixture
    def agent(self, mock_clockify, mock_unified_to):
        """Create DataIngestionAgent instance."""
        return DataIngestionAgent(
            clockify_connector=mock_clockify,
            unified_to_connector=mock_unified_to
        )
    
    def test_initialization(self, mock_clockify, mock_unified_to):
        """Test agent initialization."""
        agent = DataIngestionAgent(
            clockify_connector=mock_clockify,
            unified_to_connector=mock_unified_to
        )
        
        assert agent.clockify == mock_clockify
        assert agent.unified_to == mock_unified_to
        assert agent.status_callback is None
        assert isinstance(agent.state, DataIngestionState)
        assert agent.state.status == AgentStatus.PENDING
    
    def test_initialization_with_callback(self, mock_clockify, mock_unified_to):
        """Test agent initialization with status callback."""
        callback = Mock()
        
        agent = DataIngestionAgent(
            clockify_connector=mock_clockify,
            unified_to_connector=mock_unified_to,
            status_callback=callback
        )
        
        assert agent.status_callback == callback
    
    def test_initialization_without_clockify(self, mock_unified_to):
        """Test that initialization fails without Clockify connector."""
        with pytest.raises(ValueError, match="clockify_connector cannot be None"):
            DataIngestionAgent(
                clockify_connector=None,
                unified_to_connector=mock_unified_to
            )
    
    def test_initialization_without_unified_to(self, mock_clockify):
        """Test that initialization fails without Unified.to connector."""
        with pytest.raises(ValueError, match="unified_to_connector cannot be None"):
            DataIngestionAgent(
                clockify_connector=mock_clockify,
                unified_to_connector=None
            )
    
    def test_get_state(self, agent):
        """Test getting agent state."""
        state = agent.get_state()
        
        assert isinstance(state, DataIngestionState)
        assert state.status == AgentStatus.PENDING
    
    def test_reset_state(self, agent):
        """Test resetting agent state."""
        # Modify state
        agent.state.time_entries_fetched = 100
        agent.state.status = AgentStatus.COMPLETED
        
        # Reset
        agent.reset_state()
        
        # Verify reset
        assert agent.state.time_entries_fetched == 0
        assert agent.state.status == AgentStatus.PENDING
    
    def test_update_status(self, agent):
        """Test status update method."""
        agent._update_status(
            stage="fetching_time_entries",
            status=AgentStatus.IN_PROGRESS
        )
        
        assert agent.state.stage == "fetching_time_entries"
        assert agent.state.status == AgentStatus.IN_PROGRESS
        assert agent.state.error_message is None
    
    def test_update_status_with_error(self, agent):
        """Test status update with error message."""
        agent._update_status(
            stage="error",
            status=AgentStatus.ERROR,
            error_message="Test error"
        )
        
        assert agent.state.stage == "error"
        assert agent.state.status == AgentStatus.ERROR
        assert agent.state.error_message == "Test error"
    
    def test_update_status_with_callback(self, mock_clockify, mock_unified_to):
        """Test status update triggers callback."""
        callback = Mock()
        agent = DataIngestionAgent(
            clockify_connector=mock_clockify,
            unified_to_connector=mock_unified_to,
            status_callback=callback
        )
        
        agent._update_status(
            stage="test_stage",
            status=AgentStatus.IN_PROGRESS
        )
        
        # Verify callback was called
        callback.assert_called_once()
        
        # Verify callback received StatusUpdateMessage
        call_args = callback.call_args[0]
        assert isinstance(call_args[0], StatusUpdateMessage)
    
    def test_run_invalid_date_range(self, agent):
        """Test that run fails with invalid date range."""
        start_date = datetime(2024, 2, 1)
        end_date = datetime(2024, 1, 1)  # Before start_date
        
        with pytest.raises(ValueError, match="start_date must be before or equal to end_date"):
            agent.run(start_date=start_date, end_date=end_date)
    
    def test_run_empty_data(self, agent, mock_clockify):
        """Test run with empty data from APIs."""
        # Mock empty responses
        mock_clockify.fetch_time_entries.return_value = []
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = agent.run(start_date=start_date, end_date=end_date)
        
        # Verify result
        assert isinstance(result, DataIngestionResult)
        assert len(result.time_entries) == 0
        assert len(result.costs) == 0
        assert agent.state.status == AgentStatus.COMPLETED
        assert agent.state.start_time is not None
        assert agent.state.end_time is not None
    
    def test_run_with_time_entries(self, agent, mock_clockify):
        """Test run with time entries from Clockify."""
        # Create sample time entry
        sample_entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime(2024, 1, 15)
        )
        
        # Mock Clockify responses
        raw_entry = {
            'id': 'entry123',
            'userId': 'EMP001',
            'userName': 'John Doe',
            'projectName': 'Project Alpha',
            'description': 'Development work',
            'duration': 'PT8H',
            'timeInterval': {
                'start': '2024-01-15T09:00:00Z',
                'end': '2024-01-15T17:00:00Z'
            }
        }
        
        mock_clockify.fetch_time_entries.return_value = [raw_entry]
        mock_clockify._transform_time_entry.return_value = sample_entry
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = agent.run(start_date=start_date, end_date=end_date)
        
        # Verify result
        assert len(result.time_entries) == 1
        assert result.time_entries[0].employee_id == "EMP001"
        assert agent.state.time_entries_fetched == 1
        assert agent.state.status == AgentStatus.COMPLETED
    
    def test_run_handles_api_error(self, agent, mock_clockify):
        """Test that run handles API connection errors."""
        # Mock API error
        mock_clockify.fetch_time_entries.side_effect = APIConnectionError(
            message="Connection failed",
            api_name="Clockify",
            endpoint="/time-entries"
        )
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        with pytest.raises(APIConnectionError):
            agent.run(start_date=start_date, end_date=end_date)
        
        # Verify error state
        assert agent.state.status == AgentStatus.ERROR
        assert agent.state.error_message is not None
        assert "API connection failed" in agent.state.error_message
    
    def test_fetch_time_entries_success(self, agent, mock_clockify):
        """Test successful time entry fetching."""
        sample_entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime(2024, 1, 15)
        )
        
        raw_entry = {'id': 'entry123'}
        mock_clockify.fetch_time_entries.return_value = [raw_entry]
        mock_clockify._transform_time_entry.return_value = sample_entry
        
        entries, errors = agent._fetch_time_entries(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert len(entries) == 1
        assert len(errors) == 0
        assert entries[0].employee_id == "EMP001"
    
    def test_fetch_time_entries_with_validation_errors(self, agent, mock_clockify):
        """Test time entry fetching with validation errors."""
        raw_entries = [
            {'id': 'entry1'},
            {'id': 'entry2'},
            {'id': 'entry3'}
        ]
        
        # Mock: first succeeds, second fails, third succeeds
        valid_entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime(2024, 1, 15)
        )
        
        mock_clockify.fetch_time_entries.return_value = raw_entries
        mock_clockify._transform_time_entry.side_effect = [
            valid_entry,
            None,  # Failed transformation
            valid_entry
        ]
        
        entries, errors = agent._fetch_time_entries(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert len(entries) == 2
        assert len(errors) == 1
        assert "entry2" in errors[0]
    
    def test_fetch_time_entries_with_empty_fields(self, agent, mock_clockify):
        """Test time entry fetching with empty required fields."""
        raw_entries = [
            {'id': 'entry1'},
            {'id': 'entry2'}
        ]
        
        # Create entries - one with whitespace-only field, one valid
        # Note: Pydantic min_length prevents truly empty strings, but we can test whitespace
        invalid_entry = EmployeeTimeEntry(
            employee_id=" ",  # Whitespace-only employee_id
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime(2024, 1, 15)
        )
        
        valid_entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime(2024, 1, 15)
        )
        
        mock_clockify.fetch_time_entries.return_value = raw_entries
        mock_clockify._transform_time_entry.side_effect = [
            invalid_entry,
            valid_entry
        ]
        
        entries, errors = agent._fetch_time_entries(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        # Only valid entry should be included
        assert len(entries) == 1
        assert len(errors) == 1
        assert "employee_id is empty" in errors[0]
    
    def test_fetch_time_entries_with_exception(self, agent, mock_clockify):
        """Test time entry fetching when transformation raises exception."""
        raw_entries = [
            {'id': 'entry1'},
            {'id': 'entry2'}
        ]
        
        valid_entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime(2024, 1, 15)
        )
        
        mock_clockify.fetch_time_entries.return_value = raw_entries
        mock_clockify._transform_time_entry.side_effect = [
            ValueError("Invalid hours value"),
            valid_entry
        ]
        
        entries, errors = agent._fetch_time_entries(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        # Only valid entry should be included
        assert len(entries) == 1
        assert len(errors) == 1
        assert "entry1" in errors[0]
        assert "ValueError" in errors[0] or "Pydantic validation failed" in errors[0]
    
    def test_validate_pydantic_model_success(self, agent):
        """Test successful Pydantic model validation."""
        data = {
            'employee_id': 'EMP001',
            'employee_name': 'John Doe',
            'project_name': 'Project Alpha',
            'task_description': 'Development work',
            'hours_spent': 8.0,
            'date': datetime(2024, 1, 15)
        }
        
        model, error = agent._validate_pydantic_model(
            EmployeeTimeEntry,
            data,
            'test_entry'
        )
        
        assert model is not None
        assert error is None
        assert isinstance(model, EmployeeTimeEntry)
        assert model.employee_id == 'EMP001'
    
    def test_validate_pydantic_model_failure(self, agent):
        """Test Pydantic model validation failure."""
        data = {
            'employee_id': 'EMP001',
            'employee_name': 'John Doe',
            'project_name': 'Project Alpha',
            'task_description': 'Development work',
            'hours_spent': 25.0,  # Invalid: > 24 hours
            'date': datetime(2024, 1, 15)
        }
        
        model, error = agent._validate_pydantic_model(
            EmployeeTimeEntry,
            data,
            'test_entry'
        )
        
        assert model is None
        assert error is not None
        assert 'test_entry' in error
        assert 'validation failed' in error.lower()
    
    def test_validate_pydantic_model_missing_field(self, agent):
        """Test Pydantic model validation with missing required field."""
        data = {
            'employee_id': 'EMP001',
            'employee_name': 'John Doe',
            # Missing project_name
            'task_description': 'Development work',
            'hours_spent': 8.0,
            'date': datetime(2024, 1, 15)
        }
        
        model, error = agent._validate_pydantic_model(
            EmployeeTimeEntry,
            data,
            'test_entry'
        )
        
        assert model is None
        assert error is not None
        assert 'test_entry' in error
    
    def test_run_collects_all_validation_errors(self, agent, mock_clockify):
        """Test that run collects all validation errors without stopping."""
        raw_entries = [
            {'id': 'entry1'},
            {'id': 'entry2'},
            {'id': 'entry3'},
            {'id': 'entry4'}
        ]
        
        valid_entry1 = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime(2024, 1, 15)
        )
        
        # Second valid entry with different date to avoid deduplication
        valid_entry2 = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="John Doe",
            project_name="Project Alpha",
            task_description="Development work",
            hours_spent=8.0,
            date=datetime(2024, 1, 16)  # Different date
        )
        
        # Mix of valid and invalid entries
        mock_clockify.fetch_time_entries.return_value = raw_entries
        mock_clockify._transform_time_entry.side_effect = [
            valid_entry1,
            None,  # Failed transformation
            ValueError("Invalid data"),
            valid_entry2
        ]
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = agent.run(start_date=start_date, end_date=end_date)
        
        # Should have 2 valid entries and 2 errors
        assert len(result.time_entries) == 2
        assert len(result.validation_errors) == 2
        assert agent.state.validation_errors == 2
        assert agent.state.status == AgentStatus.COMPLETED
    
    def test_fetch_costs_placeholder(self, agent):
        """Test that fetch_costs returns empty list (placeholder)."""
        costs, errors = agent._fetch_costs(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )
        
        assert costs == []
        assert errors == []
    
    def test_deduplicate_time_entries_no_duplicates(self, agent):
        """Test deduplication with no duplicate entries."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work",
                hours_spent=8.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Project Beta",
                task_description="Work",
                hours_spent=6.0,
                date=datetime(2024, 1, 15)
            )
        ]
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        assert len(deduplicated) == 2
        assert count == 0
    
    def test_deduplicate_time_entries_with_duplicates(self, agent):
        """Test deduplication with duplicate entries."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Morning work",
                hours_spent=4.0,
                date=datetime(2024, 1, 15, 9, 0)
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Afternoon work",
                hours_spent=4.0,
                date=datetime(2024, 1, 15, 14, 0)
            )
        ]
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        # Should merge into one entry with 8 hours
        assert len(deduplicated) == 1
        assert count == 1
        assert deduplicated[0].hours_spent == 8.0
        assert deduplicated[0].employee_id == "EMP001"
        assert deduplicated[0].project_name == "Project Alpha"
    
    def test_deduplicate_time_entries_multiple_duplicates(self, agent):
        """Test deduplication with multiple duplicate entries."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work 1",
                hours_spent=2.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work 2",
                hours_spent=3.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work 3",
                hours_spent=3.0,
                date=datetime(2024, 1, 15)
            )
        ]
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        # Should merge into one entry with 8 hours total
        assert len(deduplicated) == 1
        assert count == 2  # 2 duplicates removed
        assert deduplicated[0].hours_spent == 8.0
    
    def test_deduplicate_time_entries_different_dates(self, agent):
        """Test that entries on different dates are not deduplicated."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work",
                hours_spent=8.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work",
                hours_spent=8.0,
                date=datetime(2024, 1, 16)
            )
        ]
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        # Should keep both entries (different dates)
        assert len(deduplicated) == 2
        assert count == 0
    
    def test_deduplicate_time_entries_different_projects(self, agent):
        """Test that entries on different projects are not deduplicated."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work",
                hours_spent=4.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Beta",
                task_description="Work",
                hours_spent=4.0,
                date=datetime(2024, 1, 15)
            )
        ]
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        # Should keep both entries (different projects)
        assert len(deduplicated) == 2
        assert count == 0
    
    def test_deduplicate_time_entries_different_employees(self, agent):
        """Test that entries from different employees are not deduplicated."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work",
                hours_spent=8.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Project Alpha",
                task_description="Work",
                hours_spent=8.0,
                date=datetime(2024, 1, 15)
            )
        ]
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        # Should keep both entries (different employees)
        assert len(deduplicated) == 2
        assert count == 0
    
    def test_deduplicate_time_entries_empty_list(self, agent):
        """Test deduplication with empty list."""
        entries = []
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        assert len(deduplicated) == 0
        assert count == 0
    
    def test_deduplicate_time_entries_preserves_first_entry_fields(self, agent):
        """Test that deduplication preserves fields from the first entry."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="First task description",
                hours_spent=4.0,
                date=datetime(2024, 1, 15, 9, 0),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Second task description",
                hours_spent=4.0,
                date=datetime(2024, 1, 15, 14, 0),
                is_rd_classified=False
            )
        ]
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        # Should keep first entry's fields (except hours which are summed)
        assert len(deduplicated) == 1
        assert count == 1
        assert deduplicated[0].task_description == "First task description"
        assert deduplicated[0].is_rd_classified == True
        assert deduplicated[0].hours_spent == 8.0
    
    def test_deduplicate_time_entries_complex_scenario(self, agent):
        """Test deduplication with complex mix of duplicates and unique entries."""
        entries = [
            # EMP001 - Project Alpha - Jan 15 (3 duplicates)
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work 1",
                hours_spent=2.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work 2",
                hours_spent=3.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work 3",
                hours_spent=3.0,
                date=datetime(2024, 1, 15)
            ),
            # EMP001 - Project Alpha - Jan 16 (unique)
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Work",
                hours_spent=8.0,
                date=datetime(2024, 1, 16)
            ),
            # EMP001 - Project Beta - Jan 15 (unique)
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Beta",
                task_description="Work",
                hours_spent=4.0,
                date=datetime(2024, 1, 15)
            ),
            # EMP002 - Project Alpha - Jan 15 (2 duplicates)
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Project Alpha",
                task_description="Work 1",
                hours_spent=4.0,
                date=datetime(2024, 1, 15)
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Project Alpha",
                task_description="Work 2",
                hours_spent=4.0,
                date=datetime(2024, 1, 15)
            )
        ]
        
        deduplicated, count = agent._deduplicate_time_entries(entries)
        
        # Should have 4 unique entries (2 duplicates removed from EMP001, 1 from EMP002)
        assert len(deduplicated) == 4
        assert count == 3
        
        # Verify the merged entries have correct hours
        emp001_alpha_jan15 = [e for e in deduplicated 
                              if e.employee_id == "EMP001" 
                              and e.project_name == "Project Alpha" 
                              and e.date.day == 15][0]
        assert emp001_alpha_jan15.hours_spent == 8.0
        
        emp002_alpha_jan15 = [e for e in deduplicated 
                              if e.employee_id == "EMP002" 
                              and e.project_name == "Project Alpha"][0]
        assert emp002_alpha_jan15.hours_spent == 8.0
    
    def test_check_data_quality_no_issues(self, agent):
        """Test data quality checks with clean data."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Development work",
                hours_spent=8.0,
                date=datetime.now() - timedelta(days=1)
            )
        ]
        
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=1000.0,
                project_name="Project Alpha",
                employee_id="EMP001",
                date=datetime.now() - timedelta(days=1)
            )
        ]
        
        warnings = agent._check_data_quality(entries, costs)
        
        assert warnings == []
    
    def test_check_data_quality_suspicious_hours(self, agent):
        """Test data quality check flags suspicious hours (> 16 hours/day)."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Development work",
                hours_spent=18.0,  # Suspicious: > 16 hours
                date=datetime.now() - timedelta(days=1)
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Project Beta",
                task_description="Development work",
                hours_spent=8.0,  # Normal
                date=datetime.now() - timedelta(days=1)
            )
        ]
        
        warnings = agent._check_data_quality(entries, [])
        
        assert len(warnings) == 1
        assert "Suspicious time entry" in warnings[0]
        assert "18.0 hours" in warnings[0]
        assert "EMP001" in warnings[0]
        assert "exceeds 16 hours/day threshold" in warnings[0]
    
    def test_check_data_quality_future_date_time_entry(self, agent):
        """Test that Pydantic validation prevents future dates in time entries.
        
        Note: The EmployeeTimeEntry model has a validator that prevents future dates,
        so this test verifies that invalid entries cannot be created in the first place.
        The data quality check serves as a defensive secondary check.
        """
        future_date = datetime.now() + timedelta(days=7)
        
        # Verify that Pydantic prevents creation of entries with future dates
        with pytest.raises(Exception):  # Will raise ValidationError
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Development work",
                hours_spent=8.0,
                date=future_date
            )
    
    def test_check_data_quality_future_date_cost(self, agent):
        """Test data quality check flags future dates in costs."""
        future_date = datetime.now() + timedelta(days=7)
        
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=1000.0,
                project_name="Project Alpha",
                employee_id="EMP001",
                date=future_date
            )
        ]
        
        warnings = agent._check_data_quality([], costs)
        
        assert len(warnings) == 1
        assert "Invalid date" in warnings[0]
        assert "future" in warnings[0]
        assert "COST001" in warnings[0]
    
    def test_check_data_quality_multiple_issues(self, agent):
        """Test data quality check with multiple issues."""
        past_date = datetime.now() - timedelta(days=1)
        
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Development work",
                hours_spent=20.0,  # Suspicious
                date=past_date
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Project Beta",
                task_description="Development work",
                hours_spent=8.0,
                date=past_date
            ),
            EmployeeTimeEntry(
                employee_id="EMP003",
                employee_name="Bob Wilson",
                project_name="Project Gamma",
                task_description="Development work",
                hours_spent=18.5,  # Suspicious
                date=past_date
            )
        ]
        
        warnings = agent._check_data_quality(entries, [])
        
        # Should have 2 warnings: 2 suspicious hours
        assert len(warnings) == 2
        
        # Check that all issues are captured
        suspicious_warnings = [w for w in warnings if "Suspicious" in w]
        
        assert len(suspicious_warnings) == 2
        assert "EMP001" in suspicious_warnings[0] or "EMP001" in suspicious_warnings[1]
        assert "EMP003" in suspicious_warnings[0] or "EMP003" in suspicious_warnings[1]
    
    def test_check_data_quality_empty_lists(self, agent):
        """Test data quality checks with empty lists."""
        warnings = agent._check_data_quality([], [])
        
        assert warnings == []
    
    def test_check_data_quality_edge_case_16_hours(self, agent):
        """Test that exactly 16 hours does not trigger warning."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Development work",
                hours_spent=16.0,  # Exactly 16 hours - should be OK
                date=datetime.now() - timedelta(days=1)
            )
        ]
        
        warnings = agent._check_data_quality(entries, [])
        
        assert warnings == []
    
    def test_check_data_quality_edge_case_16_point_1_hours(self, agent):
        """Test that 16.1 hours triggers warning."""
        entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Project Alpha",
                task_description="Development work",
                hours_spent=16.1,  # Just over 16 hours
                date=datetime.now() - timedelta(days=1)
            )
        ]
        
        warnings = agent._check_data_quality(entries, [])
        
        assert len(warnings) == 1
        assert "Suspicious" in warnings[0]
        assert "16.1 hours" in warnings[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
