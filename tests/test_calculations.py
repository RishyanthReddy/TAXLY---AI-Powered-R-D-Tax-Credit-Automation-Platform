"""
Calculation Accuracy Verification Test

This test module implements Task 19 from the pipeline-fix spec:
- Create tests/test_calculations.py
- Generate test PDF with known data
- Extract totals from PDF
- Verify total_qualified_hours = sum of project hours
- Verify total_qualified_cost = sum of project costs
- Verify estimated_credit = total_qualified_cost * 0.20
- Verify average_confidence = mean of project confidence scores
- Assert all calculations within 0.01% accuracy

Requirements: Testing, 3.3
"""

import pytest
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import PyPDF2

from agents.audit_trail_agent import AuditTrailAgent
from models.tax_models import QualifiedProject, AuditReport
from tools.you_com_client import YouComClient
from tools.glm_reasoner import GLMReasoner
from utils.pdf_generator import PDFGenerator
from utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestCalculationAccuracy:
    """Comprehensive calculation accuracy verification tests."""
    
    @pytest.fixture
    def sample_projects(self):
        """Load sample qualified projects with known values for calculation testing."""
        fixture_path = Path('tests/fixtures/sample_qualified_projects.json')
        
        if not fixture_path.exists():
            pytest.skip(f"Sample projects fixture not found: {fixture_path}")
        
        with open(fixture_path, 'r') as f:
            projects_data = json.load(f)
        
        # Use 5 projects for testing
        selected_projects = projects_data[:5]
        
        logger.info(f"Loaded {len(selected_projects)} sample projects for calculation testing")
        
        # Log known values for verification
        total_hours = sum(p['qualified_hours'] for p in selected_projects)
        total_cost = sum(p['qualified_cost'] for p in selected_projects)
        expected_credit = total_cost * 0.20
        avg_confidence = sum(p['confidence_score'] for p in selected_projects) / len(selected_projects)
        
        logger.info(f"Known calculation values:")
        logger.info(f"  - Total Hours: {total_hours:.2f}")
        logger.info(f"  - Total Cost: ${total_cost:,.2f}")
        logger.info(f"  - Expected Credit (20%): ${expected_credit:,.2f}")
        logger.info(f"  - Average Confidence: {avg_confidence:.4f}")
        
        return [QualifiedProject(**p) for p in selected_projects]
    
    @pytest.fixture
    def audit_trail_agent(self):
        """Initialize AuditTrailAgent with real API clients."""
        config = get_config()
        
        # Initialize real API clients (no mocks per design policy)
        youcom_client = YouComClient(api_key=config.youcom_api_key)
        glm_reasoner = GLMReasoner(api_key=config.openrouter_api_key)
        pdf_generator = PDFGenerator()
        
        agent = AuditTrailAgent(
            youcom_client=youcom_client,
            glm_reasoner=glm_reasoner,
            pdf_generator=pdf_generator
        )
        
        logger.info("Initialized AuditTrailAgent with real API clients")
        return agent
    
    @pytest.fixture
    def generated_report_and_pdf(self, audit_trail_agent, sample_projects):
        """Generate a test PDF with known data and return both report and PDF path."""
        logger.info("=" * 80)
        logger.info("GENERATING TEST PDF FOR CALCULATION VERIFICATION")
        logger.info("=" * 80)
        
        # Run audit trail to generate PDF
        result = audit_trail_agent.run(
            qualified_projects=sample_projects,
            tax_year=2024,
            company_name="Test Company - Calculations"
        )
        
        assert result.pdf_path is not None, "PDF path should be set"
        assert Path(result.pdf_path).exists(), f"PDF file should exist: {result.pdf_path}"
        
        logger.info(f"✓ Test PDF generated: {result.pdf_path}")
        logger.info(f"  - Projects: {len(sample_projects)}")
        logger.info(f"  - Report ID: {result.report.report_id}")
        
        return result.report, result.pdf_path
    
    def test_total_qualified_hours_calculation(self, generated_report_and_pdf, sample_projects):
        """
        Verify total_qualified_hours = sum of project hours.
        
        Requirements: Testing, 3.3
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Total Qualified Hours Calculation")
        logger.info("=" * 80)
        
        report, pdf_path = generated_report_and_pdf
        
        # Calculate expected total from projects
        expected_total_hours = sum(p.qualified_hours for p in sample_projects)
        
        # Get actual total from report
        actual_total_hours = report.total_qualified_hours
        
        logger.info(f"Expected Total Hours: {expected_total_hours:.2f}")
        logger.info(f"Actual Total Hours: {actual_total_hours:.2f}")
        
        # Verify calculation accuracy (within 0.01%)
        tolerance = expected_total_hours * 0.0001  # 0.01% tolerance
        difference = abs(actual_total_hours - expected_total_hours)
        
        logger.info(f"Difference: {difference:.6f}")
        logger.info(f"Tolerance (0.01%): {tolerance:.6f}")
        
        assert difference <= tolerance, \
            f"Total hours calculation incorrect: {actual_total_hours} != {expected_total_hours} (diff: {difference})"
        
        # Also verify in PDF text
        pdf_text = self._extract_pdf_text(pdf_path)
        hours_in_pdf = self._extract_total_hours_from_pdf(pdf_text)
        
        if hours_in_pdf is not None:
            logger.info(f"Total Hours in PDF: {hours_in_pdf:.2f}")
            pdf_difference = abs(hours_in_pdf - expected_total_hours)
            assert pdf_difference <= tolerance, \
                f"Total hours in PDF incorrect: {hours_in_pdf} != {expected_total_hours}"
            logger.info("✓ Total hours in PDF matches expected value")
        
        logger.info("✓ Total Qualified Hours Calculation: VERIFIED")
    
    def test_total_qualified_cost_calculation(self, generated_report_and_pdf, sample_projects):
        """
        Verify total_qualified_cost = sum of project costs.
        
        Requirements: Testing, 3.3
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Total Qualified Cost Calculation")
        logger.info("=" * 80)
        
        report, pdf_path = generated_report_and_pdf
        
        # Calculate expected total from projects
        expected_total_cost = sum(p.qualified_cost for p in sample_projects)
        
        # Get actual total from report
        actual_total_cost = report.total_qualified_cost
        
        logger.info(f"Expected Total Cost: ${expected_total_cost:,.2f}")
        logger.info(f"Actual Total Cost: ${actual_total_cost:,.2f}")
        
        # Verify calculation accuracy (within 0.01%)
        tolerance = expected_total_cost * 0.0001  # 0.01% tolerance
        difference = abs(actual_total_cost - expected_total_cost)
        
        logger.info(f"Difference: ${difference:.2f}")
        logger.info(f"Tolerance (0.01%): ${tolerance:.2f}")
        
        assert difference <= tolerance, \
            f"Total cost calculation incorrect: {actual_total_cost} != {expected_total_cost} (diff: {difference})"
        
        # Also verify in PDF text
        pdf_text = self._extract_pdf_text(pdf_path)
        cost_in_pdf = self._extract_total_cost_from_pdf(pdf_text)
        
        if cost_in_pdf is not None:
            logger.info(f"Total Cost in PDF: ${cost_in_pdf:,.2f}")
            pdf_difference = abs(cost_in_pdf - expected_total_cost)
            assert pdf_difference <= tolerance, \
                f"Total cost in PDF incorrect: {cost_in_pdf} != {expected_total_cost}"
            logger.info("✓ Total cost in PDF matches expected value")
        
        logger.info("✓ Total Qualified Cost Calculation: VERIFIED")
    
    def test_estimated_credit_calculation(self, generated_report_and_pdf, sample_projects):
        """
        Verify estimated_credit = total_qualified_cost * 0.20.
        
        Requirements: Testing, 3.3
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Estimated Credit Calculation (20% of QREs)")
        logger.info("=" * 80)
        
        report, pdf_path = generated_report_and_pdf
        
        # Calculate expected credit (20% of total qualified cost)
        total_cost = sum(p.qualified_cost for p in sample_projects)
        expected_credit = total_cost * 0.20
        
        # Get actual credit from report
        actual_credit = report.estimated_credit
        
        logger.info(f"Total Qualified Cost: ${total_cost:,.2f}")
        logger.info(f"Expected Credit (20%): ${expected_credit:,.2f}")
        logger.info(f"Actual Credit: ${actual_credit:,.2f}")
        
        # Verify calculation accuracy (within 0.01%)
        tolerance = expected_credit * 0.0001  # 0.01% tolerance
        difference = abs(actual_credit - expected_credit)
        
        logger.info(f"Difference: ${difference:.2f}")
        logger.info(f"Tolerance (0.01%): ${tolerance:.2f}")
        
        assert difference <= tolerance, \
            f"Estimated credit calculation incorrect: {actual_credit} != {expected_credit} (diff: {difference})"
        
        # Also verify in PDF text
        pdf_text = self._extract_pdf_text(pdf_path)
        credit_in_pdf = self._extract_estimated_credit_from_pdf(pdf_text)
        
        if credit_in_pdf is not None:
            logger.info(f"Estimated Credit in PDF: ${credit_in_pdf:,.2f}")
            pdf_difference = abs(credit_in_pdf - expected_credit)
            assert pdf_difference <= tolerance, \
                f"Estimated credit in PDF incorrect: {credit_in_pdf} != {expected_credit}"
            logger.info("✓ Estimated credit in PDF matches expected value")
        
        logger.info("✓ Estimated Credit Calculation: VERIFIED")
    
    def test_average_confidence_calculation(self, generated_report_and_pdf, sample_projects):
        """
        Verify average_confidence = mean of project confidence scores.
        
        Requirements: Testing, 3.3
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST: Average Confidence Calculation")
        logger.info("=" * 80)
        
        report, pdf_path = generated_report_and_pdf
        
        # Calculate expected average confidence
        expected_avg_confidence = sum(p.confidence_score for p in sample_projects) / len(sample_projects)
        
        # Get actual average from report
        actual_avg_confidence = report.average_confidence
        
        logger.info(f"Project Confidence Scores:")
        for p in sample_projects:
            logger.info(f"  - {p.project_name}: {p.confidence_score:.4f}")
        
        logger.info(f"Expected Average Confidence: {expected_avg_confidence:.4f}")
        logger.info(f"Actual Average Confidence: {actual_avg_confidence:.4f}")
        
        # Verify calculation accuracy (within 0.01%)
        tolerance = expected_avg_confidence * 0.0001  # 0.01% tolerance
        difference = abs(actual_avg_confidence - expected_avg_confidence)
        
        logger.info(f"Difference: {difference:.6f}")
        logger.info(f"Tolerance (0.01%): {tolerance:.6f}")
        
        assert difference <= tolerance, \
            f"Average confidence calculation incorrect: {actual_avg_confidence} != {expected_avg_confidence} (diff: {difference})"
        
        # Also verify in PDF text
        pdf_text = self._extract_pdf_text(pdf_path)
        confidence_in_pdf = self._extract_average_confidence_from_pdf(pdf_text)
        
        if confidence_in_pdf is not None:
            logger.info(f"Average Confidence in PDF: {confidence_in_pdf:.4f}")
            pdf_difference = abs(confidence_in_pdf - expected_avg_confidence)
            # Use slightly larger tolerance for PDF extraction (rounding in display)
            pdf_tolerance = 0.01  # 1% tolerance for PDF display
            assert pdf_difference <= pdf_tolerance, \
                f"Average confidence in PDF incorrect: {confidence_in_pdf} != {expected_avg_confidence}"
            logger.info("✓ Average confidence in PDF matches expected value")
        
        logger.info("✓ Average Confidence Calculation: VERIFIED")
    
    def test_all_calculations_comprehensive(self, generated_report_and_pdf, sample_projects):
        """
        Comprehensive test verifying ALL calculations are accurate within 0.01%.
        
        This is the master test that verifies all calculation accuracy requirements.
        
        Requirements: Testing, 3.3
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST: COMPREHENSIVE CALCULATION VERIFICATION")
        logger.info("=" * 80)
        
        report, pdf_path = generated_report_and_pdf
        
        # Calculate all expected values
        expected_total_hours = sum(p.qualified_hours for p in sample_projects)
        expected_total_cost = sum(p.qualified_cost for p in sample_projects)
        expected_credit = expected_total_cost * 0.20
        expected_avg_confidence = sum(p.confidence_score for p in sample_projects) / len(sample_projects)
        
        # Get all actual values from report
        actual_total_hours = report.total_qualified_hours
        actual_total_cost = report.total_qualified_cost
        actual_credit = report.estimated_credit
        actual_avg_confidence = report.average_confidence
        
        # Define tolerance (0.01%)
        tolerance_hours = expected_total_hours * 0.0001
        tolerance_cost = expected_total_cost * 0.0001
        tolerance_credit = expected_credit * 0.0001
        tolerance_confidence = expected_avg_confidence * 0.0001
        
        # Verify all calculations
        calculations = [
            {
                'name': 'Total Qualified Hours',
                'expected': expected_total_hours,
                'actual': actual_total_hours,
                'tolerance': tolerance_hours,
                'unit': 'hours'
            },
            {
                'name': 'Total Qualified Cost',
                'expected': expected_total_cost,
                'actual': actual_total_cost,
                'tolerance': tolerance_cost,
                'unit': '$'
            },
            {
                'name': 'Estimated Credit (20%)',
                'expected': expected_credit,
                'actual': actual_credit,
                'tolerance': tolerance_credit,
                'unit': '$'
            },
            {
                'name': 'Average Confidence',
                'expected': expected_avg_confidence,
                'actual': actual_avg_confidence,
                'tolerance': tolerance_confidence,
                'unit': ''
            }
        ]
        
        logger.info("\nVerifying all calculations:")
        all_calculations_accurate = True
        
        for calc in calculations:
            difference = abs(calc['actual'] - calc['expected'])
            accuracy_pct = (1 - difference / calc['expected']) * 100 if calc['expected'] != 0 else 100
            
            if calc['unit'] == '$':
                logger.info(f"\n{calc['name']}:")
                logger.info(f"  Expected: ${calc['expected']:,.2f}")
                logger.info(f"  Actual: ${calc['actual']:,.2f}")
                logger.info(f"  Difference: ${difference:.2f}")
                logger.info(f"  Tolerance: ${calc['tolerance']:.2f}")
            elif calc['unit'] == 'hours':
                logger.info(f"\n{calc['name']}:")
                logger.info(f"  Expected: {calc['expected']:.2f} hours")
                logger.info(f"  Actual: {calc['actual']:.2f} hours")
                logger.info(f"  Difference: {difference:.2f} hours")
                logger.info(f"  Tolerance: {calc['tolerance']:.2f} hours")
            else:
                logger.info(f"\n{calc['name']}:")
                logger.info(f"  Expected: {calc['expected']:.4f}")
                logger.info(f"  Actual: {calc['actual']:.4f}")
                logger.info(f"  Difference: {difference:.6f}")
                logger.info(f"  Tolerance: {calc['tolerance']:.6f}")
            
            logger.info(f"  Accuracy: {accuracy_pct:.4f}%")
            
            if difference <= calc['tolerance']:
                logger.info(f"  ✓ PASS (within 0.01% tolerance)")
            else:
                logger.error(f"  ✗ FAIL (exceeds 0.01% tolerance)")
                all_calculations_accurate = False
        
        # Final assertion
        assert all_calculations_accurate, "Some calculations are not within 0.01% accuracy"
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE CALCULATION VERIFICATION: PASSED")
        logger.info("=" * 80)
        logger.info(f"✓ All 4 calculations verified within 0.01% accuracy")
        logger.info(f"✓ Total Hours: {actual_total_hours:.2f} hours")
        logger.info(f"✓ Total Cost: ${actual_total_cost:,.2f}")
        logger.info(f"✓ Estimated Credit: ${actual_credit:,.2f}")
        logger.info(f"✓ Average Confidence: {actual_avg_confidence:.4f}")
        logger.info("=" * 80)
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """
        Extract all text from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Complete text content of PDF
        """
        full_text = ""
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        full_text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page: {e}")
        
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}", exc_info=True)
            raise
        
        return full_text
    
    def _extract_total_hours_from_pdf(self, pdf_text: str) -> Optional[float]:
        """
        Extract total qualified hours from PDF text.
        
        Args:
            pdf_text: Complete PDF text content
            
        Returns:
            Total hours value or None if not found
        """
        # Look for patterns like "Total Qualified Hours: 145.5" or "Total Qualified Hours:145.5"
        patterns = [
            r'Total Qualified Hours[:\s]+([0-9,]+\.?[0-9]*)',
            r'Total Hours[:\s]+([0-9,]+\.?[0-9]*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pdf_text, re.IGNORECASE)
            if match:
                hours_str = match.group(1).replace(',', '')
                try:
                    return float(hours_str)
                except ValueError:
                    continue
        
        return None
    
    def _extract_total_cost_from_pdf(self, pdf_text: str) -> Optional[float]:
        """
        Extract total qualified cost from PDF text.
        
        Args:
            pdf_text: Complete PDF text content
            
        Returns:
            Total cost value or None if not found
        """
        # Look for patterns like "Total Qualified Cost: $10,457.40" or "Total Cost: $10457.40"
        patterns = [
            r'Total Qualified Cost[:\s]+\$([0-9,]+\.?[0-9]*)',
            r'Total Cost[:\s]+\$([0-9,]+\.?[0-9]*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pdf_text, re.IGNORECASE)
            if match:
                cost_str = match.group(1).replace(',', '')
                try:
                    return float(cost_str)
                except ValueError:
                    continue
        
        return None
    
    def _extract_estimated_credit_from_pdf(self, pdf_text: str) -> Optional[float]:
        """
        Extract estimated R&D credit from PDF text.
        
        Args:
            pdf_text: Complete PDF text content
            
        Returns:
            Estimated credit value or None if not found
        """
        # Look for patterns like "Estimated R&D Credit: $2,091.48" or "Estimated Credit: $2091.48"
        patterns = [
            r'Estimated R&D (?:Tax )?Credit[:\s]+\$([0-9,]+\.?[0-9]*)',
            r'Estimated Credit[:\s]+\$([0-9,]+\.?[0-9]*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pdf_text, re.IGNORECASE)
            if match:
                credit_str = match.group(1).replace(',', '')
                try:
                    return float(credit_str)
                except ValueError:
                    continue
        
        return None
    
    def _extract_average_confidence_from_pdf(self, pdf_text: str) -> Optional[float]:
        """
        Extract average confidence from PDF text.
        
        Args:
            pdf_text: Complete PDF text content
            
        Returns:
            Average confidence value (0-1) or None if not found
        """
        # Look for patterns like "Average Confidence: 85.5%" or "Average Confidence: 0.855"
        patterns = [
            r'Average Confidence[:\s]+([0-9]+\.?[0-9]*)%',  # Percentage format
            r'Average Confidence[:\s]+([0-9]+\.?[0-9]*)',   # Decimal format
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, pdf_text, re.IGNORECASE)
            if match:
                confidence_str = match.group(1)
                try:
                    confidence = float(confidence_str)
                    # If it's a percentage (first pattern), convert to decimal
                    if i == 0:
                        confidence = confidence / 100.0
                    return confidence
                except ValueError:
                    continue
        
        return None


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--log-cli-level=INFO"])
