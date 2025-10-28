"""
Example usage of EmployeeTimeEntry model.

This script demonstrates how to create, validate, and work with EmployeeTimeEntry
objects, including loading from Phase 1 JSON fixtures.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.financial_models import EmployeeTimeEntry


def example_create_time_entry():
    """Example: Create a valid time entry."""
    print("=" * 60)
    print("Example 1: Creating a valid EmployeeTimeEntry")
    print("=" * 60)
    
    entry = EmployeeTimeEntry(
        employee_id="EMP001",
        employee_name="Alice Johnson",
        project_name="Alpha Development",
        task_description="Implemented new authentication algorithm with encryption",
        hours_spent=8.5,
        date="2024-03-15T09:00:00",
        is_rd_classified=True
    )
    
    print(f"Created entry: {entry}")
    print(f"Employee ID: {entry.employee_id}")
    print(f"Hours spent: {entry.hours_spent}")
    print(f"R&D classified: {entry.is_rd_classified}")
    print()


def example_validation_errors():
    """Example: Demonstrate validation errors."""
    print("=" * 60)
    print("Example 2: Validation Errors")
    print("=" * 60)
    
    # Try to create entry with invalid hours
    try:
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=25.0,  # Invalid: exceeds 24 hours
            date="2024-03-15T09:00:00"
        )
    except Exception as e:
        print(f"❌ Validation error (hours > 24): {type(e).__name__}")
        print(f"   Message: Input should be less than or equal to 24")
    
    # Try to create entry with future date
    try:
        entry = EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Test Project",
            task_description="Test task",
            hours_spent=8.0,
            date="2030-12-31T09:00:00"  # Invalid: future date
        )
    except Exception as e:
        print(f"❌ Validation error (future date): {type(e).__name__}")
        print(f"   Message: date cannot be in the future")
    
    print()


def example_json_serialization():
    """Example: JSON serialization and deserialization."""
    print("=" * 60)
    print("Example 3: JSON Serialization")
    print("=" * 60)
    
    # Create an entry
    entry = EmployeeTimeEntry(
        employee_id="EMP002",
        employee_name="Bob Smith",
        project_name="Beta Infrastructure",
        task_description="Developed novel data compression algorithm",
        hours_spent=7.5,
        date="2024-03-15T10:00:00",
        is_rd_classified=True
    )
    
    # Serialize to JSON
    json_str = entry.model_dump_json(indent=2)
    print("Serialized to JSON:")
    print(json_str)
    
    # Deserialize from JSON
    json_data = json.loads(json_str)
    entry_restored = EmployeeTimeEntry(**json_data)
    print(f"\nRestored entry: {entry_restored}")
    print()


def example_load_phase1_fixtures():
    """Example: Load and process Phase 1 fixture data."""
    print("=" * 60)
    print("Example 4: Loading Phase 1 Fixtures")
    print("=" * 60)
    
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_time_entries.json"
    
    # Load the fixture
    with open(fixture_path, 'r') as f:
        time_entries_data = json.load(f)
    
    print(f"Loaded {len(time_entries_data)} time entries from fixture")
    
    # Convert to Pydantic models
    entries = [EmployeeTimeEntry(**entry_data) for entry_data in time_entries_data]
    
    # Calculate statistics
    total_hours = sum(entry.hours_spent for entry in entries)
    rd_hours = sum(entry.hours_spent for entry in entries if entry.is_rd_classified)
    rd_percentage = (rd_hours / total_hours * 100) if total_hours > 0 else 0
    
    print(f"\nStatistics:")
    print(f"  Total hours: {total_hours:.1f}")
    print(f"  R&D hours: {rd_hours:.1f}")
    print(f"  R&D percentage: {rd_percentage:.1f}%")
    
    # Show first few entries
    print(f"\nFirst 3 entries:")
    for i, entry in enumerate(entries[:3], 1):
        print(f"  {i}. {entry}")
    
    print()


def example_filter_and_aggregate():
    """Example: Filter and aggregate time entries."""
    print("=" * 60)
    print("Example 5: Filtering and Aggregation")
    print("=" * 60)
    
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_time_entries.json"
    
    with open(fixture_path, 'r') as f:
        time_entries_data = json.load(f)
    
    entries = [EmployeeTimeEntry(**entry_data) for entry_data in time_entries_data]
    
    # Filter by project
    alpha_entries = [e for e in entries if e.project_name == "Alpha Development"]
    print(f"Alpha Development entries: {len(alpha_entries)}")
    print(f"Total hours on Alpha: {sum(e.hours_spent for e in alpha_entries):.1f}")
    
    # Filter by employee
    alice_entries = [e for e in entries if e.employee_id == "EMP001"]
    print(f"\nAlice Johnson entries: {len(alice_entries)}")
    print(f"Total hours by Alice: {sum(e.hours_spent for e in alice_entries):.1f}")
    
    # Group by project
    projects = {}
    for entry in entries:
        if entry.project_name not in projects:
            projects[entry.project_name] = []
        projects[entry.project_name].append(entry)
    
    print(f"\nHours by project:")
    for project_name, project_entries in projects.items():
        total = sum(e.hours_spent for e in project_entries)
        rd_only = sum(e.hours_spent for e in project_entries if e.is_rd_classified)
        print(f"  {project_name}: {total:.1f} hours ({rd_only:.1f} R&D)")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("EmployeeTimeEntry Model Usage Examples")
    print("=" * 60 + "\n")
    
    example_create_time_entry()
    example_validation_errors()
    example_json_serialization()
    example_load_phase1_fixtures()
    example_filter_and_aggregate()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
