"""
Test PDF Generator Validation for Complete AuditReport.

This test verifies that the PDFGenerator validates AuditReport completeness
and raises appropriate exceptions when required fields are missing or None.

This implements Task 9 from the pipeline-fix spec.
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import AuditReport, QualifiedProject
from utils.logger import AgentLogger

# Initialize logger for tests
AgentLogger.initialize()
logger = AgentLogger.get_logger("tests.test_pdf_generator_validation")


@pytest.fixture
def pdf_generator():
    """Create a PDFGenerator instance for testing."""
    return PDFGenerator()


@pytest.fixture
def sample_project():
    """Create a sample qualified project for testing."""
    return QualifiedProject(
        project_name="API Development",
        qualified_hours=50.0,
        qualified_cost=3600.0,
        qualification_percentage=100.0,
        confidence_score=0.85,
        estimated_credit=720.0,
        reasoning="Developing new REST API endpoints with novel algorithms",
        irs_source="IRC Section 41(d)(1)",
        supporting_citation="Qualified research activities under the four-part test",
        flagged_for_review=False
    )


@pytest.fixture
def complete_report(sample_project):
    """Create a complete AuditReport with all required fields."""
    return AuditReport(
        report_id="TEST-2024-001",
        generation_date=datetime.now(),
        tax_year=2024,
        company_name="Test Corporation",
        total_qualified_hours=50.0,
        total_qualified_cost=3600.0,
        estimated_credit=720.0,
        average_confidence=0.85,
        project_count=1,
        flagged_project_count=0,
        projects=[sample_project],
        narratives={
            "API Development": "This project involved developing new REST API endpoints..."
        },
        compliance_reviews={
            "API Development": {
                "status": "Compliant",
                "completeness_score": 0.95,
                "required_revisions": []
            }
        },
        aggregated_data={
            "total_qualified_hours": 50.0,
            "total_qualified_cost": 3600.0,
            "estimated_credit": 720.0,
            "average_confidence": 0.85,
            "flagged_count": 0
        }
    )


def test_pdf_generator_validates_narratives_field_missing(pdf_generator, sample_project):
    """
    Test that PDFGenerator raises ValueError when narratives field is missing.
    
    Requirement: Task 9 - Verify report.narratives is not None
    """
    # Create report without narratives field (by using a mock object)
    class IncompleteReport:
        def __init__(self):
            self.report_id = "TEST-2024-001"
            self.generation_date = datetime.now()
            self.tax_year = 2024
            self.company_name = "Test Corporation"
            self.total_qualified_hours = 50.0
            self.total_qualified_cost = 3600.0
            self.estimated_credit = 720.0
            self.average_confidence = 0.85
            self.project_count = 1
            self.flagged_project_count = 0
            self.projects = [sample_project]
            self.compliance_reviews = {}
            self.aggregated_data = {}
            # Missing: narratives
    
    report = IncompleteReport()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(ValueError) as exc_info:
            pdf_generator.generate_report(report, tmp_dir)
        
        # Verify error message mentions missing narratives
        assert "narratives" in str(exc_info.value).lower()
        assert "incomplete" in str(exc_info.value).lower()
        
        logger.info("✓ Test passed: ValueError raised for missing narratives field")


def test_pdf_generator_validates_narratives_field_none(pdf_generator, sample_project):
    """
    Test that PDFGenerator raises ValueError when narratives field is None.
    
    Requirement: Task 9 - Verify report.narratives is not None
    
    Note: AuditReport model has Pydantic validators that prevent None values,
    so we use a mock object to test the PDF generator's validation layer.
    """
    # Create mock report with narratives=None to test PDF generator validation
    class MockReport:
        def __init__(self):
            self.report_id = "TEST-2024-001"
            self.generation_date = datetime.now()
            self.tax_year = 2024
            self.company_name = "Test Corporation"
            self.total_qualified_hours = 50.0
            self.total_qualified_cost = 3600.0
            self.estimated_credit = 720.0
            self.average_confidence = 0.85
            self.project_count = 1
            self.flagged_project_count = 0
            self.projects = [sample_project]
            self.narratives = None  # Explicitly None
            self.compliance_reviews = {}
            self.aggregated_data = {}
    
    report = MockReport()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(ValueError) as exc_info:
            pdf_generator.generate_report(report, tmp_dir)
        
        # Verify error message mentions narratives is None
        assert "narratives" in str(exc_info.value).lower()
        assert "none" in str(exc_info.value).lower() or "incomplete" in str(exc_info.value).lower()
        
        logger.info("✓ Test passed: ValueError raised for narratives=None")


def test_pdf_generator_validates_compliance_reviews_field_none(pdf_generator, sample_project):
    """
    Test that PDFGenerator raises ValueError when compliance_reviews field is None.
    
    Requirement: Task 9 - Verify report.compliance_reviews is not None
    
    Note: Using mock object to test PDF generator's validation layer.
    """
    # Create mock report with compliance_reviews=None
    class MockReport:
        def __init__(self):
            self.report_id = "TEST-2024-001"
            self.generation_date = datetime.now()
            self.tax_year = 2024
            self.company_name = "Test Corporation"
            self.total_qualified_hours = 50.0
            self.total_qualified_cost = 3600.0
            self.estimated_credit = 720.0
            self.average_confidence = 0.85
            self.project_count = 1
            self.flagged_project_count = 0
            self.projects = [sample_project]
            self.narratives = {"API Development": "Test narrative"}
            self.compliance_reviews = None  # Explicitly None
            self.aggregated_data = {
                "total_qualified_hours": 50.0,
                "total_qualified_cost": 3600.0,
                "estimated_credit": 720.0,
                "average_confidence": 0.85
            }
    
    report = MockReport()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(ValueError) as exc_info:
            pdf_generator.generate_report(report, tmp_dir)
        
        # Verify error message mentions compliance_reviews
        assert "compliance_reviews" in str(exc_info.value).lower()
        
        logger.info("✓ Test passed: ValueError raised for compliance_reviews=None")


def test_pdf_generator_validates_aggregated_data_field_none(pdf_generator, sample_project):
    """
    Test that PDFGenerator raises ValueError when aggregated_data field is None.
    
    Requirement: Task 9 - Verify report.aggregated_data is not None
    
    Note: Using mock object to test PDF generator's validation layer.
    """
    # Create mock report with aggregated_data=None
    class MockReport:
        def __init__(self):
            self.report_id = "TEST-2024-001"
            self.generation_date = datetime.now()
            self.tax_year = 2024
            self.company_name = "Test Corporation"
            self.total_qualified_hours = 50.0
            self.total_qualified_cost = 3600.0
            self.estimated_credit = 720.0
            self.average_confidence = 0.85
            self.project_count = 1
            self.flagged_project_count = 0
            self.projects = [sample_project]
            self.narratives = {"API Development": "Test narrative"}
            self.compliance_reviews = {}
            self.aggregated_data = None  # Explicitly None
    
    report = MockReport()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(ValueError) as exc_info:
            pdf_generator.generate_report(report, tmp_dir)
        
        # Verify error message mentions aggregated_data
        assert "aggregated_data" in str(exc_info.value).lower()
        
        logger.info("✓ Test passed: ValueError raised for aggregated_data=None")


def test_pdf_generator_validates_multiple_missing_fields(pdf_generator, sample_project):
    """
    Test that PDFGenerator raises ValueError listing all missing fields.
    
    Requirement: Task 9 - If any field is None, log error and raise exception
    
    Note: Using mock object to test PDF generator's validation layer.
    """
    # Create mock report with multiple None fields
    class MockReport:
        def __init__(self):
            self.report_id = "TEST-2024-001"
            self.generation_date = datetime.now()
            self.tax_year = 2024
            self.company_name = "Test Corporation"
            self.total_qualified_hours = 50.0
            self.total_qualified_cost = 3600.0
            self.estimated_credit = 720.0
            self.average_confidence = 0.85
            self.project_count = 1
            self.flagged_project_count = 0
            self.projects = [sample_project]
            self.narratives = None  # None
            self.compliance_reviews = None  # None
            self.aggregated_data = None  # None
    
    report = MockReport()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(ValueError) as exc_info:
            pdf_generator.generate_report(report, tmp_dir)
        
        error_msg = str(exc_info.value).lower()
        
        # Verify error message mentions all three missing fields
        assert "narratives" in error_msg
        assert "compliance_reviews" in error_msg
        assert "aggregated_data" in error_msg
        
        logger.info("✓ Test passed: ValueError raised listing all missing fields")


def test_pdf_generator_accepts_complete_report(pdf_generator, complete_report):
    """
    Test that PDFGenerator accepts a complete AuditReport with all required fields.
    
    Requirement: Task 9 - Validation should pass for complete reports
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Should not raise any exception
        pdf_path = pdf_generator.generate_report(complete_report, tmp_dir)
        
        # Verify PDF was created
        assert Path(pdf_path).exists()
        assert Path(pdf_path).stat().st_size > 0
        
        logger.info("✓ Test passed: Complete report accepted and PDF generated")


def test_pdf_generator_logs_validation_errors(pdf_generator, sample_project, caplog):
    """
    Test that PDFGenerator logs validation errors before raising exception.
    
    Requirement: Task 9 - Log error if any field is None
    
    Note: Using mock object to test PDF generator's validation layer.
    """
    import logging
    caplog.set_level(logging.ERROR)
    
    # Create mock report with None fields
    class MockReport:
        def __init__(self):
            self.report_id = "TEST-2024-001"
            self.generation_date = datetime.now()
            self.tax_year = 2024
            self.company_name = "Test Corporation"
            self.total_qualified_hours = 50.0
            self.total_qualified_cost = 3600.0
            self.estimated_credit = 720.0
            self.average_confidence = 0.85
            self.project_count = 1
            self.flagged_project_count = 0
            self.projects = [sample_project]
            self.narratives = None
            self.compliance_reviews = None
            self.aggregated_data = None
    
    report = MockReport()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(ValueError):
            pdf_generator.generate_report(report, tmp_dir)
        
        # Verify errors were logged
        log_text = caplog.text.lower()
        assert "validation failed" in log_text or "narratives" in log_text
        
        logger.info("✓ Test passed: Validation errors logged correctly")


if __name__ == "__main__":
    # Run tests
    print("=" * 80)
    print("Running PDF Generator Validation Tests (Task 9)")
    print("=" * 80)
    
    pytest.main([__file__, "-v", "-s"])
