"""
PDF Generator Usage Examples

This module demonstrates various ways to use the PDFGenerator class
for creating R&D Tax Credit audit reports.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors


def example_basic_report():
    """
    Example 1: Generate a basic report with one project.
    """
    print("\n=== Example 1: Basic Report ===")
    
    # Create a qualified project
    project = QualifiedProject(
        project_name="Alpha Development",
        qualified_hours=14.5,
        qualified_cost=1045.74,
        confidence_score=0.92,
        qualification_percentage=95.0,
        supporting_citation="The project involves developing a new authentication algorithm with encryption, which constitutes qualified research under IRC Section 41.",
        reasoning="This project clearly meets the four-part test: (1) Technological in nature, (2) Qualified purpose, (3) Technological uncertainty, (4) Process of experimentation.",
        irs_source="CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research"
    )
    
    # Create audit report
    report = AuditReport(
        report_id="RPT-2024-001",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=14.5,
        total_qualified_cost=1045.74,
        estimated_credit=209.15,
        projects=[project],
        company_name="Acme Corporation"
    )
    
    # Generate PDF with default settings
    generator = PDFGenerator()
    pdf_path = generator.generate_report(report, "outputs/reports/")
    
    print(f"✓ Basic report generated: {pdf_path}")
    return pdf_path


def example_custom_styling():
    """
    Example 2: Generate a report with custom styling.
    """
    print("\n=== Example 2: Custom Styling ===")
    
    # Create sample project
    project = QualifiedProject(
        project_name="Beta Testing Framework",
        qualified_hours=20.0,
        qualified_cost=1500.00,
        confidence_score=0.88,
        qualification_percentage=90.0,
        supporting_citation="Development of automated testing framework with AI-powered test generation.",
        reasoning="Meets qualified research criteria through technological innovation in test automation.",
        irs_source="CFR Title 26 § 1.41-4"
    )
    
    report = AuditReport(
        report_id="RPT-2024-002",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=20.0,
        total_qualified_cost=1500.00,
        estimated_credit=300.00,
        projects=[project],
        company_name="Tech Innovations Inc."
    )
    
    # Create generator with custom styling
    generator = PDFGenerator(
        page_size=A4,
        margin=1.0,
        title_font="Times-Bold",
        body_font="Times-Roman",
        font_size_title=20,
        font_size_heading=16,
        font_size_body=12,
        primary_color=colors.HexColor("#003366")
    )
    
    pdf_path = generator.generate_report(
        report,
        "outputs/reports/",
        filename="custom_styled_report.pdf"
    )
    
    print(f"✓ Custom styled report generated: {pdf_path}")
    return pdf_path


def example_multiple_projects():
    """
    Example 3: Generate a report with multiple projects.
    """
    print("\n=== Example 3: Multiple Projects ===")
    
    # Create multiple projects
    projects = [
        QualifiedProject(
            project_name="Cloud Infrastructure Optimization",
            qualified_hours=25.5,
            qualified_cost=1850.00,
            confidence_score=0.95,
            qualification_percentage=98.0,
            supporting_citation="Development of novel cloud resource allocation algorithms.",
            reasoning="Significant technological uncertainty in optimizing multi-cloud deployments.",
            irs_source="CFR Title 26 § 1.41-4(a)(1)",
            technical_details={
                "technological_uncertainty": "Uncertainty in optimal resource allocation across multiple cloud providers",
                "experimentation_process": "Systematic testing of various allocation strategies",
                "business_component": "Cloud Resource Manager"
            }
        ),
        QualifiedProject(
            project_name="Machine Learning Model Training",
            qualified_hours=30.0,
            qualified_cost=2200.00,
            confidence_score=0.91,
            qualification_percentage=95.0,
            supporting_citation="Development of custom ML models for predictive analytics.",
            reasoning="Research into novel neural network architectures for time-series prediction.",
            irs_source="CFR Title 26 § 1.41-4(a)(1)",
            technical_details={
                "technological_uncertainty": "Uncertainty in model architecture selection",
                "experimentation_process": "Iterative testing of different architectures",
                "business_component": "Predictive Analytics Engine"
            }
        ),
        QualifiedProject(
            project_name="Security Protocol Enhancement",
            qualified_hours=18.0,
            qualified_cost=1300.00,
            confidence_score=0.87,
            qualification_percentage=92.0,
            supporting_citation="Enhancement of encryption protocols for data transmission.",
            reasoning="Research into quantum-resistant encryption methods.",
            irs_source="CFR Title 26 § 1.41-4(a)(1)"
        )
    ]
    
    # Calculate totals
    total_hours = sum(p.qualified_hours for p in projects)
    total_cost = sum(p.qualified_cost for p in projects)
    
    report = AuditReport(
        report_id="RPT-2024-003",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        projects=projects,
        company_name="Innovation Labs LLC"
    )
    
    generator = PDFGenerator()
    pdf_path = generator.generate_report(report, "outputs/reports/")
    
    print(f"✓ Multi-project report generated: {pdf_path}")
    print(f"  - Total projects: {len(projects)}")
    print(f"  - Total hours: {total_hours:.1f}")
    print(f"  - Total cost: ${total_cost:,.2f}")
    print(f"  - Estimated credit: ${report.estimated_credit:,.2f}")
    return pdf_path


def example_flagged_projects():
    """
    Example 4: Generate a report with flagged projects.
    """
    print("\n=== Example 4: Report with Flagged Projects ===")
    
    projects = [
        QualifiedProject(
            project_name="High Confidence Project",
            qualified_hours=15.0,
            qualified_cost=1100.00,
            confidence_score=0.93,
            qualification_percentage=95.0,
            supporting_citation="Well-documented R&D activities.",
            reasoning="Clear evidence of qualified research.",
            irs_source="CFR Title 26 § 1.41-4"
        ),
        QualifiedProject(
            project_name="Low Confidence Project",
            qualified_hours=8.0,
            qualified_cost=600.00,
            confidence_score=0.65,  # Will be auto-flagged
            qualification_percentage=70.0,
            supporting_citation="Limited documentation available.",
            reasoning="May require additional review and documentation.",
            irs_source="CFR Title 26 § 1.41-4"
        )
    ]
    
    total_hours = sum(p.qualified_hours for p in projects)
    total_cost = sum(p.qualified_cost for p in projects)
    
    report = AuditReport(
        report_id="RPT-2024-004",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        projects=projects,
        company_name="Review Required Corp"
    )
    
    generator = PDFGenerator()
    pdf_path = generator.generate_report(report, "outputs/reports/")
    
    print(f"✓ Report with flagged projects generated: {pdf_path}")
    print(f"  - Flagged projects: {report.flagged_project_count}")
    print(f"  - Average confidence: {report.average_confidence:.2f}")
    return pdf_path


def example_no_company_name():
    """
    Example 5: Generate a report without company name.
    """
    print("\n=== Example 5: Report Without Company Name ===")
    
    project = QualifiedProject(
        project_name="Anonymous Project",
        qualified_hours=10.0,
        qualified_cost=750.00,
        confidence_score=0.85,
        qualification_percentage=88.0,
        supporting_citation="R&D activities for confidential client.",
        reasoning="Qualified research under standard criteria.",
        irs_source="CFR Title 26 § 1.41-4"
    )
    
    report = AuditReport(
        report_id="RPT-2024-005",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=10.0,
        total_qualified_cost=750.00,
        estimated_credit=150.00,
        projects=[project],
        company_name=None  # No company name
    )
    
    generator = PDFGenerator()
    pdf_path = generator.generate_report(report, "outputs/reports/")
    
    print(f"✓ Report without company name generated: {pdf_path}")
    return pdf_path


def example_error_handling():
    """
    Example 6: Demonstrate error handling.
    """
    print("\n=== Example 6: Error Handling ===")
    
    project = QualifiedProject(
        project_name="Test Project",
        qualified_hours=5.0,
        qualified_cost=400.00,
        confidence_score=0.80,
        qualification_percentage=85.0,
        supporting_citation="Test citation.",
        reasoning="Test reasoning.",
        irs_source="Test source"
    )
    
    report = AuditReport(
        report_id="RPT-2024-006",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=5.0,
        total_qualified_cost=400.00,
        estimated_credit=80.00,
        projects=[project]
    )
    
    generator = PDFGenerator()
    
    # Try to generate with valid path
    try:
        pdf_path = generator.generate_report(report, "outputs/reports/")
        print(f"✓ Report generated successfully: {pdf_path}")
    except Exception as e:
        print(f"✗ Error generating report: {e}")
    
    # Try to generate with potentially invalid path (will create it)
    try:
        pdf_path = generator.generate_report(report, "outputs/new_folder/reports/")
        print(f"✓ Report generated in new directory: {pdf_path}")
    except Exception as e:
        print(f"✗ Error with new directory: {e}")


def main():
    """
    Run all examples.
    """
    print("=" * 60)
    print("PDF Generator Usage Examples")
    print("=" * 60)
    
    try:
        example_basic_report()
        example_custom_styling()
        example_multiple_projects()
        example_flagged_projects()
        example_no_company_name()
        example_error_handling()
        
        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
