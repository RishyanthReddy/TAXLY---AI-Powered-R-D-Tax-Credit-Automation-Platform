"""
PDF Generator utility for R&D Tax Credit Audit Reports.

This module provides the PDFGenerator class for creating professional,
audit-ready PDF reports using ReportLab. The generator creates multi-page
reports with cover pages, executive summaries, project breakdowns, technical
narratives, and IRS citations.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from io import BytesIO

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfgen import canvas

from models.tax_models import QualifiedProject, AuditReport
from utils.logger import AgentLogger

# Initialize logger
AgentLogger.initialize()
logger = AgentLogger.get_logger("utils.pdf_generator")


class PDFGenerator:
    """
    PDF Generator for R&D Tax Credit Audit Reports.
    
    This class uses ReportLab to create professional, audit-ready PDF reports
    containing executive summaries, project breakdowns, technical narratives,
    and IRS citations. The generator supports customizable styling and can
    handle reports with up to 50+ qualified projects.
    
    Attributes:
        page_size: Page size for the PDF (default: letter)
        margin: Page margins in inches (default: 0.75)
        title_font: Font for titles (default: Helvetica-Bold)
        body_font: Font for body text (default: Helvetica)
        font_size_title: Font size for titles (default: 18)
        font_size_heading: Font size for headings (default: 14)
        font_size_body: Font size for body text (default: 10)
        primary_color: Primary color for styling (default: dark blue)
        
    Example:
        >>> from datetime import datetime
        >>> generator = PDFGenerator()
        >>> report = AuditReport(
        ...     report_id="RPT-2024-001",
        ...     generation_date=datetime.now(),
        ...     tax_year=2024,
        ...     total_qualified_hours=145.5,
        ...     total_qualified_cost=10457.40,
        ...     estimated_credit=2091.48,
        ...     projects=[...],
        ...     company_name="Acme Corp"
        ... )
        >>> pdf_path = generator.generate_report(report, "outputs/reports/")
        >>> print(f"Report generated: {pdf_path}")
    """
    
    def __init__(
        self,
        page_size=letter,
        margin: float = 0.75,
        title_font: str = "Helvetica-Bold",
        body_font: str = "Helvetica",
        font_size_title: int = 18,
        font_size_heading: int = 14,
        font_size_body: int = 10,
        primary_color: colors.Color = colors.HexColor("#1a365d")
    ):
        """
        Initialize the PDF Generator with styling options.
        
        Args:
            page_size: Page size tuple (default: letter)
            margin: Page margins in inches (default: 0.75)
            title_font: Font for titles (default: Helvetica-Bold)
            body_font: Font for body text (default: Helvetica)
            font_size_title: Font size for titles (default: 18)
            font_size_heading: Font size for headings (default: 14)
            font_size_body: Font size for body text (default: 10)
            primary_color: Primary color for styling (default: dark blue)
        """
        self.page_size = page_size
        self.margin = margin * inch
        self.title_font = title_font
        self.body_font = body_font
        self.font_size_title = font_size_title
        self.font_size_heading = font_size_heading
        self.font_size_body = font_size_body
        self.primary_color = primary_color
        
        # Initialize styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        logger.info("PDFGenerator initialized with custom styling")
    
    def _setup_custom_styles(self):
        """
        Set up custom paragraph styles for the PDF report.
        
        Creates custom styles for titles, headings, body text, and other
        elements used throughout the report.
        """
        # Custom title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontName=self.title_font,
            fontSize=self.font_size_title,
            textColor=self.primary_color,
            alignment=TA_CENTER,
            spaceAfter=12
        ))
        
        # Custom heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading1'],
            fontName=self.title_font,
            fontSize=self.font_size_heading,
            textColor=self.primary_color,
            spaceBefore=12,
            spaceAfter=6
        ))
        
        # Custom subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubheading',
            parent=self.styles['Heading2'],
            fontName=self.title_font,
            fontSize=self.font_size_body + 2,
            textColor=self.primary_color,
            spaceBefore=8,
            spaceAfter=4
        ))
        
        # Custom body style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontName=self.body_font,
            fontSize=self.font_size_body,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))
        
        # Custom citation style
        self.styles.add(ParagraphStyle(
            name='Citation',
            parent=self.styles['BodyText'],
            fontName=self.body_font,
            fontSize=self.font_size_body - 1,
            textColor=colors.grey,
            leftIndent=20,
            spaceAfter=4
        ))
        
        logger.debug("Custom PDF styles configured")
    
    def _create_cover_page(self, report: AuditReport) -> List:
        """
        Create the cover page for the audit report.
        
        The cover page includes the report title, company name, tax year,
        generation date, and report ID. It uses centered alignment and
        professional styling.
        
        Args:
            report: AuditReport object containing report metadata
            
        Returns:
            List of ReportLab flowables for the cover page
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> cover_elements = generator._create_cover_page(report)
        """
        elements = []
        
        # Add vertical spacing
        elements.append(Spacer(1, 2 * inch))
        
        # Main title
        title = Paragraph(
            "R&D Tax Credit<br/>Audit Report",
            self.styles['CustomTitle']
        )
        elements.append(title)
        elements.append(Spacer(1, 0.5 * inch))
        
        # Company name (if provided)
        if report.company_name:
            company = Paragraph(
                f"<b>{report.company_name}</b>",
                ParagraphStyle(
                    name='CompanyName',
                    parent=self.styles['CustomBody'],
                    fontSize=self.font_size_heading,
                    alignment=TA_CENTER,
                    textColor=self.primary_color
                )
            )
            elements.append(company)
            elements.append(Spacer(1, 0.3 * inch))
        
        # Tax year
        tax_year = Paragraph(
            f"<b>Tax Year {report.tax_year}</b>",
            ParagraphStyle(
                name='TaxYear',
                parent=self.styles['CustomBody'],
                fontSize=self.font_size_heading - 2,
                alignment=TA_CENTER
            )
        )
        elements.append(tax_year)
        elements.append(Spacer(1, 1 * inch))
        
        # Report metadata table
        metadata_data = [
            ['Report ID:', report.report_id],
            ['Generation Date:', report.generation_date.strftime('%B %d, %Y')],
            ['Total Projects:', str(report.project_count)],
            ['Total Qualified Hours:', f"{report.total_qualified_hours:,.1f}"],
            ['Total Qualified Cost:', f"${report.total_qualified_cost:,.2f}"],
            ['Estimated Credit:', f"${report.estimated_credit:,.2f}"]
        ]
        
        metadata_table = Table(
            metadata_data,
            colWidths=[2.5 * inch, 3 * inch],
            hAlign='CENTER'
        )
        
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), self.title_font),
            ('FONTNAME', (1, 0), (1, -1), self.body_font),
            ('FONTSIZE', (0, 0), (-1, -1), self.font_size_body),
            ('TEXTCOLOR', (0, 0), (0, -1), self.primary_color),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(metadata_table)
        
        # Add page break after cover
        elements.append(PageBreak())
        
        logger.debug(f"Cover page created for report {report.report_id}")
        return elements
    
    def _create_executive_summary(self, report: AuditReport) -> List:
        """
        Create the executive summary section of the audit report.
        
        The executive summary provides a high-level overview of the R&D tax
        credit qualification results, including total qualified expenditures,
        estimated credit amount, project count, average confidence score,
        and any flagged projects requiring review.
        
        Args:
            report: AuditReport object containing aggregated data
            
        Returns:
            List of ReportLab flowables for the executive summary
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> summary_elements = generator._create_executive_summary(report)
        """
        elements = []
        
        # Section title
        title = Paragraph("Executive Summary", self.styles['CustomHeading'])
        elements.append(title)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Summary text
        summary_text = f"""
        This report documents the qualified research expenditures (QREs) for 
        <b>{report.company_name or 'the company'}</b> for tax year <b>{report.tax_year}</b>. 
        The analysis identified <b>{report.project_count}</b> qualified research project(s) 
        that meet the IRS four-part test for R&D tax credit eligibility.
        """
        
        summary_para = Paragraph(summary_text, self.styles['CustomBody'])
        elements.append(summary_para)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Key findings table
        findings_data = [
            ['Metric', 'Value'],
            ['Total Qualified Hours', f"{report.total_qualified_hours:,.1f}"],
            ['Total Qualified Cost', f"${report.total_qualified_cost:,.2f}"],
            ['Estimated R&D Tax Credit', f"${report.estimated_credit:,.2f}"],
            ['Number of Qualified Projects', str(report.project_count)],
            ['Average Confidence Score', f"{report.average_confidence:.2f}"],
            ['Projects Flagged for Review', str(report.flagged_project_count)]
        ]
        
        findings_table = Table(
            findings_data,
            colWidths=[3.5 * inch, 2.5 * inch],
            hAlign='LEFT'
        )
        
        findings_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.title_font),
            ('FONTSIZE', (0, 0), (-1, 0), self.font_size_body + 1),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Data rows
            ('FONTNAME', (0, 1), (0, -1), self.title_font),
            ('FONTNAME', (1, 1), (1, -1), self.body_font),
            ('FONTSIZE', (0, 1), (-1, -1), self.font_size_body),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Borders and padding
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            # Highlight estimated credit row
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#e6f2ff")),
            ('FONTNAME', (0, 3), (-1, 3), self.title_font),
        ]))
        
        elements.append(findings_table)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Risk assessment (if any projects flagged)
        if report.flagged_project_count > 0:
            risk_text = f"""
            <b>Risk Assessment:</b> {report.flagged_project_count} project(s) have been 
            flagged for manual review due to confidence scores below 0.7. These projects 
            may require additional documentation or clarification to support the R&D 
            qualification decision during an IRS audit.
            """
            risk_para = Paragraph(risk_text, self.styles['CustomBody'])
            elements.append(risk_para)
            elements.append(Spacer(1, 0.1 * inch))
        
        # Credit calculation note
        credit_note = """
        <b>Note:</b> The estimated R&D tax credit is calculated at 20% of qualified 
        research expenditures (QREs), representing the regular credit rate under 
        IRC Section 41. Actual credit amounts may vary based on the alternative 
        simplified credit (ASC) calculation or other factors. Consult with a tax 
        professional for final credit determination.
        """
        note_para = Paragraph(credit_note, self.styles['CustomBody'])
        elements.append(note_para)
        
        # Add page break after executive summary
        elements.append(PageBreak())
        
        logger.debug(f"Executive summary created with {report.project_count} projects")
        return elements
    
    def _create_project_section(self, project: QualifiedProject, project_number: int) -> List:
        """
        Create a detailed section for a single qualified project.
        
        This method generates a comprehensive project breakdown including
        project name, qualification metrics, confidence score, technical
        reasoning, and IRS citations. Each project section is formatted
        consistently and includes all information needed for audit defense.
        
        Args:
            project: QualifiedProject object containing project data
            project_number: Sequential number for this project in the report
            
        Returns:
            List of ReportLab flowables for the project section
            
        Example:
            >>> generator = PDFGenerator()
            >>> project = QualifiedProject(...)
            >>> project_elements = generator._create_project_section(project, 1)
        """
        elements = []
        
        # Project title with flag indicator
        flag_indicator = " [FLAGGED FOR REVIEW]" if project.flagged_for_review else ""
        project_title = f"Project {project_number}: {project.project_name}{flag_indicator}"
        
        title_style = ParagraphStyle(
            name=f'ProjectTitle{project_number}',
            parent=self.styles['CustomHeading'],
            textColor=colors.red if project.flagged_for_review else self.primary_color
        )
        
        title = Paragraph(project_title, title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.1 * inch))
        
        # Project metrics table
        metrics_data = [
            ['Qualified Hours:', f"{project.qualified_hours:,.1f}"],
            ['Qualified Cost:', f"${project.qualified_cost:,.2f}"],
            ['Qualification Percentage:', f"{project.qualification_percentage:.1f}%"],
            ['Confidence Score:', f"{project.confidence_score:.2f}"],
            ['Estimated Credit:', f"${project.estimated_credit:,.2f}"]
        ]
        
        metrics_table = Table(
            metrics_data,
            colWidths=[2 * inch, 2 * inch],
            hAlign='LEFT'
        )
        
        metrics_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), self.title_font),
            ('FONTNAME', (1, 0), (1, -1), self.body_font),
            ('FONTSIZE', (0, 0), (-1, -1), self.font_size_body),
            ('TEXTCOLOR', (0, 0), (0, -1), self.primary_color),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.15 * inch))
        
        # Qualification reasoning
        reasoning_heading = Paragraph(
            "<b>Qualification Reasoning:</b>",
            self.styles['CustomSubheading']
        )
        elements.append(reasoning_heading)
        
        reasoning_text = Paragraph(project.reasoning, self.styles['CustomBody'])
        elements.append(reasoning_text)
        elements.append(Spacer(1, 0.1 * inch))
        
        # IRS citation
        citation_heading = Paragraph(
            "<b>IRS Citation:</b>",
            self.styles['CustomSubheading']
        )
        elements.append(citation_heading)
        
        citation_text = Paragraph(
            f"<i>{project.irs_source}</i>",
            self.styles['Citation']
        )
        elements.append(citation_text)
        elements.append(Spacer(1, 0.1 * inch))
        
        # Supporting citation
        support_heading = Paragraph(
            "<b>Supporting Documentation:</b>",
            self.styles['CustomSubheading']
        )
        elements.append(support_heading)
        
        support_text = Paragraph(
            project.supporting_citation,
            self.styles['CustomBody']
        )
        elements.append(support_text)
        
        # Technical details (if provided)
        if project.technical_details:
            elements.append(Spacer(1, 0.1 * inch))
            tech_heading = Paragraph(
                "<b>Technical Details:</b>",
                self.styles['CustomSubheading']
            )
            elements.append(tech_heading)
            
            for key, value in project.technical_details.items():
                # Format key as readable text
                formatted_key = key.replace('_', ' ').title()
                detail_text = f"<b>{formatted_key}:</b> {value}"
                detail_para = Paragraph(detail_text, self.styles['CustomBody'])
                elements.append(detail_para)
        
        # Add spacing between projects
        elements.append(Spacer(1, 0.3 * inch))
        
        logger.debug(f"Project section created for: {project.project_name}")
        return elements
    
    def generate_report(
        self,
        report: AuditReport,
        output_dir: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Generate the complete PDF audit report.
        
        This method orchestrates the creation of the full PDF report by
        combining the cover page, executive summary, and all project sections.
        The report is saved to the specified output directory.
        
        Args:
            report: AuditReport object containing all report data
            output_dir: Directory path where the PDF will be saved
            filename: Optional custom filename (default: auto-generated from report_id)
            
        Returns:
            Full path to the generated PDF file
            
        Raises:
            IOError: If the output directory doesn't exist or isn't writable
            ValueError: If the report contains invalid data
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> pdf_path = generator.generate_report(
            ...     report,
            ...     "outputs/reports/",
            ...     "custom_report.pdf"
            ... )
            >>> print(f"Report saved to: {pdf_path}")
        """
        try:
            # Create output directory if it doesn't exist
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"rd_tax_credit_report_{report.report_id}_{timestamp}.pdf"
            
            # Full path to output file
            pdf_path = output_path / filename
            
            logger.info(f"Generating PDF report: {pdf_path}")
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=self.page_size,
                leftMargin=self.margin,
                rightMargin=self.margin,
                topMargin=self.margin,
                bottomMargin=self.margin
            )
            
            # Build document elements
            elements = []
            
            # Add cover page
            elements.extend(self._create_cover_page(report))
            
            # Add executive summary
            elements.extend(self._create_executive_summary(report))
            
            # Add project sections
            if report.projects:
                # Projects heading
                projects_title = Paragraph(
                    "Qualified Research Projects",
                    self.styles['CustomHeading']
                )
                elements.append(projects_title)
                elements.append(Spacer(1, 0.2 * inch))
                
                # Add each project
                for i, project in enumerate(report.projects, 1):
                    project_elements = self._create_project_section(project, i)
                    elements.extend(project_elements)
                    
                    # Add page break between projects (except last one)
                    if i < len(report.projects):
                        elements.append(PageBreak())
            
            # Build the PDF
            doc.build(elements)
            
            logger.info(f"PDF report generated successfully: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
            raise
    
    def __str__(self) -> str:
        """Return string representation of the PDF generator."""
        return f"PDFGenerator(page_size={self.page_size}, margin={self.margin/inch}in)"


# Example usage
if __name__ == "__main__":
    from datetime import datetime
    
    # Create sample data
    sample_project = QualifiedProject(
        project_name="Alpha Development",
        qualified_hours=14.5,
        qualified_cost=1045.74,
        confidence_score=0.92,
        qualification_percentage=95.0,
        supporting_citation="The project involves developing a new authentication algorithm...",
        reasoning="This project clearly meets the four-part test...",
        irs_source="CFR Title 26 § 1.41-4(a)(1)",
        technical_details={
            "technological_uncertainty": "Uncertainty about optimal encryption approach",
            "experimentation_process": "Systematic evaluation of authentication methods"
        }
    )
    
    sample_report = AuditReport(
        report_id="RPT-2024-001",
        generation_date=datetime.now(),
        tax_year=2024,
        total_qualified_hours=14.5,
        total_qualified_cost=1045.74,
        estimated_credit=209.15,
        projects=[sample_project],
        company_name="Acme Corporation"
    )
    
    # Generate PDF
    generator = PDFGenerator()
    pdf_path = generator.generate_report(sample_report, "outputs/reports/")
    print(f"Sample report generated: {pdf_path}")
