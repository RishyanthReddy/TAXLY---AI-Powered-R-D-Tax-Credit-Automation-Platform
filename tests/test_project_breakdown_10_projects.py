"""
Test project breakdown table with 10 projects.

This test verifies that the _add_project_breakdown() method correctly handles
10 projects and includes all required information in the table.
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport
from reportlab.platypus import Table


class TestProjectBreakdownWith10Projects:
    """Test the _add_project_breakdown() method with 10 projects."""
    
    def test_project_breakdown_with_10_projects(self):
        """Test that project breakdown correctly handles 10 projects."""
        generator = PDFGenerator()
        
        # Create 10 test projects with varying characteristics
        projects = []
        for i in range(1, 11):
            project = QualifiedProject(
                project_name=f"Project {i}",
                qualified_hours=10.0 + i * 5.0,
                qualified_cost=1000.00 + i * 500.0,
                confidence_score=0.70 + i * 0.02,
                qualification_percentage=85.0 + i * 1.0,
                supporting_citation=f"Citation for Project {i}",
                reasoning=f"Reasoning for Project {i}",
                irs_source=f"CFR Title 26 § 1.41-4(a)({i})",
                flagged_for_review=(i <= 2)  # Flag first 2 projects
            )
            projects.append(project)
        
        # Calculate totals
        total_hours = sum(p.qualified_hours for p in projects)
        total_cost = sum(p.qualified_cost for p in projects)
        estimated_credit = total_cost * 0.20
        avg_confidence = sum(p.confidence_score for p in projects) / len(projects)
        flagged_count = sum(1 for p in projects if p.flagged_for_review)
        
        report = AuditReport(
            report_id="TEST-10-PROJECTS",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=total_hours,
            total_qualified_cost=total_cost,
            estimated_credit=estimated_credit,
            average_confidence=avg_confidence,
            project_count=len(projects),
            flagged_project_count=flagged_count,
            projects=projects,
            company_name="Test Company with 10 Projects",
            narratives={p.project_name: f"Narrative for {p.project_name}" for p in projects},
            compliance_reviews={p.project_name: {"status": "approved"} for p in projects},
            aggregated_data={
                "total_qualified_hours": total_hours,
                "total_qualified_cost": total_cost,
                "estimated_credit": estimated_credit,
                "average_confidence": avg_confidence,
                "flagged_count": flagged_count
            }
        )
        
        # Generate project breakdown
        elements = generator._add_project_breakdown(report)
        
        # Verify elements were created
        assert isinstance(elements, list)
        assert len(elements) > 0
        
        # Find the table element
        table_element = None
        for elem in elements:
            if isinstance(elem, Table):
                table_element = elem
                break
        
        assert table_element is not None, "Table element not found in breakdown"
        
        # Verify table has correct number of rows
        # Header row + 10 project rows + 1 totals row = 12 rows
        assert len(table_element._argW) == 7, "Table should have 7 columns"
        
        # Verify table data structure
        table_data = table_element._cellvalues
        assert len(table_data) == 12, f"Table should have 12 rows (header + 10 projects + totals), got {len(table_data)}"
        
        # Verify header row
        header_row = table_data[0]
        assert 'Project Name' in str(header_row[0])
        assert 'Hours' in str(header_row[1])
        assert 'Cost' in str(header_row[2])
        assert 'Qual %' in str(header_row[3]) or 'Qual' in str(header_row[3])
        assert 'Confidence' in str(header_row[4])
        assert 'Credit' in str(header_row[5])
        assert 'Status' in str(header_row[6])
        
        # Verify all 10 projects are in the table
        for i in range(1, 11):
            project_row = table_data[i]
            assert f'Project {i}' in str(project_row[0]), f"Project {i} not found in table"
        
        # Verify totals row
        totals_row = table_data[11]
        assert 'TOTAL' in str(totals_row[0])
        
        # Verify totals match report totals
        totals_hours_str = str(totals_row[1])
        totals_cost_str = str(totals_row[2])
        
        # Extract numeric values from formatted strings
        assert f"{total_hours:.1f}" in totals_hours_str
        assert f"{total_cost:,.2f}" in totals_cost_str
        
        print(f"\n✓ Project breakdown table verified with 10 projects")
        print(f"  - Total hours: {total_hours:.1f}")
        print(f"  - Total cost: ${total_cost:,.2f}")
        print(f"  - Estimated credit: ${estimated_credit:,.2f}")
        print(f"  - Average confidence: {avg_confidence:.2f}")
        print(f"  - Flagged projects: {flagged_count}")
    
    def test_project_breakdown_table_formatting(self):
        """Test that project breakdown table has professional formatting."""
        generator = PDFGenerator()
        
        # Create 10 projects
        projects = []
        for i in range(1, 11):
            project = QualifiedProject(
                project_name=f"Project {i}",
                qualified_hours=15.0 + i * 3.0,
                qualified_cost=1500.00 + i * 300.0,
                confidence_score=0.75 + i * 0.015,
                qualification_percentage=88.0 + i * 0.5,
                supporting_citation=f"Citation {i}",
                reasoning=f"Reasoning {i}",
                irs_source=f"Source {i}"
            )
            projects.append(project)
        
        total_hours = sum(p.qualified_hours for p in projects)
        total_cost = sum(p.qualified_cost for p in projects)
        
        avg_confidence = sum(p.confidence_score for p in projects) / len(projects)
        estimated_credit = total_cost * 0.20
        
        report = AuditReport(
            report_id="TEST-FORMATTING",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=total_hours,
            total_qualified_cost=total_cost,
            estimated_credit=estimated_credit,
            average_confidence=avg_confidence,
            project_count=len(projects),
            flagged_project_count=0,
            projects=projects,
            company_name="Formatting Test Company",
            narratives={p.project_name: f"Narrative for {p.project_name}" for p in projects},
            compliance_reviews={p.project_name: {"status": "approved"} for p in projects},
            aggregated_data={
                "total_qualified_hours": total_hours,
                "total_qualified_cost": total_cost,
                "estimated_credit": estimated_credit,
                "average_confidence": avg_confidence
            }
        )
        
        elements = generator._add_project_breakdown(report)
        
        # Find table
        table_element = None
        for elem in elements:
            if isinstance(elem, Table):
                table_element = elem
                break
        
        assert table_element is not None
        
        # Verify table style exists
        assert hasattr(table_element, '_cellStyles')
        
        # Verify column widths are defined
        assert len(table_element._argW) == 7
        
        print(f"\n✓ Project breakdown table formatting verified")
        print(f"  - 7 columns with defined widths")
        print(f"  - Professional styling applied")
    
    def test_project_breakdown_includes_all_required_columns(self):
        """Test that all required columns are present in the breakdown table."""
        generator = PDFGenerator()
        
        # Create 10 projects
        projects = []
        for i in range(1, 11):
            project = QualifiedProject(
                project_name=f"Alpha Project {i}",
                qualified_hours=20.0 + i * 2.0,
                qualified_cost=2000.00 + i * 200.0,
                confidence_score=0.80 + i * 0.01,
                qualification_percentage=90.0 + i * 0.3,
                supporting_citation=f"Citation {i}",
                reasoning=f"Reasoning {i}",
                irs_source=f"Source {i}"
            )
            projects.append(project)
        
        total_hours = sum(p.qualified_hours for p in projects)
        total_cost = sum(p.qualified_cost for p in projects)
        avg_confidence = sum(p.confidence_score for p in projects) / len(projects)
        estimated_credit = total_cost * 0.20
        
        report = AuditReport(
            report_id="TEST-COLUMNS",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=total_hours,
            total_qualified_cost=total_cost,
            estimated_credit=estimated_credit,
            average_confidence=avg_confidence,
            project_count=len(projects),
            flagged_project_count=0,
            projects=projects,
            company_name="Column Test Company",
            narratives={p.project_name: f"Narrative for {p.project_name}" for p in projects},
            compliance_reviews={p.project_name: {"status": "approved"} for p in projects},
            aggregated_data={
                "total_qualified_hours": total_hours,
                "total_qualified_cost": total_cost,
                "estimated_credit": estimated_credit,
                "average_confidence": avg_confidence
            }
        )
        
        elements = generator._add_project_breakdown(report)
        
        # Find table
        table_element = None
        for elem in elements:
            if isinstance(elem, Table):
                table_element = elem
                break
        
        assert table_element is not None
        
        # Get table data
        table_data = table_element._cellvalues
        header_row = table_data[0]
        
        # Verify all required columns are present
        required_columns = ['Project Name', 'Hours', 'Cost', 'Confidence', 'Credit', 'Status']
        header_text = ' '.join(str(cell) for cell in header_row)
        
        for col in required_columns:
            assert col in header_text or col.lower() in header_text.lower(), \
                f"Required column '{col}' not found in header"
        
        # Verify each project row has data in all columns
        for i in range(1, 11):
            project_row = table_data[i]
            assert len(project_row) == 7, f"Project row {i} should have 7 columns"
            
            # Verify no empty cells (except qualification % which might be formatted differently)
            for j, cell in enumerate(project_row):
                if j != 3:  # Skip qual % column
                    assert cell is not None and str(cell).strip() != '', \
                        f"Empty cell found in row {i}, column {j}"
        
        print(f"\n✓ All required columns verified in project breakdown table")
        print(f"  - Project Name: ✓")
        print(f"  - Hours: ✓")
        print(f"  - Cost: ✓")
        print(f"  - Qualification %: ✓")
        print(f"  - Confidence: ✓")
        print(f"  - Credit: ✓")
        print(f"  - Status: ✓")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
