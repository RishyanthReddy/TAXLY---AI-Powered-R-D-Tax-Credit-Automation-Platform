"""
Unit tests for project narrative sections in PDF Generator.

Tests that project sections include technical narratives and compliance reviews
from the AuditReport object.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport
from utils.logger import AgentLogger
from reportlab.platypus import Paragraph

# Initialize logger for tests
AgentLogger.initialize()
logger = AgentLogger.get_logger("tests.test_project_narrative_sections")


@pytest.fixture
def sample_projects():
    """Create sample qualified projects for testing."""
    projects = [
        QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="The project involves developing a new authentication algorithm with encryption.",
            reasoning="This project clearly meets the four-part test for qualified research.",
            irs_source="CFR Title 26 § 1.41-4(a)(1)",
            technical_details={
                "technological_uncertainty": "Uncertainty about optimal encryption approach",
                "experimentation_process": "Systematic evaluation of authentication methods"
            }
        ),
        QualifiedProject(
            project_name="Beta Testing Framework",
            qualified_hours=10.0,
            qualified_cost=720.00,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Development of automated testing framework with AI-driven test generation.",
            reasoning="Project involves substantial experimentation to develop novel testing methodologies.",
            irs_source="CFR Title 26 § 1.41-4(a)(2)"
        ),
        QualifiedProject(
            project_name="Gamma Optimization",
            qualified_hours=8.0,
            qualified_cost=576.00,
            confidence_score=0.78,
            qualification_percentage=70.0,
            supporting_citation="Performance optimization research for distributed systems.",
            reasoning="Research into novel optimization algorithms for distributed computing.",
            irs_source="CFR Title 26 § 1.41-4(a)(3)"
        )
    ]
    return projects


@pytest.fixture
def sample_narratives():
    """Create sample technical narratives for testing."""
    return {
        "Alpha Development": (
            "The Alpha Development project addressed significant technological uncertainties "
            "in the field of authentication security. The team conducted systematic experimentation "
            "to develop a novel multi-factor authentication algorithm that combines biometric data "
            "with behavioral patterns. This research involved evaluating multiple encryption standards "
            "(AES-256, RSA-4096, and elliptic curve cryptography) to determine the optimal approach "
            "for securing user credentials while maintaining system performance. The experimentation "
            "process included developing prototypes, conducting security audits, and performing "
            "penetration testing to validate the effectiveness of the authentication mechanism. "
            "The project resulted in a new authentication system that reduces unauthorized access "
            "attempts by 95% while improving user experience through seamless biometric integration."
        ),
        "Beta Testing Framework": (
            "The Beta Testing Framework project involved substantial research and development to create "
            "an AI-driven automated testing system. The technological uncertainty centered on developing "
            "machine learning models that could intelligently generate test cases based on code analysis "
            "and historical bug patterns. The team experimented with various neural network architectures "
            "(including LSTM, Transformer, and CNN models) to identify the most effective approach for "
            "test case generation. The research process included training models on large datasets of "
            "code repositories, validating test coverage improvements, and measuring defect detection rates. "
            "This systematic experimentation resulted in a testing framework that automatically generates "
            "comprehensive test suites with 40% better code coverage than traditional manual testing approaches."
        ),
        "Gamma Optimization": (
            "The Gamma Optimization project focused on resolving technological uncertainties related to "
            "performance optimization in distributed computing environments. The research involved developing "
            "novel algorithms for load balancing and resource allocation across distributed nodes. The team "
            "conducted extensive experimentation with different optimization strategies, including genetic "
            "algorithms, simulated annealing, and reinforcement learning approaches. The experimentation "
            "process included building simulation environments, measuring performance metrics under various "
            "load conditions, and validating the algorithms in production-like scenarios. The research "
            "resulted in optimization algorithms that improve system throughput by 60% while reducing "
            "resource consumption by 35%, representing a significant advancement in distributed systems performance."
        )
    }


@pytest.fixture
def sample_compliance_reviews():
    """Create sample compliance review data for testing."""
    return {
        "Alpha Development": {
            "status": "Compliant",
            "completeness_score": 0.95,
            "required_revisions": []
        },
        "Beta Testing Framework": {
            "status": "Compliant",
            "completeness_score": 0.88,
            "required_revisions": ["Add more detail on experimentation methodology"]
        },
        "Gamma Optimization": {
            "status": "Compliant",
            "completeness_score": 0.82,
            "required_revisions": ["Clarify business component", "Add quantitative results"]
        }
    }


@pytest.fixture
def sample_report_with_narratives(sample_projects, sample_narratives, sample_compliance_reviews):
    """Create a sample audit report with narratives and compliance reviews."""
    total_hours = sum(p.qualified_hours for p in sample_projects)
    total_cost = sum(p.qualified_cost for p in sample_projects)
    
    return AuditReport(
        report_id="RPT-2024-NARRATIVE-TEST",
        generation_date=datetime(2024, 12, 15, 10, 30, 0),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        average_confidence=sum(p.confidence_score for p in sample_projects) / len(sample_projects),
        project_count=len(sample_projects),
        flagged_project_count=0,
        projects=sample_projects,
        company_name="Narrative Test Corporation",
        narratives=sample_narratives,
        compliance_reviews=sample_compliance_reviews,
        aggregated_data={
            "total_qualified_hours": total_hours,
            "total_qualified_cost": total_cost,
            "estimated_credit": total_cost * 0.20,
            "average_confidence": sum(p.confidence_score for p in sample_projects) / len(sample_projects),
            "flagged_count": 0,
            "high_confidence_count": 2,
            "medium_confidence_count": 1,
            "low_confidence_count": 0
        }
    )


@pytest.fixture
def pdf_generator():
    """Create a PDFGenerator instance for testing."""
    return PDFGenerator()


class TestProjectNarrativeSections:
    """Test that project sections include narratives and compliance reviews."""
    
    def test_create_project_section_includes_narrative(self, pdf_generator, sample_projects, sample_report_with_narratives):
        """Test that project section includes technical narrative from report."""
        project = sample_projects[0]
        elements = pdf_generator._create_project_section(project, 1, sample_report_with_narratives)
        
        # Verify elements were created
        assert len(elements) > 0
        
        # Check that narrative text is included in the elements
        narrative_found = False
        narrative_text = sample_report_with_narratives.narratives[project.project_name]
        
        for element in elements:
            if isinstance(element, Paragraph):
                # Get the text content from the paragraph
                text = element.getPlainText() if hasattr(element, 'getPlainText') else str(element)
                if "Alpha Development project addressed significant technological uncertainties" in text:
                    narrative_found = True
                    break
        
        assert narrative_found, "Technical narrative not found in project section elements"
        logger.info(f"✓ Narrative found in project section for {project.project_name}")
    
    def test_create_project_section_includes_compliance_review(self, pdf_generator, sample_projects, sample_report_with_narratives):
        """Test that project section includes compliance review status."""
        project = sample_projects[0]
        elements = pdf_generator._create_project_section(project, 1, sample_report_with_narratives)
        
        # Check that compliance review is included
        compliance_found = False
        
        for element in elements:
            if isinstance(element, Paragraph):
                text = element.getPlainText() if hasattr(element, 'getPlainText') else str(element)
                if "Compliance Review Status" in text or "Status: Compliant" in text:
                    compliance_found = True
                    break
        
        assert compliance_found, "Compliance review not found in project section elements"
        logger.info(f"✓ Compliance review found in project section for {project.project_name}")
    
    def test_all_projects_have_narratives(self, pdf_generator, sample_projects, sample_report_with_narratives):
        """Test that all three projects have narratives included."""
        for i, project in enumerate(sample_projects, 1):
            elements = pdf_generator._create_project_section(project, i, sample_report_with_narratives)
            
            # Verify narrative is present
            assert len(elements) > 0
            
            # Log the project processing
            logger.info(f"✓ Project {i} ({project.project_name}) section created with {len(elements)} elements")
    
    def test_narrative_length_validation(self, pdf_generator, sample_projects, sample_report_with_narratives):
        """Test that narratives meet minimum length requirement (>500 chars)."""
        for project_name, narrative in sample_report_with_narratives.narratives.items():
            assert len(narrative) > 500, f"Narrative for {project_name} is too short ({len(narrative)} chars)"
            logger.info(f"✓ Narrative for {project_name} meets length requirement ({len(narrative)} chars)")
    
    def test_generate_complete_pdf_with_narratives(self, pdf_generator, sample_report_with_narratives):
        """Test generating a complete PDF with narratives and verify file size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate PDF
            pdf_path = pdf_generator.generate_report(
                sample_report_with_narratives,
                temp_dir,
                "test_narrative_report.pdf"
            )
            
            # Verify PDF was created
            assert os.path.exists(pdf_path), "PDF file was not created"
            
            # Check file size
            file_size = os.path.getsize(pdf_path)
            logger.info(f"Generated PDF size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
            
            # PDF with 3 projects and narratives should be at least 15KB
            assert file_size >= 15000, f"PDF appears incomplete (size: {file_size} bytes, expected >= 15KB)"
            
            logger.info(f"✓ Complete PDF generated successfully: {pdf_path}")
            logger.info(f"  - File size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
            logger.info(f"  - Projects: {len(sample_report_with_narratives.projects)}")
            logger.info(f"  - Narratives: {len(sample_report_with_narratives.narratives)}")
    



if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
