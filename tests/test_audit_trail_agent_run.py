"""
Unit tests for Audit Trail Agent run() method and PDF generation.

Tests the complete workflow orchestration, PDF generation integration,
and error handling in the full pipeline.

Requirements: Testing
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from agents.audit_trail_agent import (
    AuditTrailAgent,
    AuditTrailState,
    AuditTrailResult
)
from models.tax_models import QualifiedProject, AuditReport
from models.websocket_models import AgentStage, AgentStatus
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.exceptions import APIConnectionError


class TestAuditTrailAgentRun:
    """Test the main run() method that orchestrates the workflow"""
    
    def test_run_complete_workflow_without_pdf(self):
        """Test complete workflow without PDF generator"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API for narrative generation
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Generated narrative for the project...'
                }
            ]
        }
        
        # Create agent WITHOUT PDF generator
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create test projects
        projects = [
            QualifiedProject(
                project_name="Project Alpha",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.92,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="CFR Title 26 § 1.41-4"
            ),
            QualifiedProject(
                project_name="Project Beta",
                qualified_hours=50.0,
                qualified_cost=5000.00,
                confidence_score=0.85,
                qualification_percentage=85.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Form 6765 Instructions"
            )
        ]
        
        # Run the workflow
        result = agent.run(
            qualified_projects=projects,
            tax_year=2024,
            company_name="Test Company"
        )
        
        # Verify result structure
        assert isinstance(result, AuditTrailResult)
        assert result.report is not None
        assert isinstance(result.report, AuditReport)
        assert result.pdf_path is None  # No PDF generator provided
        assert len(result.narratives) == 2
        assert len(result.compliance_reviews) == 2
        assert result.execution_time_seconds > 0
        
        # Verify report data
        assert result.report.tax_year == 2024
        assert result.report.total_qualified_hours == 150.0
        assert result.report.total_qualified_cost == 15000.00
        assert result.report.estimated_credit == 3000.00
        
        # Verify narratives were generated
        assert "Project Alpha" in result.narratives
        assert "Project Beta" in result.narratives
        
        # Verify compliance reviews were performed
        assert "Project Alpha" in result.compliance_reviews
        assert "Project Beta" in result.compliance_reviews
        
        # Verify You.com API was called for each project
        assert youcom_client.agent_run.call_count >= 2
        
        # Verify summary contains key information
        assert "2 projects" in result.summary
        
        # Verify agent state is completed
        assert agent.state.status == AgentStatus.COMPLETED
        assert agent.state.stage == "completed"
        assert agent.state.projects_to_process == 2
        assert agent.state.narratives_generated == 2
    
    def test_run_complete_workflow_with_pdf(self):
        """Test complete workflow with PDF generator"""
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        pdf_generator = Mock()  # Mock PDF generator without spec
        
        # Mock You.com Agent API
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Generated narrative...'
                }
            ]
        }
        
        # Mock PDF generation
        expected_pdf_path = "outputs/reports/rd_tax_credit_report_2024_20240101_120000.pdf"
        pdf_generator.generate_report.return_value = expected_pdf_path
        
        # Create agent WITH PDF generator
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            pdf_generator=pdf_generator
        )
        
        # Create test project
        projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.90,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Run the workflow
        result = agent.run(
            qualified_projects=projects,
            tax_year=2024,
            company_name="Acme Corp"
        )
        
        # Verify PDF was generated
        assert result.pdf_path == expected_pdf_path
        assert result.report.pdf_path == expected_pdf_path
        
        # Verify PDF generator was called
        assert pdf_generator.generate_report.called
        call_args = pdf_generator.generate_report.call_args
        
        # Verify report object was passed
        assert isinstance(call_args[1]['report'], AuditReport)
        assert call_args[1]['report'].tax_year == 2024
        
        # Verify output directory and filename
        assert call_args[1]['output_dir'] == "outputs/reports/"
        assert "rd_tax_credit_report_2024" in call_args[1]['filename']
        assert call_args[1]['filename'].endswith('.pdf')
        
        # Verify state shows PDF was generated
        assert agent.state.report_generated is True
    
    def test_run_validates_empty_projects(self):
        """Test that run() validates empty projects list"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        with pytest.raises(ValueError, match="qualified_projects cannot be empty"):
            agent.run(qualified_projects=[], tax_year=2024)
    
    def test_run_validates_tax_year(self):
        """Test that run() validates tax year"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.90,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        with pytest.raises(ValueError, match="Invalid tax_year"):
            agent.run(qualified_projects=projects, tax_year=1999)
        
        with pytest.raises(ValueError, match="Invalid tax_year"):
            agent.run(qualified_projects=projects, tax_year=2101)
    
    def test_run_handles_narrative_generation_failure(self):
        """Test that run() handles narrative generation failures gracefully"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API to fail
        youcom_client.agent_run.side_effect = APIConnectionError(
            message="You.com API failed",
            api_name="You.com Agent",
            endpoint="/v1/agents/runs"
        )
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.90,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Run should handle the error gracefully
        result = agent.run(qualified_projects=projects, tax_year=2024)
        
        # Verify result still contains data
        assert isinstance(result, AuditTrailResult)
        assert len(result.narratives) == 1
        
        # Verify narrative contains error message
        assert "ERROR" in result.narratives["Test Project"]
        assert "Failed to generate narrative" in result.narratives["Test Project"]
    
    def test_run_handles_pdf_generation_failure(self):
        """Test that run() continues when PDF generation fails"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        pdf_generator = Mock()  # Mock PDF generator without spec
        
        # Mock You.com Agent API to succeed
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Generated narrative...'
                }
            ]
        }
        
        # Mock PDF generation to fail
        pdf_generator.generate_report.side_effect = Exception("PDF generation failed")
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            pdf_generator=pdf_generator
        )
        
        projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.90,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Run should not raise exception even though PDF generation failed
        result = agent.run(qualified_projects=projects, tax_year=2024)
        
        # Verify workflow completed despite PDF failure
        assert isinstance(result, AuditTrailResult)
        assert result.report is not None
        assert result.pdf_path is None  # PDF generation failed
        assert len(result.narratives) == 1
        assert len(result.compliance_reviews) == 1
        
        # Verify state shows PDF was NOT generated
        assert agent.state.report_generated is False
    
    def test_run_with_status_callback(self):
        """Test that run() calls status callback during execution"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        status_callback = Mock()
        
        # Mock You.com Agent API
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Generated narrative...'
                }
            ]
        }
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            status_callback=status_callback
        )
        
        projects = [
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.90,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Run the workflow
        result = agent.run(qualified_projects=projects, tax_year=2024)
        
        # Verify status callback was called multiple times
        assert status_callback.call_count > 0
        
        # Verify callback was called with status messages
        # Should be called for: initializing, generating_narratives, reviewing_narratives, aggregating_data, completed
        assert status_callback.call_count >= 4
    
    def test_run_with_flagged_projects(self):
        """Test that run() properly handles flagged projects"""
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Generated narrative...'
                }
            ]
        }
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
        )
        
        # Create projects with one flagged for review
        projects = [
            QualifiedProject(
                project_name="High Confidence Project",
                qualified_hours=100.0,
                qualified_cost=10000.00,
                confidence_score=0.92,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            ),
            QualifiedProject(
                project_name="Low Confidence Project",
                qualified_hours=50.0,
                qualified_cost=5000.00,
                confidence_score=0.65,  # Low confidence
                qualification_percentage=70.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source",
                flagged_for_review=True
            )
        ]
        
        # Run the workflow
        result = agent.run(qualified_projects=projects, tax_year=2024)
        
        # Verify result includes flagged project warning
        assert "flagged for manual review" in result.summary.lower() or "WARNING" in result.summary
        
        # Verify aggregated data shows flagged count
        assert result.aggregated_data['flagged_count'] == 1
