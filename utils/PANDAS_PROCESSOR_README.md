# Pandas Processor Module

## Overview

The `pandas_processor` module provides Pandas-based data processing utilities for correlating costs with time entries and aggregating data for R&D tax credit calculations. This module is a core component of the R&D Tax Credit Automation Agent, enabling efficient data manipulation and analysis for qualified research expenditure (QRE) calculations.

## Features

- **Cost Correlation**: Merge time tracking data with payroll/cost data on employee_id
- **Qualified Wage Calculation**: Calculate qualified wages by multiplying hours by hourly rates
- **IRS Wage Cap Application**: Apply Social Security wage base limits per employee per year
- **Multi-Cost Type Support**: Handle payroll, contractor, materials, cloud, and other cost types
- **Project Aggregation**: Aggregate costs and hours by project for reporting
- **Cost Type Aggregation**: Break down costs by type for IRS reporting
- **R&D Filtering**: Filter entries by R&D classification status
- **Comprehensive Logging**: Track all data processing operations

## Functions

### `correlate_costs()`

Correlate time entries with payroll data to calculate qualified wages.

**Signature:**
```python
def correlate_costs(
    time_entries: List[EmployeeTimeEntry],
    payroll_costs: List[ProjectCost],
    filter_rd_only: bool = True
) -> pd.DataFrame
```

**Parameters:**
- `time_entries`: List of EmployeeTimeEntry objects from time tracking systems
- `payroll_costs`: List of ProjectCost objects from HRIS/payroll systems
- `filter_rd_only`: If True, only include entries where is_rd_classified=True (default: True)

**Returns:**
DataFrame with columns:
- `project_name`: Name of the project
- `employee_id`: Employee identifier (or None for non-payroll costs)
- `employee_name`: Employee name
- `cost_type`: Type of cost (Payroll, Contractor, Materials, Cloud, Other)
- `total_hours`: Total hours spent on the project
- `hourly_rate`: Hourly compensation rate
- `qualified_wages`: Calculated wages (hours × hourly_rate)
- `other_costs`: Non-payroll costs
- `total_qualified_cost`: Sum of qualified_wages and other_costs

**Example:**
```python
from utils.pandas_processor import correlate_costs
from models.financial_models import EmployeeTimeEntry, ProjectCost

time_entries = [
    EmployeeTimeEntry(
        employee_id="EMP001",
        employee_name="Alice Johnson",
        project_name="Alpha Development",
        task_description="Algorithm development",
        hours_spent=8.5,
        date=datetime(2024, 3, 15),
        is_rd_classified=True
    )
]

payroll_costs = [
    ProjectCost(
        cost_id="PAY001",
        cost_type="Payroll",
        amount=12500.00,
        project_name="Alpha Development",
        employee_id="EMP001",
        date=datetime(2024, 3, 31),
        is_rd_classified=True,
        metadata={"hourly_rate": 72.12}
    )
]

result_df = correlate_costs(time_entries, payroll_costs)
print(result_df)
```

### `aggregate_by_project()`

Aggregate correlated cost data by project.

**Signature:**
```python
def aggregate_by_project(correlated_df: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `correlated_df`: DataFrame output from correlate_costs()

**Returns:**
DataFrame with columns:
- `project_name`: Name of the project
- `total_hours`: Total qualified hours for the project
- `total_qualified_wages`: Total qualified wages (payroll only)
- `total_other_costs`: Total non-payroll costs
- `total_qualified_cost`: Total qualified cost (wages + other costs)
- `employee_count`: Number of unique employees on the project

**Example:**
```python
from utils.pandas_processor import correlate_costs, aggregate_by_project

correlated_df = correlate_costs(time_entries, payroll_costs)
project_summary = aggregate_by_project(correlated_df)
print(project_summary)
```

### `aggregate_by_cost_type()`

Aggregate correlated cost data by cost type.

**Signature:**
```python
def aggregate_by_cost_type(correlated_df: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `correlated_df`: DataFrame output from correlate_costs()

**Returns:**
DataFrame with columns:
- `cost_type`: Type of cost
- `total_hours`: Total hours (for Payroll only)
- `total_cost`: Total cost for this type
- `percentage`: Percentage of total qualified costs

**Example:**
```python
from utils.pandas_processor import correlate_costs, aggregate_by_cost_type

correlated_df = correlate_costs(time_entries, payroll_costs)
cost_type_summary = aggregate_by_cost_type(correlated_df)
print(cost_type_summary)
```

### `apply_wage_caps()`

Apply IRS wage caps to qualified wages per employee per year.

**Signature:**
```python
def apply_wage_caps(
    correlated_df: pd.DataFrame,
    tax_year: int = 2024
) -> pd.DataFrame
```

**Parameters:**
- `correlated_df`: DataFrame output from correlate_costs() containing qualified wages
- `tax_year`: Tax year for determining the applicable wage cap (default: 2024)

**Returns:**
DataFrame with the same structure as input, but with capped wages:
- `qualified_wages`: Adjusted to not exceed wage cap per employee per year
- `total_qualified_cost`: Recalculated with capped wages
- `wage_cap_applied`: Boolean flag indicating if cap was applied
- `original_qualified_wages`: Original wages before capping (for transparency)
- `capped_amount`: Amount reduced due to wage cap

**Example:**
```python
from utils.pandas_processor import correlate_costs, apply_wage_caps

# First correlate costs
correlated_df = correlate_costs(time_entries, payroll_costs)

# Then apply IRS wage caps
capped_df = apply_wage_caps(correlated_df, tax_year=2024)

# Check which employees had wages capped
capped_employees = capped_df[capped_df['wage_cap_applied'] == True]
print(f"Capped {len(capped_employees)} employee records")
print(f"Total capped amount: ${capped_df['capped_amount'].sum():.2f}")
```

**Notes:**
- Wage caps are applied per employee per year, not per project
- Non-payroll costs (Contractor, Materials, Cloud, Other) are not subject to wage caps
- The function preserves original wage data for audit trail purposes
- Wage cap values are sourced from `utils.constants.IRSWageCap`
- For 2024: $168,600 (Social Security wage base)
- For 2023: $160,200 (Social Security wage base)
- If an employee works on multiple projects, the cap is applied proportionally across all projects

## Data Flow

```
┌─────────────────────┐     ┌─────────────────────┐
│  Time Entries       │     │  Payroll Costs      │
│  (Clockify API)     │     │  (Unified.to API)   │
└──────────┬──────────┘     └──────────┬──────────┘
           │                           │
           │                           │
           └───────────┬───────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │  correlate_costs()    │
           │  - Merge on employee  │
           │  - Calculate wages    │
           │  - Include other costs│
           └───────────┬───────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │  Correlated DataFrame │
           └───────────┬───────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
┌──────────────────────┐  ┌──────────────────────┐
│ aggregate_by_project │  │aggregate_by_cost_type│
│ - Sum by project     │  │ - Sum by cost type   │
│ - Count employees    │  │ - Calculate %        │
└──────────────────────┘  └──────────────────────┘
```

## Cost Types Supported

The module supports the following cost types as defined in `utils/constants.py`:

1. **Payroll**: Employee wages and salaries
   - Requires: employee_id, hourly_rate in metadata
   - Calculated: hours × hourly_rate

2. **Contractor**: External contractor costs
   - No employee_id required
   - Direct cost amount used

3. **Materials**: Physical materials and supplies
   - No employee_id required
   - Direct cost amount used

4. **Cloud**: Cloud computing and infrastructure costs
   - No employee_id required
   - Direct cost amount used

5. **Other**: Miscellaneous qualified costs
   - No employee_id required
   - Direct cost amount used

## Requirements Mapping

This module implements the following requirements from the design document:

- **Requirement 3.1**: Merge time entries with payroll data from Unified.to API
- **Requirement 3.2**: Calculate qualified wages by multiplying hours by hourly rates
- **Requirement 3.3**: Aggregate qualified costs by project and cost type with high accuracy
- **Requirement 3.4**: Apply IRS wage caps and limitations as specified in Form 6765 instructions

## Error Handling

The module includes comprehensive error handling:

- **Empty Input Lists**: Raises ValueError if time_entries or payroll_costs are empty
- **Missing Hourly Rates**: Logs warning and sets qualified_wages to 0
- **Missing Employee Matches**: Handles gracefully with left join
- **Empty DataFrames**: Returns empty DataFrame with expected columns

## Logging

All operations are logged using the centralized logging infrastructure:

```python
logger.info("Starting cost correlation: X time entries, Y cost entries")
logger.info("Created time DataFrame with X R&D-classified entries")
logger.warning("X employee-project combinations missing hourly rate data")
logger.info("Cost correlation complete: X total records, $Y total qualified cost")
```

## Performance Considerations

- **Efficient Aggregation**: Uses Pandas groupby for fast aggregation
- **Memory Efficient**: Processes data in-memory with Pandas DataFrames
- **Scalability**: Tested with up to 10,000 time entries
- **Vectorized Operations**: Uses Pandas vectorized operations for calculations

## Testing

Comprehensive test suite in `tests/test_pandas_processor.py`:

- ✅ Basic cost correlation
- ✅ Multiple employees and projects
- ✅ Non-payroll cost types (contractor, materials, cloud)
- ✅ R&D filtering (filter_rd_only parameter)
- ✅ Missing hourly rate handling
- ✅ Empty input validation
- ✅ Hour aggregation per employee-project
- ✅ Project-level aggregation
- ✅ Cost type aggregation
- ✅ Empty DataFrame handling

Run tests:
```bash
pytest tests/test_pandas_processor.py -v
```

## Usage Examples

See `examples/pandas_processor_usage_example.py` for comprehensive usage examples including:

1. Basic cost correlation
2. Multiple employees and projects
3. Including non-payroll costs
4. Project-level aggregation
5. Cost type aggregation
6. R&D filtering

Run examples:
```bash
python examples/pandas_processor_usage_example.py
```

## Integration with Agents

The pandas_processor module is used by:

1. **Qualification Agent**: Correlates time entries with costs to determine qualified expenditures
2. **Audit Trail Agent**: Aggregates data for final report generation
3. **Data Ingestion Agent**: May use for data quality checks and validation

## Future Enhancements

Potential future improvements:

- [x] Support for wage cap application (IRS Form 6765 limits) - **COMPLETED**
- [ ] Multi-year aggregation support
- [ ] Export to Excel/CSV functionality
- [ ] Advanced filtering options (date ranges, departments)
- [ ] Performance optimization for very large datasets (>100k entries)

## Dependencies

- `pandas`: Data manipulation and analysis
- `typing`: Type hints for function signatures
- `datetime`: Date/time handling
- `pathlib`: Path operations
- Custom modules:
  - `models.financial_models`: EmployeeTimeEntry, ProjectCost
  - `models.tax_models`: QualifiedProject
  - `utils.logger`: Logging infrastructure

## License

Part of the R&D Tax Credit Automation Agent project.
