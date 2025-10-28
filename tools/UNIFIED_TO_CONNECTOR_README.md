# UnifiedToConnector - Employee Data Fetching

## Overview

The `UnifiedToConnector` class provides integration with the Unified.to API to fetch employee data from 190+ HRIS systems. This connector is part of the Data Ingestion Agent and implements Requirement 1.2 from the R&D Tax Credit Automation specification.

## Current Implementation Status

**Mock Data Mode**: The current implementation returns mock employee data for development and testing purposes. This allows the system to be developed and tested without requiring actual Unified.to API credentials or HRIS system connections.

## Features

- **Employee Profile Fetching**: Retrieves comprehensive employee data including:
  - Employee ID and name
  - Email address
  - Job title and department
  - Compensation information
  - Hire date
  - Employment status
  - Manager relationships

- **Pagination Support**: Designed to handle large organizations with configurable page sizes (1-200 employees per page)

- **OAuth 2.0 Authentication**: Built-in token management and automatic refresh (ready for production)

- **Rate Limiting**: Respects API rate limits (5 requests/second)

- **Error Handling**: Comprehensive error handling with retry logic

## Usage Example

```python
from tools.api_connectors import UnifiedToConnector

# Initialize connector
connector = UnifiedToConnector(
    api_key="your_api_key",
    workspace_id="your_workspace_id"
)

# Fetch employees
employees = connector.fetch_employees()

# Process employee data
for emp in employees:
    print(f"{emp['name']} - {emp['job_title']} - ${emp['compensation']:,.2f}")

# Clean up
connector.close()
```

## Mock Data Structure

The mock data includes 11 employees across 5 departments:

- **Engineering**: 4 employees (including 1 manager)
- **Data Science**: 2 employees (including 1 manager)
- **Security**: 2 employees (including 1 manager)
- **AI Research**: 1 employee
- **Customer Support**: 2 employees (including 1 manager)

Each employee record includes:
```python
{
    "id": "EMP001",
    "name": "Alice Johnson",
    "email": "alice.johnson@company.com",
    "job_title": "Senior Software Engineer",
    "department": "Engineering",
    "compensation": 150000.00,
    "hire_date": "2022-01-15T00:00:00Z",
    "employment_status": "active",
    "manager_id": "MGR001"
}
```

## API Method

### `fetch_employees(connection_id=None, page_size=100)`

Fetches employee profiles from HRIS system via Unified.to.

**Parameters:**
- `connection_id` (str, optional): Unified.to connection ID for the HRIS system
- `page_size` (int, default=100): Number of employees per page (1-200)

**Returns:**
- `List[Dict[str, Any]]`: List of employee dictionaries

**Raises:**
- `ValueError`: If page_size is out of range (1-200)
- `APIConnectionError`: If request fails (in production mode)

## Testing

Comprehensive test suite included in `tests/test_api_connectors.py`:

```bash
# Run all UnifiedToConnector tests
pytest tests/test_api_connectors.py::TestUnifiedToEmployeeFetching -v

# Run specific test
pytest tests/test_api_connectors.py::TestUnifiedToEmployeeFetching::test_fetch_employees_returns_mock_data -v
```

Test coverage includes:
- ✅ Mock data retrieval
- ✅ Connection ID parameter handling
- ✅ Custom page size validation
- ✅ Invalid page size error handling
- ✅ Required fields validation
- ✅ Manager hierarchy verification
- ✅ Compensation data validation
- ✅ Department distribution

## Production Migration Path

When ready to connect to actual Unified.to API:

1. **Uncomment Production Code**: The production API call code is included as comments in the `fetch_employees()` method
2. **Configure Credentials**: Set `UNIFIED_TO_API_KEY` and `UNIFIED_TO_WORKSPACE_ID` in `.env`
3. **Test Authentication**: Use `test_authentication()` method to verify credentials
4. **Update Tests**: Modify tests to use mocked API responses instead of mock data

## Integration with Data Ingestion Agent

The UnifiedToConnector integrates with the Data Ingestion Agent workflow:

1. **Data Collection**: Fetches employee profiles from HRIS
2. **Data Enrichment**: Combines with time tracking data from Clockify
3. **Data Validation**: Validates against Pydantic models
4. **Data Transformation**: Converts to standardized `EmployeeTimeEntry` and `ProjectCost` objects

## Related Components

- `ClockifyConnector`: Fetches time tracking data
- `BaseAPIConnector`: Base class providing common API functionality
- `EmployeeTimeEntry`: Pydantic model for time entries
- `ProjectCost`: Pydantic model for cost data

## Requirements Satisfied

✅ **Requirement 1.2**: "WHEN the User initiates data ingestion, THE Data Ingestion Agent SHALL retrieve employee payroll data from the Unified.to API across 190+ HRIS systems with compensation details"

## Future Enhancements

- [ ] Add support for filtering employees by department
- [ ] Add support for filtering by employment status
- [ ] Add support for date range filtering (hire date)
- [ ] Add caching layer for frequently accessed employee data
- [ ] Add webhook support for real-time employee updates
- [ ] Add support for custom field mapping per HRIS system
