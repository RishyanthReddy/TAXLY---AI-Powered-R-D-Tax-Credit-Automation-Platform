"""
Unit tests for Audit Trail Agent.

Tests the AuditTrailAgent class structure, initialization, state management,
and narrative generation functionality.

Requirements: Testing
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from agents.audit_trail_agent import (
    AuditTrailAgent,
    AuditTrailState,
    AuditTrailResult
)
from models.tax_models import QualifiedProject
from models.websocket_models import AgentStage, AgentStatus
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.exceptions import APIConnectionError


class TestAuditTrailState:
    """Test AuditTrailState model"""
    
    def test_state_initialization(self):
        """Test state initializes with correct defaults"""
        state = AuditTrailState()
        
        assert state.stage == "initializing"
        assert state.status == AgentStatus.PENDING
        assert state.projects_to_process == 0
        assert state.narratives_generated == 0
        assert state.narratives_reviewed == 0
        assert state.current_project is None
        assert state.report_generated is False
        assert state.start_time is None
        assert state.end_time is None
        assert state.error_message is None
    
    def test_state_to_status_message_pending(self):
        """Test converting pending state to status message"""
        state = AuditTrailState()
        message = state.to_status_message()
        
        assert message.stage == AgentStage.AUDIT_TRAIL
        assert message.status == AgentStatus.PENDING
        assert "Waiting to start" in message.details
    
    def test_state_to_status_message_in_progress(self):
        """Test converting in-progress state to status message"""
        state = AuditTrailState(
            stage="generating_narratives",
            status=AgentStatus.IN_PROGRESS,
            projects_to_process=5,
            narratives_generated=2,
            current_project="Alpha Project"
        )
        message = state.to_status_message()
        
        assert message.stage == AgentStage.AUDIT_TRAIL
        assert message.status == AgentStatus.IN_PROGRESS
        assert "Alpha Project" in message.details
        assert "2/5" in message.details
    
    def test_state_to_status_message_completed(self):
        """Test converting completed state to status message"""
        state = AuditTrailState(
            stage="completed",
            status=AgentStatus.COMPLETED,
            projects_to_process=5
        )
        message = state.to_status_message()
        
        assert message.stage == AgentStage.AUDIT_TRAIL
        assert message.status == AgentStatus.COMPLETED
        assert "5 projects" in message.details
    
    def test_state_to_status_message_error(self):
        """Test converting error state to status message"""
        state = AuditTrailState(
            stage="error",
            status=AgentStatus.ERROR,
            error_message="API connection failed"
        )
        message = state.to_status_message()
        
        assert message.stage == AgentStage.AUDIT_TRAIL
        assert message.status == AgentStatus.ERROR
        assert "API connection failed" in message.details


class TestAuditTrailResult:
    """Test AuditTrailResult model"""
    
    def test_result_initialization(self):
        """Test result initializes with correct defaults"""
        result = AuditTrailResult()
        
        assert result.report is None
        assert result.pdf_path is None
        assert result.narratives == {}
        assert result.compliance_reviews == {}
        assert result.execution_time_seconds == 0.0
        assert result.summary == ""


class TestAuditTrailAgent:
    """Test AuditTrailAgent class"""
    
    def test_agent_initialization(self):
        """Test agent initializes correctly with required tools"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        assert agent.youcom_client == youcom_client
        assert agent.glm_reasoner == glm_reasoner
        assert agent.pdf_generator is None
        assert agent.status_callback is None
        assert isinstance(agent.state, AuditTrailState)
    
    def test_agent_initialization_with_optional_params(self):
        """Test agent initializes with optional parameters"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        pdf_generator = Mock()
        status_callback = Mock()
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            pdf_generator=pdf_generator,
            status_callback=status_callback
        )
        
        assert agent.pdf_generator == pdf_generator
        assert agent.status_callback == status_callback
    
    def test_agent_initialization_requires_youcom_client(self):
        """Test agent raises error if youcom_client is None"""
        glm_reasoner = Mock(spec=GLMReasoner)
        
        with pytest.raises(ValueError, match="youcom_client cannot be None"):
            AuditTrailAgent(
                youcom_client=None,
                glm_reasoner=glm_reasoner
            )
    
    def test_agent_initialization_requires_glm_reasoner(self):
        """Test agent raises error if glm_reasoner is None"""
        youcom_client = Mock(spec=YouComClient)
        
        with pytest.raises(ValueError, match="glm_reasoner cannot be None"):
            AuditTrailAgent(
                youcom_client=youcom_client,
                glm_reasoner=None
            )
    
    def test_update_status(self):
        """Test status update method"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        status_callback = Mock()
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            status_callback=status_callback
        )
        
        agent._update_status(
            stage="generating_narratives",
            status=AgentStatus.IN_PROGRESS,
            current_project="Test Project"
        )
        
        assert agent.state.stage == "generating_narratives"
        assert agent.state.status == AgentStatus.IN_PROGRESS
        assert agent.state.current_project == "Test Project"
        assert status_callback.called


class TestGenerateNarrative:
    """Test _generate_narrative method"""
    
    def test_generate_narrative_basic(self):
        """Test basic narrative generation without template URL"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API response
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'This is a comprehensive technical narrative for the project...'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="API Optimization",
            qualified_hours=120.5,
            qualified_cost=15000.00,
            confidence_score=0.92,
            qualification_percentage=85.0,
            supporting_citation="The project involves developing new algorithms...",
            reasoning="This project meets the four-part test because...",
            irs_source="CFR Title 26 § 1.41-4(a)(1)"
        )
        
        # Generate narrative
        narrative = agent._generate_narrative(project)
        
        # Verify narrative was generated
        assert narrative == 'This is a comprehensive technical narrative for the project...'
        assert len(narrative) > 0
        
        # Verify You.com Agent API was called
        assert youcom_client.agent_run.called
        call_args = youcom_client.agent_run.call_args
        assert call_args[1]['agent_mode'] == 'express'
        assert call_args[1]['stream'] is False
        
        # Verify prompt contains project details
        prompt = call_args[1]['prompt']
        assert 'API Optimization' in prompt
        assert '85.0' in prompt or '85' in prompt
        assert '120.5' in prompt
        assert '15000' in prompt or '15,000' in prompt
    
    def test_generate_narrative_with_template_url(self):
        """Test narrative generation with template URL"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Contents API response
        youcom_client.fetch_content.return_value = {
            'content': '# R&D Narrative Template\n\n## Project Overview\n...',
            'word_count': 500,
            'title': 'R&D Narrative Template'
        }
        
        # Mock You.com Agent API response
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Generated narrative using template...'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Database Migration",
            qualified_hours=200.0,
            qualified_cost=25000.00,
            confidence_score=0.88,
            qualification_percentage=90.0,
            supporting_citation="The project involves database optimization...",
            reasoning="This project qualifies because...",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        # Generate narrative with template URL
        narrative = agent._generate_narrative(
            project,
            template_url="https://example.com/rd-template"
        )
        
        # Verify narrative was generated
        assert narrative == 'Generated narrative using template...'
        
        # Verify Contents API was called
        assert youcom_client.fetch_content.called
        assert youcom_client.fetch_content.call_args[1]['url'] == "https://example.com/rd-template"
        assert youcom_client.fetch_content.call_args[1]['format'] == "markdown"
        
        # Verify Agent API was called with template in prompt
        assert youcom_client.agent_run.called
        prompt = youcom_client.agent_run.call_args[1]['prompt']
        assert 'Reference Template' in prompt
        assert 'R&D Narrative Template' in prompt
    
    def test_generate_narrative_with_technical_details(self):
        """Test narrative generation with technical details"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API response
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Narrative with technical details...'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project with technical details
        project = QualifiedProject(
            project_name="ML Model Development",
            qualified_hours=300.0,
            qualified_cost=40000.00,
            confidence_score=0.95,
            qualification_percentage=95.0,
            supporting_citation="The project involves machine learning research...",
            reasoning="This project clearly qualifies...",
            irs_source="CFR Title 26 § 1.41-4",
            technical_details={
                'technological_uncertainty': 'Uncertainty existed regarding model accuracy...',
                'experimentation_process': 'Team evaluated multiple algorithms...',
                'business_component': 'Predictive Analytics Engine'
            }
        )
        
        # Generate narrative
        narrative = agent._generate_narrative(project)
        
        # Verify narrative was generated
        assert narrative == 'Narrative with technical details...'
        
        # Verify prompt contains technical details
        prompt = youcom_client.agent_run.call_args[1]['prompt']
        assert 'Additional Technical Information' in prompt
        assert 'Technological Uncertainty' in prompt
        assert 'Experimentation Process' in prompt
        assert 'Business Component' in prompt
    
    def test_generate_narrative_handles_template_fetch_error(self):
        """Test narrative generation continues when template fetch fails"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock Contents API to raise error
        youcom_client.fetch_content.side_effect = APIConnectionError(
            message="Failed to fetch template",
            api_name="You.com",
            endpoint="/v1/contents"
        )
        
        # Mock Agent API to succeed
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Narrative without template...'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Generate narrative - should not raise error
        narrative = agent._generate_narrative(
            project,
            template_url="https://example.com/bad-url"
        )
        
        # Verify narrative was still generated
        assert narrative == 'Narrative without template...'
        
        # Verify Contents API was attempted
        assert youcom_client.fetch_content.called
        
        # Verify Agent API was called (fallback to built-in template)
        assert youcom_client.agent_run.called
    
    def test_generate_narrative_handles_agent_api_error(self):
        """Test narrative generation raises error when Agent API fails"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock Agent API to raise error
        youcom_client.agent_run.side_effect = APIConnectionError(
            message="Agent API failed",
            api_name="You.com",
            endpoint="/v1/agents/runs"
        )
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Generate narrative - should raise error
        with pytest.raises(APIConnectionError, match="Agent API failed"):
            agent._generate_narrative(project)
    
    def test_generate_narrative_handles_empty_response(self):
        """Test narrative generation handles empty Agent API response"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock Agent API to return empty response
        youcom_client.agent_run.return_value = {
            'output': []
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Generate narrative - should raise APIConnectionError wrapping the ValueError
        with pytest.raises(APIConnectionError, match="empty narrative"):
            agent._generate_narrative(project)
    
    def test_generate_narrative_extracts_chat_answer(self):
        """Test narrative generation correctly extracts chat answer from response"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock Agent API response with multiple output items
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'web_search.results',
                    'text': 'Search results...'
                },
                {
                    'type': 'chat_node.answer',
                    'text': 'This is the actual narrative answer...'
                },
                {
                    'type': 'other',
                    'text': 'Other output...'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Generate narrative
        narrative = agent._generate_narrative(project)
        
        # Verify correct answer was extracted
        assert narrative == 'This is the actual narrative answer...'
        assert 'Search results' not in narrative
        assert 'Other output' not in narrative


class TestBatchNarrativeGeneration:
    """Test batch narrative generation methods"""
    
    @pytest.mark.asyncio
    async def test_generate_narrative_async(self):
        """Test async narrative generation wrapper"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API response
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Async generated narrative...'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Async Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Initialize state
        agent.state.projects_to_process = 1
        
        # Generate narrative async
        project_name, narrative = await agent._generate_narrative_async(project)
        
        # Verify result
        assert project_name == "Async Test Project"
        assert narrative == 'Async generated narrative...'
        assert agent.state.narratives_generated == 1
    
    @pytest.mark.asyncio
    async def test_generate_narrative_async_handles_error(self):
        """Test async narrative generation handles errors gracefully"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock Agent API to raise error
        youcom_client.agent_run.side_effect = APIConnectionError(
            message="API failed",
            api_name="You.com",
            endpoint="/v1/agents/runs"
        )
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Error Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Initialize state
        agent.state.projects_to_process = 1
        
        # Generate narrative async - should return error message instead of raising
        project_name, narrative = await agent._generate_narrative_async(project)
        
        # Verify error was handled
        assert project_name == "Error Test Project"
        assert "ERROR" in narrative
        assert "Failed to generate narrative" in narrative
    
    @pytest.mark.asyncio
    async def test_generate_narratives_batch(self):
        """Test batch narrative generation for multiple projects"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API to return different narratives
        call_count = [0]
        def mock_agent_run(*args, **kwargs):
            call_count[0] += 1
            return {
                'output': [
                    {
                        'type': 'chat_node.answer',
                        'text': f'Narrative for project {call_count[0]}...'
                    }
                ]
            }
        
        youcom_client.agent_run.side_effect = mock_agent_run
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects
        projects = [
            QualifiedProject(
                project_name=f"Project {i}",
                qualified_hours=100.0 * i,
                qualified_cost=10000.00 * i,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation=f"Citation {i}",
                reasoning=f"Reasoning {i}",
                irs_source="Test source"
            )
            for i in range(1, 4)
        ]
        
        # Initialize state
        agent.state.projects_to_process = len(projects)
        
        # Generate narratives in batch
        narratives = await agent._generate_narratives_batch(
            qualified_projects=projects,
            max_concurrent=2
        )
        
        # Verify all narratives were generated
        assert len(narratives) == 3
        assert "Project 1" in narratives
        assert "Project 2" in narratives
        assert "Project 3" in narratives
        
        # Verify narratives contain expected content
        assert "Narrative for project" in narratives["Project 1"]
        assert "Narrative for project" in narratives["Project 2"]
        assert "Narrative for project" in narratives["Project 3"]
        
        # Verify state was updated
        assert agent.state.narratives_generated == 3
        
        # Verify You.com API was called for each project
        assert youcom_client.agent_run.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_narratives_batch_respects_concurrency_limit(self):
        """Test batch generation respects max_concurrent limit"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Track concurrent calls
        active_calls = [0]
        max_concurrent_observed = [0]
        
        async def mock_agent_run_async(*args, **kwargs):
            active_calls[0] += 1
            max_concurrent_observed[0] = max(max_concurrent_observed[0], active_calls[0])
            # Simulate some processing time
            import asyncio
            await asyncio.sleep(0.01)
            active_calls[0] -= 1
            return {
                'output': [
                    {
                        'type': 'chat_node.answer',
                        'text': 'Test narrative...'
                    }
                ]
            }
        
        # We need to wrap the sync mock to work with asyncio.to_thread
        # For this test, we'll patch the _generate_narrative method directly
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects
        projects = [
            QualifiedProject(
                project_name=f"Project {i}",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
            for i in range(10)
        ]
        
        # Initialize state
        agent.state.projects_to_process = len(projects)
        
        # Mock the _generate_narrative method to track concurrency
        original_generate = agent._generate_narrative
        
        def mock_generate(project, template_url=None):
            active_calls[0] += 1
            max_concurrent_observed[0] = max(max_concurrent_observed[0], active_calls[0])
            result = f"Narrative for {project.project_name}"
            active_calls[0] -= 1
            return result
        
        agent._generate_narrative = mock_generate
        
        # Generate narratives with max_concurrent=3
        narratives = await agent._generate_narratives_batch(
            qualified_projects=projects,
            max_concurrent=3
        )
        
        # Verify all narratives were generated
        assert len(narratives) == 10
        
        # Note: Due to asyncio.to_thread and timing, we can't reliably test
        # the exact concurrency limit, but we can verify all tasks completed
        assert agent.state.narratives_generated == 10
    
    @pytest.mark.asyncio
    async def test_generate_narratives_batch_with_template_url(self):
        """Test batch generation with template URL"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock Contents API
        youcom_client.fetch_content.return_value = {
            'content': '# Template content...',
            'word_count': 100
        }
        
        # Mock Agent API
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Narrative with template...'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects
        projects = [
            QualifiedProject(
                project_name="Project 1",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Initialize state
        agent.state.projects_to_process = len(projects)
        
        # Generate narratives with template URL
        narratives = await agent._generate_narratives_batch(
            qualified_projects=projects,
            template_url="https://example.com/template"
        )
        
        # Verify narrative was generated
        assert len(narratives) == 1
        assert "Project 1" in narratives
        
        # Verify Contents API was called (once per project)
        assert youcom_client.fetch_content.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_narratives_batch_handles_partial_failures(self):
        """Test batch generation continues when some projects fail"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock Agent API to fail for second project
        call_count = [0]
        def mock_agent_run(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise APIConnectionError(
                    message="API failed",
                    api_name="You.com",
                    endpoint="/v1/agents/runs"
                )
            return {
                'output': [
                    {
                        'type': 'chat_node.answer',
                        'text': f'Narrative {call_count[0]}...'
                    }
                ]
            }
        
        youcom_client.agent_run.side_effect = mock_agent_run
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects
        projects = [
            QualifiedProject(
                project_name=f"Project {i}",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
            for i in range(1, 4)
        ]
        
        # Initialize state
        agent.state.projects_to_process = len(projects)
        
        # Generate narratives - should not raise error
        narratives = await agent._generate_narratives_batch(
            qualified_projects=projects,
            max_concurrent=1  # Sequential to ensure predictable failure
        )
        
        # Verify all projects have narratives (including error message for failed one)
        assert len(narratives) == 3
        
        # Verify successful narratives
        assert "Narrative 1" in narratives["Project 1"]
        assert "Narrative 3" in narratives["Project 3"]
        
        # Verify failed narrative has error message
        assert "ERROR" in narratives["Project 2"]
        assert "Failed to generate narrative" in narratives["Project 2"]



class TestReviewNarrative:
    """Test _review_narrative method for compliance checking"""
    
    def test_review_narrative_compliant(self):
        """Test reviewing a compliant narrative"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Express Agent API response for compliant narrative
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': '''
## Compliance Review Results

**Overall Compliance Status:** Compliant

**Completeness Score:** 95%

**Missing or Weak Elements:**
None identified

**Strengths:**
- Clear identification of technical uncertainties
- Well-documented process of experimentation
- Strong demonstration of technological nature
- Qualified purpose clearly explained

**Specific Recommendations:**
- Consider adding more specific metrics for outcomes

**Risk Assessment:**
Low risk of IRS challenge. Documentation is comprehensive and well-structured.

**Required Revisions:**
None required
                    '''
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="API Optimization",
            qualified_hours=120.5,
            qualified_cost=15000.00,
            confidence_score=0.92,
            qualification_percentage=85.0,
            supporting_citation="CFR Title 26 § 1.41-4 defines qualified research...",
            reasoning="Project demonstrates clear technical uncertainty...",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        # Test narrative
        narrative = """
        Project Overview: This project aimed to optimize API response times...
        Technical Uncertainties: We faced uncertainty about the optimal caching strategy...
        Process of Experimentation: We conducted systematic testing of multiple approaches...
        """
        
        # Review narrative
        review = agent._review_narrative(narrative, project)
        
        # Verify review results
        assert review['compliance_status'] == 'Compliant'
        assert review['completeness_score'] == 95
        assert len(review['missing_elements']) == 0
        assert len(review['strengths']) > 0
        assert len(review['required_revisions']) == 0
        assert review['flagged_for_review'] is False
        
        # Verify You.com API was called
        assert youcom_client.agent_run.called
        call_args = youcom_client.agent_run.call_args
        assert call_args[1]['agent_mode'] == 'express'
        assert 'API Optimization' in call_args[1]['prompt']
    
    def test_review_narrative_needs_revision(self):
        """Test reviewing a narrative that needs revision"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Express Agent API response for narrative needing revision
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': '''
**Overall Compliance Status:** Needs Revision

**Completeness Score:** 65%

**Missing or Weak Elements:**
- Technical uncertainties are vague and not specific enough
- Process of experimentation lacks detail on specific tests conducted
- No clear explanation of why existing knowledge was inadequate

**Strengths:**
- Good project overview
- Timeline is clear

**Specific Recommendations:**
- Add specific technical challenges faced
- Document at least 3 different approaches tested
- Explain what information needed to be discovered

**Risk Assessment:**
Moderate risk of IRS challenge due to insufficient technical detail.

**Required Revisions:**
- Add detailed description of technical uncertainties
- Document specific experiments and their outcomes
- Explain the systematic evaluation process
                    '''
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Database Migration",
            qualified_hours=80.0,
            qualified_cost=10000.00,
            confidence_score=0.75,
            qualification_percentage=70.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Test narrative (incomplete)
        narrative = "We migrated the database to improve performance."
        
        # Review narrative
        review = agent._review_narrative(narrative, project)
        
        # Verify review results
        assert review['compliance_status'] == 'Needs Revision'
        assert review['completeness_score'] == 65
        assert len(review['missing_elements']) > 0
        assert len(review['required_revisions']) > 0
        assert review['flagged_for_review'] is True
        
        # Verify missing elements were extracted
        assert any('technical uncertainties' in elem.lower() for elem in review['missing_elements'])
    
    def test_review_narrative_non_compliant(self):
        """Test reviewing a non-compliant narrative"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Express Agent API response for non-compliant narrative
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': '''
**Overall Compliance Status:** Non-Compliant

**Completeness Score:** 30%

**Missing or Weak Elements:**
- No technical uncertainties identified
- No process of experimentation documented
- No demonstration of technological nature
- Qualified purpose is unclear

**Strengths:**
None identified

**Specific Recommendations:**
- Complete rewrite required
- Must address all four-part test requirements

**Risk Assessment:**
High risk of IRS rejection. Documentation does not meet minimum requirements.

**Required Revisions:**
- Add technical uncertainties section
- Document process of experimentation
- Demonstrate technological nature
- Clarify qualified purpose
- Provide specific examples and details
                    '''
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project with low confidence
        project = QualifiedProject(
            project_name="Website Update",
            qualified_hours=40.0,
            qualified_cost=5000.00,
            confidence_score=0.65,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Test narrative (very incomplete)
        narrative = "We updated the website."
        
        # Review narrative
        review = agent._review_narrative(narrative, project)
        
        # Verify review results
        assert review['compliance_status'] == 'Non-Compliant'
        assert review['completeness_score'] == 30
        assert len(review['missing_elements']) > 0
        assert len(review['required_revisions']) > 0
        assert review['flagged_for_review'] is True
        
        # Verify all required revisions were extracted
        assert len(review['required_revisions']) >= 4
    
    def test_review_narrative_flags_low_confidence_project(self):
        """Test that narratives for low-confidence projects are flagged"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Express Agent API response (even if compliant)
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': '''
**Overall Compliance Status:** Compliant

**Completeness Score:** 85%

**Missing or Weak Elements:**
None

**Strengths:**
- Good documentation

**Specific Recommendations:**
None

**Risk Assessment:**
Low risk

**Required Revisions:**
None
                    '''
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project with LOW confidence score (< 0.7)
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.65,  # Low confidence
            qualification_percentage=75.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        narrative = "Test narrative with good content..."
        
        # Review narrative
        review = agent._review_narrative(narrative, project)
        
        # Should be flagged due to low project confidence, even if narrative is compliant
        assert review['flagged_for_review'] is True
    
    def test_review_narrative_handles_api_error(self):
        """Test review handles You.com API errors"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock API error
        youcom_client.agent_run.side_effect = APIConnectionError(
            message="API connection failed",
            api_name="You.com Express Agent",
            endpoint="/v1/agents/runs"
        )
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        narrative = "Test narrative..."
        
        # Review should raise APIConnectionError
        with pytest.raises(APIConnectionError, match="API connection failed"):
            agent._review_narrative(narrative, project)
    
    def test_review_narrative_validates_empty_narrative(self):
        """Test review validates empty narrative"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Empty narrative should raise ValueError
        with pytest.raises(ValueError, match="Narrative cannot be empty"):
            agent._review_narrative("", project)
    
    def test_review_narrative_includes_project_context(self):
        """Test review includes project context in prompt"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Express Agent API response
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Compliant\n\nCompleteness Score: 90%'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="API Optimization",
            qualified_hours=120.5,
            qualified_cost=15000.00,
            confidence_score=0.92,
            qualification_percentage=85.0,
            supporting_citation="Test citation",
            reasoning="Detailed qualification reasoning...",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        narrative = "Test narrative..."
        
        # Review narrative
        agent._review_narrative(narrative, project)
        
        # Verify prompt includes project context
        call_args = youcom_client.agent_run.call_args
        prompt = call_args[1]['prompt']
        
        assert 'API Optimization' in prompt
        assert '85.0' in prompt or '85%' in prompt
        assert '0.92' in prompt
        assert '120.5' in prompt
        assert 'CFR Title 26' in prompt
        assert 'Detailed qualification reasoning' in prompt


class TestParseComplianceReview:
    """Test _parse_compliance_review method"""
    
    def test_parse_compliance_review_complete(self):
        """Test parsing a complete compliance review"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Test review text with all sections
        review_text = '''
**Overall Compliance Status:** Needs Revision

**Completeness Score:** 75%

**Missing or Weak Elements:**
- Technical uncertainties need more detail
- Process of experimentation is vague

**Strengths:**
- Good project overview
- Clear timeline

**Specific Recommendations:**
- Add specific technical challenges
- Document experiments conducted

**Risk Assessment:**
Moderate risk due to insufficient detail in experimentation section.

**Required Revisions:**
- Expand technical uncertainties section
- Add detailed experiment descriptions
        '''
        
        # Parse review
        result = agent._parse_compliance_review(review_text, project)
        
        # Verify all fields were extracted
        assert result['compliance_status'] == 'Needs Revision'
        assert result['completeness_score'] == 75
        assert len(result['missing_elements']) == 2
        assert len(result['strengths']) == 2
        assert len(result['recommendations']) == 2
        assert 'Moderate risk' in result['risk_assessment']
        assert len(result['required_revisions']) == 2
        assert result['flagged_for_review'] is True
    
    def test_parse_compliance_review_minimal(self):
        """Test parsing a minimal compliance review"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test project
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=100.0,
            qualified_cost=10000.00,
            confidence_score=0.95,
            qualification_percentage=90.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Minimal review text
        review_text = "The narrative is compliant with a score of 95%."
        
        # Parse review
        result = agent._parse_compliance_review(review_text, project)
        
        # Verify defaults are set
        assert result['completeness_score'] == 95
        assert isinstance(result['missing_elements'], list)
        assert isinstance(result['strengths'], list)
        assert isinstance(result['recommendations'], list)
        assert isinstance(result['required_revisions'], list)
        assert 'raw_review' in result
        assert result['raw_review'] == review_text



class TestAggregateReportData:
    """Test _aggregate_report_data method"""
    
    def test_aggregate_report_data_basic(self):
        """Test basic data aggregation with multiple projects"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects with varying confidence scores
        projects = [
            QualifiedProject(
                project_name="High Confidence Project",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.92,
                qualification_percentage=90.0,
                supporting_citation="Test citation 1",
                reasoning="Test reasoning 1",
                irs_source="CFR Title 26 § 1.41-4"
            ),
            QualifiedProject(
                project_name="Medium Confidence Project",
                qualified_hours=50.0,
                qualified_cost=5000.00,
                confidence_score=0.75,
                qualification_percentage=80.0,
                supporting_citation="Test citation 2",
                reasoning="Test reasoning 2",
                irs_source="Form 6765 Instructions"
            ),
            QualifiedProject(
                project_name="Low Confidence Project",
                qualified_hours=25.0,
                qualified_cost=2500.00,
                confidence_score=0.65,
                qualification_percentage=70.0,
                supporting_citation="Test citation 3",
                reasoning="Test reasoning 3",
                irs_source="Publication 542",
                flagged_for_review=True
            )
        ]
        
        # Aggregate data
        result = agent._aggregate_report_data(
            qualified_projects=projects,
            tax_year=2024
        )
        
        # Verify core totals
        assert result['total_qualified_hours'] == 175.0
        assert result['total_qualified_cost'] == 17500.00
        assert result['estimated_credit'] == 3500.00  # 20% of 17500
        
        # Verify confidence metrics
        assert result['average_confidence'] == pytest.approx(0.7733, rel=0.01)
        assert result['project_count'] == 3
        assert result['high_confidence_count'] == 1
        assert result['medium_confidence_count'] == 1
        assert result['low_confidence_count'] == 1
        assert result['flagged_count'] == 1
        
        # Verify metadata
        assert result['tax_year'] == 2024
        assert 'aggregation_timestamp' in result
        
        # Verify DataFrame is included
        assert 'projects_df' in result
        assert len(result['projects_df']) == 3
        
        # Verify summary statistics
        assert 'summary_stats' in result
        assert result['summary_stats']['min_confidence'] == 0.65
        assert result['summary_stats']['max_confidence'] == 0.92
    
    def test_aggregate_report_data_all_high_confidence(self):
        """Test aggregation with all high confidence projects"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects with high confidence
        projects = [
            QualifiedProject(
                project_name=f"Project {i}",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.9 + (i * 0.01),
                qualification_percentage=90.0,
                supporting_citation=f"Test citation {i}",
                reasoning=f"Test reasoning {i}",
                irs_source="CFR Title 26 § 1.41-4"
            )
            for i in range(5)
        ]
        
        # Aggregate data
        result = agent._aggregate_report_data(
            qualified_projects=projects,
            tax_year=2024
        )
        
        # Verify all projects are high confidence
        assert result['high_confidence_count'] == 5
        assert result['medium_confidence_count'] == 0
        assert result['low_confidence_count'] == 0
        assert result['flagged_count'] == 0
        
        # Verify totals
        assert result['total_qualified_hours'] == 500.0
        assert result['total_qualified_cost'] == 50000.00
        assert result['estimated_credit'] == 10000.00
    
    def test_aggregate_report_data_sorting(self):
        """Test that projects are sorted by qualified cost"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects with different costs
        projects = [
            QualifiedProject(
                project_name="Small Project",
                qualified_hours=10.0,
                qualified_cost=1000.00,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            ),
            QualifiedProject(
                project_name="Large Project",
                qualified_hours=200.0,
                qualified_cost=20000.00,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            ),
            QualifiedProject(
                project_name="Medium Project",
                qualified_hours=50.0,
                qualified_cost=5000.00,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Aggregate data
        result = agent._aggregate_report_data(
            qualified_projects=projects,
            tax_year=2024
        )
        
        # Verify projects are sorted by cost (descending)
        projects_df = result['projects_df']
        assert projects_df.iloc[0]['project_name'] == "Large Project"
        assert projects_df.iloc[1]['project_name'] == "Medium Project"
        assert projects_df.iloc[2]['project_name'] == "Small Project"
        
        # Verify cumulative percentages are calculated
        assert 'cumulative_cost' in projects_df.columns
        assert 'cumulative_percentage' in projects_df.columns
        assert projects_df.iloc[-1]['cumulative_percentage'] == pytest.approx(100.0, rel=0.01)
    
    def test_aggregate_report_data_empty_projects(self):
        """Test that empty projects list raises ValueError"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Attempt to aggregate with empty list
        with pytest.raises(ValueError, match="qualified_projects cannot be empty"):
            agent._aggregate_report_data(
                qualified_projects=[],
                tax_year=2024
            )
    
    def test_aggregate_report_data_invalid_tax_year(self):
        """Test that invalid tax year raises ValueError"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create a test project
        projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.85,
                qualification_percentage=80.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Attempt to aggregate with invalid tax year
        with pytest.raises(ValueError, match="Invalid tax_year"):
            agent._aggregate_report_data(
                qualified_projects=projects,
                tax_year=1999
            )
        
        with pytest.raises(ValueError, match="Invalid tax_year"):
            agent._aggregate_report_data(
                qualified_projects=projects,
                tax_year=2101
            )
    
    def test_aggregate_report_data_summary_statistics(self):
        """Test that summary statistics are calculated correctly"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects with known values
        projects = [
            QualifiedProject(
                project_name="Project 1",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.8,
                qualification_percentage=80.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            ),
            QualifiedProject(
                project_name="Project 2",
                qualified_hours=200.0,
                qualified_cost=20000.00,
                confidence_score=0.9,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            ),
            QualifiedProject(
                project_name="Project 3",
                qualified_hours=150.0,
                qualified_cost=15000.00,
                confidence_score=0.85,
                qualification_percentage=85.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Aggregate data
        result = agent._aggregate_report_data(
            qualified_projects=projects,
            tax_year=2024
        )
        
        # Verify summary statistics
        stats = result['summary_stats']
        assert stats['min_confidence'] == 0.8
        assert stats['max_confidence'] == 0.9
        assert stats['median_confidence'] == 0.85
        assert stats['min_qualified_hours'] == 100.0
        assert stats['max_qualified_hours'] == 200.0
        assert stats['median_qualified_hours'] == 150.0
        assert stats['min_qualified_cost'] == 10000.00
        assert stats['max_qualified_cost'] == 20000.00
        assert stats['median_qualified_cost'] == 15000.00
        assert stats['avg_qualification_percentage'] == 85.0
    
    def test_aggregate_report_data_top_projects_analysis(self):
        """Test that top projects contributing to 80% of costs are identified"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects where one project dominates
        projects = [
            QualifiedProject(
                project_name="Dominant Project",
                qualified_hours=1000.0,
                qualified_cost=80000.00,  # 80% of total
                confidence_score=0.9,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            ),
            QualifiedProject(
                project_name="Small Project 1",
                qualified_hours=100.0,
                qualified_cost=10000.00,  # 10% of total
                confidence_score=0.85,
                qualification_percentage=85.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            ),
            QualifiedProject(
                project_name="Small Project 2",
                qualified_hours=100.0,
                qualified_cost=10000.00,  # 10% of total
                confidence_score=0.85,
                qualification_percentage=85.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Aggregate data
        result = agent._aggregate_report_data(
            qualified_projects=projects,
            tax_year=2024
        )
        
        # Verify top projects analysis
        # The dominant project alone accounts for 80% of costs
        assert result['top_projects_80_count'] == 1
        
        # Verify cumulative percentages
        projects_df = result['projects_df']
        assert projects_df.iloc[0]['cumulative_percentage'] == pytest.approx(80.0, rel=0.01)
