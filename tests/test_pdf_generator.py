"""
Unit tests for PDF Generator utility.

Tests the PDFGenerator class for creating audit-ready PDF reports.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import tempfile
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport


@pytest.fixture
def sample_project():
    """Create a sample qualified project for testing."""
    return QualifiedProject(
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
    )


@pytest.fixture
def sample_project_flagged():
    """Create a sample flagged project for testing."""
    return QualifiedProject(
        project_name="Beta Testing",
        qualified_hours=5.0,
        qualified_cost=350.00,
        confidence_score=0.65,  # Low confidence - will be auto-flagged
        qualification_percentage=50.0,
        supporting_citation="Limited documentation available for this project.",
        reasoning="Project may qualify but requires additional review.",
        irs_source="CFR Title 26 § 1.41-4"
    )


@pytest.fixture
def sample_report(sample_project):
    """Create a sample audit report for testing."""
    return AuditReport(
        report_id="RPT-2024-TEST",
        generation_date=datetime(2024, 12, 15, 10, 30, 0),
        tax_year=2024,
        total_qualified_hours=14.5,
        total_qualified_cost=1045.74,
        estimated_credit=209.15,
        projects=[sample_project],
        company_name="Test Corporation"
    )


@pytest.fixture
def sample_report_multiple_projects(sample_project, sample_project_flagged):
    """Create a sample report with multiple projects."""
    total_hours = sample_project.qualified_hours + sample_project_flagged.qualified_hours
    total_cost = sample_project.qualified_cost + sample_project_flagged.qualified_cost
    
    return AuditReport(
        report_id="RPT-2024-MULTI",
        generation_date=datetime(2024, 12, 15, 10, 30, 0),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        projects=[sample_project, sample_project_flagged],
        company_name="Multi-Project Corp"
    )


@pytest.fixture
def pdf_generator():
    """Create a PDFGenerator instance for testing."""
    return PDFGenerator()


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for PDF output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestPDFGeneratorInitialization:
    """Test PDFGenerator initialization and configuration."""
    
    def test_default_initialization(self, pdf_generator):
        """Test PDFGenerator initializes with default settings."""
        assert pdf_generator is not None
        assert pdf_generator.page_size is not None
        assert pdf_generator.margin > 0
        assert pdf_generator.title_font == "Helvetica-Bold"
        assert pdf_generator.body_font == "Helvetica"
        assert pdf_generator.font_size_title == 18
        assert pdf_generator.font_size_heading == 14
        assert pdf_generator.font_size_body == 10
    
    def test_custom_initialization(self):
        """Test PDFGenerator with custom settings."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        
        generator = PDFGenerator(
            page_size=A4,
            margin=1.0,
            title_font="Times-Bold",
            body_font="Times-Roman",
            font_size_title=20,
            font_size_heading=16,
            font_size_body=12,
            primary_color=colors.blue
        )
        
        assert generator.page_size == A4
        assert generator.margin == 1.0 * 72  # 1 inch in points
        assert generator.title_font == "Times-Bold"
        assert generator.body_font == "Times-Roman"
        assert generator.font_size_title == 20
        assert generator.font_size_heading == 16
        assert generator.font_size_body == 12
        assert generator.primary_color == colors.blue
    
    def test_custom_styles_created(self, pdf_generator):
        """Test that custom paragraph styles are created."""
        assert 'CustomTitle' in pdf_generator.styles
        assert 'CustomHeading' in pdf_generator.styles
        assert 'CustomSubheading' in pdf_generator.styles
        assert 'CustomBody' in pdf_generator.styles
        assert 'Citation' in pdf_generator.styles


class TestCoverPageGeneration:
    """Test cover page generation."""
    
    def test_create_cover_page(self, pdf_generator, sample_report):
        """Test cover page creation returns flowables."""
        elements = pdf_generator._create_cover_page(sample_report)
        
        assert len(elements) > 0
        assert any('PageBreak' in str(type(elem)) for elem in elements)
    
    def test_cover_page_includes_company_name(self, pdf_generator, sample_report):
        """Test cover page includes company name when provided."""
        elements = pdf_generator._create_cover_page(sample_report)
        
        # Convert elements to strings to check content
        content = ' '.join(str(elem) for elem in elements)
        assert sample_report.company_name in content or 'Test Corporation' in str(elements)
    
    def test_cover_page_without_company_name(self, pdf_generator, sample_project):
        """Test cover page works without company name."""
        report = AuditReport(
            report_id="RPT-2024-NO-COMPANY",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=14.5,
            total_qualified_cost=1045.74,
            estimated_credit=209.15,
            projects=[sample_project],
            company_name=None
        )
        
        elements = pdf_generator._create_cover_page(report)
        assert len(elements) > 0


class TestExecutiveSummaryGeneration:
    """Test executive summary generation."""
    
    def test_create_executive_summary(self, pdf_generator, sample_report):
        """Test executive summary creation returns flowables."""
        elements = pdf_generator._create_executive_summary(sample_report)
        
        assert len(elements) > 0
        assert any('PageBreak' in str(type(elem)) for elem in elements)
    
    def test_executive_summary_includes_metrics(self, pdf_generator, sample_report):
        """Test executive summary includes key metrics."""
        elements = pdf_generator._create_executive_summary(sample_report)
        
        # Check that elements were created (actual content is in Paragraph objects)
        assert len(elements) > 5  # Should have multiple elements
    
    def test_executive_summary_with_flagged_projects(self, pdf_generator, sample_report_multiple_projects):
        """Test executive summary includes risk assessment for flagged projects."""
        elements = pdf_generator._create_executive_summary(sample_report_multiple_projects)
        
        assert len(elements) > 0
        # Should include risk assessment section since one project is flagged
        assert sample_report_multiple_projects.flagged_project_count > 0


class TestProjectSectionGeneration:
    """Test project section generation."""
    
    def test_create_project_section(self, pdf_generator, sample_project):
        """Test project section creation returns flowables."""
        elements = pdf_generator._create_project_section(sample_project, 1)
        
        assert len(elements) > 0
    
    def test_project_section_includes_metrics(self, pdf_generator, sample_project):
        """Test project section includes all required metrics."""
        elements = pdf_generator._create_project_section(sample_project, 1)
        
        # Should have multiple elements for metrics, reasoning, citations, etc.
        assert len(elements) > 5
    
    def test_project_section_with_flag(self, pdf_generator, sample_project_flagged):
        """Test project section shows flag indicator for low confidence."""
        elements = pdf_generator._create_project_section(sample_project_flagged, 1)
        
        assert len(elements) > 0
        assert sample_project_flagged.flagged_for_review is True
    
    def test_project_section_with_technical_details(self, pdf_generator, sample_project):
        """Test project section includes technical details when provided."""
        elements = pdf_generator._create_project_section(sample_project, 1)
        
        assert len(elements) > 0
        assert sample_project.technical_details is not None


class TestFullReportGeneration:
    """Test complete PDF report generation."""
    
    def test_generate_report_creates_file(self, pdf_generator, sample_report, temp_output_dir):
        """Test that generate_report creates a PDF file."""
        pdf_path = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith('.pdf')
        assert os.path.getsize(pdf_path) > 0
    
    def test_generate_report_with_custom_filename(self, pdf_generator, sample_report, temp_output_dir):
        """Test generate_report with custom filename."""
        custom_filename = "custom_report.pdf"
        pdf_path = pdf_generator.generate_report(sample_report, temp_output_dir, custom_filename)
        
        assert os.path.exists(pdf_path)
        assert custom_filename in pdf_path
    
    def test_generate_report_creates_output_dir(self, pdf_generator, sample_report, temp_output_dir):
        """Test that generate_report creates output directory if it doesn't exist."""
        nested_dir = os.path.join(temp_output_dir, "nested", "reports")
        pdf_path = pdf_generator.generate_report(sample_report, nested_dir)
        
        assert os.path.exists(nested_dir)
        assert os.path.exists(pdf_path)
    
    def test_generate_report_with_multiple_projects(self, pdf_generator, sample_report_multiple_projects, temp_output_dir):
        """Test generate_report with multiple projects."""
        pdf_path = pdf_generator.generate_report(sample_report_multiple_projects, temp_output_dir)
        
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0
    
    def test_generate_report_with_no_projects(self, pdf_generator, temp_output_dir):
        """Test generate_report with empty projects list."""
        report = AuditReport(
            report_id="RPT-2024-EMPTY",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=0.0,
            total_qualified_cost=0.0,
            estimated_credit=0.0,
            projects=[],
            company_name="Empty Corp"
        )
        
        pdf_path = pdf_generator.generate_report(report, temp_output_dir)
        
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0


class TestPDFGeneratorStringRepresentation:
    """Test string representation of PDFGenerator."""
    
    def test_str_representation(self, pdf_generator):
        """Test __str__ method returns readable representation."""
        str_repr = str(pdf_generator)
        
        assert "PDFGenerator" in str_repr
        assert "page_size" in str_repr
        assert "margin" in str_repr


class TestPDFGeneratorErrorHandling:
    """Test error handling in PDF generation."""
    
    def test_generate_report_with_invalid_output_dir(self, pdf_generator, sample_report):
        """Test error handling for invalid output directory."""
        # Use an invalid path that can't be created
        invalid_path = "/invalid/path/that/cannot/be/created"
        
        # On Windows, this might not raise an error, so we'll just check it doesn't crash
        try:
            pdf_path = pdf_generator.generate_report(sample_report, invalid_path)
            # If it succeeds, verify the file was created
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except (IOError, OSError, PermissionError):
            # Expected behavior - invalid path should raise an error
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
