"""
Test IRS Citations Section Implementation (Task 14)

This test verifies that the _add_irs_citations() method correctly generates
the IRS citations section with proper formatting for each project.

Requirements tested:
- _add_irs_citations() method exists
- For each project, citation section includes:
  - Project name
  - IRS source reference (project.irs_source)
  - Supporting citation text (project.supporting_citation)
  - Professional formatting
- Method is called in generate_report() workflow
"""

import sys
from pathlib import Path
from datetime import datetime
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pdf_generator import PDFGenerator
from models.tax_models import QualifiedProject, AuditReport


class TestIRSCitationsSection:
    """Test suite for IRS citations section implementation."""
    
    @pytest.fixture
    def sample_projects(self):
        """Create sample qualified projects with IRS citations."""
        return [
            QualifiedProject(
                project_name="Authentication System Development",
                qualified_hours=45.5,
                qualified_cost=3275.50,
                confidence_score=0.92,
                qualification_percentage=95.0,
                supporting_citation=(
                    "The development of new or improved business components through "
                    "a process of experimentation constitutes qualified research under "
                    "IRC Section 41. The authentication system development involved "
                    "systematic evaluation of multiple encryption algorithms and "
                    "authentication protocols to resolve technological uncertainty "
                    "regarding secure, high-performance user authentication."
                ),
                reasoning=(
                    "This project meets the four-part test: (1) Technological in nature - "
                    "involves computer science and cryptography; (2) Qualified purpose - "
                    "developing new functionality; (3) Technological uncertainty - "
                    "uncertainty about optimal encryption approach; (4) Process of "
                    "experimentation - systematic evaluation of authentication methods."
                ),
                irs_source="CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research"
            ),
            QualifiedProject(
                project_name="Database Optimization Engine",
                qualified_hours=32.0,
                qualified_cost=2304.00,
                confidence_score=0.88,
                qualification_percentage=90.0,
                supporting_citation=(
                    "Research activities that seek to discover information that is "
                    "technological in nature and intended to eliminate uncertainty "
                    "concerning the development of a business component qualify under "
                    "IRC Section 41. The database optimization work addressed uncertainty "
                    "regarding query performance at scale and involved systematic testing "
                    "of indexing strategies and caching mechanisms."
                ),
                reasoning=(
                    "The database optimization project qualifies as it involved resolving "
                    "technological uncertainty through experimentation with various indexing "
                    "algorithms, query optimization techniques, and caching strategies to "
                    "achieve sub-100ms query response times for datasets exceeding 10M records."
                ),
                irs_source="CFR Title 26 § 1.41-4(a)(3) - Process of Experimentation"
            ),
            QualifiedProject(
                project_name="Machine Learning Model Training",
                qualified_hours=28.5,
                qualified_cost=2052.00,
                confidence_score=0.85,
                qualification_percentage=85.0,
                supporting_citation=(
                    "Qualified research includes activities undertaken to discover "
                    "information that would eliminate uncertainty concerning the capability "
                    "or method for developing or improving a business component. The ML "
                    "model training involved experimentation with neural network architectures, "
                    "hyperparameter tuning, and feature engineering to achieve target accuracy."
                ),
                reasoning=(
                    "This project involved systematic experimentation to resolve uncertainty "
                    "about which neural network architecture and training approach would achieve "
                    "95% accuracy on the classification task, meeting all four parts of the test."
                ),
                irs_source="CFR Title 26 § 1.41-4(a)(2) - Elimination of Uncertainty"
            )
        ]
    
    @pytest.fixture
    def sample_report(self, sample_projects):
        """Create a complete audit report with narratives and aggregated data."""
        # Calculate aggregated metrics
        total_hours = sum(p.qualified_hours for p in sample_projects)
        total_cost = sum(p.qualified_cost for p in sample_projects)
        estimated_credit = total_cost * 0.20
        avg_confidence = sum(p.confidence_score for p in sample_projects) / len(sample_projects)
        
        # Create narratives dictionary
        narratives = {
            "Authentication System Development": (
                "The Authentication System Development project addressed significant "
                "technological uncertainty regarding the implementation of a secure, "
                "high-performance authentication system capable of handling 10,000+ "
                "concurrent users. The team systematically evaluated multiple encryption "
                "algorithms (AES-256, RSA-4096, ECC) and authentication protocols "
                "(OAuth 2.0, JWT, SAML) through a rigorous process of experimentation. "
                "This involved designing test scenarios, implementing prototypes, conducting "
                "security vulnerability assessments, and performance benchmarking. The "
                "experimentation process revealed that a hybrid approach combining ECC for "
                "key exchange and AES-256 for session encryption provided the optimal "
                "balance of security and performance. The project clearly meets the four-part "
                "test as it was technological in nature, undertaken for a qualified purpose, "
                "involved eliminating uncertainty, and followed a systematic process of "
                "experimentation."
            ),
            "Database Optimization Engine": (
                "The Database Optimization Engine project focused on resolving technological "
                "uncertainty related to achieving sub-100ms query response times for a "
                "database containing over 10 million records. The development team conducted "
                "systematic experiments with various indexing strategies (B-tree, hash, "
                "bitmap), query optimization techniques (query rewriting, execution plan "
                "analysis), and caching mechanisms (Redis, Memcached, application-level "
                "caching). Through controlled testing and performance measurement, the team "
                "evaluated each approach's impact on query latency, memory usage, and "
                "scalability. The experimentation revealed that a combination of composite "
                "B-tree indexes with Redis caching achieved the target performance while "
                "maintaining data consistency. This project qualifies under IRC Section 41 "
                "as it involved technological uncertainty, systematic experimentation, and "
                "resulted in improved database performance capabilities."
            ),
            "Machine Learning Model Training": (
                "The Machine Learning Model Training project addressed uncertainty regarding "
                "the optimal neural network architecture and training methodology to achieve "
                "95% classification accuracy on a complex multi-class dataset. The research "
                "team systematically experimented with various deep learning architectures "
                "(CNNs, RNNs, Transformers), hyperparameter configurations (learning rates, "
                "batch sizes, regularization), and feature engineering approaches. Each "
                "configuration was evaluated through rigorous cross-validation and performance "
                "metrics analysis. The experimentation process involved over 200 training runs "
                "with different combinations of architectures and parameters. Ultimately, a "
                "custom Transformer-based architecture with specific attention mechanisms and "
                "regularization techniques achieved the target accuracy. This project clearly "
                "satisfies the four-part test through its technological nature, qualified "
                "purpose of improving model accuracy, elimination of architectural uncertainty, "
                "and systematic experimentation process."
            )
        }
        
        # Create compliance reviews dictionary
        compliance_reviews = {
            "Authentication System Development": {
                "status": "Compliant",
                "completeness_score": 0.95,
                "required_revisions": []
            },
            "Database Optimization Engine": {
                "status": "Compliant",
                "completeness_score": 0.92,
                "required_revisions": []
            },
            "Machine Learning Model Training": {
                "status": "Compliant",
                "completeness_score": 0.90,
                "required_revisions": []
            }
        }
        
        # Create aggregated data dictionary
        aggregated_data = {
            'total_qualified_hours': total_hours,
            'total_qualified_cost': total_cost,
            'estimated_credit': estimated_credit,
            'average_confidence': avg_confidence,
            'high_confidence_count': 2,
            'medium_confidence_count': 1,
            'low_confidence_count': 0,
            'flagged_count': 0
        }
        
        return AuditReport(
            report_id="TEST-IRS-CITATIONS-001",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=total_hours,
            total_qualified_cost=total_cost,
            estimated_credit=estimated_credit,
            average_confidence=avg_confidence,
            project_count=len(sample_projects),
            flagged_project_count=0,
            projects=sample_projects,
            company_name="Test Company Inc.",
            narratives=narratives,
            compliance_reviews=compliance_reviews,
            aggregated_data=aggregated_data
        )
    
    def test_add_irs_citations_method_exists(self):
        """Test that _add_irs_citations method exists on PDFGenerator."""
        generator = PDFGenerator()
        assert hasattr(generator, '_add_irs_citations'), \
            "_add_irs_citations method does not exist on PDFGenerator"
        assert callable(generator._add_irs_citations), \
            "_add_irs_citations is not callable"
    
    def test_add_irs_citations_returns_elements(self, sample_report):
        """Test that _add_irs_citations returns a list of elements."""
        generator = PDFGenerator()
        elements = generator._add_irs_citations(sample_report)
        
        assert isinstance(elements, list), \
            "_add_irs_citations should return a list"
        assert len(elements) > 0, \
            "_add_irs_citations should return non-empty list"
    
    def test_irs_citations_includes_all_projects(self, sample_report):
        """Test that IRS citations section includes all projects."""
        generator = PDFGenerator()
        elements = generator._add_irs_citations(sample_report)
        
        # Convert elements to string for content checking
        content = str(elements)
        
        # Verify all project names are present
        for project in sample_report.projects:
            assert project.project_name in content, \
                f"Project '{project.project_name}' not found in IRS citations section"
    
    def test_irs_citations_includes_irs_sources(self, sample_report):
        """Test that IRS citations include IRS source references."""
        generator = PDFGenerator()
        elements = generator._add_irs_citations(sample_report)
        
        # Convert elements to string for content checking
        content = str(elements)
        
        # Verify all IRS sources are present
        for project in sample_report.projects:
            assert project.irs_source in content, \
                f"IRS source '{project.irs_source}' not found in citations section"
    
    def test_irs_citations_includes_supporting_citations(self, sample_report):
        """Test that IRS citations include supporting citation text."""
        generator = PDFGenerator()
        elements = generator._add_irs_citations(sample_report)
        
        # Convert elements to string for content checking
        content = str(elements)
        
        # Verify supporting citations are present (check for key phrases)
        for project in sample_report.projects:
            # Check for a significant portion of the citation text
            citation_snippet = project.supporting_citation[:50]
            assert citation_snippet in content, \
                f"Supporting citation for '{project.project_name}' not found"
    
    def test_irs_citations_professional_formatting(self, sample_report):
        """Test that IRS citations section has professional formatting."""
        generator = PDFGenerator()
        elements = generator._add_irs_citations(sample_report)
        
        # Convert elements to string
        content = str(elements)
        
        # Check for section heading
        assert "IRS Citations" in content, \
            "Section heading 'IRS Citations' not found"
        
        # Check for professional formatting indicators
        assert "IRS Source Reference" in content, \
            "IRS Source Reference heading not found"
        assert "Supporting Citation" in content, \
            "Supporting Citation heading not found"
        assert "Application to Project" in content, \
            "Application to Project context not found"
    
    def test_irs_citations_includes_general_references(self, sample_report):
        """Test that IRS citations section includes general regulatory references."""
        generator = PDFGenerator()
        elements = generator._add_irs_citations(sample_report)
        
        # Convert elements to string
        content = str(elements)
        
        # Check for general references section
        assert "General Regulatory Framework" in content, \
            "General Regulatory Framework section not found"
        
        # Check for key regulatory references
        assert "Internal Revenue Code (IRC) Section 41" in content, \
            "IRC Section 41 reference not found"
        assert "Code of Federal Regulations (CFR)" in content, \
            "CFR reference not found"
        assert "IRS Form 6765" in content, \
            "IRS Form 6765 reference not found"
    
    def test_generate_report_calls_add_irs_citations(self, sample_report, tmp_path):
        """Test that generate_report() calls _add_irs_citations in the workflow."""
        generator = PDFGenerator()
        
        # Generate PDF report
        pdf_path = generator.generate_report(
            sample_report,
            str(tmp_path),
            "test_irs_citations.pdf"
        )
        
        # Verify PDF was created
        assert Path(pdf_path).exists(), \
            "PDF file was not created"
        
        # Verify PDF has reasonable size (should include citations section)
        pdf_size = Path(pdf_path).stat().st_size
        assert pdf_size > 10000, \
            f"PDF size ({pdf_size} bytes) is too small - may be missing sections"
        
        print(f"\n✓ PDF generated successfully: {pdf_path}")
        print(f"✓ PDF size: {pdf_size:,} bytes ({pdf_size / 1024:.2f} KB)")
    
    def test_irs_citations_with_empty_report(self):
        """Test that _add_irs_citations handles empty report gracefully."""
        generator = PDFGenerator()
        
        # Create empty report
        empty_report = AuditReport(
            report_id="EMPTY-001",
            generation_date=datetime.now(),
            tax_year=2024,
            total_qualified_hours=0.0,
            total_qualified_cost=0.0,
            estimated_credit=0.0,
            average_confidence=0.0,
            project_count=0,
            flagged_project_count=0,
            projects=[],
            narratives={},
            compliance_reviews={},
            aggregated_data={}
        )
        
        # Should not raise exception
        elements = generator._add_irs_citations(empty_report)
        
        assert isinstance(elements, list), \
            "_add_irs_citations should return list even for empty report"
        
        # Convert to string and check for appropriate message
        content = str(elements)
        assert "No IRS citations available" in content or "IRS Citations" in content, \
            "Should indicate no citations available for empty report"
    
    def test_irs_citations_section_order(self, sample_report):
        """Test that IRS citations are presented in correct order."""
        generator = PDFGenerator()
        elements = generator._add_irs_citations(sample_report)
        
        # Convert elements to string
        content = str(elements)
        
        # Find positions of project names in content
        positions = {}
        for i, project in enumerate(sample_report.projects, 1):
            # Look for "Citation X: Project Name" pattern
            citation_label = f"Citation {i}: {project.project_name}"
            pos = content.find(citation_label)
            if pos != -1:
                positions[project.project_name] = pos
        
        # Verify all projects were found
        assert len(positions) == len(sample_report.projects), \
            "Not all projects found in citations section"
        
        # Verify they appear in order
        project_names = [p.project_name for p in sample_report.projects]
        sorted_positions = sorted(positions.items(), key=lambda x: x[1])
        sorted_names = [name for name, _ in sorted_positions]
        
        assert sorted_names == project_names, \
            f"Projects not in correct order. Expected: {project_names}, Got: {sorted_names}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
