"""
Unit Tests for Prompt Templates Module

Tests all prompt template functions and helper utilities.
"""

import pytest
import json
from datetime import datetime

from tools.prompt_templates import (
    RAG_INFERENCE_PROMPT,
    AGENT_DECISION_PROMPT,
    THESYS_DATA_INGESTION_PROMPT,
    THESYS_QUALIFICATION_DASHBOARD_PROMPT,
    THESYS_REPORT_CONFIRMATION_PROMPT,
    NARRATIVE_GENERATION_PROMPT,
    COMPLIANCE_REVIEW_PROMPT,
    populate_rag_inference_prompt,
    populate_agent_decision_prompt,
    populate_thesys_data_ingestion_prompt,
    populate_thesys_qualification_dashboard_prompt,
    populate_thesys_report_confirmation_prompt,
    populate_narrative_generation_prompt,
    populate_compliance_review_prompt,
    create_batch_rag_prompts,
    create_batch_narrative_prompts
)


class TestRAGInferencePrompt:
    """Tests for RAG inference prompt"""
    
    def test_populate_rag_inference_prompt(self):
        """Test basic RAG inference prompt population"""
        prompt = populate_rag_inference_prompt(
            rag_context="Test IRS context",
            project_name="Test Project",
            project_description="Test description",
            technical_activities="Test activities",
            total_hours=100.0,
            total_cost=10000.0
        )
        
        assert "Test IRS context" in prompt
        assert "Test Project" in prompt
        assert "Test description" in prompt
        assert "Test activities" in prompt
        assert "100.0" in prompt
        assert "10,000.00" in prompt
        assert "four-part test" in prompt.lower()
    
    def test_rag_prompt_includes_json_format(self):
        """Test that RAG prompt includes JSON output format"""
        prompt = populate_rag_inference_prompt(
            rag_context="Context",
            project_name="Project",
            project_description="Desc",
            technical_activities="Activities",
            total_hours=50.0,
            total_cost=5000.0
        )
        
        assert "qualification_percentage" in prompt
        assert "confidence_score" in prompt
        assert "reasoning" in prompt
        assert "citations" in prompt
        assert "four_part_test_results" in prompt
    
    def test_rag_prompt_formatting(self):
        """Test proper number formatting in RAG prompt"""
        prompt = populate_rag_inference_prompt(
            rag_context="Context",
            project_name="Project",
            project_description="Desc",
            technical_activities="Activities",
            total_hours=123.45,
            total_cost=15678.90
        )
        
        assert "123.45" in prompt
        assert "$15,678.90" in prompt


class TestAgentDecisionPrompt:
    """Tests for agent decision prompt"""
    
    def test_populate_agent_decision_prompt(self):
        """Test basic agent decision prompt population"""
        agent_state = {
            "projects_analyzed": 10,
            "low_confidence_count": 2
        }
        
        prompt = populate_agent_decision_prompt(
            stage_name="Qualification",
            agent_state=agent_state,
            available_actions=["proceed", "flag", "abort"],
            context_information="Test context",
            decision_question="What should we do?"
        )
        
        assert "Qualification" in prompt
        assert "projects_analyzed" in prompt
        assert "10" in prompt
        assert "proceed" in prompt
        assert "Test context" in prompt
        assert "What should we do?" in prompt
    
    def test_agent_prompt_json_serialization(self):
        """Test that agent state is properly JSON serialized"""
        agent_state = {
            "count": 5,
            "total": 100.5,
            "flag": True
        }
        
        prompt = populate_agent_decision_prompt(
            stage_name="Test",
            agent_state=agent_state,
            available_actions=["action1"],
            context_information="Context",
            decision_question="Question?"
        )
        
        # Should contain JSON-formatted state
        assert '"count": 5' in prompt
        assert '"total": 100.5' in prompt
        assert '"flag": true' in prompt


class TestThesysPrompts:
    """Tests for Thesys UI generation prompts"""
    
    def test_populate_data_ingestion_prompt(self):
        """Test data ingestion UI prompt population"""
        data = [
            {
                "employee_name": "John Doe",
                "project_name": "Project A",
                "hours_spent": 8.5,
                "date": "2024-01-15",
                "is_rd_classified": True
            }
        ]
        
        prompt = populate_thesys_data_ingestion_prompt(
            data=data,
            total_hours=100.0,
            classified_hours=75.0,
            project_count=5
        )
        
        assert "John Doe" in prompt
        assert "Project A" in prompt
        assert "100.0" in prompt
        assert "75.0" in prompt
        assert "75.0" in prompt  # classification percentage
        assert "5" in prompt
    
    def test_data_ingestion_prompt_percentage_calculation(self):
        """Test classification percentage calculation"""
        prompt = populate_thesys_data_ingestion_prompt(
            data=[],
            total_hours=200.0,
            classified_hours=150.0,
            project_count=10
        )
        
        # 150/200 = 75%
        assert "75.0" in prompt
    
    def test_data_ingestion_prompt_zero_hours(self):
        """Test handling of zero total hours"""
        prompt = populate_thesys_data_ingestion_prompt(
            data=[],
            total_hours=0.0,
            classified_hours=0.0,
            project_count=0
        )
        
        # Should not crash, percentage should be 0
        assert "0.0" in prompt
    
    def test_populate_qualification_dashboard_prompt(self):
        """Test qualification dashboard prompt population"""
        projects = [
            {
                "project_name": "Project A",
                "qualified_hours": 100.0,
                "qualified_cost": 12000.0,
                "confidence_score": 0.88
            }
        ]
        
        prompt = populate_thesys_qualification_dashboard_prompt(
            qualified_projects=projects,
            total_qualified_hours=100.0,
            total_qualified_cost=12000.0,
            estimated_credit=2400.0,
            average_confidence=0.88
        )
        
        assert "Project A" in prompt
        assert "100.0" in prompt
        assert "12,000.00" in prompt
        assert "2,400.00" in prompt
        assert "0.88" in prompt or "88" in prompt
    
    def test_populate_report_confirmation_prompt(self):
        """Test report confirmation prompt population"""
        metadata = {
            "report_id": "RPT-001",
            "file_size_mb": 2.5
        }
        
        prompt = populate_thesys_report_confirmation_prompt(
            report_metadata=metadata,
            tax_year=2024,
            generation_date="2024-01-20",
            total_qualified_cost=50000.0,
            estimated_credit=10000.0,
            project_count=10,
            report_id="RPT-001"
        )
        
        assert "2024" in prompt
        assert "RPT-001" in prompt
        assert "50,000.00" in prompt
        assert "10,000.00" in prompt
        assert "10" in prompt


class TestNarrativePrompts:
    """Tests for narrative generation and compliance prompts"""
    
    def test_populate_narrative_generation_prompt(self):
        """Test narrative generation prompt population"""
        prompt = populate_narrative_generation_prompt(
            project_name="ML Model",
            qualification_percentage=85.0,
            qualified_hours=120.0,
            qualified_cost=15000.0,
            confidence_score=0.88,
            qualification_reasoning="Meets all criteria",
            irs_citations=["CFR Title 26 § 1.41-4", "Form 6765"]
        )
        
        assert "ML Model" in prompt
        assert "85.0" in prompt
        assert "120.0" in prompt
        assert "15,000.00" in prompt
        assert "0.88" in prompt
        assert "Meets all criteria" in prompt
        assert "CFR Title 26 § 1.41-4" in prompt
        assert "Form 6765" in prompt
    
    def test_narrative_prompt_empty_citations(self):
        """Test narrative prompt with no citations"""
        prompt = populate_narrative_generation_prompt(
            project_name="Project",
            qualification_percentage=80.0,
            qualified_hours=100.0,
            qualified_cost=10000.0,
            confidence_score=0.8,
            qualification_reasoning="Reasoning",
            irs_citations=[]
        )
        
        assert "None" in prompt or "no citations" in prompt.lower()
    
    def test_populate_compliance_review_prompt(self):
        """Test compliance review prompt population"""
        narrative = "This is a test narrative with technical details."
        
        prompt = populate_compliance_review_prompt(narrative_text=narrative)
        
        assert narrative in prompt
        assert "Technical Uncertainties" in prompt
        assert "Process of Experimentation" in prompt
        assert "compliance_status" in prompt
        assert "completeness_score" in prompt


class TestBatchProcessing:
    """Tests for batch processing helpers"""
    
    def test_create_batch_rag_prompts(self):
        """Test batch RAG prompt creation"""
        projects = [
            {
                "name": "Project A",
                "description": "Desc A",
                "technical_activities": "Activities A",
                "total_hours": 100,
                "total_cost": 10000
            },
            {
                "name": "Project B",
                "description": "Desc B",
                "technical_activities": "Activities B",
                "total_hours": 150,
                "total_cost": 15000
            }
        ]
        
        rag_contexts = ["Context A", "Context B"]
        
        prompts = create_batch_rag_prompts(projects, rag_contexts)
        
        assert len(prompts) == 2
        assert "Project A" in prompts[0]
        assert "Context A" in prompts[0]
        assert "Project B" in prompts[1]
        assert "Context B" in prompts[1]
    
    def test_batch_rag_prompts_length_mismatch(self):
        """Test error handling for mismatched lengths"""
        projects = [{"name": "A"}]
        contexts = ["Context A", "Context B"]
        
        with pytest.raises(ValueError, match="must match"):
            create_batch_rag_prompts(projects, contexts)
    
    def test_create_batch_narrative_prompts(self):
        """Test batch narrative prompt creation"""
        projects = [
            {
                "project_name": "Project A",
                "qualification_percentage": 85.0,
                "qualified_hours": 100.0,
                "qualified_cost": 10000.0,
                "confidence_score": 0.85,
                "reasoning": "Reasoning A",
                "citations": ["Citation A"]
            },
            {
                "project_name": "Project B",
                "qualification_percentage": 90.0,
                "qualified_hours": 150.0,
                "qualified_cost": 15000.0,
                "confidence_score": 0.90,
                "reasoning": "Reasoning B",
                "citations": ["Citation B"]
            }
        ]
        
        prompts = create_batch_narrative_prompts(projects)
        
        assert len(prompts) == 2
        assert "Project A" in prompts[0]
        assert "Reasoning A" in prompts[0]
        assert "Project B" in prompts[1]
        assert "Reasoning B" in prompts[1]
    
    def test_batch_narrative_prompts_missing_fields(self):
        """Test batch narrative prompts with missing optional fields"""
        projects = [
            {
                "project_name": "Project A"
                # Missing other fields - should use defaults
            }
        ]
        
        prompts = create_batch_narrative_prompts(projects)
        
        assert len(prompts) == 1
        assert "Project A" in prompts[0]
        # Should not crash, should use default values


class TestPromptTemplateConstants:
    """Tests for prompt template constants"""
    
    def test_rag_inference_prompt_exists(self):
        """Test that RAG inference prompt template exists"""
        assert RAG_INFERENCE_PROMPT is not None
        assert len(RAG_INFERENCE_PROMPT) > 0
        assert "{rag_context}" in RAG_INFERENCE_PROMPT
        assert "{project_name}" in RAG_INFERENCE_PROMPT
    
    def test_agent_decision_prompt_exists(self):
        """Test that agent decision prompt template exists"""
        assert AGENT_DECISION_PROMPT is not None
        assert len(AGENT_DECISION_PROMPT) > 0
        assert "{stage_name}" in AGENT_DECISION_PROMPT
        assert "{agent_state}" in AGENT_DECISION_PROMPT
    
    def test_thesys_prompts_exist(self):
        """Test that all Thesys prompts exist"""
        assert THESYS_DATA_INGESTION_PROMPT is not None
        assert THESYS_QUALIFICATION_DASHBOARD_PROMPT is not None
        assert THESYS_REPORT_CONFIRMATION_PROMPT is not None
    
    def test_narrative_prompts_exist(self):
        """Test that narrative prompts exist"""
        assert NARRATIVE_GENERATION_PROMPT is not None
        assert COMPLIANCE_REVIEW_PROMPT is not None


class TestPromptQuality:
    """Tests for prompt quality and completeness"""
    
    def test_rag_prompt_includes_four_part_test(self):
        """Test that RAG prompt includes four-part test guidance"""
        assert "four-part test" in RAG_INFERENCE_PROMPT.lower()
        assert "technological in nature" in RAG_INFERENCE_PROMPT.lower()
        assert "uncertainty" in RAG_INFERENCE_PROMPT.lower()
        assert "experimentation" in RAG_INFERENCE_PROMPT.lower()
        assert "qualified purpose" in RAG_INFERENCE_PROMPT.lower()
    
    def test_narrative_prompt_includes_required_sections(self):
        """Test that narrative prompt includes all required sections"""
        prompt = NARRATIVE_GENERATION_PROMPT.lower()
        assert "technical uncertainties" in prompt
        assert "process of experimentation" in prompt
        assert "technological nature" in prompt
        assert "qualified purpose" in prompt
        assert "outcomes" in prompt
    
    def test_compliance_prompt_includes_checklist(self):
        """Test that compliance prompt includes review checklist"""
        prompt = COMPLIANCE_REVIEW_PROMPT.lower()
        assert "technical uncertainties" in prompt
        assert "process of experimentation" in prompt
        assert "technological nature" in prompt
        assert "qualified purpose" in prompt
        assert "compliance_status" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
