# Test Fixtures

This directory contains test fixtures generated from real API calls to support testing of the R&D Tax Credit Automation Agent.

## Overview

All fixtures in this directory were generated using real API calls to production services. This ensures that tests validate against realistic data structures and response formats.

## Fixture Files

### 1. clockify_responses.json
**Source:** Clockify API (Time Tracking)  
**Generated:** Real API calls using Clockify API key  
**Workspace:** InsightPro (ID: 69002f0cfa72440e4ca0cf35)

**Contents:**
- `workspace`: Complete workspace configuration and settings
- `users`: List of workspace users with roles and permissions
- `projects`: Project definitions (currently empty in test workspace)
- `time_entries`: Time tracking entries for R&D activities

**Use Cases:**
- Testing time entry ingestion
- Validating project-based time allocation
- Testing user role and permission handling

### 2. unified_to_responses.json
**Source:** Unified.to API (HRIS/ATS Integration)  
**Generated:** Real API calls using Unified.to authentication token  
**Workspace ID:** 690032eb88ddc076f6760d86

**Contents:**
- `candidates`: ATS candidate data with contact information and application details
- `employees`: HRIS employee records with employment information
- `payslips`: Payroll data (endpoint not implemented by provider)

**Use Cases:**
- Testing employee data synchronization
- Validating payroll expense calculations
- Testing candidate-to-employee workflows

### 3. openrouter_responses.json
**Source:** OpenRouter API (LLM via GLM 4.5 AIR)  
**Generated:** Real API calls using OpenRouter API key  
**Model:** z-ai/glm-4.5-air:free

**Contents:**
- `qualification_analysis`: Sample R&D tax credit qualification analysis
  - Includes confidence scoring
  - Four-part test evaluation
  - QRE (Qualified Research Expenses) breakdown
  - Technological uncertainty assessment
  
- `audit_trail_summary`: Sample audit trail documentation
  - Employee time entries with QRA details
  - Project descriptions and technical activities
  - Compliance certification information
  
- `compliance_check`: Sample IRS Form 6765 compliance validation
  - QRE validation by category
  - Four-part test compliance verification
  - Credit calculation examples

**Use Cases:**
- Testing LLM-based qualification analysis
- Validating audit trail generation
- Testing compliance checking logic

### 4. sample_time_entries.json
**Source:** Manually created sample data  
**Purpose:** Structured time entry examples for unit testing

**Use Cases:**
- Unit testing time entry validation
- Testing time allocation algorithms
- Validating R&D activity categorization

### 5. sample_payroll_data.json
**Source:** Manually created sample data  
**Purpose:** Payroll expense examples for testing

**Use Cases:**
- Testing wage expense calculations
- Validating QRE wage allocations
- Testing wage cap applications

### 6. sample_qualified_projects.json
**Source:** Manually created sample data  
**Purpose:** Project qualification examples

**Use Cases:**
- Testing project qualification logic
- Validating four-part test criteria
- Testing confidence scoring algorithms

## Regenerating Fixtures

To regenerate fixtures with fresh API data, run:

```bash
python scripts/generate_fixtures.py
```

This will automatically:
1. Fetch real API responses from Clockify, Unified.to, and OpenRouter
2. Enrich empty data with realistic sample entries
3. Add metadata about generation

**Prerequisites:**
- Valid API keys in `.env` file
- Active internet connection
- API rate limits not exceeded

**What Gets Updated:**
- Clockify workspace, users, projects, and time entries
- Unified.to candidates, employees, and payslips
- OpenRouter LLM responses (3 different analysis types)

### Manual Enrichment

If you only want to enrich existing fixtures without fetching new API data:

```bash
python scripts/enrich_fixtures.py
```

This adds:
- **Clockify**: 3 R&D projects with realistic descriptions
- **Clockify**: 30+ time entries spanning a month with R&D activities
- **Unified.to**: Quarterly payslips with wage calculations
- **Metadata**: Generation timestamps and source information

### Enrichment Details

The enrichment script automatically:
- Detects empty arrays in API responses
- Adds realistic sample data matching the real API schema
- Preserves all real API data that was fetched
- Adds R&D-specific descriptions and activities
- Generates time entries for weekdays only
- Calculates realistic wage and payroll data

## API Configuration

The fixture generation script uses the following API credentials (configured in `.env`):

```env
CLOCKIFY_API_KEY=<your_key>
CLOCKIFY_WORKSPACE_ID=69002f0cfa72440e4ca0cf35

UNIFIED_TO_API_KEY=<your_token>
UNIFIED_TO_WORKSPACE_ID=690032eb88ddc076f6760d86

OPENROUTER_API_KEY=<your_key>
```

## Data Privacy

**Important:** These fixtures contain:
- Real API response structures
- Sample/test data from sandbox environments
- No production customer data
- No sensitive personal information

All employee names, contact information, and business details in the fixtures are either:
- Generated by API sandbox environments
- Anonymized test data
- Synthetic examples created by LLMs

## Using Fixtures in Tests

### Loading Fixtures

```python
import json
from pathlib import Path

def load_fixture(filename):
    """Load a JSON fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with open(fixture_path) as f:
        return json.load(f)

# Example usage
clockify_data = load_fixture("clockify_responses.json")
unified_data = load_fixture("unified_to_responses.json")
openrouter_data = load_fixture("openrouter_responses.json")
```

### Fixture-Based Testing

```python
import pytest
from pathlib import Path
import json

@pytest.fixture
def clockify_workspace():
    """Provide Clockify workspace fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "clockify_responses.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return data["workspace"]

@pytest.mark.integration
def test_workspace_parsing(clockify_workspace):
    """Test workspace data parsing."""
    assert clockify_workspace["id"] == "69002f0cfa72440e4ca0cf35"
    assert clockify_workspace["name"] == "InsightPro"
```

## Maintenance

### When to Regenerate Fixtures

Regenerate fixtures when:
- API response structures change
- New API endpoints are added
- Testing new LLM prompt variations
- Updating to new API versions

### Fixture Validation

Before committing updated fixtures:
1. Verify JSON is valid and properly formatted
2. Check that all expected fields are present
3. Ensure no sensitive data is included
4. Run test suite to verify compatibility

```bash
# Validate JSON syntax
python -m json.tool tests/fixtures/clockify_responses.json > /dev/null

# Run tests with new fixtures
pytest tests/ -v
```

## Troubleshooting

### API Rate Limits

If you encounter rate limit errors:
- Wait a few minutes before retrying
- Use different free models for OpenRouter
- Consider using cached fixtures for development

### Missing Data

Some endpoints may return empty arrays:
- Clockify projects: Empty if no projects exist in workspace
- Clockify time entries: Empty if no time tracked
- Unified.to payslips: Endpoint not implemented by provider

This is expected and tests should handle empty data gracefully.

### Authentication Errors

If API calls fail:
1. Verify API keys in `.env` are current
2. Check API key permissions and scopes
3. Ensure workspace IDs are correct
4. Verify network connectivity

## Related Documentation

- [Testing Guide](../README.md) - Main testing documentation
- [API Connectors](../../tools/api_connectors.py) - API integration code
- [Environment Configuration](../../.env.example) - API key setup

## Version History

- **v1.0** (2024-12-28): Initial fixtures with real API data
  - Clockify: Workspace, users, projects, time entries
  - Unified.to: Candidates, employees
  - OpenRouter: GLM 4.5 AIR model responses
