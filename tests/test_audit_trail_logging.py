"""
Test for Task 2: Verify AuditTrailAgent data flow logging.

This test verifies that detailed logging is added to the AuditTrailAgent.run() method
to track narratives, compliance reviews, aggregated data, and AuditReport object.

Requirements: 4.1, 4.4, 8.5
"""

import pytest
import logging
from unittest.mock import Mock
from io import StringIO

from agents.audit_trail_agent import AuditTrailAgent, AuditTrailResult
from models.tax_models import QualifiedProject
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner


class TestAuditTrailLogging:
    """Test detailed logging in AuditTrailAgent data flow"""
    
    def test_narratives_dictionary_logging(self, caplog):
        """Test that narratives dictionary is logged with keys and lengths"""
        # Set up logging capture
        caplog.set_level(logging.INFO)
        
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API for narrative generation
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'This is a detailed technical narrative for the R&D project. ' * 20
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
            tax_year=2024
        )
        
        # Verify narratives were generated
        assert len(result.narratives) == 2
        
        # Check that logging contains narratives verification section
        log_text = caplog.text
        
        # Verify narratives dictionary logging
        assert "NARRATIVES DICTIONARY VERIFICATION" in log_text
        assert "Total narratives generated: 2" in log_text
        assert "Project Alpha" in log_text
        assert "Project Beta" in log_text
        assert "characters" in log_text
    
    def test_compliance_reviews_logging(self, caplog):
        """Test that compliance_reviews dictionary is logged with keys and status"""
        # Set up logging capture
        caplog.set_level(logging.INFO)
        
        # Create mock clients
        youcom_client = Mock(spec=YouComClient)
        glm_reasoner = Mock(spec=GLMReasoner)
        
        # Mock You.com Agent API
        youcom_client.agent_run.return_value = {
            'output': [
                {
                    'type': 'chat_node.answer',
                    'text': 'Generated narrative with compliance review details...'
                }
            ]
        }
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
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
            tax_year=2024
        )
        
        # Verify compliance reviews were performed
        assert len(result.compliance_reviews) == 1
        
        # Check that logging contains compliance reviews verification section
        log_text = caplog.text
        
        # Verify compliance reviews dictionary logging
        assert "COMPLIANCE REVIEWS DICTIONARY VERIFICATION" in log_text
        assert "Total compliance reviews: 1" in log_text
        assert "Test Project" in log_text
        assert "Status=" in log_text
        assert "Completeness=" in log_text
        assert "Flagged=" in log_text
    
    def test_aggregated_data_logging(self, caplog):
        """Test that aggregated_data dictionary is logged with all keys and values"""
        # Set up logging capture
        caplog.set_level(logging.INFO)
        
        # Create mock clients
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
                confidence_score=0.92,
                qualification_percentage=90.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            ),
            QualifiedProject(
                project_name="Project 2",
                qualified_hours=50.0,
                qualified_cost=5000.00,
                confidence_score=0.85,
                qualification_percentage=85.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        ]
        
        # Run the workflow
        result = agent.run(
            qualified_projects=projects,
            tax_year=2024
        )
        
        # Verify aggregated data was calculated
        assert result.aggregated_data is not None
        
        # Check that logging contains aggregated data verification section
        log_text = caplog.text
        
        # Verify aggregated data dictionary logging
        assert "AGGREGATED DATA DICTIONARY VERIFICATION" in log_text
        assert "Aggregated data keys:" in log_text
        assert "Core Metrics:" in log_text
        assert "total_qualified_hours:" in log_text
        assert "total_qualified_cost:" in log_text
        assert "estimated_credit:" in log_text
        assert "average_confidence:" in log_text
        assert "project_count:" in log_text
        assert "flagged_count:" in log_text
        assert "Summary Statistics:" in log_text
        assert "DataFrame shape:" in log_text
    
    def test_audit_report_object_logging(self, caplog):
        """Test that AuditReport object is logged before passing to PDF generator"""
        # Set up logging capture
        caplog.set_level(logging.INFO)
        
        # Create mock clients
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
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
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
            company_name="Test Company"
        )
        
        # Verify report was created
        assert result.report is not None
        
        # Check that logging contains AuditReport verification section
        log_text = caplog.text
        
        # Verify AuditReport object logging
        assert "AUDITREPORT OBJECT VERIFICATION (Before PDF Generation)" in log_text
        assert "AuditReport Fields:" in log_text
        assert "report_id:" in log_text
        assert "generation_date:" in log_text
        assert "tax_year:" in log_text
        assert "total_qualified_hours:" in log_text
        assert "total_qualified_cost:" in log_text
        assert "estimated_credit:" in log_text
        assert "projects count:" in log_text
        assert "has narratives field:" in log_text
        assert "has compliance_reviews field:" in log_text
        assert "has aggregated_data field:" in log_text
    
    def test_result_object_logging(self, caplog):
        """Test that AuditTrailResult object is logged with complete data"""
        # Set up logging capture
        caplog.set_level(logging.INFO)
        
        # Create mock clients
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
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
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
            tax_year=2024
        )
        
        # Verify result has complete data
        assert result.narratives
        assert result.compliance_reviews
        assert result.aggregated_data
        
        # Check that logging contains result verification section
        log_text = caplog.text
        
        # Verify AuditTrailResult object logging
        assert "AUDITTRAILRESULT OBJECT VERIFICATION" in log_text
        assert "Result object fields:" in log_text
        assert "narratives count:" in log_text
        assert "narratives keys:" in log_text
        assert "compliance_reviews count:" in log_text
        assert "compliance_reviews keys:" in log_text
        assert "aggregated_data:" in log_text
        assert "execution_time_seconds:" in log_text
    
    def test_missing_fields_warning_logging(self, caplog):
        """Test that warnings are logged if AuditReport is missing narratives/aggregated_data fields"""
        # Set up logging capture
        caplog.set_level(logging.WARNING)
        
        # Create mock clients
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
        
        # Create agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner
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
            tax_year=2024
        )
        
        # Check that logging contains warnings about missing fields
        log_text = caplog.text
        
        # The current AuditReport model likely doesn't have these fields yet (Task 4)
        # So we should see warnings
        assert "NOT PRESENT in AuditReport model" in log_text or "has narratives field: True" in log_text
