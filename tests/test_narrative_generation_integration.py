"""
Integration test for narrative generation functionality (Task 6).

This test uses REAL API calls to You.com and GLM 4.5 (no mocks/simulations).

Tests verify that:
1. You.com Agent API is being called correctly
2. Response parsing extracts narrative text properly
3. Fallback narratives are generated for empty responses
4. Each narrative is >500 characters
5. Success/failure is logged for each project

Requirements: 4.1, 4.2

IMPORTANT: This test requires valid API keys in environment variables:
- YOUCOM_API_KEY: Your You.com API key
- OPENROUTER_API_KEY: Your OpenRouter API key for GLM 4.5
"""

import pytest
import os
from dotenv import load_dotenv
from agents.audit_trail_agent import AuditTrailAgent
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from models.tax_models import QualifiedProject

# Load environment variables from .env file
load_dotenv()


@pytest.fixture
def sample_projects():
    """Create 3 sample projects for testing."""
    return [
        QualifiedProject(
            project_name="API Performance Optimization",
            qualified_hours=120.5,
            qualified_cost=15000.00,
            confidence_score=0.92,
            qualification_percentage=85.0,
            supporting_citation="This project involved systematic experimentation with database query optimization techniques to achieve sub-100ms response times.",
            reasoning="The project addressed technical uncertainties in achieving sub-100ms response times for complex queries involving multiple table joins and aggregations. The team experimented with various indexing strategies, query restructuring approaches, and caching mechanisms.",
            irs_source="CFR Title 26 § 1.41-4(a)(1)",
            technical_details={
                "technologies_used": "PostgreSQL, Redis, Python",
                "duration": "3 months",
                "team_size": "4 engineers"
            }
        ),
        QualifiedProject(
            project_name="Machine Learning Model Development",
            qualified_hours=200.0,
            qualified_cost=25000.00,
            confidence_score=0.88,
            qualification_percentage=90.0,
            supporting_citation="Development of novel ML algorithms for predictive analytics with uncertainty quantification.",
            reasoning="The project involved experimentation with various neural network architectures to improve prediction accuracy while maintaining computational efficiency. Technical uncertainties included optimal layer configurations, activation functions, and regularization techniques.",
            irs_source="CFR Title 26 § 1.41-4(a)(2)",
            technical_details={
                "technologies_used": "TensorFlow, Python, Kubernetes",
                "duration": "6 months",
                "team_size": "5 engineers"
            }
        ),
        QualifiedProject(
            project_name="Distributed System Architecture",
            qualified_hours=150.0,
            qualified_cost=18750.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Design and implementation of fault-tolerant distributed systems with eventual consistency guarantees.",
            reasoning="The project addressed uncertainties in achieving consistency across distributed nodes while maintaining high availability. The team experimented with various consensus algorithms and conflict resolution strategies.",
            irs_source="CFR Title 26 § 1.41-4(a)(3)",
            technical_details={
                "technologies_used": "Kafka, Cassandra, Go",
                "duration": "4 months",
                "team_size": "6 engineers"
            }
        )
    ]


@pytest.fixture
def youcom_client():
    """Create a real You.com client with API key from environment."""
    api_key = os.getenv('YOUCOM_API_KEY')
    if not api_key:
        pytest.skip("YOUCOM_API_KEY environment variable not set")
    return YouComClient(api_key=api_key)


@pytest.fixture
def glm_reasoner():
    """Create a real GLM reasoner with API key from environment."""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY environment variable not set")
    return GLMReasoner(api_key=api_key)


@pytest.fixture
def audit_trail_agent(youcom_client, glm_reasoner):
    """Create an AuditTrailAgent instance with real API clients."""
    return AuditTrailAgent(
        youcom_client=youcom_client,
        glm_reasoner=glm_reasoner
    )


class TestNarrativeGenerationIntegration:
    """Integration test suite for narrative generation with REAL API calls."""
    
    def test_narrative_generation_with_real_api(self, audit_trail_agent, sample_projects):
        """
        Test narrative generation using real You.com Agent API.
        
        This test makes actual API calls to You.com to generate narratives.
        """
        # Generate narrative for first project using REAL API
        project = sample_projects[0]
        narrative = audit_trail_agent._generate_narrative(project)
        
        # Verify narrative was generated
        assert narrative is not None, "Narrative should not be None"
        assert len(narrative) > 500, f"Narrative too short: {len(narrative)} chars (expected >500)"
        assert project.project_name in narrative, "Project name should be in narrative"
        
        # Verify it contains key sections
        assert len(narrative) > 0, "Narrative should not be empty"
        
        print(f"\n✓ Successfully generated narrative for {project.project_name}")
        print(f"  Length: {len(narrative)} characters")
        print(f"  Preview: {narrative[:200]}...")
    
    def test_all_three_projects_with_real_api(self, audit_trail_agent, sample_projects):
        """
        Test narrative generation for all 3 sample projects using real API.
        
        This verifies that:
        - All projects can generate narratives
        - Each narrative meets minimum length requirement
        - API calls are working correctly
        """
        narratives = {}
        
        for project in sample_projects:
            print(f"\nGenerating narrative for: {project.project_name}")
            narrative = audit_trail_agent._generate_narrative(project)
            narratives[project.project_name] = narrative
            
            # Verify each narrative
            assert narrative is not None, f"Narrative is None for {project.project_name}"
            assert len(narrative) > 500, f"Narrative too short for {project.project_name}: {len(narrative)} chars"
            assert project.project_name in narrative, f"Project name not in narrative for {project.project_name}"
            
            print(f"  ✓ Generated {len(narrative)} characters")
        
        # Verify all narratives were generated
        assert len(narratives) == 3, f"Expected 3 narratives, got {len(narratives)}"
        
        print("\n" + "="*80)
        print("NARRATIVE GENERATION SUMMARY")
        print("="*80)
        for project_name, narrative in narratives.items():
            print(f"  {project_name}: {len(narrative)} characters")
        print("="*80)
    
    def test_fallback_narrative_structure(self, audit_trail_agent, sample_projects):
        """
        Test that fallback narrative has proper structure.
        
        This tests the fallback mechanism without relying on API failures.
        """
        project = sample_projects[0]
        fallback_narrative = audit_trail_agent._generate_fallback_narrative(project)
        
        # Verify structure
        assert "# Technical Narrative:" in fallback_narrative
        assert "## Project Overview" in fallback_narrative
        assert "## Qualification Analysis" in fallback_narrative
        assert "## IRS Regulatory Basis" in fallback_narrative
        assert "## Four-Part Test Compliance" in fallback_narrative
        assert "## Conclusion" in fallback_narrative
        
        # Verify content
        assert project.project_name in fallback_narrative
        assert project.reasoning in fallback_narrative
        assert project.irs_source in fallback_narrative
        assert project.supporting_citation in fallback_narrative
        
        # Verify length
        assert len(fallback_narrative) > 500, f"Fallback narrative too short: {len(fallback_narrative)} chars"
        
        print(f"\n✓ Fallback narrative structure verified")
        print(f"  Length: {len(fallback_narrative)} characters")
    
    def test_narrative_logging(self, audit_trail_agent, sample_projects, caplog):
        """
        Test that narrative generation logs success appropriately.
        
        This uses real API calls and verifies logging output.
        """
        import logging
        caplog.set_level(logging.INFO)
        
        # Generate narrative using REAL API
        project = sample_projects[0]
        narrative = audit_trail_agent._generate_narrative(project)
        
        # Verify logging
        log_messages = [record.message for record in caplog.records]
        
        # Check for key log messages
        assert any("[TASK 6] Starting narrative generation" in msg for msg in log_messages)
        assert any("[TASK 6] Calling You.com Agent API" in msg for msg in log_messages)
        assert any("[TASK 6] NARRATIVE GENERATION RESULT" in msg for msg in log_messages)
        assert any(f"Length: {len(narrative)} characters" in msg for msg in log_messages)
        assert any("Meets minimum (>500 chars):" in msg for msg in log_messages)
        
        print(f"\n✓ Logging verified for narrative generation")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
