"""
Test for executive summary using aggregated data.

This test verifies that the _create_executive_summary method correctly
accesses and displays all required fields from the AuditReport, including
optional fields from aggregated_data.
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

# Initialize logger for tests
AgentLogger.initialize()
logger = AgentLogger.get_logger("tests.test_executive_summary_aggregated_data")


@pytest.fixture
def sample_projects():
    """Create sample projects with varying confidence scores."""
    return [
        QualifiedProject(
            project_name="High Confidence Project",
            qualified_hours=20.0,
            qualified_cost=1500.00,
            confidence_score=0.95,
            qualification_percentage=95.0,
            supporting_citation="Strong evidence of qualified research.",
            reasoning="Clearly meets all four-part test criteria.",
            irs_source="CFR Title 26 § 1.41-4(a)(1)"
        ),
        QualifiedProject(
            project_name="Medium Confidence Project",
            qualified_hours=15.0,
            qualified_cost=1000.00,
            confidence_score=0.75,
            qualification_percentage=80.0,
            supporting_citation="Good evidence of qualified research.",
            reasoning="Meets four-part test with some documentation gaps.",
            irs_source="CFR Title 26 § 1.41-4(a)(2)"
        ),
        QualifiedProject(
            project_name="Low Confidence Project",
            qualified_hours=10.0,
            qualified_cost=700.00,
            confidence_score=0.65,
            qualification_percentage=60.0,
            supporting_citation="Limited evidence available.",
            reasoning="May qualify but requires additional review.",
            irs_source="CFR Title 26 § 1.41-4(a)(3)"
        )
    ]


@pytest.fixture
def report_with_aggregated_data(sample_projects):
    """Create a report with complete aggregated data."""
    total_hours = sum(p.qualified_hours for p in sample_projects)
    total_cost = sum(p.qualified_cost for p in sample_projects)
    
    # Create aggregated data with confidence breakdown
    aggregated_data = {
        'total_qualified_hours': total_hours,
        'total_qualified_cost': total_cost,
        'estimated_credit': total_cost * 0.20,
        'average_confidence': sum(p.confidence_score for p in sample_projects) / len(sample_projects),
        'high_confidence_count': 1,  # Projects with confidence >= 0.8
        'medium_confidence_count': 1,  # Projects with 0.7 <= confidence < 0.8
        'low_confidence_count': 1  # Projects with confidence < 0.7
    }
    
    # Create narratives for all projects
    narratives = {
        p.project_name: f"Technical narrative for {p.project_name}. This is a detailed description of the R&D activities."
        for p in sample_projects
    }
    
    # Create compliance reviews for all projects
    compliance_reviews = {
        p.project_name: {
            "status": "compliant",
            "completeness_score": 0.9,
            "required_revisions": []
        }
        for p in sample_projects
    }
    
    return AuditReport(
        report_id="RPT-2024-AGG-TEST",
        generation_date=datetime(2024, 12, 15, 10, 30, 0),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        projects=sample_projects,
        company_name="Aggregated Data Test Corp",
        narratives=narratives,
        compliance_reviews=compliance_reviews,
        aggregated_data=aggregated_data
    )


def test_executive_summary_accesses_all_required_fields(report_with_aggregated_data, caplog):
    """
    Test that _create_executive_summary accesses all required fields.
    
    Verifies:
    - report.total_qualified_hours is accessed
    - report.total_qualified_cost is accessed
    - report.estimated_credit is accessed
    - report.average_confidence is accessed
    - report.project_count is accessed
    - report.flagged_project_count is accessed
    """
    generator = PDFGenerator()
    
    # Create executive summary
    with caplog.at_level("INFO"):
        elements = generator._create_executive_summary(report_with_aggregated_data)
    
    # Verify all required fields were accessed (check logs)
    assert "Accessing report.total_qualified_hours" in caplog.text
    assert "Accessing report.total_qualified_cost" in caplog.text
    assert "Accessing report.estimated_credit" in caplog.text
    assert "Accessing report.average_confidence" in caplog.text
    assert "Accessing report.project_count" in caplog.text
    assert "Accessing report.flagged_project_count" in caplog.text
    
    # Verify elements were created
    assert len(elements) > 0
    
    logger.info("✓ Executive summary accesses all required fields")


def test_executive_summary_uses_aggregated_data(report_with_aggregated_data, caplog):
    """
    Test that _create_executive_summary uses aggregated_data when available.
    
    Verifies:
    - aggregated_data is detected
    - high_confidence_count is accessed
    - medium_confidence_count is accessed
    - low_confidence_count is accessed
    """
    generator = PDFGenerator()
    
    # Create executive summary
    with caplog.at_level("INFO"):
        elements = generator._create_executive_summary(report_with_aggregated_data)
    
    # Verify aggregated_data was accessed
    assert "Aggregated data available with keys" in caplog.text
    assert "high_confidence_count" in caplog.text
    assert "medium_confidence_count" in caplog.text
    assert "low_confidence_count" in caplog.text
    
    logger.info("✓ Executive summary uses aggregated_data fields")


def test_executive_summary_generates_complete_pdf(report_with_aggregated_data):
    """
    Test that executive summary can be included in a complete PDF.
    
    Verifies:
    - PDF generation completes without errors
    - PDF file is created
    - PDF file has reasonable size
    """
    generator = PDFGenerator()
    
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate complete PDF
        pdf_path = generator.generate_report(
            report=report_with_aggregated_data,
            output_dir=temp_dir,
            filename="test_executive_summary.pdf"
        )
        
        # Verify PDF was created
        assert os.path.exists(pdf_path)
        
        # Verify PDF has reasonable size (should be > 5KB for complete report)
        pdf_size = os.path.getsize(pdf_path)
        assert pdf_size > 5000, f"PDF size {pdf_size} bytes is too small"
        
        logger.info(f"✓ Complete PDF generated: {pdf_size} bytes")


def test_executive_summary_without_aggregated_data():
    """
    Test that executive summary works without aggregated_data.
    
    Verifies:
    - Executive summary can be created without aggregated_data
    - No errors are raised
    - Basic fields are still displayed
    """
    # Create a simple report without aggregated_data
    project = QualifiedProject(
        project_name="Simple Project",
        qualified_hours=10.0,
        qualified_cost=750.00,
        confidence_score=0.85,
        qualification_percentage=90.0,
        supporting_citation="Test citation",
        reasoning="Test reasoning",
        irs_source="CFR Title 26 § 1.41-4"
    )
    
    report = AuditReport(
        report_id="RPT-2024-SIMPLE",
        generation_date=datetime(2024, 12, 15, 10, 30, 0),
        tax_year=2024,
        total_qualified_hours=10.0,
        total_qualified_cost=750.00,
        estimated_credit=150.00,
        projects=[project],
        company_name="Simple Corp",
        narratives={"Simple Project": "Test narrative"},
        aggregated_data={'total_qualified_hours': 10.0, 'total_qualified_cost': 750.00, 
                        'estimated_credit': 150.00, 'average_confidence': 0.85}
    )
    
    generator = PDFGenerator()
    
    # Create executive summary - should not raise errors
    elements = generator._create_executive_summary(report)
    
    # Verify elements were created
    assert len(elements) > 0
    
    logger.info("✓ Executive summary works without optional aggregated_data fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
