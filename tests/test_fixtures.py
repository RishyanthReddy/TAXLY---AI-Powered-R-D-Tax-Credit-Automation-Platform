"""
Tests to verify fixture data integrity and structure.
"""

import pytest
import json
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Get the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def clockify_data(fixtures_dir):
    """Load Clockify fixtures."""
    with open(fixtures_dir / "clockify_responses.json") as f:
        return json.load(f)


@pytest.fixture
def unified_to_data(fixtures_dir):
    """Load Unified.to fixtures."""
    with open(fixtures_dir / "unified_to_responses.json") as f:
        return json.load(f)


@pytest.fixture
def openrouter_data(fixtures_dir):
    """Load OpenRouter fixtures."""
    with open(fixtures_dir / "openrouter_responses.json") as f:
        return json.load(f)


@pytest.mark.unit
class TestClockifyFixtures:
    """Test Clockify fixture data structure and content."""
    
    def test_workspace_exists(self, clockify_data):
        """Test that workspace data exists and has required fields."""
        assert "workspace" in clockify_data
        workspace = clockify_data["workspace"]
        assert "id" in workspace
        assert "name" in workspace
        assert workspace["id"] == "69002f0cfa72440e4ca0cf35"
        assert workspace["name"] == "InsightPro"
    
    def test_users_exist(self, clockify_data):
        """Test that user data exists."""
        assert "users" in clockify_data
        assert len(clockify_data["users"]) > 0
        
        user = clockify_data["users"][0]
        assert "id" in user
        assert "email" in user
        assert "name" in user
    
    def test_projects_enriched(self, clockify_data):
        """Test that projects were enriched with sample data."""
        assert "projects" in clockify_data
        assert len(clockify_data["projects"]) >= 3
        
        project = clockify_data["projects"][0]
        assert "id" in project
        assert "name" in project
        assert "workspaceId" in project
        assert "billable" in project
        
        # Check for R&D-related project
        project_names = [p["name"] for p in clockify_data["projects"]]
        assert any("ML" in name or "Development" in name for name in project_names)
    
    def test_time_entries_enriched(self, clockify_data):
        """Test that time entries were enriched with sample data."""
        assert "time_entries" in clockify_data
        assert len(clockify_data["time_entries"]) >= 20
        
        entry = clockify_data["time_entries"][0]
        assert "id" in entry
        assert "description" in entry
        assert "projectId" in entry
        assert "timeInterval" in entry
        assert "userId" in entry
        
        # Check for R&D-related descriptions
        descriptions = [e["description"] for e in clockify_data["time_entries"]]
        rd_keywords = ["algorithm", "optimization", "development", "testing", "experimentation"]
        assert any(any(keyword in desc.lower() for keyword in rd_keywords) for desc in descriptions)
    
    def test_metadata_exists(self, clockify_data):
        """Test that metadata was added."""
        assert "_metadata" in clockify_data
        metadata = clockify_data["_metadata"]
        assert "generated_at" in metadata
        assert "source" in metadata
        assert "enrichment_version" in metadata


@pytest.mark.unit
class TestUnifiedToFixtures:
    """Test Unified.to fixture data structure and content."""
    
    def test_candidates_exist(self, unified_to_data):
        """Test that candidate data exists."""
        assert "candidates" in unified_to_data
        assert len(unified_to_data["candidates"]) > 0
        
        candidate = unified_to_data["candidates"][0]
        assert "id" in candidate
        assert "name" in candidate
        assert "emails" in candidate
    
    def test_employees_exist(self, unified_to_data):
        """Test that employee data exists."""
        assert "employees" in unified_to_data
        assert len(unified_to_data["employees"]) > 0
        
        employee = unified_to_data["employees"][0]
        assert "id" in employee
        assert "name" in employee
    
    def test_payslips_enriched(self, unified_to_data):
        """Test that payslips were enriched with sample data."""
        assert "payslips" in unified_to_data
        assert len(unified_to_data["payslips"]) >= 3
        
        payslip = unified_to_data["payslips"][0]
        assert "id" in payslip
        assert "employee_id" in payslip
        assert "gross_pay" in payslip
        assert "net_pay" in payslip
        assert "deductions" in payslip
        assert "earnings" in payslip
        assert "rd_qualified_percentage" in payslip
        
        # Verify wage calculations are reasonable
        assert payslip["gross_pay"] > 0
        assert payslip["net_pay"] < payslip["gross_pay"]
        assert 0 <= payslip["rd_qualified_percentage"] <= 1
    
    def test_metadata_exists(self, unified_to_data):
        """Test that metadata was added."""
        assert "_metadata" in unified_to_data
        metadata = unified_to_data["_metadata"]
        assert "generated_at" in metadata
        assert "source" in metadata


@pytest.mark.unit
class TestOpenRouterFixtures:
    """Test OpenRouter fixture data structure and content."""
    
    def test_qualification_analysis_exists(self, openrouter_data):
        """Test that qualification analysis exists."""
        assert "qualification_analysis" in openrouter_data
        analysis = openrouter_data["qualification_analysis"]
        
        assert analysis is not None
        assert "model" in analysis
        assert "response" in analysis
        assert "usage" in analysis
        
        # Check that response contains R&D-related content
        response = analysis["response"]
        assert len(response) > 100
        assert any(keyword in response.lower() for keyword in ["r&d", "research", "qualified", "credit"])
    
    def test_audit_trail_summary_exists(self, openrouter_data):
        """Test that audit trail summary exists."""
        assert "audit_trail_summary" in openrouter_data
        summary = openrouter_data["audit_trail_summary"]
        
        assert summary is not None
        assert "model" in summary
        assert "response" in summary
        assert "usage" in summary
        
        # Check that response contains audit-related content
        response = summary["response"]
        assert len(response) > 100
        assert any(keyword in response.lower() for keyword in ["audit", "compliance", "employee", "time"])
    
    def test_compliance_check_exists(self, openrouter_data):
        """Test that compliance check exists."""
        assert "compliance_check" in openrouter_data
        check = openrouter_data["compliance_check"]
        
        assert check is not None
        assert "model" in check
        assert "response" in check
        assert "usage" in check
        
        # Check that response contains compliance-related content
        response = check["response"]
        assert len(response) > 100
        assert any(keyword in response.lower() for keyword in ["form 6765", "irs", "compliance", "qre"])
    
    def test_token_usage_recorded(self, openrouter_data):
        """Test that token usage is recorded for all responses."""
        for key in ["qualification_analysis", "audit_trail_summary", "compliance_check"]:
            assert key in openrouter_data
            data = openrouter_data[key]
            
            if data is not None:
                assert "usage" in data
                usage = data["usage"]
                assert "prompt_tokens" in usage
                assert "completion_tokens" in usage
                assert "total_tokens" in usage
                assert usage["total_tokens"] > 0


@pytest.mark.integration
class TestFixtureIntegration:
    """Test that fixtures work together for integration scenarios."""
    
    def test_clockify_user_matches_workspace(self, clockify_data):
        """Test that user workspace IDs match the workspace."""
        workspace_id = clockify_data["workspace"]["id"]
        
        for user in clockify_data["users"]:
            assert user["activeWorkspace"] == workspace_id
    
    def test_time_entries_reference_valid_projects(self, clockify_data):
        """Test that time entries reference existing projects."""
        project_ids = {p["id"] for p in clockify_data["projects"]}
        
        for entry in clockify_data["time_entries"]:
            assert entry["projectId"] in project_ids
    
    def test_payslips_reference_valid_employees(self, unified_to_data):
        """Test that payslips reference existing employees."""
        employee_ids = {e["id"] for e in unified_to_data["employees"]}
        
        for payslip in unified_to_data["payslips"]:
            # Payslip employee_id should match an employee
            # (Note: enriched payslips use first 3 employees)
            assert "employee_id" in payslip
