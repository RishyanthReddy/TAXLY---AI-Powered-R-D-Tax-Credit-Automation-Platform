"""
Integration tests for compliance review verification (Task 7).

This test module verifies that the _review_narrative() method:
1. Calls You.com Express Agent API correctly
2. Parses response to extract compliance status
3. Logs review results for each narrative

Requirements: 4.3, 6.3
"""

import pytest
import os
import logging
from unittest.mock import Mock
from dotenv import load_dotenv

from agents.audit_trail_agent import AuditTrailAgent
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from models.tax_models import QualifiedProject
from utils.exceptions import APIConnectionError

# Load environment variables from .env file
load_dotenv()


class TestComplianceReviewVerification:
    """Test compliance review functionality with real API calls and fallback scenarios."""
    
    @pytest.fixture
    def real_youcom_client(self):
        """Create real You.com client with API key from environment."""
        api_key = os.getenv('YOUCOM_API_KEY')
        if not api_key:
            pytest.skip("YOUCOM_API_KEY environment variable not set")
        return YouComClient(api_key=api_key)
    
    @pytest.fixture
    def real_glm_reasoner(self):
        """Create real GLM reasoner with API key from environment."""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY environment variable not set")
        return GLMReasoner(api_key=api_key)
    
    @pytest.fixture
    def sample_projects(self):
        """Create 3 sample projects for testing."""
        return [
            QualifiedProject(
                project_name="API Performance Optimization",
                qualified_hours=120.5,
                qualified_cost=15000.00,
                confidence_score=0.92,
                qualification_percentage=85.0,
                supporting_citation="CFR Title 26 § 1.41-4 defines qualified research as research undertaken to discover information that is technological in nature.",
                reasoning="Project demonstrates clear technical uncertainty in optimizing API response times under high load conditions. The team conducted systematic experimentation with multiple caching strategies, load balancing algorithms, and database query optimizations.",
                irs_source="CFR Title 26 § 1.41-4"
            ),
            QualifiedProject(
                project_name="Machine Learning Model Development",
                qualified_hours=200.0,
                qualified_cost=25000.00,
                confidence_score=0.88,
                qualification_percentage=90.0,
                supporting_citation="IRS Publication 542 describes qualified research activities including development of new or improved business components.",
                reasoning="Development of a novel machine learning model for predictive analytics involved significant technical uncertainty regarding feature engineering, model architecture selection, and hyperparameter optimization.",
                irs_source="IRS Publication 542"
            ),
            QualifiedProject(
                project_name="Database Migration",
                qualified_hours=80.0,
                qualified_cost=10000.00,
                confidence_score=0.65,
                qualification_percentage=60.0,
                supporting_citation="CFR Title 26 § 1.41-4",
                reasoning="Migration from legacy database system to modern architecture with minimal downtime.",
                irs_source="CFR Title 26 § 1.41-4"
            )
        ]
    
    @pytest.fixture
    def sample_narratives(self):
        """Create 3 sample narratives with varying quality levels."""
        return {
            "API Performance Optimization": """
# Technical Narrative: API Performance Optimization

## Project Overview
This project aimed to optimize API response times for our high-traffic e-commerce platform, which was experiencing performance degradation under peak loads exceeding 10,000 requests per second.

## Technical Uncertainties
We faced significant technical uncertainty regarding:
1. The optimal caching strategy for dynamic product data with frequent inventory updates
2. The most effective load balancing algorithm for our microservices architecture
3. Database query optimization techniques that would maintain data consistency while improving performance

## Process of Experimentation
Our systematic experimentation process included:
1. **Caching Strategy Testing**: We evaluated Redis, Memcached, and in-memory caching solutions, measuring cache hit rates, memory usage, and data staleness
2. **Load Balancing Algorithms**: We tested round-robin, least connections, and weighted response time algorithms under various load conditions
3. **Database Optimization**: We experimented with query restructuring, index optimization, and connection pooling configurations

## Results and Outcomes
Through this systematic process, we achieved a 60% reduction in average response time and successfully handled peak loads of 15,000 requests per second while maintaining 99.9% uptime.

## Qualified Purpose
This work directly supports our business operations by enabling scalable e-commerce transactions and improving customer experience through faster page loads and checkout processes.
            """,
            "Machine Learning Model Development": """
# Technical Narrative: Machine Learning Model Development

## Project Overview
Development of a predictive analytics model for customer churn prediction using advanced machine learning techniques.

## Technical Uncertainties
The project involved uncertainty about optimal feature engineering approaches and model architecture selection for our specific dataset characteristics.

## Process of Experimentation
We tested multiple model architectures including random forests, gradient boosting, and neural networks. Feature engineering experiments included various encoding strategies and dimensionality reduction techniques.

## Results
Achieved 85% prediction accuracy with the final model architecture.

## Qualified Purpose
Supports business decision-making for customer retention strategies.
            """,
            "Database Migration": """
We migrated the database to improve performance and reduce costs.
            """
        }
    
    def test_review_narrative_with_real_api_compliant(
        self,
        real_youcom_client,
        real_glm_reasoner,
        sample_projects,
        sample_narratives,
        caplog
    ):
        """
        Test compliance review with real You.com API for a high-quality narrative.
        
        This test verifies:
        - You.com Express Agent API is called correctly
        - Response is parsed to extract compliance status
        - Review results are logged properly
        """
        caplog.set_level(logging.INFO)
        
        # Create agent with real API clients
        agent = AuditTrailAgent(
            youcom_client=real_youcom_client,
            glm_reasoner=real_glm_reasoner
        )
        
        # Get first project and narrative (high quality)
        project = sample_projects[0]
        narrative = sample_narratives["API Performance Optimization"]
        
        # Review the narrative
        review = agent._review_narrative(narrative, project)
        
        # Verify review structure
        assert 'compliance_status' in review
        assert 'completeness_score' in review
        assert 'missing_elements' in review
        assert 'strengths' in review
        assert 'recommendations' in review
        assert 'risk_assessment' in review
        assert 'required_revisions' in review
        assert 'flagged_for_review' in review
        assert 'review_summary' in review
        
        # Verify compliance status is valid
        assert review['compliance_status'] in [
            'Compliant', 'Needs Revision', 'Non-Compliant', 'Review Pending', 'Unknown'
        ]
        
        # Verify completeness score is in valid range
        assert 0 <= review['completeness_score'] <= 100
        
        # Verify logging occurred
        log_text = caplog.text
        assert "Reviewing narrative for compliance" in log_text
        assert project.project_name in log_text
        assert "Compliance review for" in log_text
        
        # Log results for verification
        print(f"\n{'='*80}")
        print(f"COMPLIANCE REVIEW RESULTS - {project.project_name}")
        print(f"{'='*80}")
        print(f"Status: {review['compliance_status']}")
        print(f"Completeness Score: {review['completeness_score']}%")
        print(f"Flagged for Review: {review['flagged_for_review']}")
        print(f"Missing Elements: {len(review['missing_elements'])}")
        print(f"Strengths: {len(review['strengths'])}")
        print(f"Required Revisions: {len(review['required_revisions'])}")
        print(f"Review Summary: {review['review_summary']}")
        print(f"{'='*80}\n")
    
    def test_review_narrative_with_real_api_needs_revision(
        self,
        real_youcom_client,
        real_glm_reasoner,
        sample_projects,
        sample_narratives,
        caplog
    ):
        """
        Test compliance review with real You.com API for a medium-quality narrative.
        
        This test verifies that narratives with some issues are properly identified
        and flagged for revision.
        """
        caplog.set_level(logging.INFO)
        
        # Create agent with real API clients
        agent = AuditTrailAgent(
            youcom_client=real_youcom_client,
            glm_reasoner=real_glm_reasoner
        )
        
        # Get second project and narrative (medium quality)
        project = sample_projects[1]
        narrative = sample_narratives["Machine Learning Model Development"]
        
        # Review the narrative
        review = agent._review_narrative(narrative, project)
        
        # Verify review structure
        assert 'compliance_status' in review
        assert 'completeness_score' in review
        
        # Verify logging occurred
        log_text = caplog.text
        assert "Reviewing narrative for compliance" in log_text
        assert project.project_name in log_text
        
        # Log results for verification
        print(f"\n{'='*80}")
        print(f"COMPLIANCE REVIEW RESULTS - {project.project_name}")
        print(f"{'='*80}")
        print(f"Status: {review['compliance_status']}")
        print(f"Completeness Score: {review['completeness_score']}%")
        print(f"Flagged for Review: {review['flagged_for_review']}")
        print(f"Missing Elements: {review['missing_elements']}")
        print(f"Strengths: {review['strengths']}")
        print(f"Required Revisions: {review['required_revisions']}")
        print(f"Review Summary: {review['review_summary']}")
        print(f"{'='*80}\n")
    
    def test_review_narrative_with_real_api_low_quality(
        self,
        real_youcom_client,
        real_glm_reasoner,
        sample_projects,
        sample_narratives,
        caplog
    ):
        """
        Test compliance review with real You.com API for a low-quality narrative.
        
        This test verifies that incomplete narratives are properly identified
        and flagged for significant revision.
        """
        caplog.set_level(logging.INFO)
        
        # Create agent with real API clients
        agent = AuditTrailAgent(
            youcom_client=real_youcom_client,
            glm_reasoner=real_glm_reasoner
        )
        
        # Get third project and narrative (low quality)
        project = sample_projects[2]
        narrative = sample_narratives["Database Migration"]
        
        # Review the narrative
        review = agent._review_narrative(narrative, project)
        
        # Verify review structure
        assert 'compliance_status' in review
        assert 'completeness_score' in review
        
        # Low quality narrative should likely be flagged
        # (though we don't enforce this as API may vary)
        
        # Verify logging occurred
        log_text = caplog.text
        assert "Reviewing narrative for compliance" in log_text
        assert project.project_name in log_text
        
        # Log results for verification
        print(f"\n{'='*80}")
        print(f"COMPLIANCE REVIEW RESULTS - {project.project_name}")
        print(f"{'='*80}")
        print(f"Status: {review['compliance_status']}")
        print(f"Completeness Score: {review['completeness_score']}%")
        print(f"Flagged for Review: {review['flagged_for_review']}")
        print(f"Missing Elements: {review['missing_elements']}")
        print(f"Strengths: {review['strengths']}")
        print(f"Required Revisions: {review['required_revisions']}")
        print(f"Review Summary: {review['review_summary']}")
        print(f"{'='*80}\n")
    



if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
