# PDF Generator Utility

## Overview

The `PDFGenerator` class provides professional PDF report generation for R&D Tax Credit audit documentation using ReportLab. It creates multi-page reports with cover pages, executive summaries, project breakdowns, technical narratives, and IRS citations.

## Features

- **Professional Styling**: Customizable fonts, colors, and layout with consistent spacing
- **Table of Contents**: Automatically generated with bookmarks to major sections
- **Page Numbers**: Automatic page numbering with "Page X of Y" format
- **Headers & Footers**: Company name, report ID, generation date, and confidentiality notice
- **Company Logo**: Optional logo support with placeholder when not provided
- **Cover Page**: Report metadata and company information
- **Executive Summary**: Aggregated metrics and risk assessment
- **Project Sections**: Detailed breakdowns with qualification reasoning
- **IRS Citations**: Proper source attribution for audit defense
- **Automatic Flagging**: Visual indicators for low-confidence projects
- **Flexible Output**: Configurable output directory and filename

## Installation

The PDF generator requires ReportLab, which is included in `requirements.txt`:

```bash
pip install reportlab
```

## Basic Usage

```python
from datetime import datetime
from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport

# Create sample project
project = QualifiedProject(
    project_name="Alpha Development",
    qualified_hours=14.5,
    qualified_cost=1045.74,
    confidence_score=0.92,
    qualification_percentage=95.0,
    supporting_citation="The project involves developing...",
    reasoning="This project meets the four-part test...",
    irs_source="CFR Title 26 § 1.41-4(a)(1)"
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

# Generate PDF
generator = PDFGenerator()
pdf_path = generator.generate_report(report, "outputs/reports/")
print(f"Report generated: {pdf_path}")
```

## Advanced Usage

### Custom Styling

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

generator = PDFGenerator(
    page_size=A4,
    margin=1.0,  # inches
    title_font="Times-Bold",
    body_font="Times-Roman",
    font_size_title=20,
    font_size_heading=16,
    font_size_body=12,
    primary_color=colors.HexColor("#003366"),
    logo_path="path/to/company_logo.png"  # Optional company logo
)
```

### With Company Logo

```python
# Initialize with logo path
generator = PDFGenerator(logo_path="assets/company_logo.png")

# Generate report - logo will appear on cover page
pdf_path = generator.generate_report(report, "outputs/reports/")
```

**Logo Requirements:**
- Supported formats: PNG, JPG, GIF
- Recommended size: 200x100 pixels (2:1 aspect ratio)
- Will be scaled proportionally to fit 2" x 1" space
- If logo file not found, a placeholder will be shown

### Custom Filename

```python
pdf_path = generator.generate_report(
    report,
    "outputs/reports/",
    filename="custom_report_2024.pdf"
)
```

### Multiple Projects

```python
# Create multiple projects
projects = [project1, project2, project3]

# Calculate totals
total_hours = sum(p.qualified_hours for p in projects)
total_cost = sum(p.qualified_cost for p in projects)

report = AuditReport(
    report_id="RPT-2024-MULTI",
    generation_date=datetime.now(),
    tax_year=2024,
    total_qualified_hours=total_hours,
    total_qualified_cost=total_cost,
    estimated_credit=total_cost * 0.20,
    projects=projects,
    company_name="Multi-Project Corp"
)

pdf_path = generator.generate_report(report, "outputs/reports/")
```

## Report Structure

### 1. Cover Page
- Report title
- Company name (if provided)
- Tax year
- Report metadata table:
  - Report ID
  - Generation date
  - Total projects
  - Total qualified hours
  - Total qualified cost
  - Estimated credit

### 2. Executive Summary
- Overview text
- Key findings table:
  - Total qualified hours
  - Total qualified cost
  - Estimated R&D tax credit
  - Number of qualified projects
  - Average confidence score
  - Projects flagged for review
- Risk assessment (if applicable)
- Credit calculation note

### 3. Project Sections
For each qualified project:
- Project title with flag indicator
- Metrics table:
  - Qualified hours
  - Qualified cost
  - Qualification percentage
  - Confidence score
  - Estimated credit
- Qualification reasoning
- IRS citation
- Supporting documentation
- Technical details (if provided)

## Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page_size` | tuple | `letter` | Page size (letter, A4, etc.) |
| `margin` | float | `0.75` | Page margins in inches |
| `title_font` | str | `"Helvetica-Bold"` | Font for titles |
| `body_font` | str | `"Helvetica"` | Font for body text |
| `font_size_title` | int | `18` | Title font size |
| `font_size_heading` | int | `14` | Heading font size |
| `font_size_body` | int | `10` | Body text font size |
| `primary_color` | Color | `HexColor("#1a365d")` | Primary color for styling |

## Methods

### `__init__(**kwargs)`
Initialize the PDF generator with custom styling options.

### `generate_report(report, output_dir, filename=None)`
Generate the complete PDF audit report.

**Parameters:**
- `report` (AuditReport): Report data to generate PDF from
- `output_dir` (str): Directory path for output
- `filename` (str, optional): Custom filename (auto-generated if not provided)

**Returns:**
- `str`: Full path to generated PDF file

**Raises:**
- `IOError`: If output directory is not writable
- `ValueError`: If report contains invalid data

### `_create_cover_page(report)`
Create the cover page flowables (internal method).

### `_create_executive_summary(report)`
Create the executive summary flowables (internal method).

### `_create_project_section(project, project_number)`
Create a project section flowables (internal method).

## Error Handling

The PDF generator includes comprehensive error handling:

```python
try:
    pdf_path = generator.generate_report(report, "outputs/reports/")
    print(f"Success: {pdf_path}")
except IOError as e:
    print(f"IO Error: {e}")
except ValueError as e:
    print(f"Invalid data: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Styling and Formatting Features

### Consistent Styling

The PDF generator ensures professional appearance through:

**Colors:**
- Primary color (default: dark blue #1a365d) used for headings and accents
- Consistent color scheme throughout the document
- Customizable via `primary_color` parameter

**Fonts:**
- Title font (default: Helvetica-Bold) for headings
- Body font (default: Helvetica) for content
- Consistent font sizes: Title (18pt), Heading (14pt), Body (10pt)

**Spacing:**
- Consistent margins (default: 0.75 inches)
- Proper spacing between sections
- Professional line spacing for readability

### Table of Contents

Automatically generated table of contents with:
- Bookmarks to all major sections
- Page number references
- Two-level hierarchy (main sections and subsections)
- Clickable links in PDF viewers

**Sections included:**
1. Executive Summary
2. Project Breakdown Summary
3. Qualified Research Projects
4. Technical Project Narratives
5. IRS Citations and References
6. Appendices

### Headers and Footers

Every page (except cover) includes:

**Header:**
- Company name and report title (left side)
- Report ID (right side)
- Horizontal line separator

**Footer:**
- Generation date (left side)
- Page number "Page X of Y" (center)
- Confidentiality notice (right side)
- Horizontal line separator

### Company Logo

Optional logo support on cover page:
- Displays at top of cover page
- Scales proportionally to 2" x 1" space
- Falls back to placeholder if logo not found
- Supports PNG, JPG, GIF formats

## Testing

Run the test suite:

```bash
pytest tests/test_pdf_generator.py -v
```

Test coverage includes:
- Initialization with default and custom settings
- Cover page generation with logo and placeholder
- Table of contents generation
- Headers and footers with page numbers
- Executive summary generation
- Project section generation
- Full report generation with various scenarios
- Styling consistency (colors, fonts, spacing)
- Error handling

## Performance

- Typical report generation time: < 1 second for 10 projects
- Maximum recommended projects per report: 50
- PDF file size: ~5-10 KB per project

## Integration with Audit Trail Agent

The PDF generator is designed to be used by the Audit Trail Agent:

```python
from agents.audit_trail_agent import AuditTrailAgent
from utils.pdf_generator import PDFGenerator

# Initialize PDF generator
pdf_generator = PDFGenerator()

# Initialize Audit Trail Agent with PDF generator
agent = AuditTrailAgent(
    youcom_client=youcom_client,
    glm_reasoner=glm_reasoner,
    pdf_generator=pdf_generator
)

# Agent will use PDF generator to create reports
result = await agent.run(qualified_projects)
```

## Troubleshooting

### Issue: PDF not generated
**Solution:** Check that the output directory exists and is writable.

### Issue: Fonts not rendering correctly
**Solution:** Ensure ReportLab is properly installed. Try reinstalling:
```bash
pip install --upgrade reportlab
```

### Issue: Large file sizes
**Solution:** Reduce the number of projects per report or optimize technical details.

### Issue: Missing content in PDF
**Solution:** Verify that all required fields in QualifiedProject and AuditReport are populated.

## Requirements

- Python 3.8+
- ReportLab 4.4.4+
- Pydantic 2.10+

## Related Documentation

- [Tax Models README](../models/TAX_MODELS_README.md)
- [Audit Trail Agent README](../agents/AUDIT_TRAIL_AGENT_README.md)
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)

## License

Part of the R&D Tax Credit Automation Agent project.
