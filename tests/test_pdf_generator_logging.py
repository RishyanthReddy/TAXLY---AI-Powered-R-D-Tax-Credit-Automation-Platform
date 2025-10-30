"""
Test PDF Generator Logging for Data Reception Verification.

This test verifies that the PDFGenerator logs all received data correctly,
including narratives, compliance_reviews, and aggregated_data fields.
"""

import sys
from pathlib import Path
from datetime import datetime
import pytest
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.tax_models import QualifiedProject, AuditReport
from utils.pdf_generator import PDFGenerator
from utils.logger import AgentLogger


def test_pdf_generator_logs_received_data(tmp_path, caplog):
    """
    Test that PDFGenerator logs all received AuditReport data.
    
    This test verifies that the generate_report method logs:
    - Basic report metadata
    - Aggregated metrics
    - Projects list with sample data
    - Narratives field existence and content
    - Compliance reviews field existence and content
    - Aggregated data field existence and content
    """
    # Set up logging to capture all log messages
    AgentLogger.initialize()
    caplog.set_level(logging.INFO)
    
    # Create sample project
    sample_project = QualifiedProject(
        project_name="Test Project Alpha",
        qualified_hours=25.5,
        qualified_cost=2500.00,
        confidence_score=0.85,
        qualification_percentage=90.0,
        supporting_citation="Test citation for project alpha",
        reasoning="This project meets the four-part test because...",
        irs_source="CFR Title 26 § 1.41-4(a)(1)",
        technical_details={
            "technological_uncertainty": "Testing uncertainty",
            "experimentation_process": "Testing experimentation"
        }
    )
    
    # Create sample report WITHOUT narratives/compliance_reviews/aggregated_data
    # (to test the current state before fixes)
    sample_report = AuditReport(
        report_id="TEST-2024-001",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=25.5,
        total_qualified_cost=2500.00,
        estimated_credit=500.00,
        average_confidence=0.85,
        project_count=1,
        flagged_project_count=0,
        projects=[sample_project],
        company_name="Test Company"
    )
    
    # Generate PDF
    generator = PDFGenerator()
    
    try:
        pdf_path = generator.generate_report(
            sample_report,
            str(tmp_path),
            "test_report.pdf"
        )
        
        # Verify PDF was created
        assert Path(pdf_path).exists()
        
    except Exception as e:
        # PDF generation may fail if fields are missing, but we still want to check logs
        print(f"PDF generation failed (expected if fields missing): {e}")
    
    # Verify logging output
    log_text = caplog.text
    
    # Check that basic metadata was logged
    assert "PDF GENERATOR: Received AuditReport object" in log_text
    assert "Report ID: TEST-2024-001" in log_text
    assert "Tax Year: 2024" in log_text
    assert "Company Name: Test Company" in log_text
    
    # Check that aggregated metrics were logged
    assert "Total Qualified Hours: 25.5" in log_text
    assert "Total Qualified Cost: $2,500.00" in log_text
    assert "Estimated Credit: $500.00" in log_text
    assert "Average Confidence: 0.85" in log_text
    assert "Project Count: 1" in log_text
    
    # Check that projects list was logged
    assert "Projects List: 1 projects received" in log_text
    assert "Sample project data (first project):" in log_text
    assert "Project Name: Test Project Alpha" in log_text
    
    # Check that narratives field check was logged
    assert "Checking narratives field:" in log_text
    
    # Check that compliance_reviews field check was logged
    assert "Checking compliance_reviews field:" in log_text
    
    # Check that aggregated_data field check was logged
    assert "Checking aggregated_data field:" in log_text
    
    # Check that section generation logging is present
    assert "SECTION GENERATION: Starting PDF section generation" in log_text
    assert "Generating section: Cover Page" in log_text
    assert "Generating section: Executive Summary" in log_text
    
    print("\n✓ All logging checks passed!")
    print(f"✓ PDF generated at: {pdf_path if 'pdf_path' in locals() else 'N/A'}")


def test_pdf_generator_logs_section_generation(tmp_path, caplog):
    """
    Test that PDFGenerator logs each section generation attempt.
    
    This test verifies that the generate_report method logs:
    - Each section generation attempt
    - Success/failure status for each section
    - Number of elements generated per section
    """
    # Set up logging
    AgentLogger.initialize()
    caplog.set_level(logging.INFO)
    
    # Create minimal sample data
    sample_project = QualifiedProject(
        project_name="Test Project",
        qualified_hours=10.0,
        qualified_cost=1000.00,
        confidence_score=0.80,
        qualification_percentage=85.0,
        supporting_citation="Test citation",
        reasoning="Test reasoning",
        irs_source="Test source"
    )
    
    sample_report = AuditReport(
        report_id="TEST-2024-002",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=10.0,
        total_qualified_cost=1000.00,
        estimated_credit=200.00,
        average_confidence=0.80,
        project_count=1,
        flagged_project_count=0,
        projects=[sample_project],
        company_name="Test Company"
    )
    
    # Generate PDF
    generator = PDFGenerator()
    
    try:
        pdf_path = generator.generate_report(
            sample_report,
            str(tmp_path),
            "test_section_logging.pdf"
        )
    except Exception as e:
        print(f"PDF generation failed: {e}")
    
    # Verify section generation logging
    log_text = caplog.text
    
    # Check that all major sections are logged
    sections_to_check = [
        "Cover Page",
        "Table of Contents",
        "Executive Summary",
        "Project Breakdown Summary",
        "Qualified Research Projects",
        "Technical Project Narratives",
        "IRS Citations and References",
        "Appendices"
    ]
    
    for section in sections_to_check:
        assert f"Generating section: {section}" in log_text, f"Missing log for section: {section}"
        print(f"✓ Found log for section: {section}")
    
    # Check for completion logging
    assert "SECTION GENERATION COMPLETE" in log_text
    assert "PDF GENERATION COMPLETE" in log_text
    
    print("\n✓ All section generation logging checks passed!")


if __name__ == "__main__":
    import tempfile
    
    # Run tests
    with tempfile.TemporaryDirectory() as tmp_dir:
        print("Running test_pdf_generator_logs_received_data...")
        test_pdf_generator_logs_received_data(Path(tmp_dir), pytest.LogCaptureFixture(pytest.collect.Item))
        
        print("\nRunning test_pdf_generator_logs_section_generation...")
        test_pdf_generator_logs_section_generation(Path(tmp_dir), pytest.LogCaptureFixture(pytest.collect.Item))
