"""
Example demonstrating PDF styling and formatting features.

This example shows how to use the enhanced PDF generator with:
- Table of contents
- Page numbers and headers/footers
- Company logo (or placeholder)
- Consistent styling
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport
from reportlab.lib import colors


def create_sample_projects():
    """Create sample projects for demonstration."""
    projects = [
        QualifiedProject(
            project_name="Cloud Infrastructure Optimization",
            qualified_hours=45.5,
            qualified_cost=3275.50,
            confidence_score=0.95,
            qualification_percentage=98.0,
            supporting_citation="The project involved developing novel algorithms for resource allocation...",
            reasoning="This project clearly meets the four-part test: (1) Technological uncertainty existed regarding optimal resource allocation, (2) Process of experimentation was systematic, (3) Work was technological in nature, (4) Purpose was to create new functionality.",
            irs_source="CFR Title 26 § 1.41-4(a)(1)",
            technical_details={
                "technological_uncertainty": "Uncertainty about optimal load balancing algorithms",
                "experimentation_process": "Systematic testing of multiple allocation strategies",
                "business_component": "Cloud resource management system"
            }
        ),
        QualifiedProject(
            project_name="Machine Learning Model Development",
            qualified_hours=62.0,
            qualified_cost=4464.00,
            confidence_score=0.88,
            qualification_percentage=92.0,
            supporting_citation="Development of proprietary ML algorithms for predictive analytics...",
            reasoning="Project involved substantial experimentation with novel neural network architectures to solve previously unsolved problems in predictive accuracy.",
            irs_source="CFR Title 26 § 1.41-4(a)(2)",
            technical_details={
                "technological_uncertainty": "Uncertainty about model architecture for specific use case",
                "experimentation_process": "Iterative testing of various neural network designs",
                "business_component": "Predictive analytics engine"
            }
        ),
        QualifiedProject(
            project_name="Security Protocol Enhancement",
            qualified_hours=28.0,
            qualified_cost=2016.00,
            confidence_score=0.82,
            qualification_percentage=85.0,
            supporting_citation="Enhanced encryption protocols for data transmission security...",
            reasoning="Project involved research into novel encryption methods to address specific security vulnerabilities not addressed by existing solutions.",
            irs_source="CFR Title 26 § 1.41-4(a)(3)",
            technical_details={
                "technological_uncertainty": "Uncertainty about encryption performance vs. security trade-offs",
                "experimentation_process": "Systematic evaluation of encryption algorithms",
                "business_component": "Secure communication module"
            }
        )
    ]
    
    return projects


def example_basic_styling():
    """Example 1: Basic PDF with default styling."""
    print("\n=== Example 1: Basic PDF with Default Styling ===")
    
    projects = create_sample_projects()
    
    # Calculate totals
    total_hours = sum(p.qualified_hours for p in projects)
    total_cost = sum(p.qualified_cost for p in projects)
    
    # Create report
    report = AuditReport(
        report_id="RPT-2024-STYLE-001",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        projects=projects,
        company_name="TechCorp Industries"
    )
    
    # Generate PDF with default styling
    generator = PDFGenerator()
    pdf_path = generator.generate_report(report, "outputs/reports/")
    
    print(f"✓ Generated PDF with default styling: {pdf_path}")
    print(f"  - Table of contents: Included")
    print(f"  - Page numbers: Automatic")
    print(f"  - Headers/footers: Included")
    print(f"  - Logo: Placeholder shown")


def example_custom_styling():
    """Example 2: PDF with custom styling."""
    print("\n=== Example 2: PDF with Custom Styling ===")
    
    projects = create_sample_projects()
    
    # Calculate totals
    total_hours = sum(p.qualified_hours for p in projects)
    total_cost = sum(p.qualified_cost for p in projects)
    
    # Create report
    report = AuditReport(
        report_id="RPT-2024-STYLE-002",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        projects=projects,
        company_name="Innovation Labs LLC"
    )
    
    # Generate PDF with custom styling
    generator = PDFGenerator(
        margin=1.0,  # Wider margins
        font_size_title=20,  # Larger title
        font_size_heading=15,  # Larger headings
        font_size_body=11,  # Larger body text
        primary_color=colors.HexColor("#003366")  # Navy blue
    )
    
    pdf_path = generator.generate_report(
        report,
        "outputs/reports/",
        filename="custom_styled_report.pdf"
    )
    
    print(f"✓ Generated PDF with custom styling: {pdf_path}")
    print(f"  - Margins: 1.0 inches")
    print(f"  - Title size: 20pt")
    print(f"  - Primary color: Navy blue (#003366)")
    print(f"  - Custom filename: custom_styled_report.pdf")


def example_with_logo():
    """Example 3: PDF with company logo (or placeholder)."""
    print("\n=== Example 3: PDF with Company Logo ===")
    
    projects = create_sample_projects()[:2]  # Use first 2 projects
    
    # Calculate totals
    total_hours = sum(p.qualified_hours for p in projects)
    total_cost = sum(p.qualified_cost for p in projects)
    
    # Create report
    report = AuditReport(
        report_id="RPT-2024-STYLE-003",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        projects=projects,
        company_name="Acme Corporation"
    )
    
    # Try to use logo (will show placeholder if not found)
    logo_path = "assets/company_logo.png"  # This file doesn't exist
    
    generator = PDFGenerator(logo_path=logo_path)
    pdf_path = generator.generate_report(report, "outputs/reports/")
    
    print(f"✓ Generated PDF with logo support: {pdf_path}")
    print(f"  - Logo path: {logo_path}")
    print(f"  - Logo status: Placeholder shown (file not found)")
    print(f"  - Note: Place actual logo at specified path to display it")


def example_professional_report():
    """Example 4: Complete professional report with all features."""
    print("\n=== Example 4: Complete Professional Report ===")
    
    projects = create_sample_projects()
    
    # Calculate totals
    total_hours = sum(p.qualified_hours for p in projects)
    total_cost = sum(p.qualified_cost for p in projects)
    
    # Create comprehensive report
    report = AuditReport(
        report_id="RPT-2024-PROFESSIONAL",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=total_hours,
        total_qualified_cost=total_cost,
        estimated_credit=total_cost * 0.20,
        projects=projects,
        company_name="Enterprise Solutions Inc.",
        report_notes="This report demonstrates all professional styling features."
    )
    
    # Create generator with professional styling
    generator = PDFGenerator(
        margin=0.75,
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        font_size_title=18,
        font_size_heading=14,
        font_size_body=10,
        primary_color=colors.HexColor("#1a365d")  # Professional dark blue
    )
    
    pdf_path = generator.generate_report(
        report,
        "outputs/reports/",
        filename="professional_audit_report.pdf"
    )
    
    print(f"✓ Generated professional audit report: {pdf_path}")
    print(f"\nReport includes:")
    print(f"  ✓ Cover page with company name and metadata")
    print(f"  ✓ Table of contents with page numbers")
    print(f"  ✓ Executive summary with key metrics")
    print(f"  ✓ Project breakdown summary table")
    print(f"  ✓ Detailed project sections ({len(projects)} projects)")
    print(f"  ✓ Technical narratives for each project")
    print(f"  ✓ IRS citations and references")
    print(f"  ✓ Appendices with detailed data")
    print(f"  ✓ Headers with company name and report ID")
    print(f"  ✓ Footers with page numbers and date")
    print(f"  ✓ Consistent styling throughout")


def main():
    """Run all examples."""
    print("=" * 70)
    print("PDF Styling and Formatting Examples")
    print("=" * 70)
    
    # Create output directory
    Path("outputs/reports").mkdir(parents=True, exist_ok=True)
    
    # Run examples
    example_basic_styling()
    example_custom_styling()
    example_with_logo()
    example_professional_report()
    
    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("Check the 'outputs/reports/' directory for generated PDFs.")
    print("=" * 70)


if __name__ == "__main__":
    main()
