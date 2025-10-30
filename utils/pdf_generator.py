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
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas

from models.tax_models import QualifiedProject, AuditReport
from utils.logger import AgentLogger

# Initialize logger
AgentLogger.initialize()
logger = AgentLogger.get_logger("utils.pdf_generator")


class NumberedCanvas(canvas.Canvas):
    """
    Custom canvas class for adding page numbers and headers/footers.
    
    This class extends ReportLab's Canvas to automatically add page numbers,
    headers, and footers to each page of the PDF report.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the canvas with custom properties."""
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.company_name = kwargs.get('company_name', '')
        self.report_id = kwargs.get('report_id', '')
        self.primary_color = kwargs.get('primary_color', colors.HexColor("#1a365d"))
    
    def showPage(self):
        """
        Override showPage to save page state before showing.
        This allows us to add headers/footers after all content is drawn.
        """
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
    
    def save(self):
        """
        Override save to add headers/footers to all pages before saving.
        """
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    
    def draw_page_decorations(self, page_count):
        """
        Draw headers, footers, and page numbers on the current page.
        
        Args:
            page_count: Total number of pages in the document
        """
        page_num = self._pageNumber
        
        # Skip decorations on cover page (page 1)
        if page_num == 1:
            return
        
        # Get page dimensions
        page_width, page_height = letter
        
        # Draw header line
        self.setStrokeColor(self.primary_color)
        self.setLineWidth(1)
        self.line(0.75 * inch, page_height - 0.5 * inch, 
                 page_width - 0.75 * inch, page_height - 0.5 * inch)
        
        # Draw header text (company name on left, report ID on right)
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        
        if self.company_name:
            self.drawString(0.75 * inch, page_height - 0.45 * inch, 
                          f"{self.company_name} - R&D Tax Credit Report")
        else:
            self.drawString(0.75 * inch, page_height - 0.45 * inch, 
                          "R&D Tax Credit Report")
        
        if self.report_id:
            self.drawRightString(page_width - 0.75 * inch, page_height - 0.45 * inch, 
                               f"Report ID: {self.report_id}")
        
        # Draw footer line
        self.setStrokeColor(self.primary_color)
        self.setLineWidth(1)
        self.line(0.75 * inch, 0.75 * inch, 
                 page_width - 0.75 * inch, 0.75 * inch)
        
        # Draw page number in footer
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        footer_text = f"Page {page_num} of {page_count}"
        self.drawCentredString(page_width / 2, 0.6 * inch, footer_text)
        
        # Draw generation date in footer (left side)
        from datetime import datetime
        gen_date = datetime.now().strftime("%B %d, %Y")
        self.drawString(0.75 * inch, 0.6 * inch, f"Generated: {gen_date}")
        
        # Draw confidentiality notice in footer (right side)
        self.drawRightString(page_width - 0.75 * inch, 0.6 * inch, "Confidential")


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
        primary_color: colors.Color = colors.HexColor("#1a365d"),
        logo_path: Optional[str] = None
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
            logo_path: Optional path to company logo image file
        """
        self.page_size = page_size
        self.margin = margin * inch
        self.title_font = title_font
        self.body_font = body_font
        self.font_size_title = font_size_title
        self.font_size_heading = font_size_heading
        self.font_size_body = font_size_body
        self.primary_color = primary_color
        self.logo_path = logo_path
        
        # Initialize styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Initialize table of contents
        self.toc = TableOfContents()
        self._setup_toc_styles()
        
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
    
    def _setup_toc_styles(self):
        """
        Set up table of contents styles.
        
        Creates custom styles for the table of contents entries at different
        levels (main sections, subsections, etc.).
        """
        # TOC heading style
        self.styles.add(ParagraphStyle(
            name='TOCHeading',
            parent=self.styles['CustomHeading'],
            fontSize=self.font_size_heading + 2,
            spaceAfter=12
        ))
        
        # TOC level 1 (main sections)
        self.styles.add(ParagraphStyle(
            name='TOCEntry1',
            parent=self.styles['CustomBody'],
            fontName=self.title_font,
            fontSize=self.font_size_body + 1,
            leftIndent=0,
            spaceAfter=6
        ))
        
        # TOC level 2 (subsections)
        self.styles.add(ParagraphStyle(
            name='TOCEntry2',
            parent=self.styles['CustomBody'],
            fontSize=self.font_size_body,
            leftIndent=20,
            spaceAfter=4
        ))
        
        logger.debug("Table of contents styles configured")
    
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
        
        # Add company logo if provided
        if self.logo_path and Path(self.logo_path).exists():
            try:
                logo = Image(self.logo_path, width=2*inch, height=1*inch, kind='proportional')
                logo.hAlign = 'CENTER'
                elements.append(Spacer(1, 0.5 * inch))
                elements.append(logo)
                elements.append(Spacer(1, 0.5 * inch))
            except Exception as e:
                logger.warning(f"Failed to load logo from {self.logo_path}: {e}")
                elements.append(Spacer(1, 1.5 * inch))
        else:
            # Logo placeholder
            elements.append(Spacer(1, 0.5 * inch))
            logo_placeholder = Table(
                [['[Company Logo]']],
                colWidths=[2 * inch],
                rowHeights=[1 * inch],
                hAlign='CENTER'
            )
            logo_placeholder.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOX', (0, 0), (-1, -1), 1, colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Oblique'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))
            elements.append(logo_placeholder)
            elements.append(Spacer(1, 0.5 * inch))
        
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
    
    def _create_table_of_contents(self) -> List:
        """
        Create the table of contents for the audit report.
        
        The table of contents provides a navigable index of all major sections
        in the report with page numbers. It is automatically populated based
        on the document structure.
        
        Returns:
            List of ReportLab flowables for the table of contents
            
        Example:
            >>> generator = PDFGenerator()
            >>> toc_elements = generator._create_table_of_contents()
        """
        elements = []
        
        # TOC title
        toc_title = Paragraph("Table of Contents", self.styles['TOCHeading'])
        elements.append(toc_title)
        elements.append(Spacer(1, 0.3 * inch))
        
        # Configure the TOC
        self.toc.levelStyles = [
            self.styles['TOCEntry1'],
            self.styles['TOCEntry2']
        ]
        
        # Add the TOC flowable
        elements.append(self.toc)
        
        # Add page break after TOC
        elements.append(PageBreak())
        
        logger.debug("Table of contents created")
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
        # Log data access for verification
        logger.info("Creating executive summary")
        logger.info(f"  Accessing report.total_qualified_hours: {report.total_qualified_hours}")
        logger.info(f"  Accessing report.total_qualified_cost: {report.total_qualified_cost}")
        logger.info(f"  Accessing report.estimated_credit: {report.estimated_credit}")
        logger.info(f"  Accessing report.average_confidence: {report.average_confidence}")
        logger.info(f"  Accessing report.project_count: {report.project_count}")
        logger.info(f"  Accessing report.flagged_project_count: {report.flagged_project_count}")
        
        if report.aggregated_data:
            logger.info(f"  Aggregated data available with keys: {list(report.aggregated_data.keys())}")
            if 'high_confidence_count' in report.aggregated_data:
                logger.info(f"    high_confidence_count: {report.aggregated_data['high_confidence_count']}")
            if 'medium_confidence_count' in report.aggregated_data:
                logger.info(f"    medium_confidence_count: {report.aggregated_data['medium_confidence_count']}")
            if 'low_confidence_count' in report.aggregated_data:
                logger.info(f"    low_confidence_count: {report.aggregated_data['low_confidence_count']}")
        else:
            logger.warning("  No aggregated_data available in report")
        
        elements = []
        
        # Section title with bookmark for TOC
        title = Paragraph(
            '<a name="executive_summary"/>Executive Summary',
            self.styles['CustomHeading']
        )
        elements.append(title)
        self.toc.addEntry(1, 'Executive Summary', 'executive_summary')
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
        
        # Add additional stats from aggregated_data if available
        if report.aggregated_data:
            # Add confidence breakdown if available
            if 'high_confidence_count' in report.aggregated_data:
                findings_data.append([
                    'High Confidence Projects (≥0.8)',
                    str(report.aggregated_data.get('high_confidence_count', 0))
                ])
            if 'medium_confidence_count' in report.aggregated_data:
                findings_data.append([
                    'Medium Confidence Projects (0.7-0.8)',
                    str(report.aggregated_data.get('medium_confidence_count', 0))
                ])
            if 'low_confidence_count' in report.aggregated_data:
                findings_data.append([
                    'Low Confidence Projects (<0.7)',
                    str(report.aggregated_data.get('low_confidence_count', 0))
                ])
        
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
    
    def _create_project_section(self, project: QualifiedProject, project_number: int, report: AuditReport) -> List:
        """
        Create a detailed section for a single qualified project.
        
        This method generates a comprehensive project breakdown including
        project name, qualification metrics, confidence score, technical
        reasoning, IRS citations, technical narrative, and compliance review.
        Each project section is formatted consistently and includes all 
        information needed for audit defense.
        
        Args:
            project: QualifiedProject object containing project data
            project_number: Sequential number for this project in the report
            report: AuditReport object containing narratives and compliance reviews
            
        Returns:
            List of ReportLab flowables for the project section
            
        Example:
            >>> generator = PDFGenerator()
            >>> project = QualifiedProject(...)
            >>> report = AuditReport(...)
            >>> project_elements = generator._create_project_section(project, 1, report)
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
        elements.append(Spacer(1, 0.15 * inch))
        
        # **CRITICAL**: Add technical narrative from report.narratives
        if report.narratives and project.project_name in report.narratives:
            narrative_heading = Paragraph(
                "<b>Technical Narrative:</b>",
                self.styles['CustomSubheading']
            )
            elements.append(narrative_heading)
            
            narrative_text = report.narratives[project.project_name]
            
            # Verify narrative length
            if len(narrative_text) < 500:
                logger.warning(
                    f"Narrative for {project.project_name} is short ({len(narrative_text)} chars). "
                    f"Expected >500 characters for audit-ready documentation."
                )
            
            narrative_para = Paragraph(narrative_text, self.styles['CustomBody'])
            elements.append(narrative_para)
            elements.append(Spacer(1, 0.15 * inch))
            
            logger.info(f"  ✓ Added technical narrative for {project.project_name} ({len(narrative_text)} chars)")
        else:
            logger.warning(f"  ⚠ No narrative found for {project.project_name} in report.narratives")
            # Add placeholder to indicate missing narrative
            missing_narrative = Paragraph(
                "<b>Technical Narrative:</b> <i>[Narrative not available]</i>",
                self.styles['CustomBody']
            )
            elements.append(missing_narrative)
            elements.append(Spacer(1, 0.15 * inch))
        
        # Add compliance review status from report.compliance_reviews
        if report.compliance_reviews and project.project_name in report.compliance_reviews:
            review_heading = Paragraph(
                "<b>Compliance Review Status:</b>",
                self.styles['CustomSubheading']
            )
            elements.append(review_heading)
            
            review_data = report.compliance_reviews[project.project_name]
            
            # Extract review information
            status = review_data.get('status', 'Unknown')
            completeness = review_data.get('completeness_score', 'N/A')
            required_revisions = review_data.get('required_revisions', [])
            
            # Format status with color coding
            status_color = colors.green if status.lower() == 'compliant' else colors.orange
            status_text = f"<font color='{status_color.hexval()}'>Status: {status}</font>"
            
            if isinstance(completeness, (int, float)):
                status_text += f" | Completeness: {completeness:.1%}"
            
            status_para = Paragraph(status_text, self.styles['CustomBody'])
            elements.append(status_para)
            
            # Add required revisions if any
            if required_revisions and len(required_revisions) > 0:
                revisions_text = "<b>Required Revisions:</b><br/>"
                for revision in required_revisions:
                    revisions_text += f"• {revision}<br/>"
                revisions_para = Paragraph(revisions_text, self.styles['CustomBody'])
                elements.append(revisions_para)
            
            elements.append(Spacer(1, 0.15 * inch))
            
            logger.info(f"  ✓ Added compliance review for {project.project_name} (status: {status})")
        else:
            logger.warning(f"  ⚠ No compliance review found for {project.project_name} in report.compliance_reviews")
            # Add placeholder to indicate missing review
            missing_review = Paragraph(
                "<b>Compliance Review Status:</b> <i>[Review pending]</i>",
                self.styles['CustomBody']
            )
            elements.append(missing_review)
            elements.append(Spacer(1, 0.15 * inch))
        
        # Technical details (if provided)
        if project.technical_details:
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
            
            elements.append(Spacer(1, 0.15 * inch))
        
        # Add spacing between projects
        elements.append(Spacer(1, 0.3 * inch))
        
        logger.debug(f"Project section created for: {project.project_name}")
        return elements
    
    def _add_project_breakdown(self, report: AuditReport) -> List:
        """
        Create detailed project breakdown section with comprehensive data tables.
        
        This method generates a comprehensive breakdown of all qualified projects,
        including summary statistics, project-by-project details, and cost analysis.
        The breakdown provides a clear overview of qualification results for audit purposes.
        
        Args:
            report: AuditReport object containing all project data
            
        Returns:
            List of ReportLab flowables for the project breakdown section
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> breakdown_elements = generator._add_project_breakdown(report)
        """
        elements = []
        
        # Section title with bookmark for TOC
        title = Paragraph(
            '<a name="project_breakdown"/>Project Breakdown Summary',
            self.styles['CustomHeading']
        )
        elements.append(title)
        self.toc.addEntry(1, 'Project Breakdown Summary', 'project_breakdown')
        elements.append(Spacer(1, 0.2 * inch))
        
        # Introduction text
        intro_text = f"""
        This section provides a detailed breakdown of all {report.project_count} qualified 
        research project(s) included in this report. Each project has been evaluated against 
        the IRS four-part test for R&D tax credit eligibility.
        """
        intro_para = Paragraph(intro_text, self.styles['CustomBody'])
        elements.append(intro_para)
        elements.append(Spacer(1, 0.2 * inch))
        
        if not report.projects:
            no_projects_text = Paragraph(
                "<i>No qualified projects found.</i>",
                self.styles['CustomBody']
            )
            elements.append(no_projects_text)
            return elements
        
        # Create summary table with all projects
        table_data = [
            ['Project Name', 'Hours', 'Cost', 'Qual %', 'Confidence', 'Credit', 'Status']
        ]
        
        for project in report.projects:
            status = "⚠ Review" if project.flagged_for_review else "✓ Approved"
            table_data.append([
                project.project_name,
                f"{project.qualified_hours:.1f}",
                f"${project.qualified_cost:,.2f}",
                f"{project.qualification_percentage:.0f}%",
                f"{project.confidence_score:.2f}",
                f"${project.estimated_credit:,.2f}",
                status
            ])
        
        # Add totals row
        table_data.append([
            'TOTAL',
            f"{report.total_qualified_hours:.1f}",
            f"${report.total_qualified_cost:,.2f}",
            '-',
            f"{report.average_confidence:.2f}",
            f"${report.estimated_credit:,.2f}",
            f"{report.flagged_project_count} flagged"
        ])
        
        # Create table
        col_widths = [2.2*inch, 0.7*inch, 1*inch, 0.6*inch, 0.8*inch, 0.9*inch, 0.9*inch]
        breakdown_table = Table(table_data, colWidths=col_widths, hAlign='LEFT')
        
        breakdown_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.title_font),
            ('FONTSIZE', (0, 0), (-1, 0), self.font_size_body),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -2), self.body_font),
            ('FONTSIZE', (0, 1), (-1, -2), self.font_size_body - 1),
            ('ALIGN', (0, 1), (0, -2), 'LEFT'),  # Project names left-aligned
            ('ALIGN', (1, 1), (-1, -2), 'RIGHT'),  # Numbers right-aligned
            # Totals row styling
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e6f2ff")),
            ('FONTNAME', (0, -1), (-1, -1), self.title_font),
            ('FONTSIZE', (0, -1), (-1, -1), self.font_size_body),
            ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, -1), (0, -1), 'LEFT'),
            # Borders and padding
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(breakdown_table)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Add note about flagged projects
        if report.flagged_project_count > 0:
            note_text = f"""
            <b>Note:</b> {report.flagged_project_count} project(s) marked with "⚠ Review" 
            have confidence scores below 0.7 and should be reviewed for additional 
            documentation or clarification before finalizing the R&D tax credit claim.
            """
            note_para = Paragraph(note_text, self.styles['CustomBody'])
            elements.append(note_para)
        
        elements.append(PageBreak())
        
        logger.debug(f"Project breakdown created with {report.project_count} projects")
        return elements
    
    def _add_narratives(self, report: AuditReport) -> List:
        """
        Create technical narratives section for all qualified projects.
        
        This method generates detailed technical narratives for each qualified project,
        including descriptions of technological uncertainties, experimentation processes,
        and business components. These narratives are essential for IRS audit defense.
        
        Args:
            report: AuditReport object containing all project data
            
        Returns:
            List of ReportLab flowables for the narratives section
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> narrative_elements = generator._add_narratives(report)
        """
        elements = []
        
        # Section title with bookmark for TOC
        title = Paragraph(
            '<a name="narratives"/>Technical Project Narratives',
            self.styles['CustomHeading']
        )
        elements.append(title)
        self.toc.addEntry(1, 'Technical Project Narratives', 'narratives')
        elements.append(Spacer(1, 0.2 * inch))
        
        # Introduction text
        intro_text = """
        This section provides detailed technical narratives for each qualified research 
        project. Each narrative describes the technological uncertainties addressed, the 
        process of experimentation undertaken, and how the project meets the IRS four-part 
        test for R&D tax credit qualification.
        """
        intro_para = Paragraph(intro_text, self.styles['CustomBody'])
        elements.append(intro_para)
        elements.append(Spacer(1, 0.3 * inch))
        
        if not report.projects:
            no_narratives_text = Paragraph(
                "<i>No project narratives available.</i>",
                self.styles['CustomBody']
            )
            elements.append(no_narratives_text)
            return elements
        
        # Add narrative for each project
        for i, project in enumerate(report.projects, 1):
            # Project header
            project_header = Paragraph(
                f"<b>Project {i}: {project.project_name}</b>",
                self.styles['CustomSubheading']
            )
            elements.append(project_header)
            elements.append(Spacer(1, 0.1 * inch))
            
            # Main reasoning/narrative
            narrative_heading = Paragraph(
                "<b>Qualification Analysis:</b>",
                ParagraphStyle(
                    name=f'NarrativeHeading{i}',
                    parent=self.styles['CustomBody'],
                    fontName=self.title_font,
                    fontSize=self.font_size_body,
                    spaceAfter=4
                )
            )
            elements.append(narrative_heading)
            
            narrative_text = Paragraph(project.reasoning, self.styles['CustomBody'])
            elements.append(narrative_text)
            elements.append(Spacer(1, 0.15 * inch))
            
            # Technical details (if available)
            if project.technical_details:
                tech_heading = Paragraph(
                    "<b>Technical Details:</b>",
                    ParagraphStyle(
                        name=f'TechHeading{i}',
                        parent=self.styles['CustomBody'],
                        fontName=self.title_font,
                        fontSize=self.font_size_body,
                        spaceAfter=4
                    )
                )
                elements.append(tech_heading)
                
                # Format technical details as bullet points
                for key, value in project.technical_details.items():
                    formatted_key = key.replace('_', ' ').title()
                    
                    # Handle list values
                    if isinstance(value, list):
                        detail_text = f"<b>{formatted_key}:</b>"
                        detail_para = Paragraph(detail_text, self.styles['CustomBody'])
                        elements.append(detail_para)
                        
                        for item in value:
                            bullet_text = f"• {item}"
                            bullet_para = Paragraph(
                                bullet_text,
                                ParagraphStyle(
                                    name=f'Bullet{i}',
                                    parent=self.styles['CustomBody'],
                                    leftIndent=20,
                                    spaceAfter=2
                                )
                            )
                            elements.append(bullet_para)
                    else:
                        detail_text = f"<b>{formatted_key}:</b> {value}"
                        detail_para = Paragraph(detail_text, self.styles['CustomBody'])
                        elements.append(detail_para)
                
                elements.append(Spacer(1, 0.15 * inch))
            
            # Qualification metrics summary
            metrics_text = f"""
            <b>Qualification Metrics:</b> {project.qualification_percentage:.0f}% of project 
            activities qualified as R&D research, resulting in {project.qualified_hours:.1f} 
            qualified hours and ${project.qualified_cost:,.2f} in qualified research expenditures. 
            Confidence score: {project.confidence_score:.2f}.
            """
            metrics_para = Paragraph(metrics_text, self.styles['CustomBody'])
            elements.append(metrics_para)
            
            # Add spacing between projects
            if i < len(report.projects):
                elements.append(Spacer(1, 0.3 * inch))
                # Add horizontal line separator
                elements.append(Table(
                    [['']],
                    colWidths=[7*inch],
                    style=TableStyle([
                        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.lightgrey)
                    ])
                ))
                elements.append(Spacer(1, 0.3 * inch))
        
        elements.append(PageBreak())
        
        logger.debug(f"Technical narratives created for {len(report.projects)} projects")
        return elements
    
    def _add_citations(self, report: AuditReport) -> List:
        """
        Create IRS citations and references section.
        
        This method generates a comprehensive list of all IRS document citations
        used to support the R&D qualification decisions. Citations are organized
        by source document and include page references for easy verification.
        
        Args:
            report: AuditReport object containing all project data
            
        Returns:
            List of ReportLab flowables for the citations section
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> citation_elements = generator._add_citations(report)
        """
        elements = []
        
        # Section title with bookmark for TOC
        title = Paragraph(
            '<a name="citations"/>IRS Citations and References',
            self.styles['CustomHeading']
        )
        elements.append(title)
        self.toc.addEntry(1, 'IRS Citations and References', 'citations')
        elements.append(Spacer(1, 0.2 * inch))
        
        # Introduction text
        intro_text = """
        This section lists all IRS documents and specific sections referenced in the 
        qualification analysis. These citations provide the regulatory foundation for 
        the R&D tax credit claims and can be used to support the qualification decisions 
        during an IRS audit.
        """
        intro_para = Paragraph(intro_text, self.styles['CustomBody'])
        elements.append(intro_para)
        elements.append(Spacer(1, 0.2 * inch))
        
        if not report.projects:
            no_citations_text = Paragraph(
                "<i>No citations available.</i>",
                self.styles['CustomBody']
            )
            elements.append(no_citations_text)
            return elements
        
        # Collect all unique citations from projects
        citations_by_source = {}
        
        for project in report.projects:
            source = project.irs_source
            
            if source not in citations_by_source:
                citations_by_source[source] = {
                    'projects': [],
                    'citation_text': project.supporting_citation
                }
            
            citations_by_source[source]['projects'].append(project.project_name)
        
        # Display citations organized by source
        for i, (source, data) in enumerate(sorted(citations_by_source.items()), 1):
            # Source heading
            source_heading = Paragraph(
                f"<b>{i}. {source}</b>",
                self.styles['CustomSubheading']
            )
            elements.append(source_heading)
            elements.append(Spacer(1, 0.05 * inch))
            
            # Citation text
            citation_para = Paragraph(
                data['citation_text'],
                self.styles['Citation']
            )
            elements.append(citation_para)
            elements.append(Spacer(1, 0.1 * inch))
            
            # List projects using this citation
            projects_text = f"<b>Referenced by projects:</b> {', '.join(data['projects'])}"
            projects_para = Paragraph(
                projects_text,
                ParagraphStyle(
                    name=f'ProjectRef{i}',
                    parent=self.styles['CustomBody'],
                    fontSize=self.font_size_body - 1,
                    leftIndent=20,
                    spaceAfter=6
                )
            )
            elements.append(projects_para)
            elements.append(Spacer(1, 0.15 * inch))
        
        # Add general references section
        elements.append(Spacer(1, 0.2 * inch))
        general_heading = Paragraph(
            "<b>General References</b>",
            self.styles['CustomSubheading']
        )
        elements.append(general_heading)
        elements.append(Spacer(1, 0.1 * inch))
        
        general_refs = [
            "Internal Revenue Code (IRC) Section 41 - Credit for Increasing Research Activities",
            "Code of Federal Regulations (CFR) Title 26 § 1.41-4 - Qualified Research",
            "IRS Form 6765 - Credit for Increasing Research Activities",
            "IRS Publication 542 - Corporations",
            "IRS Audit Technique Guide - Credit for Increasing Research Activities"
        ]
        
        for ref in general_refs:
            ref_para = Paragraph(
                f"• {ref}",
                ParagraphStyle(
                    name='GeneralRef',
                    parent=self.styles['CustomBody'],
                    leftIndent=20,
                    spaceAfter=4
                )
            )
            elements.append(ref_para)
        
        elements.append(PageBreak())
        
        logger.debug(f"Citations section created with {len(citations_by_source)} unique sources")
        return elements
    
    def _add_irs_citations(self, report: AuditReport) -> List:
        """
        Create IRS citations section for all qualified projects.
        
        This method generates a dedicated IRS citations section that lists
        all regulatory references used to support R&D qualification decisions.
        For each project, it displays the project name, IRS source reference,
        and supporting citation text in a professional format suitable for
        audit defense.
        
        Args:
            report: AuditReport object containing all project data
            
        Returns:
            List of ReportLab flowables for the IRS citations section
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> citation_elements = generator._add_irs_citations(report)
        """
        elements = []
        
        # Section title with bookmark for TOC
        title = Paragraph(
            '<a name="irs_citations"/>IRS Citations',
            self.styles['CustomHeading']
        )
        elements.append(title)
        self.toc.addEntry(1, 'IRS Citations', 'irs_citations')
        elements.append(Spacer(1, 0.2 * inch))
        
        # Introduction text
        intro_text = """
        This section provides the specific IRS regulatory citations that support 
        the R&D tax credit qualification for each project. These citations reference 
        the Internal Revenue Code (IRC) Section 41 and related regulations, providing 
        the legal foundation for the qualification decisions. Each citation includes 
        the specific IRS source document and supporting text that demonstrates how 
        the project meets the requirements for qualified research expenditures.
        """
        intro_para = Paragraph(intro_text, self.styles['CustomBody'])
        elements.append(intro_para)
        elements.append(Spacer(1, 0.3 * inch))
        
        # Check if projects are available
        if not report.projects:
            logger.warning("No projects available for IRS citations section")
            no_citations_text = Paragraph(
                "<i>No IRS citations available.</i>",
                self.styles['CustomBody']
            )
            elements.append(no_citations_text)
            elements.append(PageBreak())
            return elements
        
        logger.info(f"Adding IRS citations for {len(report.projects)} projects")
        
        # Add citation for each project
        for i, project in enumerate(report.projects, 1):
            # Project heading
            project_heading = Paragraph(
                f'<a name="citation_{i}"/><b>Citation {i}: {project.project_name}</b>',
                self.styles['CustomSubheading']
            )
            elements.append(project_heading)
            self.toc.addEntry(2, f'{project.project_name}', f'citation_{i}')
            elements.append(Spacer(1, 0.1 * inch))
            
            # IRS Source Reference
            source_heading = Paragraph(
                "<b>IRS Source Reference:</b>",
                ParagraphStyle(
                    name=f'SourceHeading{i}',
                    parent=self.styles['CustomBody'],
                    fontName=self.title_font,
                    fontSize=self.font_size_body,
                    spaceAfter=4
                )
            )
            elements.append(source_heading)
            
            # Display IRS source with professional formatting
            source_text = Paragraph(
                f"<i>{project.irs_source}</i>",
                self.styles['Citation']
            )
            elements.append(source_text)
            elements.append(Spacer(1, 0.15 * inch))
            
            # Supporting Citation Text
            citation_heading = Paragraph(
                "<b>Supporting Citation:</b>",
                ParagraphStyle(
                    name=f'CitationHeading{i}',
                    parent=self.styles['CustomBody'],
                    fontName=self.title_font,
                    fontSize=self.font_size_body,
                    spaceAfter=4
                )
            )
            elements.append(citation_heading)
            
            # Display supporting citation text
            # Format as indented citation with proper styling
            citation_text = Paragraph(
                project.supporting_citation,
                ParagraphStyle(
                    name=f'CitationText{i}',
                    parent=self.styles['Citation'],
                    leftIndent=20,
                    rightIndent=20,
                    spaceAfter=6,
                    alignment=TA_JUSTIFY
                )
            )
            elements.append(citation_text)
            elements.append(Spacer(1, 0.15 * inch))
            
            # Add project qualification summary for context
            context_text = f"""
            <b>Application to Project:</b> This citation supports the qualification of 
            {project.qualified_hours:.1f} hours and ${project.qualified_cost:,.2f} in 
            qualified research expenditures for the {project.project_name} project, 
            representing {project.qualification_percentage:.0f}% of total project activities.
            """
            context_para = Paragraph(
                context_text,
                ParagraphStyle(
                    name=f'Context{i}',
                    parent=self.styles['CustomBody'],
                    fontSize=self.font_size_body - 1,
                    leftIndent=10,
                    spaceAfter=6
                )
            )
            elements.append(context_para)
            
            # Add visual separator between citations (except for last one)
            if i < len(report.projects):
                elements.append(Spacer(1, 0.2 * inch))
                # Horizontal line separator
                separator_table = Table(
                    [['']],
                    colWidths=[7 * inch],
                    style=TableStyle([
                        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.lightgrey),
                        ('TOPPADDING', (0, 0), (-1, 0), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
                    ])
                )
                elements.append(separator_table)
                elements.append(Spacer(1, 0.3 * inch))
            
            logger.info(f"  ✓ Added IRS citation for {project.project_name}")
        
        # Add general regulatory references section
        elements.append(Spacer(1, 0.3 * inch))
        general_heading = Paragraph(
            "<b>General Regulatory Framework</b>",
            self.styles['CustomSubheading']
        )
        elements.append(general_heading)
        elements.append(Spacer(1, 0.1 * inch))
        
        framework_text = """
        All project qualifications are based on the regulatory framework established 
        by the Internal Revenue Code (IRC) Section 41 and the Code of Federal Regulations 
        (CFR) Title 26. The following documents provide the complete regulatory context:
        """
        framework_para = Paragraph(framework_text, self.styles['CustomBody'])
        elements.append(framework_para)
        elements.append(Spacer(1, 0.1 * inch))
        
        # List of general references
        general_refs = [
            "Internal Revenue Code (IRC) Section 41 - Credit for Increasing Research Activities",
            "Code of Federal Regulations (CFR) Title 26 § 1.41-4 - Qualified Research",
            "Code of Federal Regulations (CFR) Title 26 § 1.41-4(a) - Four-Part Test",
            "IRS Form 6765 - Credit for Increasing Research Activities (Instructions)",
            "IRS Publication 542 - Corporations",
            "IRS Audit Technique Guide - Credit for Increasing Research Activities (IRC § 41)"
        ]
        
        for ref in general_refs:
            ref_para = Paragraph(
                f"• {ref}",
                ParagraphStyle(
                    name='GeneralRefCitation',
                    parent=self.styles['CustomBody'],
                    leftIndent=20,
                    spaceAfter=4,
                    fontSize=self.font_size_body - 1
                )
            )
            elements.append(ref_para)
        
        # Add page break after IRS citations section
        elements.append(PageBreak())
        
        logger.info(f"IRS citations section created with {len(report.projects)} project citations")
        return elements
    
    def _add_technical_narratives(self, report: AuditReport) -> List:
        """
        Create dedicated technical narratives section for all qualified projects.
        
        This method generates a comprehensive technical narratives section with
        detailed descriptions for each project. Each narrative addresses the
        four-part test and provides audit-ready documentation. Narratives must
        be at least 500 characters to meet IRS documentation standards.
        
        Args:
            report: AuditReport object containing narratives dictionary
            
        Returns:
            List of ReportLab flowables for the technical narratives section
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> narrative_elements = generator._add_technical_narratives(report)
        """
        elements = []
        
        # Section title with bookmark for TOC
        title = Paragraph(
            '<a name="technical_narratives"/>Technical Narratives',
            self.styles['CustomHeading']
        )
        elements.append(title)
        self.toc.addEntry(1, 'Technical Narratives', 'technical_narratives')
        elements.append(Spacer(1, 0.2 * inch))
        
        # Introduction text
        intro_text = """
        This section provides detailed technical narratives for each qualified research 
        project. Each narrative describes the technological uncertainties addressed, the 
        process of experimentation undertaken, and how the project meets the IRS four-part 
        test for R&D tax credit qualification. These narratives are essential for audit 
        defense and demonstrate compliance with IRC Section 41 requirements.
        """
        intro_para = Paragraph(intro_text, self.styles['CustomBody'])
        elements.append(intro_para)
        elements.append(Spacer(1, 0.3 * inch))
        
        # Check if narratives are available
        if not report.narratives or len(report.narratives) == 0:
            logger.warning("No narratives available in report")
            no_narratives_text = Paragraph(
                "<i>No technical narratives available.</i>",
                self.styles['CustomBody']
            )
            elements.append(no_narratives_text)
            elements.append(PageBreak())
            return elements
        
        logger.info(f"Adding technical narratives for {len(report.narratives)} projects")
        
        # Add narrative for each project
        for i, project in enumerate(report.projects, 1):
            # Section heading with project name
            project_heading = Paragraph(
                f'<a name="narrative_{i}"/>Technical Narrative: {project.project_name}',
                self.styles['CustomSubheading']
            )
            elements.append(project_heading)
            self.toc.addEntry(2, f'{project.project_name}', f'narrative_{i}')
            elements.append(Spacer(1, 0.15 * inch))
            
            # Get narrative from report.narratives
            narrative_text = report.narratives.get(project.project_name, "")
            
            if not narrative_text:
                logger.warning(f"Missing narrative for project: {project.project_name}")
                missing_text = Paragraph(
                    "<i>[Narrative not available for this project]</i>",
                    self.styles['CustomBody']
                )
                elements.append(missing_text)
            else:
                # Verify narrative length (should be >500 characters)
                narrative_length = len(narrative_text)
                if narrative_length < 500:
                    logger.warning(
                        f"Narrative for {project.project_name} is short ({narrative_length} chars). "
                        f"Expected >500 characters for audit-ready documentation."
                    )
                else:
                    logger.info(f"  ✓ Narrative for {project.project_name}: {narrative_length} chars")
                
                # Format narrative with proper paragraphs and spacing
                # Split narrative into paragraphs if it contains line breaks
                if '\n\n' in narrative_text:
                    # Multiple paragraphs
                    paragraphs = narrative_text.split('\n\n')
                    for para_text in paragraphs:
                        if para_text.strip():
                            para = Paragraph(para_text.strip(), self.styles['CustomBody'])
                            elements.append(para)
                            elements.append(Spacer(1, 0.1 * inch))
                else:
                    # Single paragraph
                    narrative_para = Paragraph(narrative_text, self.styles['CustomBody'])
                    elements.append(narrative_para)
                    elements.append(Spacer(1, 0.1 * inch))
            
            # Add visual separator between narratives (except for last one)
            if i < len(report.projects):
                elements.append(Spacer(1, 0.2 * inch))
                # Horizontal line separator
                separator_table = Table(
                    [['']],
                    colWidths=[7 * inch],
                    style=TableStyle([
                        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.lightgrey),
                        ('TOPPADDING', (0, 0), (-1, 0), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
                    ])
                )
                elements.append(separator_table)
                elements.append(Spacer(1, 0.3 * inch))
        
        # Add page break after technical narratives section
        elements.append(PageBreak())
        
        logger.info(f"Technical narratives section created with {len(report.narratives)} narratives")
        return elements
    
    def _add_appendices(self, report: AuditReport) -> List:
        """
        Create appendices section with raw data tables.
        
        This method generates appendices containing detailed raw data tables for
        all qualified projects, including hour-by-hour breakdowns, cost details,
        and supporting calculations. These tables provide complete transparency
        for audit purposes.
        
        Args:
            report: AuditReport object containing all project data
            
        Returns:
            List of ReportLab flowables for the appendices section
            
        Example:
            >>> generator = PDFGenerator()
            >>> report = AuditReport(...)
            >>> appendix_elements = generator._add_appendices(report)
        """
        elements = []
        
        # Section title with bookmark for TOC
        title = Paragraph(
            '<a name="appendices"/>Appendices',
            self.styles['CustomHeading']
        )
        elements.append(title)
        self.toc.addEntry(1, 'Appendices', 'appendices')
        elements.append(Spacer(1, 0.2 * inch))
        
        # Introduction text
        intro_text = """
        This section contains detailed data tables and supporting calculations for all 
        qualified research projects. The appendices provide complete transparency and 
        traceability for audit purposes.
        """
        intro_para = Paragraph(intro_text, self.styles['CustomBody'])
        elements.append(intro_para)
        elements.append(Spacer(1, 0.3 * inch))
        
        if not report.projects:
            no_appendices_text = Paragraph(
                "<i>No appendix data available.</i>",
                self.styles['CustomBody']
            )
            elements.append(no_appendices_text)
            return elements
        
        # Appendix A: Project Summary Data
        appendix_a_title = Paragraph(
            "<b>Appendix A: Project Summary Data</b>",
            self.styles['CustomSubheading']
        )
        elements.append(appendix_a_title)
        elements.append(Spacer(1, 0.1 * inch))
        
        # Create detailed project data table
        appendix_a_data = [
            ['Project', 'Qual Hours', 'Qual Cost', 'Qual %', 'Confidence', 'Est. Credit', 'Flagged']
        ]
        
        for project in report.projects:
            appendix_a_data.append([
                project.project_name,
                f"{project.qualified_hours:.2f}",
                f"${project.qualified_cost:.2f}",
                f"{project.qualification_percentage:.1f}%",
                f"{project.confidence_score:.3f}",
                f"${project.estimated_credit:.2f}",
                "Yes" if project.flagged_for_review else "No"
            ])
        
        appendix_a_table = Table(
            appendix_a_data,
            colWidths=[1.8*inch, 0.9*inch, 1*inch, 0.7*inch, 0.9*inch, 0.9*inch, 0.7*inch],
            hAlign='LEFT'
        )
        
        appendix_a_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), self.title_font),
            ('FONTSIZE', (0, 0), (-1, 0), self.font_size_body - 1),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), self.body_font),
            ('FONTSIZE', (0, 1), (-1, -1), self.font_size_body - 2),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(appendix_a_table)
        elements.append(Spacer(1, 0.3 * inch))
        
        # Appendix B: Qualification Reasoning Summary
        appendix_b_title = Paragraph(
            "<b>Appendix B: Qualification Reasoning Summary</b>",
            self.styles['CustomSubheading']
        )
        elements.append(appendix_b_title)
        elements.append(Spacer(1, 0.1 * inch))
        
        for i, project in enumerate(report.projects, 1):
            project_label = Paragraph(
                f"<b>B.{i} {project.project_name}</b>",
                ParagraphStyle(
                    name=f'AppendixBLabel{i}',
                    parent=self.styles['CustomBody'],
                    fontName=self.title_font,
                    fontSize=self.font_size_body - 1,
                    spaceAfter=4
                )
            )
            elements.append(project_label)
            
            # Reasoning text (truncated if too long)
            reasoning_text = project.reasoning
            if len(reasoning_text) > 500:
                reasoning_text = reasoning_text[:497] + "..."
            
            reasoning_para = Paragraph(
                reasoning_text,
                ParagraphStyle(
                    name=f'AppendixBText{i}',
                    parent=self.styles['CustomBody'],
                    fontSize=self.font_size_body - 2,
                    leftIndent=10,
                    spaceAfter=6
                )
            )
            elements.append(reasoning_para)
            
            # IRS source reference
            source_para = Paragraph(
                f"<i>Source: {project.irs_source}</i>",
                ParagraphStyle(
                    name=f'AppendixBSource{i}',
                    parent=self.styles['Citation'],
                    fontSize=self.font_size_body - 2,
                    leftIndent=10,
                    spaceAfter=10
                )
            )
            elements.append(source_para)
        
        elements.append(Spacer(1, 0.3 * inch))
        
        # Appendix C: Credit Calculation Summary
        appendix_c_title = Paragraph(
            "<b>Appendix C: Credit Calculation Summary</b>",
            self.styles['CustomSubheading']
        )
        elements.append(appendix_c_title)
        elements.append(Spacer(1, 0.1 * inch))
        
        calc_text = f"""
        The R&D tax credit is calculated using the regular credit method under IRC Section 41. 
        The credit rate is 20% of qualified research expenditures (QREs).
        <br/><br/>
        <b>Total Qualified Research Expenditures:</b> ${report.total_qualified_cost:,.2f}<br/>
        <b>Credit Rate:</b> 20%<br/>
        <b>Estimated R&D Tax Credit:</b> ${report.estimated_credit:,.2f}<br/>
        <br/>
        <i>Note: This calculation uses the regular credit method. The alternative simplified 
        credit (ASC) method may result in a different credit amount. Consult with a tax 
        professional to determine the optimal credit calculation method.</i>
        """
        calc_para = Paragraph(calc_text, self.styles['CustomBody'])
        elements.append(calc_para)
        
        logger.debug(f"Appendices created with {len(report.projects)} projects")
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
            # ===== DETAILED LOGGING: Verify AuditReport Data Reception =====
            logger.info("=" * 80)
            logger.info("PDF GENERATOR: Received AuditReport object")
            logger.info("=" * 80)
            
            # Log basic report metadata
            logger.info(f"Report ID: {report.report_id}")
            logger.info(f"Generation Date: {report.generation_date}")
            logger.info(f"Tax Year: {report.tax_year}")
            logger.info(f"Company Name: {report.company_name}")
            
            # Log aggregated metrics
            logger.info(f"Total Qualified Hours: {report.total_qualified_hours}")
            logger.info(f"Total Qualified Cost: ${report.total_qualified_cost:,.2f}")
            logger.info(f"Estimated Credit: ${report.estimated_credit:,.2f}")
            logger.info(f"Average Confidence: {report.average_confidence}")
            logger.info(f"Project Count: {report.project_count}")
            logger.info(f"Flagged Project Count: {report.flagged_project_count}")
            
            # Log projects list
            logger.info(f"Projects List: {len(report.projects)} projects received")
            if report.projects:
                logger.info("Sample project data (first project):")
                sample_project = report.projects[0]
                logger.info(f"  - Project Name: {sample_project.project_name}")
                logger.info(f"  - Qualified Hours: {sample_project.qualified_hours}")
                logger.info(f"  - Qualified Cost: ${sample_project.qualified_cost:,.2f}")
                logger.info(f"  - Confidence Score: {sample_project.confidence_score}")
                logger.info(f"  - Qualification %: {sample_project.qualification_percentage}%")
                logger.info(f"  - Flagged: {sample_project.flagged_for_review}")
            else:
                logger.warning("  - No projects in report!")
            
            # Check if narratives field exists and is accessible
            logger.info("-" * 80)
            logger.info("Checking narratives field:")
            if hasattr(report, 'narratives'):
                logger.info(f"  ✓ narratives field EXISTS")
                if report.narratives is not None:
                    logger.info(f"  ✓ narratives is NOT None")
                    logger.info(f"  ✓ narratives count: {len(report.narratives)}")
                    if report.narratives:
                        logger.info(f"  ✓ narratives keys: {list(report.narratives.keys())}")
                        # Log sample narrative length
                        first_key = list(report.narratives.keys())[0]
                        narrative_length = len(report.narratives[first_key])
                        logger.info(f"  ✓ Sample narrative length ({first_key}): {narrative_length} chars")
                    else:
                        logger.warning("  ⚠ narratives dictionary is EMPTY")
                else:
                    logger.warning("  ⚠ narratives is None")
            else:
                logger.error("  ✗ narratives field DOES NOT EXIST on AuditReport")
            
            # Check if compliance_reviews field exists and is accessible
            logger.info("-" * 80)
            logger.info("Checking compliance_reviews field:")
            if hasattr(report, 'compliance_reviews'):
                logger.info(f"  ✓ compliance_reviews field EXISTS")
                if report.compliance_reviews is not None:
                    logger.info(f"  ✓ compliance_reviews is NOT None")
                    logger.info(f"  ✓ compliance_reviews count: {len(report.compliance_reviews)}")
                    if report.compliance_reviews:
                        logger.info(f"  ✓ compliance_reviews keys: {list(report.compliance_reviews.keys())}")
                    else:
                        logger.warning("  ⚠ compliance_reviews dictionary is EMPTY")
                else:
                    logger.warning("  ⚠ compliance_reviews is None")
            else:
                logger.error("  ✗ compliance_reviews field DOES NOT EXIST on AuditReport")
            
            # Check if aggregated_data field exists and is accessible
            logger.info("-" * 80)
            logger.info("Checking aggregated_data field:")
            if hasattr(report, 'aggregated_data'):
                logger.info(f"  ✓ aggregated_data field EXISTS")
                if report.aggregated_data is not None:
                    logger.info(f"  ✓ aggregated_data is NOT None")
                    logger.info(f"  ✓ aggregated_data keys: {list(report.aggregated_data.keys())}")
                    # Log key metrics from aggregated_data
                    if 'total_qualified_hours' in report.aggregated_data:
                        logger.info(f"  ✓ total_qualified_hours: {report.aggregated_data['total_qualified_hours']}")
                    if 'total_qualified_cost' in report.aggregated_data:
                        logger.info(f"  ✓ total_qualified_cost: {report.aggregated_data['total_qualified_cost']}")
                    if 'estimated_credit' in report.aggregated_data:
                        logger.info(f"  ✓ estimated_credit: {report.aggregated_data['estimated_credit']}")
                else:
                    logger.warning("  ⚠ aggregated_data is None")
            else:
                logger.error("  ✗ aggregated_data field DOES NOT EXIST on AuditReport")
            
            logger.info("=" * 80)
            # ===== END DETAILED LOGGING =====
            
            # ===== VALIDATION: Verify Required Fields =====
            logger.info("=" * 80)
            logger.info("VALIDATION: Verifying AuditReport has all required fields")
            logger.info("=" * 80)
            
            validation_errors = []
            
            # Verify narratives field
            if not hasattr(report, 'narratives'):
                error_msg = "AuditReport missing 'narratives' field"
                logger.error(f"  ✗ VALIDATION FAILED: {error_msg}")
                validation_errors.append(error_msg)
            elif report.narratives is None:
                error_msg = "AuditReport 'narratives' field is None"
                logger.error(f"  ✗ VALIDATION FAILED: {error_msg}")
                validation_errors.append(error_msg)
            else:
                logger.info(f"  ✓ narratives field is valid ({len(report.narratives)} narratives)")
            
            # Verify compliance_reviews field
            if not hasattr(report, 'compliance_reviews'):
                error_msg = "AuditReport missing 'compliance_reviews' field"
                logger.error(f"  ✗ VALIDATION FAILED: {error_msg}")
                validation_errors.append(error_msg)
            elif report.compliance_reviews is None:
                error_msg = "AuditReport 'compliance_reviews' field is None"
                logger.error(f"  ✗ VALIDATION FAILED: {error_msg}")
                validation_errors.append(error_msg)
            else:
                logger.info(f"  ✓ compliance_reviews field is valid ({len(report.compliance_reviews)} reviews)")
            
            # Verify aggregated_data field
            if not hasattr(report, 'aggregated_data'):
                error_msg = "AuditReport missing 'aggregated_data' field"
                logger.error(f"  ✗ VALIDATION FAILED: {error_msg}")
                validation_errors.append(error_msg)
            elif report.aggregated_data is None:
                error_msg = "AuditReport 'aggregated_data' field is None"
                logger.error(f"  ✗ VALIDATION FAILED: {error_msg}")
                validation_errors.append(error_msg)
            else:
                logger.info(f"  ✓ aggregated_data field is valid ({len(report.aggregated_data)} keys)")
            
            # If any validation errors, raise exception
            if validation_errors:
                logger.error("=" * 80)
                logger.error("VALIDATION FAILED: AuditReport is incomplete")
                logger.error("=" * 80)
                error_summary = "; ".join(validation_errors)
                raise ValueError(
                    f"Cannot generate PDF: AuditReport is incomplete. "
                    f"Missing or None fields: {error_summary}. "
                    f"Ensure AuditTrailAgent populates all required fields before passing to PDFGenerator."
                )
            
            logger.info("=" * 80)
            logger.info("✓ VALIDATION PASSED: All required fields are present and valid")
            logger.info("=" * 80)
            # ===== END VALIDATION =====
            
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
            
            # Create PDF document with custom canvas for headers/footers
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=self.page_size,
                leftMargin=self.margin,
                rightMargin=self.margin,
                topMargin=self.margin + 0.3 * inch,  # Extra space for header
                bottomMargin=self.margin + 0.3 * inch  # Extra space for footer
            )
            
            # Build document elements
            elements = []
            
            # ===== SECTION GENERATION LOGGING =====
            logger.info("=" * 80)
            logger.info("SECTION GENERATION: Starting PDF section generation")
            logger.info("=" * 80)
            
            # Add cover page
            try:
                logger.info("Generating section: Cover Page")
                cover_elements = self._create_cover_page(report)
                elements.extend(cover_elements)
                logger.info(f"  ✓ Cover Page generated successfully ({len(cover_elements)} elements)")
            except Exception as e:
                logger.error(f"  ✗ Cover Page generation FAILED: {e}", exc_info=True)
                raise
            
            # Add table of contents
            try:
                logger.info("Generating section: Table of Contents")
                toc_elements = self._create_table_of_contents()
                elements.extend(toc_elements)
                logger.info(f"  ✓ Table of Contents generated successfully ({len(toc_elements)} elements)")
            except Exception as e:
                logger.error(f"  ✗ Table of Contents generation FAILED: {e}", exc_info=True)
                raise
            
            # Add executive summary
            try:
                logger.info("Generating section: Executive Summary")
                summary_elements = self._create_executive_summary(report)
                elements.extend(summary_elements)
                logger.info(f"  ✓ Executive Summary generated successfully ({len(summary_elements)} elements)")
            except Exception as e:
                logger.error(f"  ✗ Executive Summary generation FAILED: {e}", exc_info=True)
                raise
            
            # Add project breakdown summary
            try:
                logger.info("Generating section: Project Breakdown Summary")
                breakdown_elements = self._add_project_breakdown(report)
                elements.extend(breakdown_elements)
                logger.info(f"  ✓ Project Breakdown Summary generated successfully ({len(breakdown_elements)} elements)")
            except Exception as e:
                logger.error(f"  ✗ Project Breakdown Summary generation FAILED: {e}", exc_info=True)
                raise
            
            # Add project sections
            if report.projects:
                try:
                    logger.info("Generating section: Qualified Research Projects")
                    # Projects heading with bookmark for TOC
                    projects_title = Paragraph(
                        '<a name="projects"/>Qualified Research Projects',
                        self.styles['CustomHeading']
                    )
                    elements.append(projects_title)
                    self.toc.addEntry(1, 'Qualified Research Projects', 'projects')
                    elements.append(Spacer(1, 0.2 * inch))
                    
                    # Add each project
                    for i, project in enumerate(report.projects, 1):
                        logger.info(f"  Generating project {i}/{len(report.projects)}: {project.project_name}")
                        project_elements = self._create_project_section(project, i, report)
                        elements.extend(project_elements)
                        logger.info(f"    ✓ Project section generated ({len(project_elements)} elements)")
                        
                        # Add page break between projects (except last one)
                        if i < len(report.projects):
                            elements.append(PageBreak())
                    
                    logger.info(f"  ✓ All {len(report.projects)} project sections generated successfully")
                except Exception as e:
                    logger.error(f"  ✗ Project sections generation FAILED: {e}", exc_info=True)
                    raise
            else:
                logger.warning("  ⚠ Skipping project sections - no projects in report")
            
            # Add technical narratives (dedicated section)
            try:
                logger.info("Generating section: Technical Narratives")
                narrative_elements = self._add_technical_narratives(report)
                elements.extend(narrative_elements)
                logger.info(f"  ✓ Technical Narratives generated successfully ({len(narrative_elements)} elements)")
            except Exception as e:
                logger.error(f"  ✗ Technical Narratives generation FAILED: {e}", exc_info=True)
                raise
            
            # Add IRS citations (NEW: dedicated IRS citations section)
            try:
                logger.info("Generating section: IRS Citations")
                citation_elements = self._add_irs_citations(report)
                elements.extend(citation_elements)
                logger.info(f"  ✓ IRS Citations generated successfully ({len(citation_elements)} elements)")
            except Exception as e:
                logger.error(f"  ✗ IRS Citations generation FAILED: {e}", exc_info=True)
                raise
            
            # Add appendices
            try:
                logger.info("Generating section: Appendices")
                appendix_elements = self._add_appendices(report)
                elements.extend(appendix_elements)
                logger.info(f"  ✓ Appendices generated successfully ({len(appendix_elements)} elements)")
            except Exception as e:
                logger.error(f"  ✗ Appendices generation FAILED: {e}", exc_info=True)
                raise
            
            logger.info("=" * 80)
            logger.info(f"SECTION GENERATION COMPLETE: Total {len(elements)} elements generated")
            logger.info("=" * 80)
            # ===== END SECTION GENERATION LOGGING =====
            
            # Build the PDF with custom canvas for headers/footers/page numbers
            logger.info("Building PDF document...")
            doc.build(
                elements,
                canvasmaker=lambda *args, **kwargs: NumberedCanvas(
                    *args,
                    company_name=report.company_name or '',
                    report_id=report.report_id,
                    primary_color=self.primary_color,
                    **kwargs
                )
            )
            
            # Log PDF file statistics
            logger.info("=" * 80)
            logger.info("PDF GENERATION COMPLETE")
            logger.info("=" * 80)
            pdf_file_size = Path(pdf_path).stat().st_size
            logger.info(f"PDF Path: {pdf_path}")
            logger.info(f"PDF File Size: {pdf_file_size:,} bytes ({pdf_file_size / 1024:.2f} KB)")
            
            # Determine if PDF is complete based on size
            if pdf_file_size >= 15000:  # 15KB minimum for complete PDF
                logger.info(f"  ✓ PDF appears COMPLETE (size >= 15KB)")
            elif pdf_file_size >= 8000:  # 8KB - possibly incomplete
                logger.warning(f"  ⚠ PDF may be INCOMPLETE (size 8-15KB)")
            else:  # < 8KB - likely incomplete
                logger.error(f"  ✗ PDF appears INCOMPLETE (size < 8KB)")
            
            logger.info("=" * 80)
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
    
    # Generate PDF with optional logo
    # generator = PDFGenerator(logo_path="path/to/company_logo.png")
    generator = PDFGenerator()  # Without logo, will show placeholder
    pdf_path = generator.generate_report(sample_report, "outputs/reports/")
    print(f"Sample report generated: {pdf_path}")
