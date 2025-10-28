# Financial Models Documentation

This document describes the financial data models used in the R&D Tax Credit Automation Agent.

## EmployeeTimeEntry

The `EmployeeTimeEntry` model represents a single time tracking entry for an employee working on a project. This model is used to capture time data from systems like Clockify and validate it for R&D tax credit qualification analysis.

### Fields

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `employee_id` | `str` | Yes | Unique identifier for the employee (e.g., "EMP001") | Min length: 1 |
| `employee_name` | `str` | Yes | Full name of the employee | Min length: 1 |
| `project_name` | `str` | Yes | Name of the project | Min length: 1 |
| `task_description` | `str` | Yes | Detailed description of the work performed | Min length: 1 |
| `hours_spent` | `float` | Yes | Number of hours spent on the task | 0 < hours ≤ 24 |
| `date` | `datetime` | Yes | Date and time when the work was performed | Cannot be future date |
| `is_rd_classified` | `bool` | No | Whether this time entry is classified as R&D work | Default: `False` |

### Validation Rules

1. **hours_spent**: Must be greater than 0 and not exceed 24 hours in a single day
2. **date**: Cannot be in the future (validated against current datetime)
3. **is_rd_classified**: Defaults to `False` if not provided

### Usage Example

```python
from models.financial_models import EmployeeTimeEntry

# Create a time entry
entry = EmployeeTimeEntry(
    employee_id="EMP001",
    employee_name="Alice Johnson",
    project_name="Alpha Development",
    task_description="Implemented new authentication algorithm with encryption",
    hours_spent=8.5,
    date="2024-03-15T09:00:00",
    is_rd_classified=True
)

# Access fields
print(entry.employee_id)  # "EMP001"
print(entry.hours_spent)  # 8.5
print(entry)  # "EMP001 - Alice Johnson: 8.5 hours on Alpha Development (2024-03-15)"

# Serialize to JSON
json_str = entry.model_dump_json()

# Deserialize from JSON
import json
entry_data = json.loads(json_str)
restored_entry = EmployeeTimeEntry(**entry_data)
```

### JSON Format

The model is compatible with the Phase 1 `sample_time_entries.json` fixture format:

```json
{
  "employee_id": "EMP001",
  "employee_name": "Alice Johnson",
  "project_name": "Alpha Development",
  "task_description": "Implemented new authentication algorithm with encryption",
  "hours_spent": 8.5,
  "date": "2024-03-15T09:00:00",
  "is_rd_classified": true
}
```

### Integration with Phase 1

This model is designed to work seamlessly with the Phase 1 JSON fixtures:
- `tests/fixtures/sample_time_entries.json` - Sample time tracking data

All Phase 1 fixture data can be loaded and validated using this model:

```python
import json
from pathlib import Path
from models.financial_models import EmployeeTimeEntry

# Load Phase 1 fixture
with open("tests/fixtures/sample_time_entries.json", 'r') as f:
    time_entries_data = json.load(f)

# Convert to Pydantic models
entries = [EmployeeTimeEntry(**entry_data) for entry_data in time_entries_data]

# All entries are now validated and type-safe
```

### Error Handling

The model raises `pydantic.ValidationError` when validation fails:

```python
from pydantic import ValidationError

try:
    entry = EmployeeTimeEntry(
        employee_id="EMP001",
        employee_name="Alice Johnson",
        project_name="Test Project",
        task_description="Test task",
        hours_spent=25.0,  # Invalid: exceeds 24 hours
        date="2024-03-15T09:00:00"
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Testing

Comprehensive unit tests are available in `tests/test_financial_models.py`:
- Valid entry creation
- Hours validation (negative, zero, exceeds 24)
- Date validation (future dates)
- Default values
- JSON serialization/deserialization
- Phase 1 fixture compatibility
- Round-trip serialization

Run tests with:
```bash
pytest tests/test_financial_models.py -v
```

### Future Models

Additional financial models will be added to this module:
- `ProjectCost` - Project cost tracking (Task 27)
- Additional cost-related models as needed

## Related Documentation

- [Phase 1 Fixtures Guide](../tests/fixtures/README.md)
- [Database Models](./DATABASE_README.md)
- [API Response Models](./api_responses.py)


## ProjectCost

The `ProjectCost` model represents a cost entry associated with a project for R&D tax credit analysis. This model is used to capture cost data from HRIS/payroll systems (via Unified.to) or expense tracking systems and validate it for R&D tax credit calculations.

### Fields

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `cost_id` | `str` | Yes | Unique identifier for the cost entry (e.g., "PAY001") | Min length: 1 |
| `cost_type` | `str` | Yes | Type of cost | Must be one of: Payroll, Contractor, Materials, Cloud, Other |
| `amount` | `float` | Yes | Cost amount in dollars | Must be positive (> 0) |
| `project_name` | `str` | Yes | Name of the project this cost is associated with | Min length: 1 |
| `employee_id` | `str` | No | Employee identifier (for payroll costs) | Optional, None for non-payroll costs |
| `date` | `datetime` | Yes | Date when the cost was incurred | - |
| `is_rd_classified` | `bool` | No | Whether this cost is classified as R&D-related | Default: `False` |
| `metadata` | `Dict[str, Any]` | No | Additional cost information | Optional dictionary |

### Validation Rules

1. **cost_type**: Must be one of the allowed values from the CostType enum (Payroll, Contractor, Materials, Cloud, Other)
2. **amount**: Must be positive (greater than 0)
3. **is_rd_classified**: Defaults to `False` if not provided
4. **employee_id**: Optional, typically provided for Payroll costs, None for other cost types

### Computed Fields

#### hourly_rate

The `hourly_rate` is a computed property that:
1. First tries to retrieve `hourly_rate` directly from metadata
2. If not found, calculates it from `annual_salary` in metadata (using 2080 hours/year as default)
3. Returns `None` if neither is available

### Usage Example

```python
from models.financial_models import ProjectCost

# Create a payroll cost entry
cost = ProjectCost(
    cost_id="PAY001",
    cost_type="Payroll",
    amount=12500.00,
    project_name="Alpha Development",
    employee_id="EMP001",
    date="2024-03-31T00:00:00",
    is_rd_classified=True,
    metadata={
        "annual_salary": 150000.00,
        "hourly_rate": 72.12,
        "pay_period": "2024-03",
        "department": "Engineering"
    }
)

# Access fields
print(cost.cost_id)  # "PAY001"
print(cost.amount)  # 12500.00
print(cost.hourly_rate)  # 72.12 (from metadata)
print(cost)  # "PAY001 - Payroll: $12500.00 on Alpha Development (2024-03-31) (Employee: EMP001)"

# Create a contractor cost (no employee_id)
contractor_cost = ProjectCost(
    cost_id="CONT001",
    cost_type="Contractor",
    amount=25000.00,
    project_name="Alpha Development",
    date="2024-03-15T00:00:00",
    is_rd_classified=True,
    metadata={
        "contractor_name": "TechConsult LLC",
        "contract_type": "Fixed Price"
    }
)

print(contractor_cost.employee_id)  # None
```

### JSON Format

The model is compatible with the Phase 1 `sample_payroll_data.json` fixture format:

```json
{
  "cost_id": "PAY001",
  "cost_type": "Payroll",
  "amount": 12500.00,
  "project_name": "Alpha Development",
  "employee_id": "EMP001",
  "date": "2024-03-31T00:00:00",
  "is_rd_classified": true,
  "metadata": {
    "annual_salary": 150000.00,
    "hourly_rate": 72.12,
    "pay_period": "2024-03",
    "department": "Engineering"
  }
}
```

### Integration with Phase 1

This model is designed to work seamlessly with the Phase 1 JSON fixtures:
- `tests/fixtures/sample_payroll_data.json` - Sample payroll and cost data

All Phase 1 fixture data can be loaded and validated using this model:

```python
import json
from pathlib import Path
from models.financial_models import ProjectCost

# Load Phase 1 fixture
with open("tests/fixtures/sample_payroll_data.json", 'r') as f:
    payroll_data = json.load(f)

# Convert to Pydantic models
costs = [ProjectCost(**cost_data) for cost_data in payroll_data]

# All costs are now validated and type-safe
# Calculate total R&D costs
rd_costs = sum(cost.amount for cost in costs if cost.is_rd_classified)
```

### Cost Types

The following cost types are supported (from `utils.constants.CostType`):

- **Payroll**: Employee salary and wage costs
- **Contractor**: External contractor and consultant fees
- **Materials**: Physical materials and supplies used in R&D
- **Cloud**: Cloud computing and infrastructure costs
- **Other**: Other qualified research expenditures

### Error Handling

The model raises `pydantic.ValidationError` when validation fails:

```python
from pydantic import ValidationError

try:
    cost = ProjectCost(
        cost_id="COST001",
        cost_type="InvalidType",  # Invalid cost type
        amount=1000.00,
        project_name="Test Project",
        date="2024-03-15T00:00:00"
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Testing

Comprehensive unit tests are available in `tests/test_financial_models.py`:
- Valid cost creation (all cost types)
- Cost type validation
- Amount validation (negative, zero)
- Optional employee_id handling
- Hourly rate computation (from metadata and calculation)
- JSON serialization/deserialization
- Phase 1 fixture compatibility
- Round-trip serialization

Run tests with:
```bash
pytest tests/test_financial_models.py::TestProjectCost -v
```

### Example Usage Script

A comprehensive example script is available at `examples/project_cost_usage_example.py` demonstrating:
- Creating payroll costs
- Creating contractor costs
- Validation error handling
- Hourly rate calculation
- JSON serialization
- Loading Phase 1 fixtures
- Filtering and aggregation

Run the example:
```bash
python examples/project_cost_usage_example.py
```
