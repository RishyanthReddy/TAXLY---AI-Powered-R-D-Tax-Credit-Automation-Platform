"""
Unit tests for AuditReport model new fields (narratives, compliance_reviews, aggregated_data).

This test module validates the new fields added to AuditReport for the pipeline fix.
"""

import pytest
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.tax_models import AuditReport, QualifiedProject


class TestAuditReportNewFields:
    """Test suite for AuditReport new fields validation."""
    
    def test_audit_report_with_complete_data(self):
        """Test creating AuditReport with all new fields populated."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        report = AuditReport(
            report_id="RPT-2024-001",
            generation_date=datetime(2024, 12, 15),
            tax_year=2024,
            total_qualified_hours=14.5,
            total_qualified_cost=1045.74,
            estimated_credit=209.15,
            projects=[project],
            narratives={"Alpha Development": "This is a detailed technical narrative..."},
            compliance_reviews={"Alpha Development": {"status": "compliant", "score": 0.95}},
            aggregated_data={
                "total_qualified_hours": 14.5,
                "total_qualified_cost": 1045.74,
                "estimated_credit": 209.15,
                "average_confidence": 0.92
            }
        )
        
        assert report.narratives is not None
        assert "Alpha Development" in report.narratives
        assert report.compliance_reviews is not None
        assert "Alpha Development" in report.compliance_reviews
        assert report.aggregated_data is not None
        assert report.aggregated_data["total_qualified_hours"] == 14.5
    
    def test_audit_report_missing_narratives_with_projects(self):
        """Test that AuditReport with projects but no narratives raises ValidationError."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            AuditReport(
                report_id="RPT-2024-001",
                generation_date=datetime(2024, 12, 15),
                tax_year=2024,
                total_qualified_hours=14.5,
                total_qualified_cost=1045.74,
                estimated_credit=209.15,
                projects=[project],
                narratives=None,  # Missing narratives
                compliance_reviews={"Alpha Development": {"status": "compliant"}},
                aggregated_data={"total_qualified_hours": 14.5}
            )
        
        error_str = str(exc_info.value)
        assert "narratives" in error_str.lower()
    
    def test_audit_report_missing_aggregated_data_with_projects(self):
        """Test that AuditReport with projects but no aggregated_data raises ValidationError."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            AuditReport(
                report_id="RPT-2024-001",
                generation_date=datetime(2024, 12, 15),
                tax_year=2024,
                total_qualified_hours=14.5,
                total_qualified_cost=1045.74,
                estimated_credit=209.15,
                projects=[project],
                narratives={"Alpha Development": "Narrative text"},
                compliance_reviews={"Alpha Development": {"status": "compliant"}},
                aggregated_data=None  # Missing aggregated_data
            )
        
        error_str = str(exc_info.value)
        assert "aggregated_data" in error_str.lower()
    
    def test_audit_report_narrative_project_mismatch(self):
        """Test that narratives must match project names."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            AuditReport(
                report_id="RPT-2024-001",
                generation_date=datetime(2024, 12, 15),
                tax_year=2024,
                total_qualified_hours=14.5,
                total_qualified_cost=1045.74,
                estimated_credit=209.15,
                projects=[project],
                narratives={"Wrong Project Name": "Narrative text"},  # Mismatch
                compliance_reviews={"Alpha Development": {"status": "compliant"}},
                aggregated_data={
                    "total_qualified_hours": 14.5,
                    "total_qualified_cost": 1045.74,
                    "estimated_credit": 209.15,
                    "average_confidence": 0.92
                }
            )
        
        error_str = str(exc_info.value)
        assert "narrative" in error_str.lower() or "missing" in error_str.lower()
    
    def test_audit_report_missing_required_aggregated_keys(self):
        """Test that aggregated_data must contain required keys."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            AuditReport(
                report_id="RPT-2024-001",
                generation_date=datetime(2024, 12, 15),
                tax_year=2024,
                total_qualified_hours=14.5,
                total_qualified_cost=1045.74,
                estimated_credit=209.15,
                projects=[project],
                narratives={"Alpha Development": "Narrative text"},
                compliance_reviews={"Alpha Development": {"status": "compliant"}},
                aggregated_data={"total_qualified_hours": 14.5}  # Missing required keys
            )
        
        error_str = str(exc_info.value)
        assert "aggregated_data" in error_str.lower() and "missing" in error_str.lower()
    
    def test_audit_report_empty_projects_no_validation(self):
        """Test that empty projects list doesn't require narratives or aggregated_data."""
        report = AuditReport(
            report_id="RPT-2024-001",
            generation_date=datetime(2024, 12, 15),
            tax_year=2024,
            total_qualified_hours=0.0,
            total_qualified_cost=0.0,
            estimated_credit=0.0,
            projects=[],
            narratives=None,
            compliance_reviews=None,
            aggregated_data=None
        )
        
        assert report.projects == []
        assert report.narratives is None
        assert report.aggregated_data is None
    
    def test_audit_report_multiple_projects(self):
        """Test AuditReport with multiple projects and matching narratives."""
        project1 = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        project2 = QualifiedProject(
            project_name="Beta Testing",
            qualified_hours=10.0,
            qualified_cost=720.00,
            confidence_score=0.85,
            qualification_percentage=90.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="CFR Title 26 § 1.41-4"
        )
        
        report = AuditReport(
            report_id="RPT-2024-001",
            generation_date=datetime(2024, 12, 15),
            tax_year=2024,
            total_qualified_hours=24.5,
            total_qualified_cost=1765.74,
            estimated_credit=353.15,
            projects=[project1, project2],
            narratives={
                "Alpha Development": "Narrative for Alpha",
                "Beta Testing": "Narrative for Beta"
            },
            compliance_reviews={
                "Alpha Development": {"status": "compliant"},
                "Beta Testing": {"status": "compliant"}
            },
            aggregated_data={
                "total_qualified_hours": 24.5,
                "total_qualified_cost": 1765.74,
                "estimated_credit": 353.15,
                "average_confidence": 0.885
            }
        )
        
        assert len(report.projects) == 2
        assert len(report.narratives) == 2
        assert "Alpha Development" in report.narratives
        assert "Beta Testing" in report.narratives
