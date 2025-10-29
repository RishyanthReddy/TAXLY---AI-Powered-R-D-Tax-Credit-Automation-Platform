"""
Unit tests for Qualification Agent.

Tests the QualificationAgent class structure, initialization, state management,
and project filtering logic.

Requirements: Testing
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from agents.qualification_agent import (
    QualificationAgent,
    QualificationState,
    QualificationResult
)
from models.financial_models import EmployeeTimeEntry, ProjectCost
from models.tax_models import QualifiedProject
from models.websocket_models import AgentStage, AgentStatus
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.exceptions import RAGRetrievalError, APIConnectionError


class TestQualificationState:
    """Test QualificationState model"""
    
    def test_state_initialization(self):
        """Test state initializes with correct defaults"""
        state = QualificationState()
        
        assert state.stage == "initializing"
        assert state.status == AgentStatus.PENDING
        assert state.projects_to_qualify == 0
        assert state.projects_qualified == 0
        assert state.projects_flagged == 0
        assert state.current_project is None
        assert state.start_time is None
        assert state.end_time is None
        assert state.error_message is None
    
    def test_state_to_status_message_pending(self):
        """Test converting pending state to status message"""
        state = QualificationState()
        message = state.to_status_message()
        
        assert message.stage == AgentStage.QUALIFICATION
        assert message.status == AgentStatus.PENDING
        assert "Waiting to start" in message.details
    
    def test_state_to_status_message_in_progress(self):
        """Test converting in-progress state to status message"""
        state = QualificationState(
            stage="qualifying_projects",
            status=AgentStatus.IN_PROGRESS,
            projects_to_qualify=5,
            projects_qualified=2,
            current_project="Alpha Project"
        )
        message = state.to_status_message()
        
        assert message.stage == AgentStage.QUALIFICATION
        assert message.status == AgentStatus.IN_PROGRESS
        assert "Alpha Project" in message.details
        assert "2/5" in message.details
    
    def test_state_to_status_message_completed(self):
        """Test converting completed state to status message"""
        state = QualificationState(
            stage="completed",
            status=AgentStatus.COMPLETED,
            projects_qualified=5,
            projects_flagged=1
        )
        message = state.to_status_message()
        
        assert message.stage == AgentStage.QUALIFICATION
        assert message.status == AgentStatus.COMPLETED
        assert "5 projects" in message.details
        assert "1 flagged" in message.details
    
    def test_state_to_status_message_error(self):
        """Test converting error state to status message"""
        state = QualificationState(
            stage="error",
            status=AgentStatus.ERROR,
            error_message="API connection failed"
        )
        message = state.to_status_message()
        
        assert message.stage == AgentStage.QUALIFICATION
        assert message.status == AgentStatus.ERROR
        assert "API connection failed" in message.details


class TestQualificationResult:
    """Test QualificationResult model"""
    
    def test_result_initialization(self):
        """Test result initializes with correct defaults"""
        result = QualificationResult()
        
        assert result.qualified_projects == []
        assert result.total_qualified_hours == 0.0
        assert result.total_qualified_cost == 0.0
        assert result.estimated_credit == 0.0
        assert result.average_confidence == 0.0
        assert result.flagged_projects == []
        assert result.execution_time_seconds == 0.0
        assert result.summary == ""
    
    def test_result_with_data(self):
        """Test result with qualified projects"""
        projects = [
            QualifiedProject(
                project_name="Project A",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="CFR 26 § 1.41-4",
                reasoning="Meets four-part test",
                irs_source="CFR Title 26"
            )
        ]
        
        result = QualificationResult(
            qualified_projects=projects,
            total_qualified_hours=100.0,
            total_qualified_cost=10000.0,
            estimated_credit=2000.0,
            average_confidence=0.85,
            execution_time_seconds=45.2,
            summary="Successfully qualified 1 project"
        )
        
        assert len(result.qualified_projects) == 1
        assert result.total_qualified_hours == 100.0
        assert result.total_qualified_cost == 10000.0
        assert result.estimated_credit == 2000.0
        assert result.average_confidence == 0.85


class TestQualificationAgentInitialization:
    """Test QualificationAgent initialization"""
    
    def test_agent_initialization_success(self):
        """Test successful agent initialization"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        assert agent.rag_tool == rag_tool
        assert agent.youcom_client == youcom_client
        assert agent.glm_reasoner == glm_reasoner
        assert agent.status_callback is None
        assert isinstance(agent.state, QualificationState)
    
    def test_agent_initialization_with_callback(self):
        """Test agent initialization with status callback"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        callback = Mock()
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            status_callback=callback
        )
        
        assert agent.status_callback == callback
    
    def test_agent_initialization_missing_rag_tool(self):
        """Test agent initialization fails without RAG tool"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        with pytest.raises(ValueError, match="rag_tool cannot be None"):
            QualificationAgent(
                rag_tool=None,
                youcom_client=youcom_client,
                glm_reasoner=glm_reasoner
            )
    
    def test_agent_initialization_missing_youcom_client(self):
        """Test agent initialization fails without You.com client"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        with pytest.raises(ValueError, match="youcom_client cannot be None"):
            QualificationAgent(
                rag_tool=rag_tool,
                youcom_client=None,
                glm_reasoner=glm_reasoner
            )
    
    def test_agent_initialization_missing_glm_reasoner(self):
        """Test agent initialization fails without GLM reasoner"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        
        with pytest.raises(ValueError, match="glm_reasoner cannot be None"):
            QualificationAgent(
                rag_tool=rag_tool,
                youcom_client=youcom_client,
                glm_reasoner=None
            )


class TestQualificationAgentStateManagement:
    """Test QualificationAgent state management"""
    
    def test_get_state(self):
        """Test getting agent state"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        state = agent.get_state()
        assert isinstance(state, QualificationState)
        assert state.status == AgentStatus.PENDING
    
    def test_reset_state(self):
        """Test resetting agent state"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Modify state
        agent.state.stage = "qualifying_projects"
        agent.state.status = AgentStatus.IN_PROGRESS
        agent.state.projects_qualified = 5
        
        # Reset
        agent.reset_state()
        
        # Verify reset
        assert agent.state.stage == "initializing"
        assert agent.state.status == AgentStatus.PENDING
        assert agent.state.projects_qualified == 0
    
    def test_update_status(self):
        """Test updating agent status"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        callback = Mock()
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            status_callback=callback
        )
        
        # Update status
        agent._update_status(
            stage="qualifying_projects",
            status=AgentStatus.IN_PROGRESS,
            current_project="Alpha Project"
        )
        
        # Verify state updated
        assert agent.state.stage == "qualifying_projects"
        assert agent.state.status == AgentStatus.IN_PROGRESS
        assert agent.state.current_project == "Alpha Project"
        
        # Verify callback called
        callback.assert_called_once()
        status_message = callback.call_args[0][0]
        assert status_message.stage == AgentStage.QUALIFICATION
        assert status_message.status == AgentStatus.IN_PROGRESS


class TestQualificationAgentProjectFiltering:
    """Test QualificationAgent project filtering logic"""
    
    def test_filter_rd_projects_empty_inputs(self):
        """Test filtering with no R&D projects"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create entries not marked as R&D
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Admin Work",
                task_description="Administrative tasks",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=False
            )
        ]
        
        costs = []
        
        projects = agent._filter_rd_projects(time_entries, costs)
        
        assert len(projects) == 0
    
    def test_filter_rd_projects_single_project(self):
        """Test filtering with single R&D project"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create R&D entries
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Alpha Development",
                task_description="Algorithm development",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Alpha Development",
                task_description="Testing new algorithms",
                hours_spent=6.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            )
        ]
        
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=5000.0,
                project_name="Alpha Development",
                employee_id="EMP001",
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            )
        ]
        
        projects = agent._filter_rd_projects(time_entries, costs)
        
        assert len(projects) == 1
        assert "Alpha Development" in projects
        assert len(projects["Alpha Development"]["time_entries"]) == 2
        assert len(projects["Alpha Development"]["costs"]) == 1
        assert projects["Alpha Development"]["total_hours"] == 14.0
        assert projects["Alpha Development"]["total_cost"] == 5000.0
    
    def test_filter_rd_projects_multiple_projects(self):
        """Test filtering with multiple R&D projects"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create entries for multiple projects
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Alpha Development",
                task_description="Algorithm development",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Beta Research",
                task_description="Research new methods",
                hours_spent=6.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP003",
                employee_name="Bob Johnson",
                project_name="Admin Work",
                task_description="Administrative tasks",
                hours_spent=4.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=False  # Not R&D
            )
        ]
        
        costs = []
        
        projects = agent._filter_rd_projects(time_entries, costs)
        
        assert len(projects) == 2
        assert "Alpha Development" in projects
        assert "Beta Research" in projects
        assert "Admin Work" not in projects
        assert projects["Alpha Development"]["total_hours"] == 8.0
        assert projects["Beta Research"]["total_hours"] == 6.0


class TestQualificationAgentRun:
    """Test QualificationAgent run method"""
    
    def test_run_with_empty_time_entries(self):
        """Test run fails with empty time entries"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        with pytest.raises(ValueError, match="time_entries cannot be empty"):
            agent.run(time_entries=[], costs=[])
    
    def test_run_with_no_rd_projects(self):
        """Test run with no R&D projects returns empty result"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create entries not marked as R&D
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Admin Work",
                task_description="Administrative tasks",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=False
            )
        ]
        
        result = agent.run(time_entries=time_entries, costs=[])
        
        assert len(result.qualified_projects) == 0
        assert result.total_qualified_hours == 0.0
        assert result.total_qualified_cost == 0.0
        assert result.estimated_credit == 0.0
        assert "No projects marked as R&D" in result.summary
        assert agent.state.status == AgentStatus.COMPLETED
    
    def test_run_with_rd_projects_structure(self):
        """Test run with R&D projects completes structure"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create R&D entries
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Alpha Development",
                task_description="Algorithm development",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            )
        ]
        
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=5000.0,
                project_name="Alpha Development",
                employee_id="EMP001",
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            )
        ]
        
        result = agent.run(time_entries=time_entries, costs=costs)
        
        # Verify structure is in place
        assert isinstance(result, QualificationResult)
        assert agent.state.status == AgentStatus.COMPLETED
        assert agent.state.projects_to_qualify == 1
        assert "initialized for 1 projects" in result.summary
        assert result.execution_time_seconds > 0
    
    def test_run_with_status_callback(self):
        """Test run sends status updates via callback"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        callback = Mock()
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            status_callback=callback
        )
        
        # Create R&D entries
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Alpha Development",
                task_description="Algorithm development",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            )
        ]
        
        result = agent.run(time_entries=time_entries, costs=[])
        
        # Verify callback was called multiple times (filtering, qualifying, completed)
        assert callback.call_count >= 3
        
        # Verify final status is completed
        final_call = callback.call_args_list[-1][0][0]
        assert final_call.status == AgentStatus.COMPLETED


class TestQualificationAgentQualifyProject:
    """Test QualificationAgent _qualify_project method"""
    
    def test_qualify_project_success(self):
        """Test successful project qualification with RAG and You.com Agent API"""
        # Setup mocks
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock RAG context
        from models.tax_models import RAGContext
        mock_rag_context = Mock(spec=RAGContext)
        mock_rag_context.chunk_count = 3
        mock_rag_context.average_relevance = 0.85
        mock_rag_context.chunks = [
            Mock(
                text="IRS guidance on qualified research...",
                source="Form 6765",
                page=1,
                relevance_score=0.9
            )
        ]
        mock_rag_context.format_for_llm_prompt.return_value = "Formatted RAG context"
        
        rag_tool.query.return_value = mock_rag_context
        
        # Mock You.com Agent API response
        mock_agent_response = {
            'output': [{
                'text': '''```json
{
  "qualification_percentage": 85.0,
  "confidence_score": 0.92,
  "reasoning": "This project clearly meets the four-part test for qualified research.",
  "citations": ["CFR Title 26 § 1.41-4(a)(1)", "Form 6765 Instructions"],
  "four_part_test_results": {
    "technological_in_nature": true,
    "elimination_of_uncertainty": true,
    "process_of_experimentation": true,
    "qualified_purpose": true
  },
  "technical_details": "Uncertainty existed regarding algorithm optimization."
}
```''',
                'type': 'chat_node.answer'
            }]
        }
        
        youcom_client.agent_run.return_value = mock_agent_response
        
        # Mock parse response
        mock_parsed_response = {
            'qualification_percentage': 85.0,
            'confidence_score': 0.92,
            'reasoning': 'This project clearly meets the four-part test for qualified research.',
            'citations': ['CFR Title 26 § 1.41-4(a)(1)', 'Form 6765 Instructions'],
            'technical_details': 'Uncertainty existed regarding algorithm optimization.'
        }
        
        youcom_client._parse_agent_response.return_value = mock_parsed_response
        
        # Create agent
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create project data
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Alpha Development",
                task_description="Algorithm optimization",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Alpha Development",
                task_description="Performance testing",
                hours_spent=6.0,
                date=datetime(2024, 1, 16),
                is_rd_classified=True
            )
        ]
        
        project_data = {
            'time_entries': time_entries,
            'costs': [],
            'total_hours': 14.0,
            'total_cost': 1750.0
        }
        
        # Call _qualify_project
        result = agent._qualify_project(
            project_name="Alpha Development",
            project_data=project_data
        )
        
        # Verify result
        assert isinstance(result, QualifiedProject)
        assert result.project_name == "Alpha Development"
        assert result.qualification_percentage == 85.0
        assert result.confidence_score == 0.92
        assert result.qualified_hours == 14.0 * 0.85  # 11.9
        assert result.qualified_cost == 1750.0 * 0.85  # 1487.5
        assert "four-part test" in result.reasoning
        assert result.irs_source is not None
        assert result.supporting_citation is not None
        
        # Verify RAG tool was called
        rag_tool.query.assert_called_once()
        call_args = rag_tool.query.call_args
        assert "Alpha Development" in call_args[1]['question']
        assert call_args[1]['top_k'] == 3
        
        # Verify You.com Agent API was called
        youcom_client.agent_run.assert_called_once()
        call_args = youcom_client.agent_run.call_args
        assert call_args[1]['agent_mode'] == 'express'
        assert call_args[1]['stream'] is False
        
        # Verify parse was called
        youcom_client._parse_agent_response.assert_called_once()
    
    def test_qualify_project_with_empty_data(self):
        """Test _qualify_project fails with empty project data"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        with pytest.raises(ValueError, match="Project data cannot be empty"):
            agent._qualify_project(
                project_name="Test Project",
                project_data={}
            )
    
    def test_qualify_project_with_missing_fields(self):
        """Test _qualify_project fails with missing required fields"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Missing total_cost
        project_data = {
            'time_entries': [],
            'total_hours': 10.0
        }
        
        with pytest.raises(ValueError, match="must contain 'total_hours' and 'total_cost'"):
            agent._qualify_project(
                project_name="Test Project",
                project_data=project_data
            )
    
    def test_qualify_project_rag_failure(self):
        """Test _qualify_project handles RAG retrieval errors"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock RAG failure
        rag_tool.query.side_effect = RAGRetrievalError(
            message="Vector database unavailable",
            query="test query",
            knowledge_base_path="/path/to/kb"
        )
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        project_data = {
            'time_entries': [],
            'total_hours': 10.0,
            'total_cost': 1000.0
        }
        
        with pytest.raises(RAGRetrievalError):
            agent._qualify_project(
                project_name="Test Project",
                project_data=project_data
            )
    
    def test_qualify_project_youcom_api_failure(self):
        """Test _qualify_project handles You.com API errors"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock successful RAG
        from models.tax_models import RAGContext
        mock_rag_context = Mock(spec=RAGContext)
        mock_rag_context.chunk_count = 3
        mock_rag_context.average_relevance = 0.85
        mock_rag_context.chunks = []
        mock_rag_context.format_for_llm_prompt.return_value = "Formatted RAG context"
        rag_tool.query.return_value = mock_rag_context
        
        # Mock You.com API failure
        youcom_client.agent_run.side_effect = APIConnectionError(
            message="API rate limit exceeded",
            endpoint="/v1/agents/runs",
            status_code=429
        )
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        project_data = {
            'time_entries': [],
            'total_hours': 10.0,
            'total_cost': 1000.0
        }
        
        with pytest.raises(APIConnectionError):
            agent._qualify_project(
                project_name="Test Project",
                project_data=project_data
            )
    
    def test_qualify_project_low_confidence_flagged(self):
        """Test _qualify_project flags low confidence projects"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock RAG context
        from models.tax_models import RAGContext
        mock_rag_context = Mock(spec=RAGContext)
        mock_rag_context.chunk_count = 3
        mock_rag_context.average_relevance = 0.85
        mock_rag_context.chunks = [
            Mock(text="IRS guidance", source="Form 6765", page=1)
        ]
        mock_rag_context.format_for_llm_prompt.return_value = "Formatted RAG context"
        rag_tool.query.return_value = mock_rag_context
        
        # Mock You.com Agent API response with low confidence
        mock_agent_response = {
            'output': [{
                'text': '{"qualification_percentage": 50.0, "confidence_score": 0.65, "reasoning": "Uncertain qualification", "citations": []}',
                'type': 'chat_node.answer'
            }]
        }
        youcom_client.agent_run.return_value = mock_agent_response
        
        # Mock parse response
        mock_parsed_response = {
            'qualification_percentage': 50.0,
            'confidence_score': 0.65,  # Below 0.7 threshold
            'reasoning': 'Uncertain qualification',
            'citations': []
        }
        youcom_client._parse_agent_response.return_value = mock_parsed_response
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        project_data = {
            'time_entries': [],
            'total_hours': 10.0,
            'total_cost': 1000.0
        }
        
        result = agent._qualify_project(
            project_name="Uncertain Project",
            project_data=project_data
        )
        
        # Verify project is flagged for review (confidence < 0.7)
        assert result.flagged_for_review is True
        assert result.confidence_score == 0.65


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestCheckRecentGuidance:
    """Test QualificationAgent _check_recent_guidance method"""
    
    def test_check_recent_guidance_with_irs_results(self):
        """Test _check_recent_guidance finds IRS guidance"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Search API response with IRS results
        mock_search_results = [
            {
                'title': 'IRS Updates R&D Tax Credit Guidance for Software Development',
                'url': 'https://www.irs.gov/newsroom/rd-credit-update-2024',
                'description': 'New IRS guidance on qualified research activities for software development',
                'snippets': ['software development', 'qualified research', 'experimentation'],
                'page_age': '2024-01-15'
            },
            {
                'title': 'Federal Register: R&D Tax Credit Regulations',
                'url': 'https://www.federalregister.gov/documents/2024/02/01/rd-credit',
                'description': 'Updated regulations for R&D tax credit qualification',
                'snippets': ['research activities', 'uncertainty', 'qualified expenditure'],
                'page_age': '2024-02-01'
            },
            {
                'title': 'Tech News: R&D Credits',
                'url': 'https://technews.com/rd-credits',
                'description': 'Industry news about R&D credits',
                'snippets': ['tax benefits'],
                'page_age': '2024-03-01'
            }
        ]
        youcom_client.search.return_value = mock_search_results
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create mock qualified projects
        from models.tax_models import QualifiedProject
        qualified_projects = [
            QualifiedProject(
                project_name="Software Development Project",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="IRS guidance",
                reasoning="Qualified research",
                irs_source="Form 6765"
            )
        ]
        
        result = agent._check_recent_guidance(
            tax_year=2024,
            qualified_projects=qualified_projects
        )
        
        # Verify search was called
        youcom_client.search.assert_called_once()
        call_args = youcom_client.search.call_args
        assert 'IRS R&D tax credit' in call_args[1]['query']
        assert call_args[1]['freshness'] == 'year'
        assert call_args[1]['country'] == 'US'
        
        # Verify results
        assert result['has_new_guidance'] is True
        assert len(result['search_results']) == 2  # Only IRS-related results
        assert 'IRS Updates' in result['guidance_summary']
        assert len(result['affected_projects']) > 0
        assert 'Software Development Project' in result['affected_projects']
        assert len(result['recommendations']) > 0
    
    def test_check_recent_guidance_no_irs_results(self):
        """Test _check_recent_guidance with no IRS results"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Search API response with no IRS results
        mock_search_results = [
            {
                'title': 'General Tax News',
                'url': 'https://taxnews.com/general',
                'description': 'General tax information',
                'snippets': ['taxes'],
                'page_age': '2024-01-15'
            }
        ]
        youcom_client.search.return_value = mock_search_results
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        from models.tax_models import QualifiedProject
        qualified_projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=50.0,
                qualified_cost=5000.0,
                confidence_score=0.80,
                qualification_percentage=75.0,
                supporting_citation="IRS guidance",
                reasoning="Qualified",
                irs_source="Form 6765"
            )
        ]
        
        result = agent._check_recent_guidance(
            tax_year=2024,
            qualified_projects=qualified_projects
        )
        
        # Verify results
        assert result['has_new_guidance'] is False
        assert len(result['search_results']) == 0
        assert 'No recent IRS guidance found' in result['guidance_summary']
        assert len(result['affected_projects']) == 0
        assert 'Continue monitoring' in result['recommendations'][0]
    
    def test_check_recent_guidance_api_error(self):
        """Test _check_recent_guidance handles API errors gracefully"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock API error
        from utils.exceptions import APIConnectionError
        youcom_client.search.side_effect = APIConnectionError(
            message="API connection failed",
            endpoint="search",
            status_code=500
        )
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        from models.tax_models import QualifiedProject
        qualified_projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=50.0,
                qualified_cost=5000.0,
                confidence_score=0.80,
                qualification_percentage=75.0,
                supporting_citation="IRS guidance",
                reasoning="Qualified",
                irs_source="Form 6765"
            )
        ]
        
        # Should not raise exception, but return error result
        result = agent._check_recent_guidance(
            tax_year=2024,
            qualified_projects=qualified_projects
        )
        
        # Verify error handling
        assert result['has_new_guidance'] is False
        assert 'Unable to check for recent guidance' in result['guidance_summary']
        assert 'Manually check IRS website' in result['recommendations'][0]
    
    def test_check_recent_guidance_empty_projects(self):
        """Test _check_recent_guidance with empty projects list"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Search API response
        mock_search_results = [
            {
                'title': 'IRS R&D Update',
                'url': 'https://www.irs.gov/rd-update',
                'description': 'R&D guidance update',
                'snippets': ['research', 'software'],
                'page_age': '2024-01-15'
            }
        ]
        youcom_client.search.return_value = mock_search_results
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        result = agent._check_recent_guidance(
            tax_year=2024,
            qualified_projects=[]
        )
        
        # Should still search and find guidance
        assert result['has_new_guidance'] is True
        assert len(result['search_results']) == 1
        # But no projects to flag
        assert len(result['affected_projects']) == 0
    
    def test_check_recent_guidance_filters_non_software_guidance(self):
        """Test _check_recent_guidance only flags relevant projects"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Search API response with non-software guidance
        mock_search_results = [
            {
                'title': 'IRS Manufacturing R&D Guidance',
                'url': 'https://www.irs.gov/manufacturing-rd',
                'description': 'New guidance for manufacturing R&D',
                'snippets': ['manufacturing', 'physical products', 'research'],
                'page_age': '2024-01-15'
            }
        ]
        youcom_client.search.return_value = mock_search_results
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        from models.tax_models import QualifiedProject
        qualified_projects = [
            QualifiedProject(
                project_name="Software Project",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="IRS guidance",
                reasoning="Software development",
                irs_source="Form 6765"
            )
        ]
        
        result = agent._check_recent_guidance(
            tax_year=2024,
            qualified_projects=qualified_projects
        )
        
        # Should find guidance but not flag software projects
        assert result['has_new_guidance'] is True
        assert len(result['search_results']) == 1
        # No software keywords in guidance, so no projects affected
        assert len(result['affected_projects']) == 0


class TestQualificationAgentWithGuidanceCheck:
    """Test QualificationAgent run method with guidance check integration"""
    
    def test_guidance_check_called_with_qualified_projects(self):
        """Test _check_recent_guidance is called when tax_year provided and projects qualified"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock search results
        youcom_client.search.return_value = []
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create mock qualified projects
        from models.tax_models import QualifiedProject
        qualified_projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="IRS guidance",
                reasoning="Qualified research",
                irs_source="Form 6765"
            )
        ]
        
        # Call _check_recent_guidance directly
        result = agent._check_recent_guidance(
            tax_year=2024,
            qualified_projects=qualified_projects
        )
        
        # Verify search was called
        youcom_client.search.assert_called_once()
        call_args = youcom_client.search.call_args
        assert '2024' in call_args[1]['query']
        assert 'IRS R&D tax credit' in call_args[1]['query']
        
        # Verify result structure
        assert 'has_new_guidance' in result
        assert 'guidance_summary' in result
        assert 'search_results' in result
        assert 'affected_projects' in result
        assert 'recommendations' in result
    
    def test_guidance_check_skipped_without_tax_year(self):
        """Test guidance check is skipped when tax_year not provided"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        from models.financial_models import EmployeeTimeEntry
        time_entries = [
            EmployeeTimeEntry(
                employee_id="emp1",
                employee_name="John Doe",
                project_name="Test Project",
                task_description="Development",
                hours_spent=10.0,
                date="2024-01-15",
                is_rd_classified=True
            )
        ]
        
        # Run without tax_year
        result = agent.run(
            time_entries=time_entries,
            costs=[]
        )
        
        # Verify search was NOT called (no tax_year provided)
        youcom_client.search.assert_not_called()
        
        # Verify result doesn't mention guidance check
        assert 'guidance' not in result.summary.lower() or 'no recent' not in result.summary.lower()
    
    def test_guidance_check_skipped_with_no_qualified_projects(self):
        """Test guidance check is skipped when no projects are qualified"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        from models.financial_models import EmployeeTimeEntry
        time_entries = [
            EmployeeTimeEntry(
                employee_id="emp1",
                employee_name="John Doe",
                project_name="Test Project",
                task_description="Development",
                hours_spent=10.0,
                date="2024-01-15",
                is_rd_classified=False  # Not classified as R&D
            )
        ]
        
        # Run with tax_year but no R&D projects
        result = agent.run(
            time_entries=time_entries,
            costs=[],
            tax_year=2024
        )
        
        # Verify search was NOT called (no qualified projects)
        youcom_client.search.assert_not_called()
        
        # Verify no projects were qualified
        assert len(result.qualified_projects) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestFlagLowConfidence:
    """Test QualificationAgent _flag_low_confidence method"""
    
    def test_flag_low_confidence_no_flagged_projects(self):
        """Test flagging when all projects have high confidence"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create projects with high confidence (>= 0.7)
        qualified_projects = [
            QualifiedProject(
                project_name="Project A",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="IRS guidance",
                reasoning="Strong R&D indicators",
                irs_source="CFR Title 26"
            ),
            QualifiedProject(
                project_name="Project B",
                qualified_hours=50.0,
                qualified_cost=5000.0,
                confidence_score=0.75,
                qualification_percentage=70.0,
                supporting_citation="IRS guidance",
                reasoning="Clear R&D activities",
                irs_source="Form 6765"
            )
        ]
        
        # Call flagging method
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify no projects flagged
        assert result['flagged_count'] == 0
        assert len(result['flagged_projects']) == 0
        assert result['average_confidence'] == 0.0
        assert "No projects flagged" in result['summary']
        assert len(result['recommendations']) == 1
        assert "proceed with report generation" in result['recommendations'][0].lower()
    
    def test_flag_low_confidence_moderate_warning(self):
        """Test flagging projects with moderate confidence (0.6 <= confidence < 0.7)"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create project with moderate confidence
        qualified_projects = [
            QualifiedProject(
                project_name="Project Moderate",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.65,
                qualification_percentage=60.0,
                supporting_citation="IRS guidance",
                reasoning="Some R&D indicators",
                irs_source="CFR Title 26"
            )
        ]
        
        # Call flagging method
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify project flagged
        assert result['flagged_count'] == 1
        assert len(result['flagged_projects']) == 1
        
        flagged = result['flagged_projects'][0]
        assert flagged['project_name'] == "Project Moderate"
        assert flagged['confidence_score'] == 0.65
        assert flagged['warning_level'] == "MODERATE"
        assert "Below-threshold confidence" in flagged['warning_message']
        assert "additional evidence" in flagged['warning_message']
        
        # Verify summary
        assert "1 of 1 projects flagged" in result['summary']
        assert "MODERATE" in result['summary']
        assert result['average_confidence'] == 0.65
        
        # Verify recommendations
        assert any("supporting evidence" in rec for rec in result['recommendations'])
        assert any("four-part test" in rec.lower() for rec in result['recommendations'])
    
    def test_flag_low_confidence_high_warning(self):
        """Test flagging projects with high warning (0.5 <= confidence < 0.6)"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create project with high warning confidence
        qualified_projects = [
            QualifiedProject(
                project_name="Project High",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.55,
                qualification_percentage=50.0,
                supporting_citation="IRS guidance",
                reasoning="Limited R&D indicators",
                irs_source="CFR Title 26"
            )
        ]
        
        # Call flagging method
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify project flagged
        assert result['flagged_count'] == 1
        
        flagged = result['flagged_projects'][0]
        assert flagged['warning_level'] == "HIGH"
        assert "Low confidence" in flagged['warning_message']
        assert "additional technical documentation" in flagged['warning_message']
        
        # Verify recommendations
        assert any("substantial additional documentation" in rec 
                  for rec in result['recommendations'])
    
    def test_flag_low_confidence_critical_warning(self):
        """Test flagging projects with critical warning (confidence < 0.5)"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create project with critical confidence
        qualified_projects = [
            QualifiedProject(
                project_name="Project Critical",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.45,
                qualification_percentage=40.0,
                supporting_citation="IRS guidance",
                reasoning="Weak R&D indicators",
                irs_source="CFR Title 26"
            )
        ]
        
        # Call flagging method
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify project flagged
        assert result['flagged_count'] == 1
        
        flagged = result['flagged_projects'][0]
        assert flagged['warning_level'] == "CRITICAL"
        assert "Very low confidence" in flagged['warning_message']
        assert "significant additional documentation" in flagged['warning_message']
        assert "may not withstand IRS audit" in flagged['warning_message']
        
        # Verify recommendations
        assert any("URGENT" in rec and "critical confidence issues" in rec 
                  for rec in result['recommendations'])
        assert any("excluding from claim" in rec or "expert review" in rec 
                  for rec in result['recommendations'])
    
    def test_flag_low_confidence_mixed_projects(self):
        """Test flagging with mix of high and low confidence projects"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create mix of projects
        qualified_projects = [
            QualifiedProject(
                project_name="High Confidence",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="IRS guidance",
                reasoning="Strong R&D",
                irs_source="CFR Title 26"
            ),
            QualifiedProject(
                project_name="Critical",
                qualified_hours=50.0,
                qualified_cost=5000.0,
                confidence_score=0.45,
                qualification_percentage=40.0,
                supporting_citation="IRS guidance",
                reasoning="Weak R&D",
                irs_source="CFR Title 26"
            ),
            QualifiedProject(
                project_name="High Warning",
                qualified_hours=75.0,
                qualified_cost=7500.0,
                confidence_score=0.55,
                qualification_percentage=50.0,
                supporting_citation="IRS guidance",
                reasoning="Limited R&D",
                irs_source="CFR Title 26"
            ),
            QualifiedProject(
                project_name="Moderate",
                qualified_hours=60.0,
                qualified_cost=6000.0,
                confidence_score=0.65,
                qualification_percentage=60.0,
                supporting_citation="IRS guidance",
                reasoning="Some R&D",
                irs_source="CFR Title 26"
            )
        ]
        
        # Call flagging method
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify 3 projects flagged (all except high confidence)
        assert result['flagged_count'] == 3
        assert len(result['flagged_projects']) == 3
        
        # Verify warning levels
        warning_levels = [p['warning_level'] for p in result['flagged_projects']]
        assert 'CRITICAL' in warning_levels
        assert 'HIGH' in warning_levels
        assert 'MODERATE' in warning_levels
        
        # Verify summary includes counts
        assert "3 of 4 projects flagged" in result['summary']
        assert "1 CRITICAL" in result['summary']
        assert "1 HIGH" in result['summary']
        assert "1 MODERATE" in result['summary']
        
        # Verify average confidence
        expected_avg = (0.45 + 0.55 + 0.65) / 3
        assert abs(result['average_confidence'] - expected_avg) < 0.01
        
        # Verify cost percentage calculation
        total_flagged_cost = 5000.0 + 7500.0 + 6000.0  # 18500
        total_cost = 10000.0 + 5000.0 + 7500.0 + 6000.0  # 28500
        expected_pct = (total_flagged_cost / total_cost) * 100
        assert f"{expected_pct:.1f}%" in result['summary']
        
        # Verify all recommendation types present
        assert any("URGENT" in rec for rec in result['recommendations'])
        assert any("substantial additional documentation" in rec for rec in result['recommendations'])
        assert any("supporting evidence" in rec for rec in result['recommendations'])
    
    def test_flag_low_confidence_high_cost_percentage_warning(self):
        """Test additional warning when flagged projects represent >25% of costs"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create projects where low confidence represents >25% of costs
        qualified_projects = [
            QualifiedProject(
                project_name="High Confidence",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="IRS guidance",
                reasoning="Strong R&D",
                irs_source="CFR Title 26"
            ),
            QualifiedProject(
                project_name="Low Confidence",
                qualified_hours=200.0,
                qualified_cost=20000.0,  # 66% of total cost
                confidence_score=0.55,
                qualification_percentage=50.0,
                supporting_citation="IRS guidance",
                reasoning="Limited R&D",
                irs_source="CFR Title 26"
            )
        ]
        
        # Call flagging method
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify high cost warning in recommendations
        assert any("high audit risk" in rec.lower() for rec in result['recommendations'])
        assert any("66.7%" in rec for rec in result['recommendations'])
    
    def test_flag_low_confidence_includes_project_details(self):
        """Test that flagged projects include all necessary details"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create low confidence project
        qualified_projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.65,
                qualification_percentage=60.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Call flagging method
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify flagged project includes all details
        flagged = result['flagged_projects'][0]
        assert flagged['project_name'] == "Test Project"
        assert flagged['confidence_score'] == 0.65
        assert flagged['qualification_percentage'] == 60.0
        assert flagged['qualified_cost'] == 10000.0
        assert flagged['warning_level'] == "MODERATE"
        assert 'warning_message' in flagged
        assert flagged['reasoning'] == "Test reasoning"
        assert flagged['irs_source'] == "Test source"
    
    def test_flag_low_confidence_empty_list(self):
        """Test flagging with empty project list"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Call with empty list
        result = agent._flag_low_confidence([])
        
        # Verify result structure
        assert result['flagged_count'] == 0
        assert len(result['flagged_projects']) == 0
        assert result['average_confidence'] == 0.0
        assert "0 qualified projects" in result['summary']


class TestQualificationAgentCostCorrelation:
    """Test cost correlation accuracy in Qualification Agent"""
    
    def test_cost_correlation_with_pandas_processor(self):
        """Test that agent correctly uses pandas_processor for cost correlation"""
        from utils.pandas_processor import correlate_costs, apply_wage_caps
        
        # Create sample time entries (multiple days to accumulate hours)
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Alpha Development",
                task_description="Development work",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Alpha Development",
                task_description="Development work",
                hours_spent=8.0,
                date=datetime(2024, 1, 16),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Alpha Development",
                task_description="Testing",
                hours_spent=7.5,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP002",
                employee_name="Jane Smith",
                project_name="Alpha Development",
                task_description="Testing",
                hours_spent=7.5,
                date=datetime(2024, 1, 16),
                is_rd_classified=True
            )
        ]
        
        # Create sample costs with hourly rates
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=8000.0,
                project_name="Alpha Development",
                employee_id="EMP001",
                date=datetime(2024, 1, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 100.0}
            ),
            ProjectCost(
                cost_id="COST002",
                cost_type="Payroll",
                amount=6000.0,
                project_name="Alpha Development",
                employee_id="EMP002",
                date=datetime(2024, 1, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 80.0}
            )
        ]
        
        # Test correlate_costs function
        correlated_df = correlate_costs(time_entries, costs, filter_rd_only=True)
        
        # Verify correlation results
        assert not correlated_df.empty
        assert len(correlated_df) >= 2  # At least 2 employee-project combinations
        
        # Verify columns exist
        required_columns = [
            'project_name', 'employee_id', 'employee_name', 'cost_type',
            'total_hours', 'hourly_rate', 'qualified_wages', 'other_costs',
            'total_qualified_cost'
        ]
        for col in required_columns:
            assert col in correlated_df.columns
        
        # Verify calculations
        emp001_row = correlated_df[correlated_df['employee_id'] == 'EMP001'].iloc[0]
        assert emp001_row['total_hours'] == 16.0  # 8 + 8 hours
        assert emp001_row['hourly_rate'] == 100.0
        assert emp001_row['qualified_wages'] == 1600.0  # 16 hours * $100/hr
        
        emp002_row = correlated_df[correlated_df['employee_id'] == 'EMP002'].iloc[0]
        assert emp002_row['total_hours'] == 15.0  # 7.5 + 7.5 hours
        assert emp002_row['hourly_rate'] == 80.0
        assert emp002_row['qualified_wages'] == 1200.0  # 15 hours * $80/hr
    
    def test_cost_correlation_with_non_payroll_costs(self):
        """Test cost correlation includes non-payroll costs (contractor, materials, etc.)"""
        from utils.pandas_processor import correlate_costs
        
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Beta Project",
                task_description="Development",
                hours_spent=20.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            )
        ]
        
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=4000.0,
                project_name="Beta Project",
                employee_id="EMP001",
                date=datetime(2024, 1, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 100.0}
            ),
            ProjectCost(
                cost_id="COST002",
                cost_type="Contractor",
                amount=5000.0,
                project_name="Beta Project",
                employee_id=None,
                date=datetime(2024, 1, 31),
                is_rd_classified=True
            ),
            ProjectCost(
                cost_id="COST003",
                cost_type="Cloud",
                amount=1500.0,
                project_name="Beta Project",
                employee_id=None,
                date=datetime(2024, 1, 31),
                is_rd_classified=True
            )
        ]
        
        correlated_df = correlate_costs(time_entries, costs, filter_rd_only=True)
        
        # Verify all cost types are included
        assert not correlated_df.empty
        cost_types = correlated_df['cost_type'].unique()
        assert 'Payroll' in cost_types
        assert 'Contractor' in cost_types
        assert 'Cloud' in cost_types
        
        # Verify non-payroll costs are captured
        contractor_row = correlated_df[correlated_df['cost_type'] == 'Contractor'].iloc[0]
        assert contractor_row['other_costs'] == 5000.0
        assert contractor_row['qualified_wages'] == 0.0
        
        cloud_row = correlated_df[correlated_df['cost_type'] == 'Cloud'].iloc[0]
        assert cloud_row['other_costs'] == 1500.0
        assert cloud_row['qualified_wages'] == 0.0
    
    def test_cost_correlation_filters_non_rd_entries(self):
        """Test that cost correlation correctly filters non-R&D entries"""
        from utils.pandas_processor import correlate_costs
        
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="R&D Project",
                task_description="Research",
                hours_spent=8.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="R&D Project",
                task_description="Research",
                hours_spent=8.0,
                date=datetime(2024, 1, 16),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="John Doe",
                project_name="Admin Work",
                task_description="Admin tasks",
                hours_spent=6.0,
                date=datetime(2024, 1, 15),
                is_rd_classified=False  # Not R&D
            )
        ]
        
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=8000.0,
                project_name="R&D Project",
                employee_id="EMP001",
                date=datetime(2024, 1, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 100.0}
            ),
            ProjectCost(
                cost_id="COST002",
                cost_type="Payroll",
                amount=2000.0,
                project_name="Admin Work",
                employee_id="EMP001",
                date=datetime(2024, 1, 31),
                is_rd_classified=False  # Not R&D
            )
        ]
        
        # Correlate with filter_rd_only=True
        correlated_df = correlate_costs(time_entries, costs, filter_rd_only=True)
        
        # Verify only R&D entries are included
        assert not correlated_df.empty
        projects = correlated_df['project_name'].unique()
        assert 'R&D Project' in projects
        assert 'Admin Work' not in projects
        
        # Verify hours only include R&D work
        total_hours = correlated_df['total_hours'].sum()
        assert total_hours == 16.0  # Only R&D hours (8+8), not admin hours (6)


class TestQualificationAgentWageCapApplication:
    """Test IRS wage cap application in Qualification Agent"""
    
    def test_wage_cap_application_basic(self):
        """Test that wage caps are correctly applied to high-earning employees"""
        from utils.pandas_processor import correlate_costs, apply_wage_caps
        from utils.constants import IRSWageCap
        
        # Create time entries for high-earning employee across multiple days
        # Total: 1000 hours spread across ~125 working days (8 hours/day)
        time_entries = []
        for day in range(125):
            time_entries.append(
                EmployeeTimeEntry(
                    employee_id="EMP_HIGH",
                    employee_name="High Earner",
                    project_name="Project A",
                    task_description="Development",
                    hours_spent=8.0,
                    date=datetime(2024, 1, 1) + timedelta(days=day),
                    is_rd_classified=True
                )
            )
        
        # Create cost with hourly rate that will exceed wage cap
        # Wage cap for 2024 is $168,600
        # 1000 hours * $200/hr = $200,000 (exceeds cap)
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=200000.0,
                project_name="Project A",
                employee_id="EMP_HIGH",
                date=datetime(2024, 1, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 200.0}
            )
        ]
        
        # Correlate costs
        correlated_df = correlate_costs(time_entries, costs, filter_rd_only=True)
        
        # Apply wage caps for 2024
        capped_df = apply_wage_caps(correlated_df, tax_year=2024)
        
        # Verify wage cap was applied
        assert 'wage_cap_applied' in capped_df.columns
        assert 'original_qualified_wages' in capped_df.columns
        assert 'capped_amount' in capped_df.columns
        
        # Check that cap was applied
        emp_row = capped_df[capped_df['employee_id'] == 'EMP_HIGH'].iloc[0]
        assert emp_row['wage_cap_applied'] == True
        assert emp_row['original_qualified_wages'] == 200000.0
        assert emp_row['qualified_wages'] <= IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
        assert emp_row['capped_amount'] > 0
        
        # Verify capped amount calculation
        expected_capped_amount = 200000.0 - IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
        assert abs(emp_row['capped_amount'] - expected_capped_amount) < 0.01
    
    def test_wage_cap_not_applied_below_threshold(self):
        """Test that wage caps are not applied when wages are below threshold"""
        from utils.pandas_processor import correlate_costs, apply_wage_caps
        
        # Create time entries for normal-earning employee across multiple days
        # Total: 100 hours spread across ~13 working days (8 hours/day)
        time_entries = []
        for day in range(13):
            time_entries.append(
                EmployeeTimeEntry(
                    employee_id="EMP_NORMAL",
                    employee_name="Normal Earner",
                    project_name="Project B",
                    task_description="Development",
                    hours_spent=8.0 if day < 12 else 4.0,  # Last day only 4 hours to total 100
                    date=datetime(2024, 1, 1) + timedelta(days=day),
                    is_rd_classified=True
                )
            )
        
        # Create cost with hourly rate below wage cap
        # 100 hours * $80/hr = $8,000 (well below cap)
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=8000.0,
                project_name="Project B",
                employee_id="EMP_NORMAL",
                date=datetime(2024, 1, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 80.0}
            )
        ]
        
        # Correlate and apply wage caps
        correlated_df = correlate_costs(time_entries, costs, filter_rd_only=True)
        capped_df = apply_wage_caps(correlated_df, tax_year=2024)
        
        # Verify wage cap was NOT applied
        emp_row = capped_df[capped_df['employee_id'] == 'EMP_NORMAL'].iloc[0]
        assert emp_row['wage_cap_applied'] == False
        assert emp_row['qualified_wages'] == 8000.0
        assert emp_row['original_qualified_wages'] == 8000.0
        assert emp_row['capped_amount'] == 0.0
    
    def test_wage_cap_applied_per_employee_per_year(self):
        """Test that wage caps are applied per employee per year across multiple projects"""
        from utils.pandas_processor import correlate_costs, apply_wage_caps
        from utils.constants import IRSWageCap
        
        # Create time entries for one employee across multiple projects
        # Project A: 500 hours across ~63 days (8 hours/day)
        # Project B: 500 hours across ~63 days (8 hours/day)
        time_entries = []
        
        # Project A entries
        for day in range(63):
            time_entries.append(
                EmployeeTimeEntry(
                    employee_id="EMP001",
                    employee_name="Multi Project",
                    project_name="Project A",
                    task_description="Development",
                    hours_spent=8.0 if day < 62 else 4.0,  # Last day 4 hours to total 500
                    date=datetime(2024, 1, 1) + timedelta(days=day),
                    is_rd_classified=True
                )
            )
        
        # Project B entries
        for day in range(63):
            time_entries.append(
                EmployeeTimeEntry(
                    employee_id="EMP001",
                    employee_name="Multi Project",
                    project_name="Project B",
                    task_description="Development",
                    hours_spent=8.0 if day < 62 else 4.0,  # Last day 4 hours to total 500
                    date=datetime(2024, 3, 1) + timedelta(days=day),
                    is_rd_classified=True
                )
            )
        
        # Create costs that together exceed wage cap
        # Total: 1000 hours * $200/hr = $200,000 (exceeds cap)
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=100000.0,
                project_name="Project A",
                employee_id="EMP001",
                date=datetime(2024, 1, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 200.0}
            ),
            ProjectCost(
                cost_id="COST002",
                cost_type="Payroll",
                amount=100000.0,
                project_name="Project B",
                employee_id="EMP001",
                date=datetime(2024, 2, 28),
                is_rd_classified=True,
                metadata={"hourly_rate": 200.0}
            )
        ]
        
        # Correlate and apply wage caps
        correlated_df = correlate_costs(time_entries, costs, filter_rd_only=True)
        capped_df = apply_wage_caps(correlated_df, tax_year=2024)
        
        # Verify wage cap was applied to both projects proportionally
        total_qualified_wages = capped_df['qualified_wages'].sum()
        assert total_qualified_wages <= IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
        
        # Verify both projects had cap applied
        project_a_row = capped_df[capped_df['project_name'] == 'Project A'].iloc[0]
        project_b_row = capped_df[capped_df['project_name'] == 'Project B'].iloc[0]
        
        assert project_a_row['wage_cap_applied'] == True
        assert project_b_row['wage_cap_applied'] == True
        
        # Verify proportional reduction (both projects should be reduced equally)
        assert abs(project_a_row['qualified_wages'] - project_b_row['qualified_wages']) < 1.0
    
    def test_wage_cap_not_applied_to_non_payroll_costs(self):
        """Test that wage caps are not applied to non-payroll costs"""
        from utils.pandas_processor import correlate_costs, apply_wage_caps
        
        # Create time entries across multiple days
        # Total: 100 hours spread across ~13 working days (8 hours/day)
        time_entries = []
        for day in range(13):
            time_entries.append(
                EmployeeTimeEntry(
                    employee_id="EMP001",
                    employee_name="Developer",
                    project_name="Project C",
                    task_description="Development",
                    hours_spent=8.0 if day < 12 else 4.0,  # Last day only 4 hours to total 100
                    date=datetime(2024, 1, 1) + timedelta(days=day),
                    is_rd_classified=True
                )
            )
        
        # Create mix of payroll and non-payroll costs
        costs = [
            ProjectCost(
                cost_id="COST001",
                cost_type="Payroll",
                amount=20000.0,
                project_name="Project C",
                employee_id="EMP001",
                date=datetime(2024, 1, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 200.0}
            ),
            ProjectCost(
                cost_id="COST002",
                cost_type="Contractor",
                amount=500000.0,  # Very high contractor cost
                project_name="Project C",
                employee_id=None,
                date=datetime(2024, 1, 31),
                is_rd_classified=True
            )
        ]
        
        # Correlate and apply wage caps
        correlated_df = correlate_costs(time_entries, costs, filter_rd_only=True)
        capped_df = apply_wage_caps(correlated_df, tax_year=2024)
        
        # Verify contractor cost is not affected by wage cap
        contractor_row = capped_df[capped_df['cost_type'] == 'Contractor'].iloc[0]
        assert contractor_row['wage_cap_applied'] == False
        assert contractor_row['other_costs'] == 500000.0  # Unchanged
        assert contractor_row['capped_amount'] == 0.0


class TestQualificationAgentComplianceChecking:
    """Test compliance checking functionality in Qualification Agent"""
    
    def test_compliance_check_validates_required_documentation(self):
        """Test that compliance check validates required documentation elements"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create qualified projects with varying documentation completeness
        qualified_projects = [
            QualifiedProject(
                project_name="Well Documented",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="CFR Title 26 § 1.41-4(a)(1)",
                reasoning="Meets all four-part test criteria with clear technical uncertainty",
                irs_source="CFR Title 26",
                technical_details={
                    "technical_uncertainty": "Algorithm performance optimization",
                    "experimentation_process": "A/B testing with multiple approaches",
                    "business_component": "Core search engine"
                }
            ),
            QualifiedProject(
                project_name="Minimal Documentation",
                qualified_hours=50.0,
                qualified_cost=5000.0,
                confidence_score=0.65,
                qualification_percentage=60.0,
                supporting_citation="General IRS guidance",
                reasoning="Some R&D indicators present",
                irs_source="Form 6765"
                # Missing technical_details
            )
        ]
        
        # Call flagging method which includes compliance checks
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify that project with minimal documentation is flagged
        assert result['flagged_count'] >= 1
        flagged_names = [p['project_name'] for p in result['flagged_projects']]
        assert "Minimal Documentation" in flagged_names
    
    def test_compliance_check_with_recent_guidance(self):
        """Test compliance check integrates recent IRS guidance"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Search API to return recent guidance
        mock_search_results = [
            {
                'title': 'IRS Updates Software R&D Guidance 2024',
                'url': 'https://www.irs.gov/newsroom/software-rd-2024',
                'description': 'New guidance on software development qualified research',
                'snippets': ['software development', 'qualified research', 'experimentation'],
                'page_age': '2024-01-15'
            }
        ]
        youcom_client.search.return_value = mock_search_results
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        qualified_projects = [
            QualifiedProject(
                project_name="Software Project",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.80,
                qualification_percentage=75.0,
                supporting_citation="IRS guidance",
                reasoning="Software development R&D",
                irs_source="Form 6765"
            )
        ]
        
        # Check recent guidance
        guidance_result = agent._check_recent_guidance(
            tax_year=2024,
            qualified_projects=qualified_projects
        )
        
        # Verify guidance was found and project was flagged for review
        assert guidance_result['has_new_guidance'] == True
        assert len(guidance_result['search_results']) > 0
        assert 'Software Project' in guidance_result['affected_projects']
        assert len(guidance_result['recommendations']) > 0
        
        # Verify recommendations include reviewing against new guidance
        recommendations_text = ' '.join(guidance_result['recommendations'])
        assert 'review' in recommendations_text.lower()
        assert 'guidance' in recommendations_text.lower()
    
    def test_compliance_check_four_part_test_validation(self):
        """Test that compliance check validates four-part test criteria"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create projects with explicit four-part test results
        qualified_projects = [
            QualifiedProject(
                project_name="Passes Four-Part Test",
                qualified_hours=100.0,
                qualified_cost=10000.0,
                confidence_score=0.90,
                qualification_percentage=85.0,
                supporting_citation="CFR Title 26 § 1.41-4",
                reasoning="Meets all four-part test: technological in nature, elimination of uncertainty, process of experimentation, qualified purpose",
                irs_source="CFR Title 26",
                technical_details={
                    "four_part_test": {
                        "technological_in_nature": True,
                        "elimination_of_uncertainty": True,
                        "process_of_experimentation": True,
                        "qualified_purpose": True
                    }
                }
            ),
            QualifiedProject(
                project_name="Fails Four-Part Test",
                qualified_hours=50.0,
                qualified_cost=5000.0,
                confidence_score=0.55,
                qualification_percentage=50.0,
                supporting_citation="General guidance",
                reasoning="Uncertain qualification - may not meet all four-part test criteria",
                irs_source="Form 6765",
                technical_details={
                    "four_part_test": {
                        "technological_in_nature": True,
                        "elimination_of_uncertainty": False,  # Fails this criterion
                        "process_of_experimentation": True,
                        "qualified_purpose": True
                    }
                }
            )
        ]
        
        # Flag low confidence projects
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify project that fails four-part test is flagged
        assert result['flagged_count'] >= 1
        flagged_names = [p['project_name'] for p in result['flagged_projects']]
        assert "Fails Four-Part Test" in flagged_names
        
        # Verify high-confidence project is not flagged
        assert "Passes Four-Part Test" not in flagged_names
    
    def test_compliance_check_generates_audit_recommendations(self):
        """Test that compliance check generates actionable audit recommendations"""
        rag_tool = Mock(spec=RD_Knowledge_Tool)
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = QualificationAgent(
            rag_tool=rag_tool,
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create mix of projects with different confidence levels
        qualified_projects = [
            QualifiedProject(
                project_name="Critical Risk",
                qualified_hours=100.0,
                qualified_cost=50000.0,  # High cost
                confidence_score=0.45,  # Critical confidence
                qualification_percentage=40.0,
                supporting_citation="Weak citation",
                reasoning="Limited evidence",
                irs_source="General"
            ),
            QualifiedProject(
                project_name="High Risk",
                qualified_hours=75.0,
                qualified_cost=30000.0,
                confidence_score=0.55,  # High warning
                qualification_percentage=50.0,
                supporting_citation="Some citation",
                reasoning="Some evidence",
                irs_source="Form 6765"
            ),
            QualifiedProject(
                project_name="Moderate Risk",
                qualified_hours=50.0,
                qualified_cost=20000.0,
                confidence_score=0.65,  # Moderate warning
                qualification_percentage=60.0,
                supporting_citation="Decent citation",
                reasoning="Decent evidence",
                irs_source="CFR Title 26"
            )
        ]
        
        # Flag low confidence projects
        result = agent._flag_low_confidence(qualified_projects)
        
        # Verify all three projects are flagged
        assert result['flagged_count'] == 3
        
        # Verify recommendations are generated
        assert len(result['recommendations']) > 0
        
        # Verify recommendations include different severity levels
        recommendations_text = ' '.join(result['recommendations'])
        assert 'URGENT' in recommendations_text or 'critical' in recommendations_text.lower()
        assert 'documentation' in recommendations_text.lower()
        assert 'four-part test' in recommendations_text.lower()
        
        # Verify high cost percentage warning
        # Total flagged cost: $100,000 out of $100,000 = 100%
        assert any('audit risk' in rec.lower() for rec in result['recommendations'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
