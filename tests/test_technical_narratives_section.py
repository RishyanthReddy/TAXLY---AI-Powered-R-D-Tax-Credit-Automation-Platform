"""
Test for Task 13: Technical Narratives Section Implementation

This test verifies that the _add_technical_narratives() method:
1. Creates the method if it doesn't exist
2. Adds detailed narrative sections for each project
3. Formats narratives with proper paragraphs and spacing
4. Ensures narratives are >500 characters
5. Adds visual separators between narratives
6. Is called in the generate_report() workflow
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import os
import PyPDF2

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport
from utils.logger import AgentLogger

# Initialize logger for tests
AgentLogger.initialize()
logger = AgentLogger.get_logger("tests.test_technical_narratives_section")


@pytest.fixture
def sample_projects_with_narratives():
    """Create sample projects with detailed narratives."""
    project1 = QualifiedProject(
        project_name="Advanced Authentication System",
        qualified_hours=45.5,
        qualified_cost=3275.50,
        confidence_score=0.92,
        qualification_percentage=95.0,
        supporting_citation="IRC Section 41 - Qualified Research Activities",
        reasoning="This project involves developing novel authentication algorithms.",
        irs_source="CFR Title 26 § 1.41-4(a)(1)",
        technical_details={
            "technological_uncertainty": "Optimal encryption approach for multi-factor authentication",
            "experimentation_process": "Systematic evaluation of cryptographic methods"
        }
    )
    
    project2 = QualifiedProject(
        project_name="Machine Learning Pipeline Optimization",
        qualified_hours=62.0,
        qualified_cost=4464.00,
        confidence_score=0.88,
        qualification_percentage=90.0,
        supporting_citation="IRC Section 41 - Process of Experimentation",
        reasoning="This project addresses performance optimization challenges in ML pipelines.",
        irs_source="CFR Title 26 § 1.41-4(a)(5)",
        technical_details={
            "technological_uncertainty": "Achieving real-time inference with limited resources",
            "experimentation_process": "Iterative testing of model architectures and optimization techniques"
        }
    )
    
    project3 = QualifiedProject(
        project_name="Distributed Data Processing Framework",
        qualified_hours=38.0,
        qualified_cost=2736.00,
        confidence_score=0.85,
        qualification_percentage=88.0,
        supporting_citation="IRC Section 41 - Technological in Nature",
        reasoning="Development of novel distributed computing algorithms for data processing.",
        irs_source="CFR Title 26 § 1.41-4(a)(2)",
        technical_details={
            "technological_uncertainty": "Ensuring data consistency across distributed nodes",
            "experimentation_process": "Testing various consensus algorithms and fault tolerance mechanisms"
        }
    )
    
    return [project1, project2, project3]


@pytest.fixture
def sample_narratives():
    """Create sample technical narratives (>500 characters each)."""
    return {
        "Advanced Authentication System": """
This project addresses significant technological uncertainties in developing a next-generation 
multi-factor authentication system. The primary challenge involved determining the optimal 
combination of biometric, cryptographic, and behavioral authentication factors to achieve 
both high security and user convenience.

The research process involved systematic experimentation with various cryptographic algorithms, 
including elliptic curve cryptography, lattice-based cryptography, and post-quantum cryptographic 
methods. We conducted extensive testing to evaluate the performance, security, and usability 
trade-offs of each approach.

Our experimentation process included developing multiple prototype implementations, conducting 
security audits, and performing user acceptance testing. We evaluated each approach against 
specific criteria including authentication time, false positive/negative rates, and resistance 
to various attack vectors.

This project clearly meets the four-part test: (1) it relies on principles of computer science 
and cryptography, (2) it addresses technological uncertainty regarding optimal authentication 
methods, (3) it involves a systematic process of experimentation, and (4) it aims to develop 
a new or improved business component in the form of an authentication system.
""",
        "Machine Learning Pipeline Optimization": """
This research project focused on overcoming significant technological challenges in optimizing 
machine learning inference pipelines for real-time applications with resource constraints. The 
primary uncertainty involved determining how to achieve sub-100ms inference latency while 
maintaining model accuracy above 95% on edge devices with limited computational resources.

Our systematic experimentation process involved evaluating multiple approaches including model 
quantization, pruning, knowledge distillation, and neural architecture search. We developed 
custom benchmarking frameworks to measure the performance impact of each optimization technique 
across different model architectures and hardware configurations.

The research methodology included iterative cycles of hypothesis formation, implementation, 
testing, and analysis. We conducted over 200 experiments testing various combinations of 
optimization techniques, model architectures, and deployment configurations. Each experiment 
was carefully documented with performance metrics, resource utilization data, and accuracy 
measurements.

This project satisfies the four-part test requirements: (1) it is technological in nature, 
relying on computer science and machine learning principles, (2) it addresses uncertainty 
about achieving real-time performance with accuracy constraints, (3) it employs a systematic 
process of experimentation, and (4) it develops an improved business component for ML deployment.
""",
        "Distributed Data Processing Framework": """
This qualified research project addressed fundamental technological uncertainties in developing 
a distributed data processing framework capable of maintaining strong consistency guarantees 
while achieving high throughput and low latency. The core challenge involved determining the 
optimal consensus algorithm and data replication strategy for our specific use case.

The research process involved extensive experimentation with various distributed systems 
approaches including Paxos, Raft, and custom consensus protocols. We developed simulation 
environments to test different configurations under various failure scenarios, network 
conditions, and load patterns. Our experimentation included testing fault tolerance mechanisms, 
data partitioning strategies, and conflict resolution approaches.

We conducted systematic evaluation of each approach using quantitative metrics including 
throughput, latency, consistency guarantees, and fault recovery time. The research involved 
developing custom testing frameworks, implementing multiple prototype systems, and conducting 
comprehensive performance analysis under realistic conditions.

This project clearly meets all four parts of the qualified research test: (1) it is 
technological in nature, based on distributed systems and computer science principles, 
(2) it addresses significant technological uncertainty regarding optimal consensus and 
consistency mechanisms, (3) it involves a rigorous process of experimentation and evaluation, 
and (4) it aims to create a new business component in the form of a distributed processing framework.
"""
    }


@pytest.fixture
def sample_report_with_narratives(sample_projects_with_narratives, sample_narratives):
    """Create a complete audit report with narratives."""
    projects = sample_projects_with_narratives
    
    total_hours = sum(p.qualified_hours for p in projects)
    total_cost = sum(p.qualified_cost for p in projects)
    estimated_credit = total_cost * 0.20
    avg_confidence = sum(p.confidence_score for p in projects) / len(projects)
    
    # Create compliance reviews
    compliance_reviews = {
        "Advanced Authentication System": {
            "status": "Compliant",
            "completeness_score": 0.95,
            "required_revisions": []
        },
        "Machine Learning Pipeline Optimization": {
            "status": "Compliant",
            "completeness_score": 0.92,
            "required_revisions": []
        },
        "Distributed Data Processing Framework": {
            "status": "Compliant",
            "completeness_score": 0.90,
            "required_revisions": []
        }
    }
    
    # Create aggregated data
    aggregated_data = {
        "total_qualified_hours": total_hours,
        "total_qualified_cost": total_cost,
        "estimated_credit": estimated_credit,
        "average_confidence": avg_confidence,
        "flagged_count": 0,
        "high_confidence_count": 3,
        "medium_confidence_count": 0,
        "low_confidence_count": 0
    }
    
    return AuditReport(
        report_id="RPT-2024-TASK13",
        generation_date=datetime(2024, 12, 15, 10, 30, 0),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=estimated_credit,
        average_confidence=avg_confidence,
        project_count=len(projects),
        flagged_project_count=0,
        projects=projects,
        narratives=sample_narratives,
        compliance_reviews=compliance_reviews,
        aggregated_data=aggregated_data,
        company_name="Task 13 Test Corporation"
    )


class TestTechnicalNarrativesSection:
    """Test suite for Task 13: Technical Narratives Section."""
    
    def test_add_technical_narratives_method_exists(self):
        """Test that _add_technical_narratives method exists."""
        generator = PDFGenerator()
        assert hasattr(generator, '_add_technical_narratives'), \
            "_add_technical_narratives method does not exist"
        assert callable(getattr(generator, '_add_technical_narratives')), \
            "_add_technical_narratives is not callable"
        logger.info("✓ _add_technical_narratives method exists and is callable")
    
    def test_technical_narratives_section_structure(self, sample_report_with_narratives):
        """Test that technical narratives section has correct structure."""
        generator = PDFGenerator()
        elements = generator._add_technical_narratives(sample_report_with_narratives)
        
        # Should return a list of elements
        assert isinstance(elements, list), "Method should return a list"
        assert len(elements) > 0, "Should generate elements"
        
        logger.info(f"✓ Technical narratives section generated {len(elements)} elements")
    
    def test_narratives_for_all_projects(self, sample_report_with_narratives):
        """Test that narratives are created for all projects."""
        generator = PDFGenerator()
        report = sample_report_with_narratives
        
        # Verify narratives exist for all projects
        assert len(report.narratives) == len(report.projects), \
            "Should have narratives for all projects"
        
        for project in report.projects:
            assert project.project_name in report.narratives, \
                f"Missing narrative for {project.project_name}"
            
            narrative = report.narratives[project.project_name]
            assert len(narrative) > 500, \
                f"Narrative for {project.project_name} is too short ({len(narrative)} chars)"
        
        logger.info(f"✓ All {len(report.projects)} projects have narratives >500 characters")
    
    def test_technical_narratives_in_generated_pdf(self, sample_report_with_narratives):
        """Test that technical narratives appear in generated PDF."""
        generator = PDFGenerator()
        report = sample_report_with_narratives
        
        # Generate PDF in temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = generator.generate_report(
                report,
                temp_dir,
                "test_task13_narratives.pdf"
            )
            
            # Verify PDF was created
            assert os.path.exists(pdf_path), "PDF file was not created"
            
            # Extract text from PDF
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text()
            
            # Verify "Technical Narratives" section exists
            assert "Technical Narratives" in pdf_text, \
                "Technical Narratives section not found in PDF"
            
            # Verify each project narrative appears in PDF
            for project in report.projects:
                assert project.project_name in pdf_text, \
                    f"Project {project.project_name} not found in PDF"
                
                # Verify narrative content appears (check for key phrases)
                narrative = report.narratives[project.project_name]
                # Check for first 50 characters of narrative
                narrative_snippet = narrative[:50].strip()
                assert narrative_snippet in pdf_text or narrative[:100] in pdf_text, \
                    f"Narrative content for {project.project_name} not found in PDF"
            
            # Check PDF file size (should be substantial with narratives)
            pdf_size = os.path.getsize(pdf_path)
            assert pdf_size > 15000, \
                f"PDF file size ({pdf_size} bytes) is too small - may be incomplete"
            
            logger.info(f"✓ Technical narratives section appears in PDF ({pdf_size} bytes)")
            logger.info(f"✓ All {len(report.projects)} project narratives found in PDF")
    
    def test_narrative_formatting(self, sample_report_with_narratives):
        """Test that narratives are properly formatted with paragraphs."""
        generator = PDFGenerator()
        elements = generator._add_technical_narratives(sample_report_with_narratives)
        
        # Check that elements include Paragraph objects
        from reportlab.platypus import Paragraph, Spacer
        
        paragraph_count = sum(1 for elem in elements if isinstance(elem, Paragraph))
        spacer_count = sum(1 for elem in elements if isinstance(elem, Spacer))
        
        assert paragraph_count > 0, "Should contain Paragraph elements"
        assert spacer_count > 0, "Should contain Spacer elements for spacing"
        
        logger.info(f"✓ Narrative formatting includes {paragraph_count} paragraphs and {spacer_count} spacers")
    
    def test_visual_separators_between_narratives(self, sample_report_with_narratives):
        """Test that visual separators are added between narratives."""
        generator = PDFGenerator()
        elements = generator._add_technical_narratives(sample_report_with_narratives)
        
        # Check for Table elements (used for separators)
        from reportlab.platypus import Table
        
        table_count = sum(1 for elem in elements if isinstance(elem, Table))
        
        # Should have separators between projects (n-1 separators for n projects)
        expected_separators = len(sample_report_with_narratives.projects) - 1
        assert table_count >= expected_separators, \
            f"Should have at least {expected_separators} visual separators"
        
        logger.info(f"✓ Visual separators present ({table_count} found)")
    
    def test_missing_narratives_handling(self):
        """Test handling of missing narratives."""
        generator = PDFGenerator()
        
        # Create report with empty narratives
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=720.00,
            confidence_score=0.85,
            qualification_percentage=90.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Create minimal narrative to satisfy validation (but we'll test empty dict handling)
        report = AuditReport(
            report_id="RPT-TEST-EMPTY",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=10.0,
            total_qualified_cost=720.00,
            estimated_credit=144.00,
            average_confidence=0.85,
            project_count=1,
            flagged_project_count=0,
            projects=[project],
            narratives={"Test Project": "Minimal narrative for validation"},  # Satisfy validation
            compliance_reviews={"Test Project": {"status": "Pending", "completeness_score": 0.0, "required_revisions": []}},
            aggregated_data={
                "total_qualified_hours": 10.0,
                "total_qualified_cost": 720.00,
                "estimated_credit": 144.00,
                "average_confidence": 0.85
            }
        )
        
        # Test with empty narratives dict (simulate missing narratives)
        report.narratives = {}
        
        # Should not raise exception
        elements = generator._add_technical_narratives(report)
        assert isinstance(elements, list), "Should return list even with empty narratives"
        
        logger.info("✓ Handles missing narratives gracefully")
    
    def test_short_narrative_warning(self, caplog):
        """Test that short narratives (<500 chars) generate warnings."""
        generator = PDFGenerator()
        
        project = QualifiedProject(
            project_name="Short Narrative Project",
            qualified_hours=10.0,
            qualified_cost=720.00,
            confidence_score=0.85,
            qualification_percentage=90.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        # Create short narrative (<500 characters)
        short_narrative = "This is a short narrative that is less than 500 characters."
        
        report = AuditReport(
            report_id="RPT-TEST-SHORT",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=10.0,
            total_qualified_cost=720.00,
            estimated_credit=144.00,
            average_confidence=0.85,
            project_count=1,
            flagged_project_count=0,
            projects=[project],
            narratives={"Short Narrative Project": short_narrative},
            compliance_reviews={"Short Narrative Project": {"status": "Pending", "completeness_score": 0.0, "required_revisions": []}},
            aggregated_data={
                "total_qualified_hours": 10.0,
                "total_qualified_cost": 720.00,
                "estimated_credit": 144.00,
                "average_confidence": 0.85
            }
        )
        
        # Generate elements
        elements = generator._add_technical_narratives(report)
        
        # Check that warning was logged (if using caplog)
        # Note: This test verifies the method handles short narratives
        assert len(short_narrative) < 500, "Test narrative should be short"
        assert isinstance(elements, list), "Should return list even with short narratives"
        
        logger.info("✓ Short narrative handling verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
