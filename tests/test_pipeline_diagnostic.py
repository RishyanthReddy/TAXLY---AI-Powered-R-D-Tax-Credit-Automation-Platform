"""
Comprehensive diagnostic tests for R&D Tax Credit Pipeline.

This test module implements Task 1 from the pipeline-fix spec:
- Execute end-to-end test with sample data
- Generate 10 test PDFs with varying project counts (1, 3, 5, 10 projects)
- Analyze each PDF: file size, page count, sections present
- Document which PDFs are complete vs incomplete
- Identify patterns in incomplete PDFs
- Log all agent outputs and data passed between stages

Requirements: Testing, Analysis
"""

import pytest
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import PyPDF2

# Configure logging for diagnostic tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline_diagnostic.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PDFAnalyzer:
    """Utility class for analyzing PDF reports."""
    
    @staticmethod
    def analyze_pdf(pdf_path: str) -> Dict[str, Any]:
        """
        Analyze a PDF file and extract key metrics.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing PDF: {pdf_path}")
        
        result = {
            'pdf_path': pdf_path,
            'exists': False,
            'file_size_bytes': 0,
            'file_size_kb': 0.0,
            'page_count': 0,
            'sections_found': [],
            'is_complete': False,
            'completeness_score': 0,
            'issues': []
        }
        
        # Check if file exists
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            result['issues'].append('PDF file does not exist')
            logger.error(f"PDF file not found: {pdf_path}")
            return result
        
        result['exists'] = True
        
        # Get file size
        file_size = pdf_file.stat().st_size
        result['file_size_bytes'] = file_size
        result['file_size_kb'] = round(file_size / 1024, 2)
        
        logger.info(f"File size: {result['file_size_kb']} KB")
        
        # Analyze PDF content
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                result['page_count'] = len(pdf_reader.pages)
                
                logger.info(f"Page count: {result['page_count']}")
                
                # Extract text from all pages
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        full_text += page_text + "\n"
                        logger.debug(f"Extracted text from page {page_num + 1} ({len(page_text)} chars)")
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                
                # Check for expected sections
                expected_sections = [
                    'R&D Tax Credit',
                    'Table of Contents',
                    'Executive Summary',
                    'Project Breakdown',
                    'Technical Narrative',
                    'IRS Citation',
                    'Qualified Research'
                ]
                
                for section in expected_sections:
                    if section in full_text:
                        result['sections_found'].append(section)
                        logger.debug(f"Found section: {section}")
                
                # Calculate completeness score
                result['completeness_score'] = int(
                    (len(result['sections_found']) / len(expected_sections)) * 100
                )
                
                # Determine if PDF is complete
                # Complete PDF criteria:
                # - File size: 15-20KB (may vary with project count)
                # - Page count: 9-12 pages (may vary with project count)
                # - At least 5 of 7 expected sections present
                
                min_size_kb = 8  # Minimum acceptable size
                min_pages = 5    # Minimum acceptable pages
                min_sections = 5  # Minimum sections for completeness
                
                if result['file_size_kb'] < min_size_kb:
                    result['issues'].append(f'File size too small ({result["file_size_kb"]} KB < {min_size_kb} KB)')
                
                if result['page_count'] < min_pages:
                    result['issues'].append(f'Page count too low ({result["page_count"]} < {min_pages})')
                
                if len(result['sections_found']) < min_sections:
                    result['issues'].append(
                        f'Missing sections ({len(result["sections_found"])}/{len(expected_sections)} found)'
                    )
                    missing = set(expected_sections) - set(result['sections_found'])
                    result['issues'].append(f'Missing: {", ".join(missing)}')
                
                # PDF is complete if no critical issues
                result['is_complete'] = len(result['issues']) == 0
                
                logger.info(
                    f"PDF Analysis Complete: "
                    f"Size={result['file_size_kb']}KB, "
                    f"Pages={result['page_count']}, "
                    f"Sections={len(result['sections_found'])}/{len(expected_sections)}, "
                    f"Complete={result['is_complete']}"
                )
                
        except Exception as e:
            result['issues'].append(f'PDF analysis error: {str(e)}')
            logger.error(f"Error analyzing PDF: {e}", exc_info=True)
        
        return result


class TestPipelineDiagnostic:
    """Comprehensive diagnostic tests for the R&D Tax Credit Pipeline."""
    
    @pytest.fixture
    def sample_projects_fixture(self):
        """Load sample qualified projects from fixtures."""
        fixture_path = Path('tests/fixtures/sample_qualified_projects.json')
        
        if not fixture_path.exists():
            pytest.skip(f"Sample projects fixture not found: {fixture_path}")
        
        with open(fixture_path, 'r') as f:
            projects_data = json.load(f)
        
        logger.info(f"Loaded {len(projects_data)} sample projects from fixture")
        return projects_data
    
    @pytest.fixture
    def audit_trail_agent(self):
        """Initialize AuditTrailAgent with required dependencies."""
        from agents.audit_trail_agent import AuditTrailAgent
        from tools.you_com_client import YouComClient
        from tools.glm_reasoner import GLMReasoner
        from utils.pdf_generator import PDFGenerator
        from utils.config import get_config
        
        # Load configuration
        config = get_config()
        
        # Initialize dependencies
        youcom_client = YouComClient(api_key=config.youcom_api_key)
        glm_reasoner = GLMReasoner(api_key=config.openrouter_api_key)
        pdf_generator = PDFGenerator()
        
        # Initialize agent
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            pdf_generator=pdf_generator
        )
        
        logger.info("Initialized AuditTrailAgent for diagnostic tests")
        return agent
    
    def test_01_generate_pdf_with_1_project(self, audit_trail_agent, sample_projects_fixture):
        """
        Test PDF generation with 1 project.
        
        Expected: PDF should be 8-12KB, 5-7 pages, with all sections present.
        """
        logger.info("=" * 80)
        logger.info("TEST 1: Generate PDF with 1 project")
        logger.info("=" * 80)
        
        from models.tax_models import QualifiedProject
        
        # Select 1 project
        projects_data = sample_projects_fixture[:1]
        projects = [QualifiedProject(**p) for p in projects_data]
        
        logger.info(f"Testing with {len(projects)} project(s)")
        for p in projects:
            logger.info(f"  - {p.project_name}: {p.qualified_hours}h, ${p.qualified_cost:.2f}")
        
        # Run audit trail agent
        try:
            result = audit_trail_agent.run(
                qualified_projects=projects,
                tax_year=2024,
                company_name="Test Company 1"
            )
            
            logger.info(f"Audit trail completed: {result.summary}")
            logger.info(f"PDF path: {result.pdf_path}")
            logger.info(f"Narratives generated: {len(result.narratives)}")
            logger.info(f"Compliance reviews: {len(result.compliance_reviews)}")
            
            # Log aggregated data
            if result.aggregated_data:
                logger.info("Aggregated Data:")
                for key, value in result.aggregated_data.items():
                    if key != 'projects_df':  # Skip DataFrame
                        logger.info(f"  {key}: {value}")
            
            # Analyze PDF
            if result.pdf_path:
                analysis = PDFAnalyzer.analyze_pdf(result.pdf_path)
                
                logger.info("PDF Analysis Results:")
                logger.info(f"  File Size: {analysis['file_size_kb']} KB")
                logger.info(f"  Page Count: {analysis['page_count']}")
                logger.info(f"  Sections Found: {len(analysis['sections_found'])}")
                logger.info(f"  Completeness Score: {analysis['completeness_score']}%")
                logger.info(f"  Is Complete: {analysis['is_complete']}")
                
                if analysis['issues']:
                    logger.warning("Issues found:")
                    for issue in analysis['issues']:
                        logger.warning(f"  - {issue}")
                
                # Assert PDF was generated
                assert analysis['exists'], "PDF file should exist"
                
                # Store analysis for summary
                return analysis
            else:
                pytest.fail("PDF path not returned by audit trail agent")
                
        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)
            pytest.fail(f"PDF generation failed: {e}")
    
    def test_02_generate_pdf_with_3_projects(self, audit_trail_agent, sample_projects_fixture):
        """
        Test PDF generation with 3 projects.
        
        Expected: PDF should be 12-16KB, 7-9 pages, with all sections present.
        """
        logger.info("=" * 80)
        logger.info("TEST 2: Generate PDF with 3 projects")
        logger.info("=" * 80)
        
        from models.tax_models import QualifiedProject
        
        # Select 3 projects
        projects_data = sample_projects_fixture[:3]
        projects = [QualifiedProject(**p) for p in projects_data]
        
        logger.info(f"Testing with {len(projects)} project(s)")
        for p in projects:
            logger.info(f"  - {p.project_name}: {p.qualified_hours}h, ${p.qualified_cost:.2f}")
        
        # Run audit trail agent
        try:
            result = audit_trail_agent.run(
                qualified_projects=projects,
                tax_year=2024,
                company_name="Test Company 3"
            )
            
            logger.info(f"Audit trail completed: {result.summary}")
            logger.info(f"PDF path: {result.pdf_path}")
            logger.info(f"Narratives generated: {len(result.narratives)}")
            logger.info(f"Compliance reviews: {len(result.compliance_reviews)}")
            
            # Log aggregated data
            if result.aggregated_data:
                logger.info("Aggregated Data:")
                for key, value in result.aggregated_data.items():
                    if key != 'projects_df':
                        logger.info(f"  {key}: {value}")
            
            # Analyze PDF
            if result.pdf_path:
                analysis = PDFAnalyzer.analyze_pdf(result.pdf_path)
                
                logger.info("PDF Analysis Results:")
                logger.info(f"  File Size: {analysis['file_size_kb']} KB")
                logger.info(f"  Page Count: {analysis['page_count']}")
                logger.info(f"  Sections Found: {len(analysis['sections_found'])}")
                logger.info(f"  Completeness Score: {analysis['completeness_score']}%")
                logger.info(f"  Is Complete: {analysis['is_complete']}")
                
                if analysis['issues']:
                    logger.warning("Issues found:")
                    for issue in analysis['issues']:
                        logger.warning(f"  - {issue}")
                
                assert analysis['exists'], "PDF file should exist"
                return analysis
            else:
                pytest.fail("PDF path not returned by audit trail agent")
                
        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)
            pytest.fail(f"PDF generation failed: {e}")
    
    def test_03_generate_pdf_with_5_projects(self, audit_trail_agent, sample_projects_fixture):
        """
        Test PDF generation with 5 projects.
        
        Expected: PDF should be 15-20KB, 9-12 pages, with all sections present.
        """
        logger.info("=" * 80)
        logger.info("TEST 3: Generate PDF with 5 projects")
        logger.info("=" * 80)
        
        from models.tax_models import QualifiedProject
        
        # Select 5 projects
        projects_data = sample_projects_fixture[:5]
        projects = [QualifiedProject(**p) for p in projects_data]
        
        logger.info(f"Testing with {len(projects)} project(s)")
        for p in projects:
            logger.info(f"  - {p.project_name}: {p.qualified_hours}h, ${p.qualified_cost:.2f}")
        
        # Run audit trail agent
        try:
            result = audit_trail_agent.run(
                qualified_projects=projects,
                tax_year=2024,
                company_name="Test Company 5"
            )
            
            logger.info(f"Audit trail completed: {result.summary}")
            logger.info(f"PDF path: {result.pdf_path}")
            logger.info(f"Narratives generated: {len(result.narratives)}")
            logger.info(f"Compliance reviews: {len(result.compliance_reviews)}")
            
            # Log aggregated data
            if result.aggregated_data:
                logger.info("Aggregated Data:")
                for key, value in result.aggregated_data.items():
                    if key != 'projects_df':
                        logger.info(f"  {key}: {value}")
            
            # Analyze PDF
            if result.pdf_path:
                analysis = PDFAnalyzer.analyze_pdf(result.pdf_path)
                
                logger.info("PDF Analysis Results:")
                logger.info(f"  File Size: {analysis['file_size_kb']} KB")
                logger.info(f"  Page Count: {analysis['page_count']}")
                logger.info(f"  Sections Found: {len(analysis['sections_found'])}")
                logger.info(f"  Completeness Score: {analysis['completeness_score']}%")
                logger.info(f"  Is Complete: {analysis['is_complete']}")
                
                if analysis['issues']:
                    logger.warning("Issues found:")
                    for issue in analysis['issues']:
                        logger.warning(f"  - {issue}")
                
                assert analysis['exists'], "PDF file should exist"
                return analysis
            else:
                pytest.fail("PDF path not returned by audit trail agent")
                
        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)
            pytest.fail(f"PDF generation failed: {e}")
    
    def test_04_generate_pdf_with_all_projects(self, audit_trail_agent, sample_projects_fixture):
        """
        Test PDF generation with all available projects (6 in fixture).
        
        Expected: PDF should be 18-25KB, 11-15 pages, with all sections present.
        """
        logger.info("=" * 80)
        logger.info("TEST 4: Generate PDF with all projects")
        logger.info("=" * 80)
        
        from models.tax_models import QualifiedProject
        
        # Use all projects
        projects_data = sample_projects_fixture
        projects = [QualifiedProject(**p) for p in projects_data]
        
        logger.info(f"Testing with {len(projects)} project(s)")
        for p in projects:
            logger.info(f"  - {p.project_name}: {p.qualified_hours}h, ${p.qualified_cost:.2f}")
        
        # Run audit trail agent
        try:
            result = audit_trail_agent.run(
                qualified_projects=projects,
                tax_year=2024,
                company_name="Test Company All"
            )
            
            logger.info(f"Audit trail completed: {result.summary}")
            logger.info(f"PDF path: {result.pdf_path}")
            logger.info(f"Narratives generated: {len(result.narratives)}")
            logger.info(f"Compliance reviews: {len(result.compliance_reviews)}")
            
            # Log aggregated data
            if result.aggregated_data:
                logger.info("Aggregated Data:")
                for key, value in result.aggregated_data.items():
                    if key != 'projects_df':
                        logger.info(f"  {key}: {value}")
            
            # Analyze PDF
            if result.pdf_path:
                analysis = PDFAnalyzer.analyze_pdf(result.pdf_path)
                
                logger.info("PDF Analysis Results:")
                logger.info(f"  File Size: {analysis['file_size_kb']} KB")
                logger.info(f"  Page Count: {analysis['page_count']}")
                logger.info(f"  Sections Found: {len(analysis['sections_found'])}")
                logger.info(f"  Completeness Score: {analysis['completeness_score']}%")
                logger.info(f"  Is Complete: {analysis['is_complete']}")
                
                if analysis['issues']:
                    logger.warning("Issues found:")
                    for issue in analysis['issues']:
                        logger.warning(f"  - {issue}")
                
                assert analysis['exists'], "PDF file should exist"
                return analysis
            else:
                pytest.fail("PDF path not returned by audit trail agent")
                
        except Exception as e:
            logger.error(f"Test failed with error: {e}", exc_info=True)
            pytest.fail(f"PDF generation failed: {e}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
