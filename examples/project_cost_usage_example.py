"""
Example usage of ProjectCost model.

This script demonstrates how to create, validate, and work with ProjectCost
objects, including loading from Phase 1 JSON fixtures.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.financial_models import ProjectCost


def example_create_payroll_cost():
    """Example: Create a valid payroll cost entry."""
    print("=" * 60)
    print("Example 1: Creating a Payroll ProjectCost")
    print("=" * 60)
    
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
    
    print(f"Created cost: {cost}")
    print(f"Cost ID: {cost.cost_id}")
    print(f"Cost Type: {cost.cost_type}")
    print(f"Amount: ${cost.amount:.2f}")
    print(f"Hourly Rate: ${cost.hourly_rate:.2f}")
    print(f"R&D classified: {cost.is_rd_classified}")
    print()


def example_create_contractor_cost():
    """Example: Create a contractor cost entry (no employee_id)."""
    print("=" * 60)
    print("Example 2: Creating a Contractor ProjectCost")
    print("=" * 60)
    
    cost = ProjectCost(
        cost_id="CONT001",
        cost_type="Contractor",
        amount=25000.00,
        project_name="Alpha Development",
        date="2024-03-15T00:00:00",
        is_rd_classified=True,
        metadata={
            "contractor_name": "TechConsult LLC",
            "contract_type": "Fixed Price",
            "service_description": "Algorithm optimization consulting"
        }
    )
    
    print(f"Created cost: {cost}")
    print(f"Cost Type: {cost.cost_type}")
    print(f"Amount: ${cost.amount:.2f}")
    print(f"Employee ID: {cost.employee_id}")  # Should be None
    print(f"Contractor: {cost.metadata['contractor_name']}")
    print()


def example_validation_errors():
    """Example: Demonstrate validation errors."""
    print("=" * 60)
    print("Example 3: Validation Errors")
    print("=" * 60)
    
    # Try to create cost with invalid cost_type
    try:
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="InvalidType",
            amount=1000.00,
            project_name="Test Project",
            date="2024-03-15T00:00:00"
        )
    except Exception as e:
        print(f"❌ Validation error (invalid cost_type): {type(e).__name__}")
        print(f"   Message: cost_type must be one of ['Payroll', 'Contractor', 'Materials', 'Cloud', 'Other']")
    
    # Try to create cost with negative amount
    try:
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Payroll",
            amount=-1000.00,
            project_name="Test Project",
            date="2024-03-15T00:00:00"
        )
    except Exception as e:
        print(f"❌ Validation error (negative amount): {type(e).__name__}")
        print(f"   Message: amount must be positive (greater than 0)")
    
    # Try to create cost with zero amount
    try:
        cost = ProjectCost(
            cost_id="COST001",
            cost_type="Payroll",
            amount=0.0,
            project_name="Test Project",
            date="2024-03-15T00:00:00"
        )
    except Exception as e:
        print(f"❌ Validation error (zero amount): {type(e).__name__}")
        print(f"   Message: amount must be positive (greater than 0)")
    
    print()


def example_hourly_rate_calculation():
    """Example: Demonstrate hourly rate calculation."""
    print("=" * 60)
    print("Example 4: Hourly Rate Calculation")
    print("=" * 60)
    
    # Hourly rate from metadata
    cost1 = ProjectCost(
        cost_id="PAY001",
        cost_type="Payroll",
        amount=12500.00,
        project_name="Alpha Development",
        employee_id="EMP001",
        date="2024-03-31T00:00:00",
        metadata={
            "annual_salary": 150000.00,
            "hourly_rate": 72.12
        }
    )
    print(f"Cost with hourly_rate in metadata: ${cost1.hourly_rate:.2f}")
    
    # Hourly rate calculated from annual_salary
    cost2 = ProjectCost(
        cost_id="PAY002",
        cost_type="Payroll",
        amount=10000.00,
        project_name="Beta Infrastructure",
        employee_id="EMP002",
        date="2024-03-31T00:00:00",
        metadata={
            "annual_salary": 120000.00
        }
    )
    print(f"Cost with calculated hourly_rate (120000/2080): ${cost2.hourly_rate:.2f}")
    
    # No hourly rate available
    cost3 = ProjectCost(
        cost_id="MAT001",
        cost_type="Materials",
        amount=5000.00,
        project_name="Gamma Analytics",
        date="2024-03-10T00:00:00"
    )
    print(f"Cost without hourly_rate: {cost3.hourly_rate}")
    
    print()


def example_json_serialization():
    """Example: JSON serialization and deserialization."""
    print("=" * 60)
    print("Example 5: JSON Serialization")
    print("=" * 60)
    
    # Create a cost
    cost = ProjectCost(
        cost_id="CLOUD001",
        cost_type="Cloud",
        amount=8500.00,
        project_name="Epsilon AI",
        date="2024-03-31T00:00:00",
        is_rd_classified=True,
        metadata={
            "provider": "AWS",
            "service_type": "GPU Compute Instances",
            "usage_hours": 850
        }
    )
    
    # Serialize to JSON
    json_str = cost.model_dump_json(indent=2)
    print("Serialized to JSON:")
    print(json_str)
    
    # Deserialize from JSON
    json_data = json.loads(json_str)
    cost_restored = ProjectCost(**json_data)
    print(f"\nRestored cost: {cost_restored}")
    print()


def example_load_phase1_fixtures():
    """Example: Load and process Phase 1 fixture data."""
    print("=" * 60)
    print("Example 6: Loading Phase 1 Fixtures")
    print("=" * 60)
    
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_payroll_data.json"
    
    # Load the fixture
    with open(fixture_path, 'r') as f:
        payroll_data = json.load(f)
    
    print(f"Loaded {len(payroll_data)} cost entries from fixture")
    
    # Convert to Pydantic models
    costs = [ProjectCost(**cost_data) for cost_data in payroll_data]
    
    # Calculate statistics
    total_cost = sum(cost.amount for cost in costs)
    rd_cost = sum(cost.amount for cost in costs if cost.is_rd_classified)
    rd_percentage = (rd_cost / total_cost * 100) if total_cost > 0 else 0
    
    # Count by cost type
    cost_types = {}
    for cost in costs:
        if cost.cost_type not in cost_types:
            cost_types[cost.cost_type] = {"count": 0, "total": 0.0}
        cost_types[cost.cost_type]["count"] += 1
        cost_types[cost.cost_type]["total"] += cost.amount
    
    print(f"\nStatistics:")
    print(f"  Total cost: ${total_cost:,.2f}")
    print(f"  R&D cost: ${rd_cost:,.2f}")
    print(f"  R&D percentage: {rd_percentage:.1f}%")
    
    print(f"\nCost breakdown by type:")
    for cost_type, stats in cost_types.items():
        print(f"  {cost_type}: {stats['count']} entries, ${stats['total']:,.2f}")
    
    # Show first few entries
    print(f"\nFirst 3 entries:")
    for i, cost in enumerate(costs[:3], 1):
        print(f"  {i}. {cost}")
    
    print()


def example_filter_and_aggregate():
    """Example: Filter and aggregate cost entries."""
    print("=" * 60)
    print("Example 7: Filtering and Aggregation")
    print("=" * 60)
    
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_payroll_data.json"
    
    with open(fixture_path, 'r') as f:
        payroll_data = json.load(f)
    
    costs = [ProjectCost(**cost_data) for cost_data in payroll_data]
    
    # Filter by project
    alpha_costs = [c for c in costs if c.project_name == "Alpha Development"]
    print(f"Alpha Development costs: {len(alpha_costs)}")
    print(f"Total cost on Alpha: ${sum(c.amount for c in alpha_costs):,.2f}")
    
    # Filter by cost type
    payroll_costs = [c for c in costs if c.cost_type == "Payroll"]
    print(f"\nPayroll costs: {len(payroll_costs)}")
    print(f"Total payroll: ${sum(c.amount for c in payroll_costs):,.2f}")
    
    # Filter by employee
    emp001_costs = [c for c in costs if c.employee_id == "EMP001"]
    print(f"\nEMP001 costs: {len(emp001_costs)}")
    print(f"Total for EMP001: ${sum(c.amount for c in emp001_costs):,.2f}")
    
    # Group by project
    projects = {}
    for cost in costs:
        if cost.project_name not in projects:
            projects[cost.project_name] = []
        projects[cost.project_name].append(cost)
    
    print(f"\nCost by project:")
    for project_name, project_costs in projects.items():
        total = sum(c.amount for c in project_costs)
        rd_only = sum(c.amount for c in project_costs if c.is_rd_classified)
        print(f"  {project_name}: ${total:,.2f} (${rd_only:,.2f} R&D)")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ProjectCost Model Usage Examples")
    print("=" * 60 + "\n")
    
    example_create_payroll_cost()
    example_create_contractor_cost()
    example_validation_errors()
    example_hourly_rate_calculation()
    example_json_serialization()
    example_load_phase1_fixtures()
    example_filter_and_aggregate()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
