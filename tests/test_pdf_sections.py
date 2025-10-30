"""
Tests for PDF report section generation methods.

This module tests the new PDF report section methods:
- _add_project_breakdown()
- _add_narratives()
- _add_citations()
- _add_appendices()
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport


class TestProjectBreakdownSection:
    """Test the _add_project_breakdown() method."""
    
    def test_add_project_breakdown_with_projects(self):
        """Test that project breakdown section is created with projects."""
        generator = PDFGenerator()
        
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.00,
            confidence_score=0.85,
            qualification_percentage=90.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        report = AuditReport(
            report_id="TEST-001",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=10.0,
            total_qualified_cost=1000.00,
            estimated_credit=200.00,
            projects=[project],
            company_name="Test Company"
        )
        
        elements = generator._add_project_breakdown(report)
        
        # Should return a list of flowables
        assert isinstance(elements, list)
        assert len(elements) > 0
        
        # Should contain title, table, and page break
        assert any("Project Breakdown" in str(elem) for elem in elements if hasattr(elem, '__str__'))
    
    def test_add_project_breakdown_without_projects(self):
        """Test that project breakdown handles empty project list."""
        generator = PDFGenerator()
        
        report = AuditReport(
            report_id="TEST-002",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=0.0,
            total_qualified_cost=0.00,
            estimated_credit=0.00,
            projects=[],
            company_name="Test Company"
        )
        
        elements = generator._add_project_breakdown(report)
        
        # Should still return elements (title and message)
        assert isinstance(elements, list)
        assert len(elements) > 0


class TestNarrativesSection:
    """Test the _add_narratives() method."""
    
    def test_add_narratives_with_projects(self):
        """Test that narratives section is created with projects."""
        generator = PDFGenerator()
        
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=15.0,
            qualified_cost=1500.00,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation for Alpha",
            reasoning="This project meets all four-part test criteria...",
            irs_source="CFR Title 26 § 1.41-4",
            technical_details={
                "technological_uncertainty": "Uncertainty about encryption methods",
                "experimentation_process": "Systematic testing of algorithms",
                "qualified_activities": ["Design", "Testing", "Integration"]
            }
        )
        
        report = AuditReport(
            report_id="TEST-003",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=15.0,
            total_qualified_cost=1500.00,
            estimated_credit=300.00,
            projects=[project],
            company_name="Test Company"
        )
        
        elements = generator._add_narratives(report)
        
        # Should return a list of flowables
        assert isinstance(elements, list)
        assert len(elements) > 0
        
        # Should contain narrative content
        assert any("Technical Project Narratives" in str(elem) for elem in elements if hasattr(elem, '__str__'))
    
    def test_add_narratives_without_projects(self):
        """Test that narratives section handles empty project list."""
        generator = PDFGenerator()
        
        report = AuditReport(
            report_id="TEST-004",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=0.0,
            total_qualified_cost=0.00,
            estimated_credit=0.00,
            projects=[],
            company_name="Test Company"
        )
        
        elements = generator._add_narratives(report)
        
        # Should still return elements
        assert isinstance(elements, list)
        assert len(elements) > 0


class TestCitationsSection:
    """Test the _add_citations() method."""
    
    def test_add_citations_with_projects(self):
        """Test that citations section is created with projects."""
        generator = PDFGenerator()
        
        project1 = QualifiedProject(
            project_name="Project A",
            qualified_hours=10.0,
            qualified_cost=1000.00,
            confidence_score=0.85,
            qualification_percentage=90.0,
            supporting_citation="Citation text for Project A",
            reasoning="Reasoning for Project A",
            irs_source="CFR Title 26 § 1.41-4(a)(1)"
        )
        
        project2 = QualifiedProject(
            project_name="Project B",
            qualified_hours=12.0,
            qualified_cost=1200.00,
            confidence_score=0.88,
            qualification_percentage=92.0,
            supporting_citation="Citation text for Project B",
            reasoning="Reasoning for Project B",
            irs_source="Form 6765 Instructions"
        )
        
        report = AuditReport(
            report_id="TEST-005",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=22.0,
            total_qualified_cost=2200.00,
            estimated_credit=440.00,
            projects=[project1, project2],
            company_name="Test Company"
        )
        
        elements = generator._add_citations(report)
        
        # Should return a list of flowables
        assert isinstance(elements, list)
        assert len(elements) > 0
        
        # Should contain citations content
        assert any("IRS Citations" in str(elem) for elem in elements if hasattr(elem, '__str__'))
    
    def test_add_citations_without_projects(self):
        """Test that citations section handles empty project list."""
        generator = PDFGenerator()
        
        report = AuditReport(
            report_id="TEST-006",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=0.0,
            total_qualified_cost=0.00,
            estimated_credit=0.00,
            projects=[],
            company_name="Test Company"
        )
        
        elements = generator._add_citations(report)
        
        # Should still return elements
        assert isinstance(elements, list)
        assert len(elements) > 0


class TestAppendicesSection:
    """Test the _add_appendices() method."""
    
    def test_add_appendices_with_projects(self):
        """Test that appendices section is created with projects."""
        generator = PDFGenerator()
        
        project = QualifiedProject(
            project_name="Beta Development",
            qualified_hours=20.0,
            qualified_cost=2000.00,
            confidence_score=0.90,
            qualification_percentage=93.0,
            supporting_citation="Citation for Beta",
            reasoning="Detailed reasoning for Beta project qualification...",
            irs_source="CFR Title 26 § 1.41-4(a)(5)"
        )
        
        report = AuditReport(
            report_id="TEST-007",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=20.0,
            total_qualified_cost=2000.00,
            estimated_credit=400.00,
            projects=[project],
            company_name="Test Company"
        )
        
        elements = generator._add_appendices(report)
        
        # Should return a list of flowables
        assert isinstance(elements, list)
        assert len(elements) > 0
        
        # Should contain appendices content
        assert any("Appendices" in str(elem) or "Appendix" in str(elem) for elem in elements if hasattr(elem, '__str__'))
    
    def test_add_appendices_without_projects(self):
        """Test that appendices section handles empty project list."""
        generator = PDFGenerator()
        
        report = AuditReport(
            report_id="TEST-008",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=0.0,
            total_qualified_cost=0.00,
            estimated_credit=0.00,
            projects=[],
            company_name="Test Company"
        )
        
        elements = generator._add_appendices(report)
        
        # Should still return elements
        assert isinstance(elements, list)
        assert len(elements) > 0


class TestFullReportWithNewSections:
    """Test that the full report generation includes all new sections."""
    
    def test_generate_report_includes_all_sections(self, tmp_path):
        """Test that generated report includes all new sections."""
        generator = PDFGenerator()
        
        project = QualifiedProject(
            project_name="Complete Test Project",
            qualified_hours=25.0,
            qualified_cost=2500.00,
            confidence_score=0.95,
            qualification_percentage=98.0,
            supporting_citation="Complete citation text",
            reasoning="Complete reasoning for qualification",
            irs_source="CFR Title 26 § 1.41-4",
            technical_details={
                "technological_uncertainty": "Test uncertainty",
                "experimentation_process": "Test process"
            }
        )
        
        report = AuditReport(
            report_id="TEST-COMPLETE",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=25.0,
            total_qualified_cost=2500.00,
            estimated_credit=500.00,
            projects=[project],
            company_name="Complete Test Company"
        )
        
        # Generate the report
        pdf_path = generator.generate_report(report, str(tmp_path), "complete_test.pdf")
        
        # Verify the PDF was created
        assert Path(pdf_path).exists()
        assert Path(pdf_path).stat().st_size > 0
        
        # Verify it's a valid PDF (starts with PDF header)
        with open(pdf_path, 'rb') as f:
            header = f.read(4)
            assert header == b'%PDF'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
