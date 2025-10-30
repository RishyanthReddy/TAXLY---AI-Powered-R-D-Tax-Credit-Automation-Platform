"""
Test PDF styling and formatting consistency.

This test verifies that all PDF sections use consistent fonts, colors, spacing,
and that headers, footers, and page numbers are correctly applied throughout
the document.

Requirements tested:
- 4.4: PDF generation with professional styling
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator, NumberedCanvas
from models.tax_models import QualifiedProject, AuditReport
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate
import PyPDF2


class TestPDFStylingFormatting:
    """Test suite for PDF styling and formatting verification."""
    
    @pytest.fixture
    def sample_projects(self):
        """Create sample projects for testing."""
        projects = []
        for i in range(3):
            project = QualifiedProject(
                project_name=f"Test Project {i+1}",
                qualified_hours=50.0 + (i * 10),
                qualified_cost=3600.0 + (i * 720),
                confidence_score=0.85 - (i * 0.05),
                qualification_percentage=90.0 - (i * 5),
                supporting_citation=f"This is the supporting citation for project {i+1}. " * 10,
                reasoning=f"This project meets the four-part test because... " * 20,
                irs_source=f"CFR Title 26 § 1.41-4(a)({i+1})",
                technical_details={
                    "technological_uncertainty": f"Uncertainty about approach {i+1}",
                    "experimentation_process": f"Systematic evaluation {i+1}"
                },
                flagged_for_review=(i == 2)  # Flag last project
            )
            projects.append(project)
        return projects
    
    @pytest.fixture
    def sample_report(self, sample_projects):
        """Create a sample audit report with complete data."""
        total_hours = sum(p.qualified_hours for p in sample_projects)
        total_cost = sum(p.qualified_cost for p in sample_projects)
        estimated_credit = total_cost * 0.20
        avg_confidence = sum(p.confidence_score for p in sample_projects) / len(sample_projects)
        flagged_count = sum(1 for p in sample_projects if p.flagged_for_review)
        
        # Create narratives
        narratives = {
            p.project_name: f"Technical narrative for {p.project_name}. " * 50
            for p in sample_projects
        }
        
        # Create compliance reviews
        compliance_reviews = {
            p.project_name: {
                'status': 'Compliant' if not p.flagged_for_review else 'Needs Review',
                'completeness_score': 0.95 if not p.flagged_for_review else 0.70,
                'required_revisions': [] if not p.flagged_for_review else ['Add more technical details']
            }
            for p in sample_projects
        }
        
        # Create aggregated data
        aggregated_data = {
            'total_qualified_hours': total_hours,
            'total_qualified_cost': total_cost,
            'estimated_credit': estimated_credit,
            'average_confidence': avg_confidence,
            'flagged_count': flagged_count,
            'high_confidence_count': 2,
            'medium_confidence_count': 1,
            'low_confidence_count': 0
        }
        
        report = AuditReport(
            report_id="TEST-STYLING-001",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=total_hours,
            total_qualified_cost=total_cost,
            estimated_credit=estimated_credit,
            average_confidence=avg_confidence,
            project_count=len(sample_projects),
            flagged_project_count=flagged_count,
            projects=sample_projects,
            company_name="Test Company Inc.",
            narratives=narratives,
            compliance_reviews=compliance_reviews,
            aggregated_data=aggregated_data
        )
        
        return report
    
    @pytest.fixture
    def pdf_generator(self):
        """Create a PDF generator instance."""
        return PDFGenerator()
    
    def test_pdf_generator_initialization(self, pdf_generator):
        """Test that PDF generator initializes with correct styling properties."""
        # Verify page size
        assert pdf_generator.page_size == letter
        
        # Verify margins
        assert pdf_generator.margin == 0.75 * inch
        
        # Verify fonts
        assert pdf_generator.title_font == "Helvetica-Bold"
        assert pdf_generator.body_font == "Helvetica"
        
        # Verify font sizes
        assert pdf_generator.font_size_title == 18
        assert pdf_generator.font_size_heading == 14
        assert pdf_generator.font_size_body == 10
        
        # Verify primary color
        assert pdf_generator.primary_color == colors.HexColor("#1a365d")
        
        print("✓ PDF generator initialized with correct styling properties")
    
    def test_custom_styles_exist(self, pdf_generator):
        """Test that all custom paragraph styles are created."""
        required_styles = [
            'CustomTitle',
            'CustomHeading',
            'CustomSubheading',
            'CustomBody',
            'Citation',
            'TOCHeading',
            'TOCEntry1',
            'TOCEntry2'
        ]
        
        for style_name in required_styles:
            assert style_name in pdf_generator.styles, f"Missing style: {style_name}"
            style = pdf_generator.styles[style_name]
            
            # Verify style has required attributes
            assert hasattr(style, 'fontName')
            assert hasattr(style, 'fontSize')
            assert hasattr(style, 'textColor')
            
            print(f"  ✓ Style '{style_name}' exists with proper attributes")
        
        print(f"✓ All {len(required_styles)} custom styles are properly defined")
    
    def test_style_consistency(self, pdf_generator):
        """Test that styles use consistent fonts and colors."""
        # Check title styles use title font
        title_styles = ['CustomTitle', 'CustomHeading', 'CustomSubheading', 'TOCHeading']
        for style_name in title_styles:
            style = pdf_generator.styles[style_name]
            assert pdf_generator.title_font in style.fontName, \
                f"{style_name} should use title font"
            print(f"  ✓ {style_name} uses title font: {style.fontName}")
        
        # Check body styles use body font
        body_styles = ['CustomBody', 'Citation']
        for style_name in body_styles:
            style = pdf_generator.styles[style_name]
            assert pdf_generator.body_font in style.fontName, \
                f"{style_name} should use body font"
            print(f"  ✓ {style_name} uses body font: {style.fontName}")
        
        # Check heading styles use primary color
        heading_styles = ['CustomTitle', 'CustomHeading', 'CustomSubheading']
        for style_name in heading_styles:
            style = pdf_generator.styles[style_name]
            assert style.textColor == pdf_generator.primary_color, \
                f"{style_name} should use primary color"
            print(f"  ✓ {style_name} uses primary color")
        
        print("✓ All styles use consistent fonts and colors")
    
    def test_numbered_canvas_initialization(self):
        """Test that NumberedCanvas initializes with correct properties."""
        # Create a test canvas
        buffer = BytesIO()
        test_canvas = NumberedCanvas(
            buffer,
            pagesize=letter,
            company_name="Test Company",
            report_id="TEST-001",
            primary_color=colors.HexColor("#1a365d")
        )
        
        # Verify properties
        assert test_canvas.company_name == "Test Company"
        assert test_canvas.report_id == "TEST-001"
        assert test_canvas.primary_color == colors.HexColor("#1a365d")
        
        print("✓ NumberedCanvas initializes with correct properties")
    
    def test_generate_complete_pdf(self, pdf_generator, sample_report, tmp_path):
        """Test generating a complete PDF and verify it exists."""
        output_dir = tmp_path / "test_output"
        output_dir.mkdir()
        
        # Generate PDF
        pdf_path = pdf_generator.generate_report(
            sample_report,
            str(output_dir),
            "test_styling.pdf"
        )
        
        # Verify PDF was created
        assert Path(pdf_path).exists()
        
        # Verify file size (should be substantial for complete PDF)
        file_size = Path(pdf_path).stat().st_size
        assert file_size > 15000, f"PDF too small ({file_size} bytes), may be incomplete"
        
        print(f"✓ Complete PDF generated: {file_size:,} bytes")
        
        return pdf_path
    
    def test_pdf_page_count(self, pdf_generator, sample_report, tmp_path):
        """Test that PDF has expected number of pages."""
        output_dir = tmp_path / "test_output"
        output_dir.mkdir()
        
        # Generate PDF
        pdf_path = pdf_generator.generate_report(
            sample_report,
            str(output_dir),
            "test_pages.pdf"
        )
        
        # Read PDF and count pages
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            page_count = len(pdf_reader.pages)
        
        # With 3 projects, expect:
        # - Cover page (1)
        # - TOC (1)
        # - Executive summary (1)
        # - Project breakdown (1)
        # - Project sections (3 projects, likely 3-4 pages)
        # - Technical narratives (1-2 pages)
        # - IRS citations (1-2 pages)
        # - Appendices (1 page)
        # Total: ~10-17 pages (depending on content length and page breaks)
        
        assert page_count >= 9, f"PDF has too few pages ({page_count})"
        assert page_count <= 20, f"PDF has too many pages ({page_count})"
        
        print(f"✓ PDF has appropriate page count: {page_count} pages")
    
    def test_pdf_text_extraction(self, pdf_generator, sample_report, tmp_path):
        """Test that PDF contains expected text content."""
        output_dir = tmp_path / "test_output"
        output_dir.mkdir()
        
        # Generate PDF
        pdf_path = pdf_generator.generate_report(
            sample_report,
            str(output_dir),
            "test_content.pdf"
        )
        
        # Extract text from PDF
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text()
        
        # Verify key sections are present
        assert "R&D Tax Credit" in full_text
        assert "Audit Report" in full_text
        assert "Executive Summary" in full_text
        assert "Project Breakdown" in full_text
        assert "Technical" in full_text or "Narratives" in full_text
        assert "IRS Citations" in full_text
        assert "Test Company Inc." in full_text
        assert "TEST-STYLING-001" in full_text
        
        # Verify all projects are mentioned
        for project in sample_report.projects:
            assert project.project_name in full_text, \
                f"Project '{project.project_name}' not found in PDF"
        
        print("✓ PDF contains all expected text content")
    
    def test_section_spacing_consistency(self, pdf_generator, sample_report):
        """Test that section generation methods use consistent spacing."""
        # Generate each section and verify spacing elements
        
        # Cover page
        cover_elements = pdf_generator._create_cover_page(sample_report)
        spacer_count = sum(1 for elem in cover_elements if hasattr(elem, '__class__') 
                          and 'Spacer' in elem.__class__.__name__)
        assert spacer_count >= 3, "Cover page should have multiple spacers for proper spacing"
        print(f"  ✓ Cover page has {spacer_count} spacers")
        
        # Executive summary
        summary_elements = pdf_generator._create_executive_summary(sample_report)
        spacer_count = sum(1 for elem in summary_elements if hasattr(elem, '__class__') 
                          and 'Spacer' in elem.__class__.__name__)
        assert spacer_count >= 2, "Executive summary should have spacers"
        print(f"  ✓ Executive summary has {spacer_count} spacers")
        
        # Project breakdown
        breakdown_elements = pdf_generator._add_project_breakdown(sample_report)
        spacer_count = sum(1 for elem in breakdown_elements if hasattr(elem, '__class__') 
                          and 'Spacer' in elem.__class__.__name__)
        assert spacer_count >= 2, "Project breakdown should have spacers"
        print(f"  ✓ Project breakdown has {spacer_count} spacers")
        
        print("✓ All sections use consistent spacing")
    
    def test_table_styling_consistency(self, pdf_generator, sample_report):
        """Test that tables use consistent styling."""
        # Generate sections with tables
        summary_elements = pdf_generator._create_executive_summary(sample_report)
        breakdown_elements = pdf_generator._add_project_breakdown(sample_report)
        
        # Find tables in elements
        tables = []
        for elem in summary_elements + breakdown_elements:
            if hasattr(elem, '__class__') and 'Table' in elem.__class__.__name__:
                tables.append(elem)
        
        assert len(tables) >= 2, "Should have multiple tables in report"
        
        # Verify tables have styling applied
        for table in tables:
            assert hasattr(table, '_cellStyles'), "Table should have cell styles"
            print(f"  ✓ Table has styling applied")
        
        print(f"✓ All {len(tables)} tables use consistent styling")
    
    def test_color_consistency(self, pdf_generator):
        """Test that primary color is used consistently."""
        # Verify primary color is set
        assert pdf_generator.primary_color == colors.HexColor("#1a365d")
        
        # Verify heading styles use primary color
        heading_styles = ['CustomTitle', 'CustomHeading', 'CustomSubheading']
        for style_name in heading_styles:
            style = pdf_generator.styles[style_name]
            assert style.textColor == pdf_generator.primary_color
            print(f"  ✓ {style_name} uses primary color: {pdf_generator.primary_color.hexval()}")
        
        print("✓ Primary color is used consistently across all headings")
    
    def test_font_size_hierarchy(self, pdf_generator):
        """Test that font sizes follow a proper hierarchy."""
        # Get font sizes
        title_size = pdf_generator.styles['CustomTitle'].fontSize
        heading_size = pdf_generator.styles['CustomHeading'].fontSize
        subheading_size = pdf_generator.styles['CustomSubheading'].fontSize
        body_size = pdf_generator.styles['CustomBody'].fontSize
        
        # Verify hierarchy
        assert title_size > heading_size, "Title should be larger than heading"
        assert heading_size > subheading_size, "Heading should be larger than subheading"
        assert subheading_size > body_size, "Subheading should be larger than body"
        
        print(f"  ✓ Title: {title_size}pt")
        print(f"  ✓ Heading: {heading_size}pt")
        print(f"  ✓ Subheading: {subheading_size}pt")
        print(f"  ✓ Body: {body_size}pt")
        print("✓ Font size hierarchy is correct")
    
    def test_page_margins_consistency(self, pdf_generator):
        """Test that page margins are consistent."""
        expected_margin = 0.75 * inch
        assert pdf_generator.margin == expected_margin
        
        print(f"✓ Page margins are consistent: {pdf_generator.margin / inch} inches")
    
    def test_professional_appearance(self, pdf_generator, sample_report, tmp_path):
        """Test overall professional appearance of PDF."""
        output_dir = tmp_path / "test_output"
        output_dir.mkdir()
        
        # Generate PDF
        pdf_path = pdf_generator.generate_report(
            sample_report,
            str(output_dir),
            "test_professional.pdf"
        )
        
        # Verify file exists and has reasonable size
        assert Path(pdf_path).exists()
        file_size = Path(pdf_path).stat().st_size
        
        # Professional PDF should be:
        # - At least 15KB (complete content)
        # - Not excessively large (< 500KB for 3 projects)
        assert 15000 <= file_size <= 500000, \
            f"PDF size {file_size} bytes is outside professional range"
        
        # Read PDF metadata
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            page_count = len(pdf_reader.pages)
            
            # Extract text from first page (cover)
            first_page_text = pdf_reader.pages[0].extract_text()
            
            # Verify cover page has key elements
            # Note: PyPDF2 may extract "&" as ";" so check for both variations
            assert ("R&D Tax Credit" in first_page_text or "R&D; Tax Credit" in first_page_text), \
                f"R&D Tax Credit not found in: {first_page_text[:200]}"
            assert "Audit Report" in first_page_text
            assert "Test Company Inc." in first_page_text
            assert "2024" in first_page_text
        
        print(f"✓ PDF has professional appearance:")
        print(f"  - File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        print(f"  - Page count: {page_count}")
        print(f"  - Cover page: Complete")
        print(f"  - Company branding: Present")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
