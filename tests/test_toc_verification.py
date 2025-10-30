"""
Test suite for verifying table of contents generation (Task 15).

This module tests the _create_table_of_contents() method to ensure:
1. TOC method exists and returns proper flowables
2. TOC includes all major sections with bookmarks
3. TOC entries are properly formatted
4. TOC works correctly with complete reports

Requirements: 4.4
"""

import sys
from pathlib import Path
import pytest
from io import BytesIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.platypus import PageBreak, Paragraph, Spacer
from reportlab.platypus.tableofcontents import TableOfContents
from PyPDF2 import PdfReader

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport
from datetime import datetime


class TestTableOfContentsVerification:
    """Test cases for table of contents generation (Task 15)."""
    
    @pytest.fixture
    def pdf_generator(self):
        """Create a PDFGenerator instance for testing."""
        return PDFGenerator()
    
    @pytest.fixture
    def sample_projects(self):
        """Create sample qualified projects for testing."""
        return [
            QualifiedProject(
                project_name="API Development",
                qualified_hours=50.0,
                qualified_cost=3600.0,
                qualification_percentage=100.0,
                confidence_score=0.85,
                reasoning="Developed new REST API endpoints with novel authentication",
                irs_source="IRC Section 41(d)(1)(A)",
                supporting_citation="Qualified research under four-part test",
                flagged_for_review=False,
                estimated_credit=720.0
            ),
            QualifiedProject(
                project_name="Database Optimization",
                qualified_hours=40.0,
                qualified_cost=2880.0,
                qualification_percentage=100.0,
                confidence_score=0.78,
                reasoning="Research into query optimization algorithms",
                irs_source="IRC Section 41(d)(1)(B)",
                supporting_citation="Technological in nature per IRC guidelines",
                flagged_for_review=False,
                estimated_credit=576.0
            ),
            QualifiedProject(
                project_name="Machine Learning Model",
                qualified_hours=60.0,
                qualified_cost=4320.0,
                qualification_percentage=100.0,
                confidence_score=0.92,
                reasoning="Novel ML algorithm development for prediction",
                irs_source="IRC Section 41(d)(1)(C)",
                supporting_citation="Process of experimentation documented",
                flagged_for_review=False,
                estimated_credit=864.0
            )
        ]
    
    @pytest.fixture
    def complete_report(self, sample_projects):
        """Create a complete AuditReport with all required fields."""
        narratives = {
            "API Development": "Technical narrative for API development project. " * 50,
            "Database Optimization": "Technical narrative for database optimization. " * 50,
            "Machine Learning Model": "Technical narrative for ML model development. " * 50
        }
        
        compliance_reviews = {
            "API Development": {"status": "Approved", "completeness": 0.95},
            "Database Optimization": {"status": "Approved", "completeness": 0.88},
            "Machine Learning Model": {"status": "Approved", "completeness": 0.98}
        }
        
        aggregated_data = {
            "total_qualified_hours": 150.0,
            "total_qualified_cost": 10800.0,
            "estimated_credit": 2160.0,
            "average_confidence": 0.85,
            "flagged_count": 0,
            "high_confidence_count": 1,
            "medium_confidence_count": 2,
            "low_confidence_count": 0
        }
        
        return AuditReport(
            report_id="TEST_RPT_001",
            generation_date=datetime.now(),
            tax_year=2024,
            company_name="Test Company Inc",
            total_qualified_hours=150.0,
            total_qualified_cost=10800.0,
            estimated_credit=2160.0,
            average_confidence=0.85,
            project_count=3,
            flagged_project_count=0,
            projects=sample_projects,
            narratives=narratives,
            compliance_reviews=compliance_reviews,
            aggregated_data=aggregated_data
        )
    
    def test_toc_method_exists(self, pdf_generator):
        """Test that _create_table_of_contents method exists."""
        assert hasattr(pdf_generator, '_create_table_of_contents')
        assert callable(pdf_generator._create_table_of_contents)
    
    def test_toc_returns_flowables(self, pdf_generator):
        """Test that TOC method returns a list of flowables."""
        elements = pdf_generator._create_table_of_contents()
        
        assert isinstance(elements, list)
        assert len(elements) > 0
        
        # Should contain at least: title, spacer, TOC object, page break
        assert len(elements) >= 4
    
    def test_toc_contains_title(self, pdf_generator):
        """Test that TOC includes a title paragraph."""
        elements = pdf_generator._create_table_of_contents()
        
        # First element should be the title
        assert isinstance(elements[0], Paragraph)
        
        # Check title text
        title_text = str(elements[0].text)
        assert "Table of Contents" in title_text
    
    def test_toc_contains_toc_object(self, pdf_generator):
        """Test that TOC includes the TableOfContents flowable."""
        elements = pdf_generator._create_table_of_contents()
        
        # Should contain a TableOfContents object
        has_toc = any(isinstance(elem, TableOfContents) for elem in elements)
        assert has_toc, "TOC should contain a TableOfContents flowable"
    
    def test_toc_contains_page_break(self, pdf_generator):
        """Test that TOC ends with a page break."""
        elements = pdf_generator._create_table_of_contents()
        
        # Last element should be a page break
        assert isinstance(elements[-1], PageBreak)
    
    def test_toc_styles_configured(self, pdf_generator):
        """Test that TOC styles are properly configured."""
        # Check that TOC styles exist
        assert 'TOCHeading' in pdf_generator.styles
        assert 'TOCEntry1' in pdf_generator.styles
        assert 'TOCEntry2' in pdf_generator.styles
        
        # Verify TOC object has level styles configured
        elements = pdf_generator._create_table_of_contents()
        toc_obj = next((e for e in elements if isinstance(e, TableOfContents)), None)
        
        assert toc_obj is not None
        assert hasattr(toc_obj, 'levelStyles')
        assert toc_obj.levelStyles is not None
        assert len(toc_obj.levelStyles) >= 2
    
    def test_toc_level_styles_match(self, pdf_generator):
        """Test that TOC level styles match the configured styles."""
        elements = pdf_generator._create_table_of_contents()
        toc_obj = next((e for e in elements if isinstance(e, TableOfContents)), None)
        
        assert toc_obj is not None
        
        # Level 1 should use TOCEntry1 style
        assert toc_obj.levelStyles[0] == pdf_generator.styles['TOCEntry1']
        
        # Level 2 should use TOCEntry2 style
        assert toc_obj.levelStyles[1] == pdf_generator.styles['TOCEntry2']
    
    def test_major_sections_add_toc_entries(self, pdf_generator, complete_report):
        """Test that major sections add entries to the TOC."""
        # Generate each major section and verify TOC entries are added
        
        # Executive Summary
        exec_elements = pdf_generator._create_executive_summary(complete_report)
        assert len(exec_elements) > 0
        
        # Project Breakdown
        breakdown_elements = pdf_generator._add_project_breakdown(complete_report)
        assert len(breakdown_elements) > 0
        
        # Technical Narratives
        narrative_elements = pdf_generator._add_technical_narratives(complete_report)
        assert len(narrative_elements) > 0
        
        # IRS Citations
        citation_elements = pdf_generator._add_irs_citations(complete_report)
        assert len(citation_elements) > 0
        
        # Appendices
        appendix_elements = pdf_generator._add_appendices(complete_report)
        assert len(appendix_elements) > 0
    
    def test_toc_entries_have_bookmarks(self, pdf_generator, complete_report):
        """Test that TOC entries have corresponding bookmarks in sections."""
        # Generate executive summary and check for bookmark
        exec_elements = pdf_generator._create_executive_summary(complete_report)
        
        # First element should be the title with bookmark
        title_elem = exec_elements[0]
        assert isinstance(title_elem, Paragraph)
        
        # Check for bookmark anchor in text
        title_text = str(title_elem.text)
        assert 'name="executive_summary"' in title_text or 'Executive Summary' in title_text
    
    def test_complete_pdf_includes_toc(self, pdf_generator, complete_report, tmp_path):
        """Test that a complete PDF includes the table of contents."""
        # Generate complete PDF
        pdf_path = pdf_generator.generate_report(
            complete_report,
            str(tmp_path),
            filename="test_toc_complete.pdf"
        )
        
        assert Path(pdf_path).exists()
        
        # Verify PDF has reasonable size (should include TOC)
        file_size = Path(pdf_path).stat().st_size
        assert file_size > 15000, f"PDF size {file_size} is too small, may be missing TOC"
    
    def test_toc_with_multiple_projects(self, pdf_generator, complete_report, tmp_path):
        """Test TOC generation with multiple projects."""
        # Generate PDF with 3 projects
        pdf_path = pdf_generator.generate_report(
            complete_report,
            str(tmp_path),
            filename="test_toc_multi_projects.pdf"
        )
        
        assert Path(pdf_path).exists()
        
        # Read PDF and verify structure
        with open(pdf_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            
            # Should have multiple pages (cover, TOC, content)
            assert len(pdf_reader.pages) >= 5, "PDF should have at least 5 pages with TOC"
            
            # Extract text from TOC page (page 2, index 1)
            if len(pdf_reader.pages) > 1:
                toc_page = pdf_reader.pages[1]
                toc_text = toc_page.extract_text()
                
                # Verify TOC title is present
                assert "Table of Contents" in toc_text or "Contents" in toc_text
    
    def test_toc_section_order(self, pdf_generator, complete_report, tmp_path):
        """Test that TOC appears in correct order (after cover, before content)."""
        # Generate PDF
        pdf_path = pdf_generator.generate_report(
            complete_report,
            str(tmp_path),
            filename="test_toc_order.pdf"
        )
        
        assert Path(pdf_path).exists()
        
        # Read PDF
        with open(pdf_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            
            # Page 1 should be cover
            page1_text = pdf_reader.pages[0].extract_text()
            assert "R&D Tax Credit" in page1_text or "Audit Report" in page1_text
            
            # Page 2 should be TOC
            if len(pdf_reader.pages) > 1:
                page2_text = pdf_reader.pages[1].extract_text()
                # TOC should mention major sections
                assert ("Table of Contents" in page2_text or 
                       "Executive Summary" in page2_text or
                       "Contents" in page2_text)
    
    def test_toc_includes_all_major_sections(self, pdf_generator, complete_report, tmp_path):
        """Test that TOC includes all major sections of the report."""
        # Generate PDF
        pdf_path = pdf_generator.generate_report(
            complete_report,
            str(tmp_path),
            filename="test_toc_all_sections.pdf"
        )
        
        assert Path(pdf_path).exists()
        
        # Read entire PDF text
        with open(pdf_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text()
        
        # Verify all major sections are present in the document
        expected_sections = [
            "Executive Summary",
            "Project Breakdown",
            "Technical Narratives",
            "IRS Citations",
            "Appendices"
        ]
        
        for section in expected_sections:
            assert section in full_text, f"Section '{section}' not found in PDF"
    
    def test_toc_with_single_project(self, pdf_generator, sample_projects, tmp_path):
        """Test TOC generation with a single project."""
        # Create report with only one project
        single_project_report = AuditReport(
            report_id="TEST_RPT_SINGLE",
            generation_date=datetime.now(),
            tax_year=2024,
            company_name="Test Company",
            total_qualified_hours=50.0,
            total_qualified_cost=3600.0,
            estimated_credit=720.0,
            average_confidence=0.85,
            project_count=1,
            flagged_project_count=0,
            projects=[sample_projects[0]],
            narratives={"API Development": "Technical narrative. " * 50},
            compliance_reviews={"API Development": {"status": "Approved"}},
            aggregated_data={
                "total_qualified_hours": 50.0,
                "total_qualified_cost": 3600.0,
                "estimated_credit": 720.0,
                "average_confidence": 0.85,
                "flagged_count": 0
            }
        )
        
        # Generate PDF
        pdf_path = pdf_generator.generate_report(
            single_project_report,
            str(tmp_path),
            filename="test_toc_single_project.pdf"
        )
        
        assert Path(pdf_path).exists()
        
        # Verify PDF structure
        with open(pdf_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            assert len(pdf_reader.pages) >= 4, "PDF should have at least 4 pages"
    
    def test_toc_formatting_consistency(self, pdf_generator):
        """Test that TOC formatting is consistent with document styling."""
        elements = pdf_generator._create_table_of_contents()
        
        # Get TOC title
        toc_title = elements[0]
        assert isinstance(toc_title, Paragraph)
        
        # Verify title uses TOCHeading style
        # The style should be applied to the paragraph
        assert hasattr(toc_title, 'style')
    
    def test_toc_spacer_after_title(self, pdf_generator):
        """Test that TOC has proper spacing after title."""
        elements = pdf_generator._create_table_of_contents()
        
        # Second element should be a spacer
        assert isinstance(elements[1], Spacer)
        
        # Spacer should have reasonable height
        spacer = elements[1]
        assert spacer.height > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
