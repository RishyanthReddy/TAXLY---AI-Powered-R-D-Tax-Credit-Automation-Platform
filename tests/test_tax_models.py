"""
Unit tests for QualifiedProject model from tax_models.

This test module focuses on validating the QualifiedProject Pydantic model
to ensure proper validation, serialization, and data integrity for R&D tax
credit qualification results.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.tax_models import QualifiedProject


class TestQualifiedProject:
    """Test suite for QualifiedProject model validation and functionality."""
    
    def test_valid_qualified_project_creation(self):
        """Test creating a valid QualifiedProject with all required fields."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="The project involves developing a new authentication algorithm...",
            reasoning="This project clearly meets the four-part test...",
            irs_source="CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research"
        )
        
        assert project.project_name == "Alpha Development"
        assert project.qualified_hours == 14.5
        assert project.qualified_cost == 1045.74
        assert project.confidence_score == 0.92
        assert project.qualification_percentage == 95.0
        assert project.flagged_for_review is False
        assert project.estimated_credit == 209.15
    
    def test_confidence_score_validation_valid_range(self):
        """Test that confidence_score within 0-1 range is valid."""
        # Test minimum valid value
        project_min = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.0,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_min.confidence_score == 0.0
        
        # Test maximum valid value
        project_max = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=1.0,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_max.confidence_score == 1.0
        
        # Test mid-range value
        project_mid = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.5,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_mid.confidence_score == 0.5
    
    def test_confidence_score_validation_below_range(self):
        """Test that confidence_score < 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=-0.1,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "confidence_score" in error_str
    
    def test_confidence_score_validation_above_range(self):
        """Test that confidence_score > 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=1.5,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "confidence_score" in error_str
    
    def test_auto_flagging_low_confidence(self):
        """Test that projects with confidence < 0.7 are automatically flagged."""
        # Test with confidence = 0.69 (should be flagged)
        project_low = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.69,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_low.flagged_for_review is True
        
        # Test with confidence = 0.5 (should be flagged)
        project_very_low = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.5,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_very_low.flagged_for_review is True
    
    def test_auto_flagging_high_confidence(self):
        """Test that projects with confidence >= 0.7 are not auto-flagged."""
        # Test with confidence = 0.7 (should NOT be flagged)
        project_threshold = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.7,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_threshold.flagged_for_review is False
        
        # Test with confidence = 0.9 (should NOT be flagged)
        project_high = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.9,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_high.flagged_for_review is False
    
    def test_manual_flagging_overrides_auto_flag(self):
        """Test that explicitly setting flagged_for_review=True works even with high confidence."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.95,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source",
            flagged_for_review=True
        )
        assert project.flagged_for_review is True
    
    def test_qualification_percentage_validation_valid_range(self):
        """Test that qualification_percentage within 0-100 range is valid."""
        # Test minimum valid value
        project_min = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=0.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_min.qualification_percentage == 0.0
        
        # Test maximum valid value
        project_max = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=100.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_max.qualification_percentage == 100.0
        
        # Test mid-range value
        project_mid = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project_mid.qualification_percentage == 50.0
    
    def test_qualification_percentage_validation_below_range(self):
        """Test that qualification_percentage < 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=-5.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "qualification_percentage" in error_str
    
    def test_qualification_percentage_validation_above_range(self):
        """Test that qualification_percentage > 100 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=105.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        error_str = str(exc_info.value)
        assert "qualification_percentage" in error_str
    
    def test_estimated_credit_computation(self):
        """Test that estimated_credit is correctly calculated as 20% of qualified_cost."""
        # Test with $1000 cost (should be $200 credit)
        project1 = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project1.estimated_credit == 200.0
        
        # Test with $1045.74 cost (should be $209.15 credit)
        project2 = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project2.estimated_credit == 209.15
        
        # Test with $5000 cost (should be $1000 credit)
        project3 = QualifiedProject(
            project_name="Test Project",
            qualified_hours=50.0,
            qualified_cost=5000.0,
            confidence_score=0.85,
            qualification_percentage=80.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project3.estimated_credit == 1000.0
    
    def test_estimated_credit_computation_zero_cost(self):
        """Test that estimated_credit is 0 when qualified_cost is 0."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=0.0,
            qualified_cost=0.0,
            confidence_score=0.8,
            qualification_percentage=0.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        assert project.estimated_credit == 0.0
    
    def test_estimated_credit_rounding(self):
        """Test that estimated_credit is properly rounded to 2 decimal places."""
        # Test with cost that results in repeating decimal
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=333.33,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        # 333.33 * 0.20 = 66.666, should round to 66.67
        assert project.estimated_credit == 66.67
    
    def test_json_serialization(self):
        """Test JSON serialization of QualifiedProject."""
        project = QualifiedProject(
            project_name="Alpha Development",
            qualified_hours=14.5,
            qualified_cost=1045.74,
            confidence_score=0.92,
            qualification_percentage=95.0,
            supporting_citation="The project involves developing a new authentication algorithm...",
            reasoning="This project clearly meets the four-part test...",
            irs_source="CFR Title 26 § 1.41-4(a)(1)"
        )
        
        json_str = project.model_dump_json()
        
        assert isinstance(json_str, str)
        assert "Alpha Development" in json_str
        assert "14.5" in json_str
        assert "1045.74" in json_str
        assert "0.92" in json_str
        assert "95" in json_str
        
        # Verify it's valid JSON
        json_dict = json.loads(json_str)
        assert json_dict["project_name"] == "Alpha Development"
        assert json_dict["confidence_score"] == 0.92
    
    def test_json_deserialization(self):
        """Test JSON deserialization into QualifiedProject."""
        json_data = {
            "project_name": "Alpha Development",
            "qualified_hours": 14.5,
            "qualified_cost": 1045.74,
            "confidence_score": 0.92,
            "qualification_percentage": 95.0,
            "supporting_citation": "The project involves developing a new authentication algorithm...",
            "reasoning": "This project clearly meets the four-part test...",
            "irs_source": "CFR Title 26 § 1.41-4(a)(1)"
        }
        
        project = QualifiedProject(**json_data)
        
        assert project.project_name == "Alpha Development"
        assert project.qualified_hours == 14.5
        assert project.qualified_cost == 1045.74
        assert project.confidence_score == 0.92
        assert project.qualification_percentage == 95.0
        assert project.estimated_credit == 209.15
    
    def test_str_representation(self):
        """Test the __str__ method returns a formatted string."""
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
        
        str_repr = str(project)
        
        # Verify string contains key information
        assert "Alpha Development" in str_repr
        assert "14.5" in str_repr
        assert "1045.74" in str_repr
        assert "95" in str_repr
        assert "0.92" in str_repr
        assert "FLAGGED" not in str_repr  # High confidence, not flagged
    
    def test_str_representation_flagged(self):
        """Test __str__ method includes flag indicator for flagged projects."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.65,  # Low confidence, will be auto-flagged
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        str_repr = str(project)
        
        # Verify string contains flag indicator
        assert "FLAGGED FOR REVIEW" in str_repr
    
    def test_technical_details_optional(self):
        """Test that technical_details is optional and defaults to None."""
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source"
        )
        
        assert project.technical_details is None
    
    def test_technical_details_provided(self):
        """Test that technical_details can be provided with custom data."""
        technical_info = {
            "technological_uncertainty": "Uncertainty about encryption methods",
            "experimentation_process": "Tested multiple algorithms",
            "business_component": "Authentication System"
        }
        
        project = QualifiedProject(
            project_name="Test Project",
            qualified_hours=10.0,
            qualified_cost=1000.0,
            confidence_score=0.8,
            qualification_percentage=50.0,
            supporting_citation="Test citation",
            reasoning="Test reasoning",
            irs_source="Test source",
            technical_details=technical_info
        )
        
        assert project.technical_details is not None
        assert project.technical_details["technological_uncertainty"] == "Uncertainty about encryption methods"
        assert project.technical_details["business_component"] == "Authentication System"
    
    def test_required_fields_validation(self):
        """Test that missing required fields raise ValidationError."""
        # Missing project_name
        with pytest.raises(ValidationError):
            QualifiedProject(
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        # Missing confidence_score
        with pytest.raises(ValidationError):
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                qualification_percentage=50.0,
                supporting_citation="Test citation",
                reasoning="Test reasoning",
                irs_source="Test source"
            )
        
        # Missing supporting_citation
        with pytest.raises(ValidationError):
            QualifiedProject(
                project_name="Test Project",
                qualified_hours=10.0,
                qualified_cost=1000.0,
                confidence_score=0.8,
                qualification_percentage=50.0,
                reasoning="Test reasoning",
                irs_source="Test source"
            )
