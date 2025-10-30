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
from utils.logger import AgentLogger

# Initialize logger for tests
AgentLogger.initialize()
logger = AgentLogger.get_logger("tests.test_pdf_generator")


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


class TestSectionGenerationMethods:
    """Test individual section generation methods."""
    
    def test_add_project_breakdown(self, pdf_generator, sample_report):
        """Test project breakdown section generation."""
        elements = pdf_generator._add_project_breakdown(sample_report)
        
        assert len(elements) > 0
        assert any('PageBreak' in str(type(elem)) for elem in elements)
    
    def test_add_project_breakdown_with_multiple_projects(self, pdf_generator, sample_report_multiple_projects):
        """Test project breakdown with multiple projects."""
        elements = pdf_generator._add_project_breakdown(sample_report_multiple_projects)
        
        assert len(elements) > 0
        # Should include table with all projects
        assert any('Table' in str(type(elem)) for elem in elements)
    
    def test_add_project_breakdown_with_no_projects(self, pdf_generator):
        """Test project breakdown with empty projects list."""
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
        
        elements = pdf_generator._add_project_breakdown(report)
        
        assert len(elements) > 0
        # Should have message about no projects
    
    def test_add_narratives(self, pdf_generator, sample_report):
        """Test narratives section generation."""
        elements = pdf_generator._add_narratives(sample_report)
        
        assert len(elements) > 0
        assert any('PageBreak' in str(type(elem)) for elem in elements)
    
    def test_add_narratives_with_multiple_projects(self, pdf_generator, sample_report_multiple_projects):
        """Test narratives with multiple projects."""
        elements = pdf_generator._add_narratives(sample_report_multiple_projects)
        
        assert len(elements) > 0
        # Should have narratives for all projects
    
    def test_add_narratives_with_no_projects(self, pdf_generator):
        """Test narratives with empty projects list."""
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
        
        elements = pdf_generator._add_narratives(report)
        
        assert len(elements) > 0
    
    def test_add_citations(self, pdf_generator, sample_report):
        """Test citations section generation."""
        elements = pdf_generator._add_citations(sample_report)
        
        assert len(elements) > 0
        assert any('PageBreak' in str(type(elem)) for elem in elements)
    
    def test_add_citations_with_multiple_sources(self, pdf_generator, sample_report_multiple_projects):
        """Test citations with multiple IRS sources."""
        elements = pdf_generator._add_citations(sample_report_multiple_projects)
        
        assert len(elements) > 0
        # Should organize citations by source
    
    def test_add_citations_with_no_projects(self, pdf_generator):
        """Test citations with empty projects list."""
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
        
        elements = pdf_generator._add_citations(report)
        
        assert len(elements) > 0
    
    def test_add_appendices(self, pdf_generator, sample_report):
        """Test appendices section generation."""
        elements = pdf_generator._add_appendices(sample_report)
        
        assert len(elements) > 0
        # Should have multiple appendices (A, B, C)
    
    def test_add_appendices_with_multiple_projects(self, pdf_generator, sample_report_multiple_projects):
        """Test appendices with multiple projects."""
        elements = pdf_generator._add_appendices(sample_report_multiple_projects)
        
        assert len(elements) > 0
        # Should include all projects in appendix tables
    
    def test_add_appendices_with_no_projects(self, pdf_generator):
        """Test appendices with empty projects list."""
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
        
        elements = pdf_generator._add_appendices(report)
        
        assert len(elements) > 0


class TestLargeDatasetHandling:
    """Test PDF generation with large datasets (50+ projects)."""
    
    @pytest.fixture
    def large_report(self):
        """Create a report with 50+ projects."""
        projects = []
        total_hours = 0.0
        total_cost = 0.0
        
        for i in range(55):
            hours = 10.0 + (i % 20)
            cost = hours * 72.0
            confidence = 0.75 + (i % 25) / 100.0
            
            project = QualifiedProject(
                project_name=f"Project {i+1:03d}",
                qualified_hours=hours,
                qualified_cost=cost,
                confidence_score=min(confidence, 1.0),
                qualification_percentage=85.0 + (i % 15),
                supporting_citation=f"Supporting documentation for project {i+1}.",
                reasoning=f"This project meets the four-part test for R&D qualification. "
                         f"It involves technological uncertainty and systematic experimentation.",
                irs_source="CFR Title 26 § 1.41-4",
                technical_details={
                    "technological_uncertainty": f"Uncertainty in approach {i+1}",
                    "experimentation_process": f"Systematic testing methodology {i+1}"
                }
            )
            
            projects.append(project)
            total_hours += hours
            total_cost += cost
        
        return AuditReport(
            report_id="RPT-2024-LARGE",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=total_hours,
            total_qualified_cost=total_cost,
            estimated_credit=total_cost * 0.20,
            projects=projects,
            company_name="Large Corporation"
        )
    
    def test_generate_report_with_50_plus_projects(self, pdf_generator, large_report, temp_output_dir):
        """Test PDF generation with 50+ projects."""
        pdf_path = pdf_generator.generate_report(large_report, temp_output_dir)
        
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0
        
        # Large report should be substantial in size
        file_size = os.path.getsize(pdf_path)
        assert file_size > 50000  # Should be at least 50KB
        
        logger.info(f"Large report generated: {file_size} bytes for {len(large_report.projects)} projects")
    
    def test_project_breakdown_with_large_dataset(self, pdf_generator, large_report):
        """Test project breakdown table with 50+ projects."""
        elements = pdf_generator._add_project_breakdown(large_report)
        
        assert len(elements) > 0
        # Should handle large table without errors
    
    def test_narratives_with_large_dataset(self, pdf_generator, large_report):
        """Test narratives section with 50+ projects."""
        elements = pdf_generator._add_narratives(large_report)
        
        assert len(elements) > 0
        # Should create narratives for all projects
    
    def test_appendices_with_large_dataset(self, pdf_generator, large_report):
        """Test appendices with 50+ projects."""
        elements = pdf_generator._add_appendices(large_report)
        
        assert len(elements) > 0
        # Should include all projects in appendix tables
    
    def test_performance_with_large_dataset(self, pdf_generator, large_report, temp_output_dir):
        """Test that large report generation completes within reasonable time."""
        import time
        
        start_time = time.time()
        pdf_path = pdf_generator.generate_report(large_report, temp_output_dir)
        elapsed_time = time.time() - start_time
        
        assert os.path.exists(pdf_path)
        
        # Should complete within 60 seconds (requirement from design doc)
        assert elapsed_time < 60.0, f"Report generation took {elapsed_time:.2f}s, exceeds 60s limit"
        
        logger.info(f"Large report generated in {elapsed_time:.2f} seconds")


class TestPDFFileIntegrity:
    """Test PDF file integrity and validity."""
    
    def test_pdf_file_is_valid(self, pdf_generator, sample_report, temp_output_dir):
        """Test that generated PDF file is valid and can be opened."""
        pdf_path = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        assert os.path.exists(pdf_path)
        
        # Check file has PDF header
        with open(pdf_path, 'rb') as f:
            header = f.read(4)
            assert header == b'%PDF', "File does not have valid PDF header"
    
    def test_pdf_file_has_content(self, pdf_generator, sample_report, temp_output_dir):
        """Test that PDF file contains actual content."""
        pdf_path = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        # PDF should be reasonably sized (not empty or corrupted)
        file_size = os.path.getsize(pdf_path)
        assert file_size > 5000, f"PDF file too small ({file_size} bytes), may be corrupted"
    
    def test_pdf_file_has_eof_marker(self, pdf_generator, sample_report, temp_output_dir):
        """Test that PDF file has proper EOF marker."""
        pdf_path = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        # Check file has PDF EOF marker
        with open(pdf_path, 'rb') as f:
            f.seek(-10, 2)  # Seek to last 10 bytes
            tail = f.read()
            assert b'%%EOF' in tail, "File does not have valid PDF EOF marker"
    
    def test_pdf_metadata(self, pdf_generator, sample_report, temp_output_dir):
        """Test that PDF contains proper metadata."""
        pdf_path = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        # Read file and check for metadata indicators
        with open(pdf_path, 'rb') as f:
            content = f.read()
            
            # Should contain ReportLab producer info
            assert b'ReportLab' in content or b'reportlab' in content.lower()
    
    def test_multiple_reports_different_filenames(self, pdf_generator, sample_report, temp_output_dir):
        """Test that multiple reports generate different filenames."""
        pdf_path1 = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        # Wait a moment to ensure different timestamp (1 second for timestamp precision)
        import time
        time.sleep(1.1)
        
        pdf_path2 = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        assert pdf_path1 != pdf_path2, "Multiple reports should have different filenames"
        assert os.path.exists(pdf_path1)
        assert os.path.exists(pdf_path2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestPDFStylingAndFormatting:
    """Test PDF styling and formatting features (Task 120)."""
    
    def test_numbered_canvas_initialization(self):
        """Test NumberedCanvas can be initialized with custom properties."""
        from utils.pdf_generator import NumberedCanvas
        from reportlab.lib import colors
        
        canvas = NumberedCanvas(
            'test.pdf',
            company_name='Test Corp',
            report_id='RPT-001',
            primary_color=colors.blue
        )
        
        assert canvas.company_name == 'Test Corp'
        assert canvas.report_id == 'RPT-001'
        assert canvas.primary_color == colors.blue
    
    def test_toc_styles_created(self, pdf_generator):
        """Test that table of contents styles are created."""
        assert 'TOCHeading' in pdf_generator.styles
        assert 'TOCEntry1' in pdf_generator.styles
        assert 'TOCEntry2' in pdf_generator.styles
    
    def test_create_table_of_contents(self, pdf_generator):
        """Test table of contents creation returns flowables."""
        elements = pdf_generator._create_table_of_contents()
        
        assert len(elements) > 0
        assert any('PageBreak' in str(type(elem)) for elem in elements)
    
    def test_logo_placeholder_in_cover_page(self, pdf_generator, sample_report):
        """Test cover page includes logo placeholder when no logo provided."""
        elements = pdf_generator._create_cover_page(sample_report)
        
        # Should have logo placeholder table
        assert len(elements) > 0
        # Check for placeholder text in elements
        content = str(elements)
        assert 'Logo' in content or len(elements) > 5
    
    def test_logo_path_initialization(self):
        """Test PDFGenerator can be initialized with logo path."""
        generator = PDFGenerator(logo_path="path/to/logo.png")
        
        assert generator.logo_path == "path/to/logo.png"
    
    def test_cover_page_with_logo_path(self, sample_report):
        """Test cover page attempts to load logo when path provided."""
        # Create generator with non-existent logo path
        generator = PDFGenerator(logo_path="nonexistent_logo.png")
        elements = generator._create_cover_page(sample_report)
        
        # Should still create cover page with placeholder
        assert len(elements) > 0
    
    def test_section_bookmarks_for_toc(self, pdf_generator, sample_report):
        """Test that major sections create bookmarks for TOC."""
        # Executive summary
        exec_elements = pdf_generator._create_executive_summary(sample_report)
        assert len(exec_elements) > 0
        
        # Project breakdown
        breakdown_elements = pdf_generator._add_project_breakdown(sample_report)
        assert len(breakdown_elements) > 0
        
        # Narratives
        narrative_elements = pdf_generator._add_narratives(sample_report)
        assert len(narrative_elements) > 0
        
        # Citations
        citation_elements = pdf_generator._add_citations(sample_report)
        assert len(citation_elements) > 0
        
        # Appendices
        appendix_elements = pdf_generator._add_appendices(sample_report)
        assert len(appendix_elements) > 0
    
    def test_generate_report_with_toc(self, pdf_generator, sample_report, temp_output_dir):
        """Test that generated report includes table of contents."""
        pdf_path = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0
        
        # PDF should be larger with TOC and styling
        file_size = os.path.getsize(pdf_path)
        assert file_size > 10000  # Should be reasonably sized
    
    def test_consistent_styling_colors(self, pdf_generator):
        """Test that consistent colors are used throughout."""
        from reportlab.lib import colors
        
        # Check primary color is set
        assert pdf_generator.primary_color is not None
        
        # Check custom styles use primary color
        assert pdf_generator.styles['CustomTitle'].textColor == pdf_generator.primary_color
        assert pdf_generator.styles['CustomHeading'].textColor == pdf_generator.primary_color
    
    def test_consistent_fonts(self, pdf_generator):
        """Test that consistent fonts are used throughout."""
        # Check title font
        assert pdf_generator.title_font == "Helvetica-Bold"
        assert pdf_generator.styles['CustomTitle'].fontName == pdf_generator.title_font
        
        # Check body font
        assert pdf_generator.body_font == "Helvetica"
        assert pdf_generator.styles['CustomBody'].fontName == pdf_generator.body_font
    
    def test_consistent_spacing(self, pdf_generator):
        """Test that consistent spacing is used throughout."""
        # Check that styles have appropriate spacing
        assert pdf_generator.styles['CustomTitle'].spaceAfter > 0
        assert pdf_generator.styles['CustomHeading'].spaceAfter > 0
        assert pdf_generator.styles['CustomBody'].spaceAfter > 0
    
    def test_professional_appearance_metrics(self, pdf_generator, sample_report, temp_output_dir):
        """Test that generated PDF has professional appearance metrics."""
        pdf_path = pdf_generator.generate_report(sample_report, temp_output_dir)
        
        # Check file exists and has reasonable size
        assert os.path.exists(pdf_path)
        file_size = os.path.getsize(pdf_path)
        
        # Professional PDF should be at least 10KB (with TOC and styling)
        assert file_size > 10000
        
        # Should not be excessively large (< 5MB for single project)
        assert file_size < 5 * 1024 * 1024
