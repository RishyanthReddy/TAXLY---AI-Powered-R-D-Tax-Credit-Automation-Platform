"""
Integration tests for Qualification Agent.

Tests the full qualification workflow with real data, concurrent processing,
error recovery, and end-to-end qualification scenarios.

Requirements: Testing
"""

import pytest
import json
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from agents.qualification_agent import (
    QualificationAgent,
    QualificationState,
    QualificationResult
)
from models.financial_models import EmployeeTimeEntry, ProjectCost
from models.tax_models import QualifiedProject, RAGContext
from models.websocket_models import AgentStatus
from tools.rd_knowledge_tool import RD_Knowledge_Tool
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.exceptions import RAGRetrievalError, APIConnectionError


# Fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_time_entries():
    """Load sample time entries from fixtures"""
    with open(FIXTURES_DIR / "sample_time_entries.json", "r") as f:
        data = json.load(f)
    
    return [
        EmployeeTimeEntry(
            employee_id=entry["employee_id"],
            employee_name=entry["employee_name"],
            project_name=entry["project_name"],
            task_description=entry.get("task_description"),
            hours_spent=entry["hours_spent"],
            date=datetime.fromisoformat(entry["date"]),
            is_rd_classified=entry["is_rd_classified"]
        )
        for entry in data
    ]


@pytest.fixture
def sample_costs():
    """Load sample costs from fixtures"""
    with open(FIXTURES_DIR / "sample_payroll_data.json", "r") as f:
        data = json.load(f)
    
    return [
        ProjectCost(
            cost_id=cost["cost_id"],
            cost_type=cost["cost_type"],
            amount=cost["amount"],
            project_name=cost["project_name"],
            employee_id=cost.get("employee_id"),
            date=datetime.fromisoformat(cost["date"]),
            is_rd_classified=cost["is_rd_classified"]
        )
        for cost in data
    ]


@pytest.fixture
def mock_rag_tool():
    """Create mock RAG tool with realistic responses"""
    rag_tool = Mock(spec=RD_Knowledge_Tool)
    
    # Create realistic RAG context
    def mock_query(question, top_k=3, **kwargs):
        chunks = [
            {
                "text": "Qualified research must meet the four-part test: (1) technological in nature, (2) qualified purpose, (3) technological uncertainty, (4) process of experimentation.",
                "source": "CFR Title 26 § 1.41-4",
                "page": 1,
                "relevance_score": 0.92
            },
            {
                "text": "Software development activities can qualify if they involve eliminating technical uncertainty through systematic experimentation.",
                "source": "Form 6765 Instructions",
                "page": 3,
                "relevance_score": 0.88
            },
            {
                "text": "The substantially all requirement means that 80% or more of the research activities must constitute elements of a process of experimentation.",
                "source": "CFR Title 26 § 1.41-4(a)(5)",
                "page": 2,
                "relevance_score": 0.85
            }
        ]
        
        rag_context = RAGContext(
            query=question,
            chunks=chunks,
            retrieval_timestamp=datetime.now(),
            total_chunks_available=150,
            retrieval_method="semantic_search"
        )
        return rag_context
    
    rag_tool.query.side_effect = mock_query
    
    return rag_tool


@pytest.fixture
def mock_youcom_client():
    """Create mock You.com client with realistic responses"""
    youcom_client = Mock(spec=YouComClient)
    
    # Mock agent_run responses
    def mock_agent_run(prompt, agent_mode="express", stream=False):
        # Extract project name from prompt
        project_name = "Unknown Project"
        if "Alpha Development" in prompt:
            project_name = "Alpha Development"
            qual_pct = 95.0
            confidence = 0.92
        elif "Beta Infrastructure" in prompt:
            project_name = "Beta Infrastructure"
            qual_pct = 90.0
            confidence = 0.88
        elif "Gamma Analytics" in prompt:
            project_name = "Gamma Analytics"
            qual_pct = 85.0
            confidence = 0.85
        elif "Delta Security" in prompt:
            project_name = "Delta Security"
            qual_pct = 98.0
            confidence = 0.94
        elif "Epsilon AI" in prompt:
            project_name = "Epsilon AI"
            qual_pct = 93.0
            confidence = 0.91
        elif "Zeta Optimization" in prompt:
            project_name = "Zeta Optimization"
            qual_pct = 80.0
            confidence = 0.78
        else:
            qual_pct = 75.0
            confidence = 0.70
        
        response = {
            'output': [{
                'text': f'''```json
{{
  "qualification_percentage": {qual_pct},
  "confidence_score": {confidence},
  "reasoning": "This project meets the four-part test for qualified research.",
  "citations": ["CFR Title 26 § 1.41-4(a)(1)", "Form 6765 Instructions"],
  "technical_details": "Technical uncertainty existed regarding optimal implementation."
}}
```''',
                'type': 'chat_node.answer'
            }]
        }
        
        return response
    
    youcom_client.agent_run.side_effect = mock_agent_run
    
    # Mock parse response
    def mock_parse_response(response_text):
        # Extract JSON from response
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group(1))
        return {
            'qualification_percentage': 75.0,
            'confidence_score': 0.70,
            'reasoning': 'Default reasoning',
            'citations': [],
            'technical_details': 'Default details'
        }
    
    youcom_client._parse_agent_response.side_effect = mock_parse_response
    
    # Mock search (for recent guidance check)
    youcom_client.search.return_value = []
    
    return youcom_client


@pytest.fixture
def mock_glm_reasoner():
    """Create mock GLM reasoner"""
    return Mock(spec=GLMReasoner)


@pytest.fixture
def qualification_agent(mock_rag_tool, mock_youcom_client, mock_glm_reasoner):
    """Create qualification agent with mocked dependencies"""
    return QualificationAgent(
        rag_tool=mock_rag_tool,
        youcom_client=mock_youcom_client,
        glm_reasoner=mock_glm_reasoner
    )


class TestQualificationIntegrationFullWorkflow:
    """Test full qualification workflow with sample data"""
    
    def test_full_workflow_with_sample_data(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test complete qualification workflow with fixture data"""
        # Run qualification
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs,
            tax_year=2024
        )
        
        # Verify result structure
        assert isinstance(result, QualificationResult)
        assert len(result.qualified_projects) > 0
        assert result.total_qualified_hours > 0
        assert result.total_qualified_cost > 0
        assert result.estimated_credit > 0
        assert result.execution_time_seconds > 0
        
        # Verify agent state
        assert qualification_agent.state.status == AgentStatus.COMPLETED
        assert qualification_agent.state.projects_qualified == len(result.qualified_projects)
        
        # Verify qualified projects
        for project in result.qualified_projects:
            assert isinstance(project, QualifiedProject)
            assert project.project_name is not None
            assert project.qualified_hours >= 0
            assert project.qualified_cost >= 0
            assert 0 <= project.confidence_score <= 1
            assert 0 <= project.qualification_percentage <= 100
            assert project.reasoning is not None
            assert project.irs_source is not None
    
    def test_workflow_with_rd_projects_only(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test workflow filters R&D projects correctly"""
        # Count R&D projects in sample data
        rd_projects = set(
            entry.project_name for entry in sample_time_entries
            if entry.is_rd_classified
        )
        
        # Run qualification
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Verify only R&D projects were qualified
        qualified_project_names = {p.project_name for p in result.qualified_projects}
        assert qualified_project_names.issubset(rd_projects)
        
        # Verify non-R&D projects were excluded
        non_rd_projects = set(
            entry.project_name for entry in sample_time_entries
            if not entry.is_rd_classified
        )
        assert not qualified_project_names.intersection(non_rd_projects)
    
    def test_workflow_calculates_correct_totals(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test workflow calculates totals correctly"""
        # Run qualification
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Verify totals match sum of individual projects
        calculated_hours = sum(p.qualified_hours for p in result.qualified_projects)
        calculated_cost = sum(p.qualified_cost for p in result.qualified_projects)
        
        assert abs(result.total_qualified_hours - calculated_hours) < 0.01
        assert abs(result.total_qualified_cost - calculated_cost) < 0.01
        
        # Verify credit calculation (20% of qualified costs)
        expected_credit = result.total_qualified_cost * 0.20
        assert abs(result.estimated_credit - expected_credit) < 0.01
    
    def test_workflow_with_status_callback(
        self,
        mock_rag_tool,
        mock_youcom_client,
        mock_glm_reasoner,
        sample_time_entries,
        sample_costs
    ):
        """Test workflow sends status updates via callback"""
        callback = Mock()
        
        agent = QualificationAgent(
            rag_tool=mock_rag_tool,
            youcom_client=mock_youcom_client,
            glm_reasoner=mock_glm_reasoner,
            status_callback=callback
        )
        
        # Run qualification
        result = agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Verify callback was called multiple times
        assert callback.call_count >= 3
        
        # Verify status progression
        statuses = [call[0][0].status for call in callback.call_args_list]
        assert AgentStatus.IN_PROGRESS in statuses
        assert AgentStatus.COMPLETED in statuses


class TestQualificationIntegrationQualifiedProjects:
    """Test QualifiedProject outputs are correct"""
    
    def test_qualified_project_structure(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test each qualified project has correct structure"""
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        for project in result.qualified_projects:
            # Verify required fields
            assert project.project_name is not None
            assert isinstance(project.qualified_hours, float)
            assert isinstance(project.qualified_cost, float)
            assert isinstance(project.confidence_score, float)
            assert isinstance(project.qualification_percentage, float)
            assert isinstance(project.supporting_citation, str)
            assert isinstance(project.reasoning, str)
            assert isinstance(project.irs_source, str)
            
            # Verify value ranges
            assert project.qualified_hours >= 0
            assert project.qualified_cost >= 0
            assert 0 <= project.confidence_score <= 1
            assert 0 <= project.qualification_percentage <= 100
            
            # Verify non-empty strings
            assert len(project.supporting_citation) > 0
            assert len(project.reasoning) > 0
            assert len(project.irs_source) > 0
    
    def test_qualified_project_flagging(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test low-confidence projects are flagged correctly"""
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Check flagging logic
        for project in result.qualified_projects:
            if project.confidence_score < 0.7:
                assert project.flagged_for_review is True
            else:
                assert project.flagged_for_review is False
        
        # Verify flagged projects list matches
        flagged_count = sum(1 for p in result.qualified_projects if p.flagged_for_review)
        assert len(result.flagged_projects) == flagged_count
    
    def test_qualified_project_calculations(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test qualified hours and costs are calculated correctly"""
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Get original project data
        rd_projects = {}
        for entry in sample_time_entries:
            if entry.is_rd_classified:
                if entry.project_name not in rd_projects:
                    rd_projects[entry.project_name] = {'hours': 0, 'cost': 0}
                rd_projects[entry.project_name]['hours'] += entry.hours_spent
        
        for cost in sample_costs:
            if cost.is_rd_classified:
                if cost.project_name not in rd_projects:
                    rd_projects[cost.project_name] = {'hours': 0, 'cost': 0}
                rd_projects[cost.project_name]['cost'] += cost.amount
        
        # Verify calculations for each project
        for project in result.qualified_projects:
            if project.project_name in rd_projects:
                original_hours = rd_projects[project.project_name]['hours']
                original_cost = rd_projects[project.project_name]['cost']
                
                qual_pct = project.qualification_percentage / 100.0
                expected_hours = original_hours * qual_pct
                expected_cost = original_cost * qual_pct
                
                # Allow small floating point differences
                assert abs(project.qualified_hours - expected_hours) < 0.1
                assert abs(project.qualified_cost - expected_cost) < 1.0


class TestQualificationIntegrationConcurrentProcessing:
    """Test concurrent processing of multiple projects"""
    
    def test_concurrent_processing_completes(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test concurrent processing completes successfully"""
        # Run qualification (uses concurrent processing internally)
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Verify all R&D projects were processed
        rd_project_count = len(set(
            entry.project_name for entry in sample_time_entries
            if entry.is_rd_classified
        ))
        
        assert len(result.qualified_projects) == rd_project_count
        assert qualification_agent.state.projects_qualified == rd_project_count
    
    def test_concurrent_processing_maintains_order(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test concurrent processing doesn't corrupt data"""
        # Run qualification multiple times
        result1 = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        qualification_agent.reset_state()
        
        result2 = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Verify results are consistent
        assert len(result1.qualified_projects) == len(result2.qualified_projects)
        
        # Sort by project name for comparison
        projects1 = sorted(result1.qualified_projects, key=lambda p: p.project_name)
        projects2 = sorted(result2.qualified_projects, key=lambda p: p.project_name)
        
        for p1, p2 in zip(projects1, projects2):
            assert p1.project_name == p2.project_name
            assert abs(p1.qualified_hours - p2.qualified_hours) < 0.1
            assert abs(p1.qualified_cost - p2.qualified_cost) < 1.0
    
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(
        self,
        mock_rag_tool,
        mock_youcom_client,
        mock_glm_reasoner,
        sample_time_entries,
        sample_costs
    ):
        """Test semaphore limits concurrent operations"""
        # Track concurrent calls
        concurrent_calls = []
        max_concurrent = 0
        
        original_agent_run = mock_youcom_client.agent_run.side_effect
        
        def tracked_agent_run(*args, **kwargs):
            concurrent_calls.append(1)
            nonlocal max_concurrent
            max_concurrent = max(max_concurrent, len(concurrent_calls))
            
            result = original_agent_run(*args, **kwargs)
            
            concurrent_calls.pop()
            return result
        
        mock_youcom_client.agent_run.side_effect = tracked_agent_run
        
        agent = QualificationAgent(
            rag_tool=mock_rag_tool,
            youcom_client=mock_youcom_client,
            glm_reasoner=mock_glm_reasoner
        )
        
        # Run qualification
        result = agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Verify concurrency was limited (max 5 concurrent)
        assert max_concurrent <= 5


class TestQualificationIntegrationErrorRecovery:
    """Test error recovery and handling"""
    
    def test_rag_failure_recovery(
        self,
        mock_rag_tool,
        mock_youcom_client,
        mock_glm_reasoner,
        sample_time_entries,
        sample_costs
    ):
        """Test agent handles RAG failures gracefully"""
        # Make RAG tool fail
        mock_rag_tool.query.side_effect = RAGRetrievalError(
            message="Vector database unavailable",
            query="test query",
            knowledge_base_path="/path/to/kb"
        )
        
        agent = QualificationAgent(
            rag_tool=mock_rag_tool,
            youcom_client=mock_youcom_client,
            glm_reasoner=mock_glm_reasoner
        )
        
        # Run qualification - should raise error
        with pytest.raises(RAGRetrievalError):
            agent.run(
                time_entries=sample_time_entries,
                costs=sample_costs
            )
        
        # Verify agent state shows error
        assert agent.state.status == AgentStatus.ERROR
        assert agent.state.error_message is not None
    
    def test_youcom_api_failure_recovery(
        self,
        mock_rag_tool,
        mock_youcom_client,
        mock_glm_reasoner,
        sample_time_entries,
        sample_costs
    ):
        """Test agent handles You.com API failures gracefully"""
        # Make You.com API fail
        mock_youcom_client.agent_run.side_effect = APIConnectionError(
            message="API rate limit exceeded",
            endpoint="/v1/agents/runs",
            status_code=429
        )
        
        agent = QualificationAgent(
            rag_tool=mock_rag_tool,
            youcom_client=mock_youcom_client,
            glm_reasoner=mock_glm_reasoner
        )
        
        # Run qualification - should raise error
        with pytest.raises(APIConnectionError):
            agent.run(
                time_entries=sample_time_entries,
                costs=sample_costs
            )
        
        # Verify agent state shows error
        assert agent.state.status == AgentStatus.ERROR
        assert "API connection failed" in agent.state.error_message
    
    def test_partial_failure_continues_processing(
        self,
        mock_rag_tool,
        mock_youcom_client,
        mock_glm_reasoner,
        sample_time_entries,
        sample_costs
    ):
        """Test agent continues processing when individual projects fail"""
        # Make You.com API fail for specific project
        call_count = [0]
        original_agent_run = mock_youcom_client.agent_run.side_effect
        
        def selective_failure(*args, **kwargs):
            call_count[0] += 1
            # Fail on second call
            if call_count[0] == 2:
                raise APIConnectionError(
                    message="Temporary failure",
                    endpoint="/v1/agents/runs",
                    status_code=500
                )
            return original_agent_run(*args, **kwargs)
        
        mock_youcom_client.agent_run.side_effect = selective_failure
        
        agent = QualificationAgent(
            rag_tool=mock_rag_tool,
            youcom_client=mock_youcom_client,
            glm_reasoner=mock_glm_reasoner
        )
        
        # Run qualification
        result = agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Verify some projects were qualified despite failure
        assert len(result.qualified_projects) > 0
        
        # Verify not all projects were qualified (one failed)
        rd_project_count = len(set(
            entry.project_name for entry in sample_time_entries
            if entry.is_rd_classified
        ))
        assert len(result.qualified_projects) < rd_project_count
    
    def test_empty_time_entries_error(
        self,
        qualification_agent,
        sample_costs
    ):
        """Test agent handles empty time entries"""
        with pytest.raises(ValueError, match="time_entries cannot be empty"):
            qualification_agent.run(
                time_entries=[],
                costs=sample_costs
            )
    
    def test_no_rd_projects_returns_empty_result(
        self,
        qualification_agent
    ):
        """Test agent handles case with no R&D projects"""
        # Create non-R&D entries
        non_rd_entries = [
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
        
        result = qualification_agent.run(
            time_entries=non_rd_entries,
            costs=[]
        )
        
        # Verify empty result
        assert len(result.qualified_projects) == 0
        assert result.total_qualified_hours == 0.0
        assert result.total_qualified_cost == 0.0
        assert result.estimated_credit == 0.0
        assert "No projects marked as R&D" in result.summary
        assert qualification_agent.state.status == AgentStatus.COMPLETED


class TestQualificationIntegrationRecentGuidance:
    """Test recent IRS guidance checking"""
    
    def test_recent_guidance_check_with_results(
        self,
        mock_rag_tool,
        mock_youcom_client,
        mock_glm_reasoner,
        sample_time_entries,
        sample_costs
    ):
        """Test recent guidance check when new guidance is found"""
        # Mock search results with IRS guidance
        mock_youcom_client.search.return_value = [
            {
                'url': 'https://www.irs.gov/pub/irs-drop/rr-24-01.pdf',
                'title': 'Revenue Ruling 2024-01: Software Development R&D Credits',
                'description': 'New guidance on qualified research for software development',
                'snippets': ['software development', 'qualified research', 'experimentation']
            }
        ]
        
        agent = QualificationAgent(
            rag_tool=mock_rag_tool,
            youcom_client=mock_youcom_client,
            glm_reasoner=mock_glm_reasoner
        )
        
        # Run qualification with tax year
        result = agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs,
            tax_year=2024
        )
        
        # Verify search was called
        mock_youcom_client.search.assert_called_once()
        
        # Verify result includes guidance info
        assert "guidance" in result.summary.lower() or "2024" in result.summary
    
    def test_recent_guidance_check_no_results(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test recent guidance check when no new guidance is found"""
        # Run qualification with tax year (mock returns empty results)
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs,
            tax_year=2024
        )
        
        # Verify qualification completed successfully
        assert len(result.qualified_projects) > 0
        assert result.execution_time_seconds > 0


class TestQualificationIntegrationStateManagement:
    """Test agent state management during workflow"""
    
    def test_state_progression(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test agent state progresses correctly through workflow"""
        # Initial state
        assert qualification_agent.state.status == AgentStatus.PENDING
        assert qualification_agent.state.projects_qualified == 0
        
        # Run qualification
        result = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        # Final state
        assert qualification_agent.state.status == AgentStatus.COMPLETED
        assert qualification_agent.state.projects_qualified > 0
        assert qualification_agent.state.start_time is not None
        assert qualification_agent.state.end_time is not None
        assert qualification_agent.state.end_time > qualification_agent.state.start_time
    
    def test_state_reset(
        self,
        qualification_agent,
        sample_time_entries,
        sample_costs
    ):
        """Test agent state can be reset between runs"""
        # First run
        result1 = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        assert qualification_agent.state.status == AgentStatus.COMPLETED
        assert qualification_agent.state.projects_qualified > 0
        
        # Reset state
        qualification_agent.reset_state()
        
        assert qualification_agent.state.status == AgentStatus.PENDING
        assert qualification_agent.state.projects_qualified == 0
        assert qualification_agent.state.start_time is None
        
        # Second run
        result2 = qualification_agent.run(
            time_entries=sample_time_entries,
            costs=sample_costs
        )
        
        assert qualification_agent.state.status == AgentStatus.COMPLETED
        assert qualification_agent.state.projects_qualified > 0
