# Tax Models Documentation

## Overview

The `tax_models.py` module contains Pydantic models for R&D tax credit qualification results and audit reporting. These models are used by the Qualification Agent and Audit Trail Agent to track which projects qualify for R&D tax credits and to generate comprehensive audit documentation.

## Models

### QualifiedProject

Represents a project that has been evaluated for R&D tax credit qualification by the Qualification Agent.

#### Key Features

1. **Automatic Low-Confidence Flagging**: Projects with `confidence_score < 0.7` are automatically flagged for manual review
2. **Estimated Credit Calculation**: Automatically calculates the estimated R&D tax credit (20% of qualified costs)
3. **Comprehensive Validation**: Ensures all qualification data meets IRS requirements
4. **Technical Details Support**: Optional field for storing detailed technical information about the R&D activities

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_name` | `str` | Yes | Name of the project being evaluated |
| `qualified_hours` | `float` | Yes | Total hours that qualify for R&D tax credit (≥ 0) |
| `qualified_cost` | `float` | Yes | Total cost that qualifies for R&D tax credit in dollars (≥ 0) |
| `confidence_score` | `float` | Yes | AI confidence in the qualification decision (0-1 range) |
| `qualification_percentage` | `float` | Yes | Percentage of project that qualifies as R&D (0-100) |
| `supporting_citation` | `str` | Yes | IRS document excerpt supporting the qualification |
| `reasoning` | `str` | Yes | Detailed explanation of why the project qualifies |
| `irs_source` | `str` | Yes | Reference to specific IRS document and section |
| `flagged_for_review` | `bool` | No | Whether this project needs manual review (auto-set for low confidence) |
| `technical_details` | `Dict[str, Any]` | No | Additional technical information (e.g., technological_uncertainty, experimentation_process) |

#### Computed Fields

- **`estimated_credit`** (float): Calculated as 20% of `qualified_cost`, representing the estimated R&D tax credit amount

#### Validation Rules

1. **Confidence Score**: Must be between 0 and 1 (inclusive)
2. **Qualification Percentage**: Must be between 0 and 100 (inclusive)
3. **Auto-Flagging**: Projects with `confidence_score < 0.7` are automatically flagged for review
4. **Required Fields**: All string fields must have minimum length of 1
5. **Non-Negative Values**: `qualified_hours` and `qualified_cost` must be ≥ 0

## Usage Examples

### Basic Usage

```python
from models.tax_models import QualifiedProject

# Create a qualified project
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

print(f"Estimated Credit: ${project.estimated_credit}")  # $209.15
print(f"Flagged: {project.flagged_for_review}")  # False
```

### Auto-Flagging for Low Confidence

```python
# Low confidence project is automatically flagged
low_confidence_project = QualifiedProject(
    project_name="Uncertain Project",
    qualified_hours=5.0,
    qualified_cost=500.0,
    confidence_score=0.65,  # Below 0.7 threshold
    qualification_percentage=70.0,
    supporting_citation="Limited evidence...",
    reasoning="Some aspects meet the test...",
    irs_source="CFR Title 26 § 1.41-4"
)

print(project.flagged_for_review)  # True (auto-flagged)
```

### Using Technical Details

```python
project = QualifiedProject(
    project_name="Delta Security",
    qualified_hours=15.0,
    qualified_cost=1370.25,
    confidence_score=0.94,
    qualification_percentage=98.0,
    supporting_citation="Research into quantum-resistant cryptography...",
    reasoning="Strongly meets four-part test...",
    irs_source="CFR Title 26 § 1.41-4(a)(1)",
    technical_details={
        "technological_uncertainty": "Uncertainty regarding post-quantum algorithms...",
        "experimentation_process": "Systematic research and prototyping...",
        "business_component": "Quantum-Resistant Security Layer",
        "qualified_activities": [
            "Post-quantum cryptography research",
            "Algorithm implementation and testing",
            "Performance optimization"
        ]
    }
)

# Access technical details
print(project.technical_details["business_component"])
```

### JSON Serialization

```python
import json

# Serialize to JSON
json_str = project.model_dump_json(indent=2)

# Deserialize from JSON
json_data = json.loads(json_str)
restored_project = QualifiedProject(**json_data)
```

### Loading from Fixture

```python
import json
from pathlib import Path

# Load Phase 1 fixture
fixture_path = Path("tests/fixtures/sample_qualified_projects.json")
with open(fixture_path, 'r') as f:
    projects_data = json.load(f)

# Convert to Pydantic models
projects = [QualifiedProject(**p) for p in projects_data]

# Calculate totals
total_credit = sum(p.estimated_credit for p in projects)
print(f"Total Estimated Credit: ${total_credit:,.2f}")
```

## Integration with Phase 1 Fixtures

The `QualifiedProject` model is fully compatible with the Phase 1 fixture at `tests/fixtures/sample_qualified_projects.json`. This fixture contains 6 sample qualified projects with realistic data for testing and development.

### Fixture Structure

Each project in the fixture includes:
- Basic qualification data (hours, cost, confidence, percentage)
- IRS citations and reasoning
- Technical details including:
  - Technological uncertainty description
  - Experimentation process details
  - Business component identification
  - List of qualified activities

## Auto-Flagging Logic

The model implements automatic flagging for quality control:

1. **Threshold**: Projects with `confidence_score < 0.7` are flagged
2. **Timing**: Flagging occurs during model validation (after all fields are validated)
3. **Override**: Explicitly setting `flagged_for_review=True` works regardless of confidence score
4. **Purpose**: Ensures low-confidence projects receive manual review before inclusion in audit reports

## Estimated Credit Calculation

The `estimated_credit` computed field calculates the R&D tax credit using the standard rate:

- **Formula**: `qualified_cost × 0.20`
- **Rate**: 20% (regular credit under IRC Section 41)
- **Rounding**: Rounded to 2 decimal places
- **Note**: This is a simplified calculation; actual credits may vary based on specific circumstances

## Testing

Comprehensive unit tests are available in `tests/test_tax_models.py`:

```bash
# Run tests
pytest tests/test_tax_models.py -v

# Run with coverage
pytest tests/test_tax_models.py --cov=models.tax_models --cov-report=html
```

Test coverage includes:
- Field validation (confidence score, qualification percentage)
- Auto-flagging logic (low confidence, boundary cases)
- Computed fields (estimated credit calculation)
- JSON serialization/deserialization
- Phase 1 fixture compatibility
- Edge cases and error handling

## Example Script

A comprehensive usage example is available at `examples/tax_models_usage_example.py`:

```bash
# Run example script
python examples/tax_models_usage_example.py
```

The example demonstrates:
1. Basic qualified project creation
2. Auto-flagging for low confidence
3. Estimated credit calculation
4. Technical details usage
5. JSON serialization
6. Validation error handling
7. Loading from Phase 1 fixture

## Requirements Mapping

This model satisfies the following requirements from the design document:

- **Requirement 2.4**: Qualification results with confidence scores and IRS citations
- **Requirement 4.4**: Audit report data structure with project breakdowns
- **Requirement 6.4**: Low-confidence flagging for manual review

## Related Models

- **EmployeeTimeEntry** (`financial_models.py`): Input data for qualification analysis
- **ProjectCost** (`financial_models.py`): Cost data correlated with qualified hours
- **AuditReport** (future): Aggregated report containing multiple QualifiedProject instances

## Best Practices

1. **Always validate confidence scores**: Ensure AI-generated confidence scores are between 0 and 1
2. **Review flagged projects**: Manually review all projects with `flagged_for_review=True`
3. **Include technical details**: Populate `technical_details` for comprehensive audit documentation
4. **Use IRS citations**: Always include specific IRS document references in `irs_source`
5. **Document reasoning**: Provide detailed explanations in the `reasoning` field

## Future Enhancements

Potential future additions to this module:

1. **AuditReport Model**: Aggregate multiple QualifiedProject instances into a complete audit report
2. **RAGContext Model**: Structure for RAG-retrieved IRS document excerpts
3. **ComplianceCheck Model**: Results of final compliance validation
4. **NarrativeTemplate Model**: Structure for R&D project narrative templates

## Support

For questions or issues with the tax models:
1. Review the example script: `examples/tax_models_usage_example.py`
2. Check the unit tests: `tests/test_tax_models.py`
3. Refer to the design document: `.kiro/specs/rd-tax-credit-automation/design.md`
