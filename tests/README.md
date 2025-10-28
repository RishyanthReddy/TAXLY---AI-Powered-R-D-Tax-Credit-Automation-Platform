# Testing Guide

This directory contains all tests for the R&D Tax Credit Automation Agent.

## Test Structure

```
tests/
├── fixtures/              # Test data fixtures
│   ├── sample_time_entries.json
│   ├── sample_payroll_data.json
│   └── sample_qualified_projects.json
├── test_*.py             # Test modules
└── README.md             # This file
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests with verbose output
```bash
pytest -v
```

### Run tests without coverage (faster)
```bash
pytest --no-cov
```

### Run specific test file
```bash
pytest tests/test_retry.py
```

### Run specific test function
```bash
pytest tests/test_retry.py::test_successful_call_no_retry
```

### Run tests matching a pattern
```bash
pytest -k "retry"
```

## Test Markers

Tests are organized using markers for easy filtering:

### Run only unit tests (fast, no external dependencies)
```bash
pytest -m unit
```

### Run only integration tests
```bash
pytest -m integration
```

### Run only end-to-end tests
```bash
pytest -m e2e
```

### Run only API tests
```bash
pytest -m api
```

### Run only RAG system tests
```bash
pytest -m rag
```

### Run only PDF generation tests
```bash
pytest -m pdf
```

### Exclude slow tests
```bash
pytest -m "not slow"
```

### Combine markers (AND logic)
```bash
pytest -m "unit and not slow"
```

### Combine markers (OR logic)
```bash
pytest -m "unit or integration"
```

## Available Markers

- `unit`: Unit tests for individual components (fast, no external dependencies)
- `integration`: Integration tests for component interactions (may use mocks)
- `e2e`: End-to-end tests for complete workflows (slow, may use real APIs)
- `slow`: Tests that take significant time to run
- `api`: Tests that interact with external APIs
- `rag`: Tests for RAG system and knowledge base
- `pdf`: Tests for PDF generation functionality
- `requires_env`: Tests that require environment variables to be set

## Coverage Reports

### View coverage in terminal
```bash
pytest --cov-report=term-missing
```

### Generate HTML coverage report
```bash
pytest --cov-report=html
# Open htmlcov/index.html in browser
```

### Generate XML coverage report (for CI/CD)
```bash
pytest --cov-report=xml
```

### Check coverage threshold
The configuration requires 80% code coverage. Tests will fail if coverage drops below this threshold.

To temporarily disable this check:
```bash
pytest --no-cov-fail-under
```

## Async Tests

Async tests are automatically detected and run with asyncio. Simply mark your test function as `async`:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected_value
```

## Test Fixtures

### Using JSON fixtures
```python
import json
import pytest
from pathlib import Path

@pytest.fixture
def sample_time_entries():
    fixture_path = Path(__file__).parent / "fixtures" / "sample_time_entries.json"
    with open(fixture_path) as f:
        return json.load(f)

def test_with_fixture(sample_time_entries):
    assert len(sample_time_entries) > 0
```

## Writing Tests

### Unit Test Example
```python
import pytest
from utils.validators import validate_api_key

@pytest.mark.unit
def test_validate_api_key():
    """Test API key validation."""
    # Valid key
    assert validate_api_key("sk-1234567890abcdef") is not None
    
    # Invalid key
    with pytest.raises(ValueError):
        validate_api_key("")
```

### Integration Test Example
```python
import pytest
from tools.api_connectors import ClockifyConnector

@pytest.mark.integration
@pytest.mark.api
def test_clockify_connector(mocker):
    """Test Clockify API connector with mocked responses."""
    mock_response = {"data": [{"id": "123", "hours": 8}]}
    mocker.patch("httpx.get", return_value=mock_response)
    
    connector = ClockifyConnector(api_key="test_key")
    result = connector.fetch_time_entries("workspace_id", start_date, end_date)
    
    assert len(result) > 0
```

### Async Test Example
```python
import pytest
from agents.qualification_agent import QualificationAgent

@pytest.mark.integration
@pytest.mark.asyncio
async def test_qualification_agent():
    """Test qualification agent async workflow."""
    agent = QualificationAgent()
    result = await agent.qualify_project(project_data)
    
    assert result.confidence_score > 0.7
```

## Debugging Tests

### Run with print statements visible
```bash
pytest -s
```

### Run with detailed output
```bash
pytest -vv
```

### Run with Python debugger on failure
```bash
pytest --pdb
```

### Show local variables in tracebacks
```bash
pytest --showlocals
```

## Continuous Integration

The pytest configuration is optimized for CI/CD pipelines:

- XML coverage reports for integration with CI tools
- Strict marker enforcement (unknown markers cause failures)
- Configurable coverage thresholds
- Structured logging to files

## Troubleshooting

### Tests not discovered
- Ensure test files start with `test_` or end with `_test.py`
- Ensure test functions start with `test_`
- Check that `__init__.py` exists in test directories

### Import errors
- Ensure you're running pytest from the project root
- Activate the virtual environment: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)

### Coverage too low
- Add more tests for uncovered code
- Check `htmlcov/index.html` to see which lines need coverage
- Use `--cov-report=term-missing` to see missing lines in terminal

### Async tests not running
- Ensure `pytest-asyncio` is installed
- Mark async tests with `@pytest.mark.asyncio`
- Check that `asyncio_mode = auto` is set in pytest.ini

## Best Practices

1. **One assertion per test** (when possible) for clear failure messages
2. **Use descriptive test names** that explain what is being tested
3. **Use fixtures** for common setup code
4. **Mock external dependencies** in unit and integration tests
5. **Use markers** to categorize tests appropriately
6. **Keep tests fast** - slow tests should be marked with `@pytest.mark.slow`
7. **Test edge cases** - empty inputs, boundary values, error conditions
8. **Write tests first** (TDD) when adding new features
9. **Maintain high coverage** - aim for 90%+ on critical code paths
10. **Document complex tests** with clear docstrings

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
