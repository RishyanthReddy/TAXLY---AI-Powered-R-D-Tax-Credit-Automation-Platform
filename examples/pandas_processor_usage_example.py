"""
Usage examples for pandas_processor module.

This script demonstrates how to use the pandas_processor functions to correlate
costs with time entries and aggregate data for R&D tax credit calculations.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.pandas_processor import (
    correlate_costs,
    aggregate_by_project,
    aggregate_by_cost_type,
    apply_wage_caps
)
from models.financial_models import EmployeeTimeEntry, ProjectCost
from utils.constants import IRSWageCap


def example_basic_correlation():
    """Example: Basic cost correlation with time entries and payroll."""
    print("=" * 80)
    print("Example 1: Basic Cost Correlation")
    print("=" * 80)
    
    # Create sample time entries
    time_entries = [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Implemented new authentication algorithm",
            hours_spent=8.5,
            date=datetime(2024, 3, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Testing and optimization",
            hours_spent=6.0,
            date=datetime(2024, 3, 16),
            is_rd_classified=True
        )
    ]
    
    # Create sample payroll costs
    payroll_costs = [
        ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Alpha Development",
            employee_id="EMP001",
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"hourly_rate": 72.12, "annual_salary": 150000.00}
        )
    ]
    
    # Correlate costs
    result_df = correlate_costs(time_entries, payroll_costs)
    
    print("\nCorrelated Cost Data:")
    print(result_df.to_string(index=False))
    print(f"\nTotal Qualified Cost: ${result_df['total_qualified_cost'].sum():.2f}")
    print()


def example_multiple_employees_and_projects():
    """Example: Cost correlation with multiple employees and projects."""
    print("=" * 80)
    print("Example 2: Multiple Employees and Projects")
    print("=" * 80)
    
    time_entries = [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Algorithm development",
            hours_spent=8.0,
            date=datetime(2024, 3, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP002",
            employee_name="Bob Smith",
            project_name="Beta Infrastructure",
            task_description="Infrastructure work",
            hours_spent=7.5,
            date=datetime(2024, 3, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP003",
            employee_name="Carol Davis",
            project_name="Gamma Analytics",
            task_description="Data pipeline development",
            hours_spent=9.0,
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
        ),
        ProjectCost(
            cost_id="PAY002",
            cost_type="Payroll",
            amount=13750.00,
            project_name="Beta Infrastructure",
            employee_id="EMP002",
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"hourly_rate": 79.33}
        ),
        ProjectCost(
            cost_id="PAY003",
            cost_type="Payroll",
            amount=14583.33,
            project_name="Gamma Analytics",
            employee_id="EMP003",
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"hourly_rate": 84.13}
        )
    ]
    
    result_df = correlate_costs(time_entries, payroll_costs)
    
    print("\nCorrelated Cost Data:")
    print(result_df[['project_name', 'employee_name', 'total_hours', 'hourly_rate', 'qualified_wages']].to_string(index=False))
    print(f"\nTotal Qualified Wages: ${result_df['qualified_wages'].sum():.2f}")
    print()


def example_with_other_cost_types():
    """Example: Cost correlation including non-payroll costs."""
    print("=" * 80)
    print("Example 3: Including Non-Payroll Costs")
    print("=" * 80)
    
    time_entries = [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Development work",
            hours_spent=8.0,
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
        ),
        ProjectCost(
            cost_id="CONT001",
            cost_type="Contractor",
            amount=25000.00,
            project_name="Alpha Development",
            employee_id=None,
            date=datetime(2024, 3, 15),
            is_rd_classified=True,
            metadata={"contractor_name": "TechConsult LLC"}
        ),
        ProjectCost(
            cost_id="CLOUD001",
            cost_type="Cloud",
            amount=8500.00,
            project_name="Alpha Development",
            employee_id=None,
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"provider": "AWS"}
        )
    ]
    
    result_df = correlate_costs(time_entries, payroll_costs)
    
    print("\nCorrelated Cost Data by Cost Type:")
    print(result_df[['cost_type', 'qualified_wages', 'other_costs', 'total_qualified_cost']].to_string(index=False))
    print(f"\nTotal Qualified Cost: ${result_df['total_qualified_cost'].sum():.2f}")
    print()


def example_project_aggregation():
    """Example: Aggregate correlated costs by project."""
    print("=" * 80)
    print("Example 4: Project-Level Aggregation")
    print("=" * 80)
    
    time_entries = [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Development",
            hours_spent=8.0,
            date=datetime(2024, 3, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP002",
            employee_name="Bob Smith",
            project_name="Alpha Development",
            task_description="Testing",
            hours_spent=6.0,
            date=datetime(2024, 3, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP003",
            employee_name="Carol Davis",
            project_name="Beta Infrastructure",
            task_description="Infrastructure",
            hours_spent=7.5,
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
        ),
        ProjectCost(
            cost_id="PAY002",
            cost_type="Payroll",
            amount=13750.00,
            project_name="Alpha Development",
            employee_id="EMP002",
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"hourly_rate": 79.33}
        ),
        ProjectCost(
            cost_id="PAY003",
            cost_type="Payroll",
            amount=14583.33,
            project_name="Beta Infrastructure",
            employee_id="EMP003",
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"hourly_rate": 84.13}
        ),
        ProjectCost(
            cost_id="CONT001",
            cost_type="Contractor",
            amount=25000.00,
            project_name="Alpha Development",
            employee_id=None,
            date=datetime(2024, 3, 15),
            is_rd_classified=True,
            metadata={"contractor_name": "TechConsult LLC"}
        )
    ]
    
    # First correlate costs
    correlated_df = correlate_costs(time_entries, payroll_costs)
    
    # Then aggregate by project
    project_summary = aggregate_by_project(correlated_df)
    
    print("\nProject Summary:")
    print(project_summary.to_string(index=False))
    print()


def example_cost_type_aggregation():
    """Example: Aggregate correlated costs by cost type."""
    print("=" * 80)
    print("Example 5: Cost Type Aggregation")
    print("=" * 80)
    
    time_entries = [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="Development",
            hours_spent=8.0,
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
        ),
        ProjectCost(
            cost_id="CONT001",
            cost_type="Contractor",
            amount=25000.00,
            project_name="Alpha Development",
            employee_id=None,
            date=datetime(2024, 3, 15),
            is_rd_classified=True,
            metadata={"contractor_name": "TechConsult LLC"}
        ),
        ProjectCost(
            cost_id="CLOUD001",
            cost_type="Cloud",
            amount=8500.00,
            project_name="Alpha Development",
            employee_id=None,
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"provider": "AWS"}
        ),
        ProjectCost(
            cost_id="MAT001",
            cost_type="Materials",
            amount=5000.00,
            project_name="Alpha Development",
            employee_id=None,
            date=datetime(2024, 3, 10),
            is_rd_classified=True,
            metadata={"description": "Testing equipment"}
        )
    ]
    
    # First correlate costs
    correlated_df = correlate_costs(time_entries, payroll_costs)
    
    # Then aggregate by cost type
    cost_type_summary = aggregate_by_cost_type(correlated_df)
    
    print("\nCost Type Summary:")
    print(cost_type_summary.to_string(index=False))
    print()


def example_filtering():
    """Example: Filtering R&D vs non-R&D entries."""
    print("=" * 80)
    print("Example 6: Filtering R&D vs Non-R&D Entries")
    print("=" * 80)
    
    time_entries = [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Alpha Development",
            task_description="R&D work",
            hours_spent=8.0,
            date=datetime(2024, 3, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson",
            project_name="Admin Tasks",
            task_description="Meetings",
            hours_spent=2.0,
            date=datetime(2024, 3, 15),
            is_rd_classified=False
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
        ),
        ProjectCost(
            cost_id="PAY002",
            cost_type="Payroll",
            amount=12500.00,
            project_name="Admin Tasks",
            employee_id="EMP001",
            date=datetime(2024, 3, 31),
            is_rd_classified=False,
            metadata={"hourly_rate": 72.12}
        )
    ]
    
    # Filter R&D only (default)
    rd_only_df = correlate_costs(time_entries, payroll_costs, filter_rd_only=True)
    print("\nR&D-Only Correlation:")
    print(rd_only_df[['project_name', 'total_hours', 'qualified_wages']].to_string(index=False))
    
    # Include all entries
    all_df = correlate_costs(time_entries, payroll_costs, filter_rd_only=False)
    print("\nAll Entries (R&D + Non-R&D):")
    print(all_df[['project_name', 'total_hours', 'qualified_wages']].to_string(index=False))
    print()


def example_wage_cap_application():
    """Example: Apply IRS wage caps to qualified wages."""
    print("=" * 80)
    print("Example 7: IRS Wage Cap Application")
    print("=" * 80)
    
    # Create time entries for a high-earning employee
    time_entries = [
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson (Senior Engineer)",
            project_name="Alpha Development",
            task_description="Algorithm development",
            hours_spent=1000.0,
            date=datetime(2024, 3, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP001",
            employee_name="Alice Johnson (Senior Engineer)",
            project_name="Beta Infrastructure",
            task_description="Infrastructure work",
            hours_spent=1000.0,
            date=datetime(2024, 6, 15),
            is_rd_classified=True
        ),
        EmployeeTimeEntry(
            employee_id="EMP002",
            employee_name="Bob Smith (Junior Developer)",
            project_name="Gamma Analytics",
            task_description="Data pipeline",
            hours_spent=1000.0,
            date=datetime(2024, 3, 15),
            is_rd_classified=True
        )
    ]
    
    # High hourly rate that will exceed wage cap
    payroll_costs = [
        ProjectCost(
            cost_id="PAY001",
            cost_type="Payroll",
            amount=100000.00,
            project_name="Alpha Development",
            employee_id="EMP001",
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"hourly_rate": 100.00}  # $100/hour
        ),
        ProjectCost(
            cost_id="PAY002",
            cost_type="Payroll",
            amount=100000.00,
            project_name="Beta Infrastructure",
            employee_id="EMP001",
            date=datetime(2024, 6, 30),
            is_rd_classified=True,
            metadata={"hourly_rate": 100.00}  # $100/hour
        ),
        ProjectCost(
            cost_id="PAY003",
            cost_type="Payroll",
            amount=50000.00,
            project_name="Gamma Analytics",
            employee_id="EMP002",
            date=datetime(2024, 3, 31),
            is_rd_classified=True,
            metadata={"hourly_rate": 50.00}  # $50/hour
        )
    ]
    
    # First correlate costs
    correlated_df = correlate_costs(time_entries, payroll_costs)
    
    print("\nBefore Wage Cap Application:")
    print(correlated_df[['employee_name', 'project_name', 'qualified_wages']].to_string(index=False))
    print(f"\nTotal Qualified Wages (Before Cap): ${correlated_df['qualified_wages'].sum():,.2f}")
    
    # Apply IRS wage caps for 2024
    capped_df = apply_wage_caps(correlated_df, tax_year=2024)
    
    print(f"\n2024 IRS Wage Cap: ${IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024:,.2f}")
    print("\nAfter Wage Cap Application:")
    print(capped_df[['employee_name', 'project_name', 'qualified_wages', 'wage_cap_applied', 'capped_amount']].to_string(index=False))
    print(f"\nTotal Qualified Wages (After Cap): ${capped_df['qualified_wages'].sum():,.2f}")
    
    # Show capped employees
    capped_employees = capped_df[capped_df['wage_cap_applied'] == True]
    if not capped_employees.empty:
        print(f"\nEmployees with wages capped: {capped_employees['employee_name'].nunique()}")
        print(f"Total amount capped: ${capped_df['capped_amount'].sum():,.2f}")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PANDAS PROCESSOR USAGE EXAMPLES")
    print("=" * 80 + "\n")
    
    example_basic_correlation()
    example_multiple_employees_and_projects()
    example_with_other_cost_types()
    example_project_aggregation()
    example_cost_type_aggregation()
    example_filtering()
    example_wage_cap_application()
    
    print("=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)
