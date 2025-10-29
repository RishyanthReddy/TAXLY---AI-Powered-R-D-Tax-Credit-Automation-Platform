"""
Unit tests for pandas_processor module.

Tests the cost correlation, aggregation, and data processing functions
that use Pandas for R&D tax credit calculations.
"""

import pytest
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

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


class TestCorrelateCosts:
    """Test suite for correlate_costs function."""
    
    def test_correlate_costs_basic(self):
        """Test basic cost correlation with time entries and payroll."""
        # Create sample time entries
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Alpha Development",
                task_description="Algorithm development",
                hours_spent=8.5,
                date=datetime(2024, 3, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Alpha Development",
                task_description="Testing",
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
                metadata={"hourly_rate": 72.12}
            )
        ]
        
        # Correlate costs
        result_df = correlate_costs(time_entries, payroll_costs)
        
        # Assertions
        assert not result_df.empty
        assert len(result_df) == 1
        assert result_df.iloc[0]['project_name'] == "Alpha Development"
        assert result_df.iloc[0]['employee_id'] == "EMP001"
        assert result_df.iloc[0]['total_hours'] == 14.5  # 8.5 + 6.0
        assert result_df.iloc[0]['hourly_rate'] == 72.12
        assert abs(result_df.iloc[0]['qualified_wages'] - (14.5 * 72.12)) < 0.01
        assert result_df.iloc[0]['cost_type'] == 'Payroll'
    
    def test_correlate_costs_multiple_employees(self):
        """Test cost correlation with multiple employees and projects."""
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
                project_name="Beta Infrastructure",
                task_description="Infrastructure work",
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
                project_name="Beta Infrastructure",
                employee_id="EMP002",
                date=datetime(2024, 3, 31),
                is_rd_classified=True,
                metadata={"hourly_rate": 79.33}
            )
        ]
        
        result_df = correlate_costs(time_entries, payroll_costs)
        
        assert len(result_df) == 2
        assert set(result_df['employee_id'].unique()) == {"EMP001", "EMP002"}
        assert set(result_df['project_name'].unique()) == {"Alpha Development", "Beta Infrastructure"}
    
    def test_correlate_costs_with_other_cost_types(self):
        """Test cost correlation including non-payroll costs."""
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
            )
        ]
        
        result_df = correlate_costs(time_entries, payroll_costs)
        
        # Should have 3 records: 1 payroll, 1 contractor, 1 cloud
        assert len(result_df) == 3
        assert set(result_df['cost_type'].unique()) == {"Payroll", "Contractor", "Cloud"}
        
        # Check payroll record
        payroll_row = result_df[result_df['cost_type'] == 'Payroll'].iloc[0]
        assert payroll_row['total_hours'] == 8.0
        assert payroll_row['qualified_wages'] > 0
        
        # Check contractor record
        contractor_row = result_df[result_df['cost_type'] == 'Contractor'].iloc[0]
        assert contractor_row['other_costs'] == 25000.00
        assert contractor_row['qualified_wages'] == 0.0
        
        # Check cloud record
        cloud_row = result_df[result_df['cost_type'] == 'Cloud'].iloc[0]
        assert cloud_row['other_costs'] == 8500.00
        assert cloud_row['qualified_wages'] == 0.0
    
    def test_correlate_costs_filter_rd_only(self):
        """Test that non-R&D entries are filtered out when filter_rd_only=True."""
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
            )
        ]
        
        result_df = correlate_costs(time_entries, payroll_costs, filter_rd_only=True)
        
        # Should only include R&D-classified entries
        assert len(result_df) == 1
        assert result_df.iloc[0]['project_name'] == "Alpha Development"
        assert result_df.iloc[0]['total_hours'] == 8.0  # Only R&D hours
    
    def test_correlate_costs_no_filter(self):
        """Test cost correlation with filter_rd_only=False."""
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
        
        result_df = correlate_costs(time_entries, payroll_costs, filter_rd_only=False)
        
        # Should include both R&D and non-R&D entries
        assert len(result_df) == 2
        assert set(result_df['project_name'].unique()) == {"Alpha Development", "Admin Tasks"}
    
    def test_correlate_costs_missing_hourly_rate(self):
        """Test handling of missing hourly rate data."""
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
        
        # Payroll cost without hourly_rate in metadata
        payroll_costs = [
            ProjectCost(
                cost_id="PAY001",
                cost_type="Payroll",
                amount=12500.00,
                project_name="Alpha Development",
                employee_id="EMP001",
                date=datetime(2024, 3, 31),
                is_rd_classified=True,
                metadata={}  # No hourly_rate
            )
        ]
        
        result_df = correlate_costs(time_entries, payroll_costs)
        
        # Should handle missing rate gracefully
        assert not result_df.empty
        assert result_df.iloc[0]['hourly_rate'] == 0.0
        assert result_df.iloc[0]['qualified_wages'] == 0.0
    
    def test_correlate_costs_empty_time_entries(self):
        """Test error handling for empty time entries."""
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
        
        with pytest.raises(ValueError, match="time_entries list cannot be empty"):
            correlate_costs([], payroll_costs)
    
    def test_correlate_costs_empty_payroll_costs(self):
        """Test error handling for empty payroll costs."""
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
        
        with pytest.raises(ValueError, match="payroll_costs list cannot be empty"):
            correlate_costs(time_entries, [])
    
    def test_correlate_costs_aggregates_hours_per_employee_project(self):
        """Test that hours are correctly aggregated per employee-project combination."""
        time_entries = [
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Alpha Development",
                task_description="Task 1",
                hours_spent=4.0,
                date=datetime(2024, 3, 15),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Alpha Development",
                task_description="Task 2",
                hours_spent=3.5,
                date=datetime(2024, 3, 16),
                is_rd_classified=True
            ),
            EmployeeTimeEntry(
                employee_id="EMP001",
                employee_name="Alice Johnson",
                project_name="Alpha Development",
                task_description="Task 3",
                hours_spent=2.5,
                date=datetime(2024, 3, 17),
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
        
        # Should aggregate all hours for the same employee-project
        assert len(result_df) == 1
        assert result_df.iloc[0]['total_hours'] == 10.0  # 4.0 + 3.5 + 2.5


class TestAggregateByProject:
    """Test suite for aggregate_by_project function."""
    
    def test_aggregate_by_project_basic(self):
        """Test basic project aggregation."""
        # Create sample correlated data
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 14.5,
                'hourly_rate': 72.12,
                'qualified_wages': 1045.74,
                'other_costs': 0.0,
                'total_qualified_cost': 1045.74
            },
            {
                'project_name': 'Alpha Development',
                'employee_id': None,
                'employee_name': None,
                'cost_type': 'Contractor',
                'total_hours': 0.0,
                'hourly_rate': 0.0,
                'qualified_wages': 0.0,
                'other_costs': 25000.00,
                'total_qualified_cost': 25000.00
            }
        ])
        
        result_df = aggregate_by_project(correlated_data)
        
        assert len(result_df) == 1
        assert result_df.iloc[0]['project_name'] == 'Alpha Development'
        assert result_df.iloc[0]['total_hours'] == 14.5
        assert abs(result_df.iloc[0]['total_qualified_wages'] - 1045.74) < 0.01
        assert result_df.iloc[0]['total_other_costs'] == 25000.00
        assert abs(result_df.iloc[0]['total_qualified_cost'] - 26045.74) < 0.01
        assert result_df.iloc[0]['employee_count'] == 1
    
    def test_aggregate_by_project_multiple_projects(self):
        """Test aggregation with multiple projects."""
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 14.5,
                'hourly_rate': 72.12,
                'qualified_wages': 1045.74,
                'other_costs': 0.0,
                'total_qualified_cost': 1045.74
            },
            {
                'project_name': 'Beta Infrastructure',
                'employee_id': 'EMP002',
                'employee_name': 'Bob Smith',
                'cost_type': 'Payroll',
                'total_hours': 15.5,
                'hourly_rate': 79.33,
                'qualified_wages': 1229.62,
                'other_costs': 0.0,
                'total_qualified_cost': 1229.62
            }
        ])
        
        result_df = aggregate_by_project(correlated_data)
        
        assert len(result_df) == 2
        assert set(result_df['project_name'].unique()) == {'Alpha Development', 'Beta Infrastructure'}
        # Should be sorted by total_qualified_cost descending
        assert result_df.iloc[0]['total_qualified_cost'] >= result_df.iloc[1]['total_qualified_cost']
    
    def test_aggregate_by_project_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame(columns=[
            'project_name', 'employee_id', 'employee_name', 'cost_type',
            'total_hours', 'hourly_rate', 'qualified_wages', 'other_costs',
            'total_qualified_cost'
        ])
        
        result_df = aggregate_by_project(empty_df)
        
        assert result_df.empty
        assert 'project_name' in result_df.columns
        assert 'total_qualified_cost' in result_df.columns


class TestAggregateByCostType:
    """Test suite for aggregate_by_cost_type function."""
    
    def test_aggregate_by_cost_type_basic(self):
        """Test basic cost type aggregation."""
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 14.5,
                'hourly_rate': 72.12,
                'qualified_wages': 1045.74,
                'other_costs': 0.0,
                'total_qualified_cost': 1045.74
            },
            {
                'project_name': 'Alpha Development',
                'employee_id': None,
                'employee_name': None,
                'cost_type': 'Contractor',
                'total_hours': 0.0,
                'hourly_rate': 0.0,
                'qualified_wages': 0.0,
                'other_costs': 25000.00,
                'total_qualified_cost': 25000.00
            },
            {
                'project_name': 'Alpha Development',
                'employee_id': None,
                'employee_name': None,
                'cost_type': 'Cloud',
                'total_hours': 0.0,
                'hourly_rate': 0.0,
                'qualified_wages': 0.0,
                'other_costs': 8500.00,
                'total_qualified_cost': 8500.00
            }
        ])
        
        result_df = aggregate_by_cost_type(correlated_data)
        
        assert len(result_df) == 3
        assert set(result_df['cost_type'].unique()) == {'Payroll', 'Contractor', 'Cloud'}
        
        # Check percentages sum to 100
        assert abs(result_df['percentage'].sum() - 100.0) < 0.1
        
        # Contractor should be the largest cost
        contractor_row = result_df[result_df['cost_type'] == 'Contractor'].iloc[0]
        assert contractor_row['total_cost'] == 25000.00
        assert contractor_row['percentage'] > 70  # Should be majority
    
    def test_aggregate_by_cost_type_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame(columns=[
            'project_name', 'employee_id', 'employee_name', 'cost_type',
            'total_hours', 'hourly_rate', 'qualified_wages', 'other_costs',
            'total_qualified_cost'
        ])
        
        result_df = aggregate_by_cost_type(empty_df)
        
        assert result_df.empty
        assert 'cost_type' in result_df.columns
        assert 'percentage' in result_df.columns


class TestApplyWageCaps:
    """Test suite for apply_wage_caps function."""
    
    def test_apply_wage_caps_no_capping_needed(self):
        """Test wage cap application when wages are below the cap."""
        # Create correlated data with wages below the cap
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 100.0,
                'hourly_rate': 50.00,
                'qualified_wages': 5000.00,  # Well below cap
                'other_costs': 0.0,
                'total_qualified_cost': 5000.00,
                'date': datetime(2024, 3, 15)
            }
        ])
        
        result_df = apply_wage_caps(correlated_data, tax_year=2024)
        
        # No capping should occur
        assert result_df.iloc[0]['wage_cap_applied'] == False
        assert result_df.iloc[0]['qualified_wages'] == 5000.00
        assert result_df.iloc[0]['capped_amount'] == 0.0
        assert result_df.iloc[0]['original_qualified_wages'] == 5000.00
    
    def test_apply_wage_caps_single_employee_exceeds_cap(self):
        """Test wage cap application when a single employee exceeds the cap."""
        wage_cap_2024 = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
        
        # Create correlated data with wages exceeding the cap
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 2000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 200000.00,  # Exceeds 2024 cap of $168,600
                'other_costs': 0.0,
                'total_qualified_cost': 200000.00,
                'date': datetime(2024, 3, 15)
            }
        ])
        
        result_df = apply_wage_caps(correlated_data, tax_year=2024)
        
        # Capping should occur
        assert result_df.iloc[0]['wage_cap_applied'] == True
        assert result_df.iloc[0]['qualified_wages'] == wage_cap_2024
        assert result_df.iloc[0]['capped_amount'] == 200000.00 - wage_cap_2024
        assert result_df.iloc[0]['original_qualified_wages'] == 200000.00
        assert result_df.iloc[0]['total_qualified_cost'] == wage_cap_2024  # Recalculated
    
    def test_apply_wage_caps_multiple_projects_same_employee(self):
        """Test wage cap application across multiple projects for the same employee."""
        wage_cap_2024 = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
        
        # Employee works on two projects, total wages exceed cap
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 1000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 100000.00,
                'other_costs': 0.0,
                'total_qualified_cost': 100000.00,
                'date': datetime(2024, 3, 15)
            },
            {
                'project_name': 'Beta Infrastructure',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 1000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 100000.00,
                'other_costs': 0.0,
                'total_qualified_cost': 100000.00,
                'date': datetime(2024, 6, 15)
            }
        ])
        
        result_df = apply_wage_caps(correlated_data, tax_year=2024)
        
        # Both projects should be capped proportionally
        assert result_df['wage_cap_applied'].all()
        
        # Total wages should equal the cap
        total_capped_wages = result_df['qualified_wages'].sum()
        assert abs(total_capped_wages - wage_cap_2024) < 0.01
        
        # Each project should get proportional reduction (50% each)
        expected_per_project = wage_cap_2024 / 2
        assert abs(result_df.iloc[0]['qualified_wages'] - expected_per_project) < 0.01
        assert abs(result_df.iloc[1]['qualified_wages'] - expected_per_project) < 0.01
    
    def test_apply_wage_caps_multiple_employees(self):
        """Test wage cap application with multiple employees."""
        wage_cap_2024 = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
        
        # Two employees: one exceeds cap, one doesn't
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 2000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 200000.00,  # Exceeds cap
                'other_costs': 0.0,
                'total_qualified_cost': 200000.00,
                'date': datetime(2024, 3, 15)
            },
            {
                'project_name': 'Beta Infrastructure',
                'employee_id': 'EMP002',
                'employee_name': 'Bob Smith',
                'cost_type': 'Payroll',
                'total_hours': 1000.0,
                'hourly_rate': 50.00,
                'qualified_wages': 50000.00,  # Below cap
                'other_costs': 0.0,
                'total_qualified_cost': 50000.00,
                'date': datetime(2024, 3, 15)
            }
        ])
        
        result_df = apply_wage_caps(correlated_data, tax_year=2024)
        
        # EMP001 should be capped
        emp001_row = result_df[result_df['employee_id'] == 'EMP001'].iloc[0]
        assert emp001_row['wage_cap_applied'] == True
        assert emp001_row['qualified_wages'] == wage_cap_2024
        
        # EMP002 should not be capped
        emp002_row = result_df[result_df['employee_id'] == 'EMP002'].iloc[0]
        assert emp002_row['wage_cap_applied'] == False
        assert emp002_row['qualified_wages'] == 50000.00
    
    def test_apply_wage_caps_non_payroll_costs_unaffected(self):
        """Test that non-payroll costs are not affected by wage caps."""
        # Mix of payroll and non-payroll costs
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 2000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 200000.00,
                'other_costs': 0.0,
                'total_qualified_cost': 200000.00,
                'date': datetime(2024, 3, 15)
            },
            {
                'project_name': 'Alpha Development',
                'employee_id': None,
                'employee_name': None,
                'cost_type': 'Contractor',
                'total_hours': 0.0,
                'hourly_rate': 0.0,
                'qualified_wages': 0.0,
                'other_costs': 50000.00,
                'total_qualified_cost': 50000.00,
                'date': datetime(2024, 3, 15)
            }
        ])
        
        result_df = apply_wage_caps(correlated_data, tax_year=2024)
        
        # Contractor costs should remain unchanged
        contractor_row = result_df[result_df['cost_type'] == 'Contractor'].iloc[0]
        assert contractor_row['wage_cap_applied'] == False
        assert contractor_row['other_costs'] == 50000.00
        assert contractor_row['total_qualified_cost'] == 50000.00
    
    def test_apply_wage_caps_2023_tax_year(self):
        """Test wage cap application for 2023 tax year."""
        wage_cap_2023 = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2023
        
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 2000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 200000.00,
                'other_costs': 0.0,
                'total_qualified_cost': 200000.00,
                'date': datetime(2023, 3, 15)
            }
        ])
        
        result_df = apply_wage_caps(correlated_data, tax_year=2023)
        
        # Should use 2023 cap ($160,200)
        assert result_df.iloc[0]['wage_cap_applied'] == True
        assert result_df.iloc[0]['qualified_wages'] == wage_cap_2023
    
    def test_apply_wage_caps_unsupported_tax_year(self):
        """Test error handling for unsupported tax year."""
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 100.0,
                'hourly_rate': 50.00,
                'qualified_wages': 5000.00,
                'other_costs': 0.0,
                'total_qualified_cost': 5000.00,
                'date': datetime(2025, 3, 15)
            }
        ])
        
        with pytest.raises(ValueError, match="Unsupported tax year: 2025"):
            apply_wage_caps(correlated_data, tax_year=2025)
    
    def test_apply_wage_caps_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame(columns=[
            'project_name', 'employee_id', 'employee_name', 'cost_type',
            'total_hours', 'hourly_rate', 'qualified_wages', 'other_costs',
            'total_qualified_cost', 'date'
        ])
        
        result_df = apply_wage_caps(empty_df, tax_year=2024)
        
        assert result_df.empty
    
    def test_apply_wage_caps_with_other_costs(self):
        """Test that other_costs are preserved when wages are capped."""
        wage_cap_2024 = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
        
        # Employee with both wages and other costs
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 2000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 200000.00,
                'other_costs': 10000.00,  # Some other costs
                'total_qualified_cost': 210000.00,
                'date': datetime(2024, 3, 15)
            }
        ])
        
        result_df = apply_wage_caps(correlated_data, tax_year=2024)
        
        # Wages should be capped, other costs preserved
        assert result_df.iloc[0]['qualified_wages'] == wage_cap_2024
        assert result_df.iloc[0]['other_costs'] == 10000.00
        assert result_df.iloc[0]['total_qualified_cost'] == wage_cap_2024 + 10000.00
    
    def test_apply_wage_caps_multi_year_data(self):
        """Test wage cap application across multiple years."""
        wage_cap_2023 = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2023
        wage_cap_2024 = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
        
        # Same employee in different years
        correlated_data = pd.DataFrame([
            {
                'project_name': 'Alpha Development',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 2000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 200000.00,
                'other_costs': 0.0,
                'total_qualified_cost': 200000.00,
                'date': datetime(2023, 3, 15)
            },
            {
                'project_name': 'Beta Infrastructure',
                'employee_id': 'EMP001',
                'employee_name': 'Alice Johnson',
                'cost_type': 'Payroll',
                'total_hours': 2000.0,
                'hourly_rate': 100.00,
                'qualified_wages': 200000.00,
                'other_costs': 0.0,
                'total_qualified_cost': 200000.00,
                'date': datetime(2024, 3, 15)
            }
        ])
        
        # Apply 2024 cap (should only affect 2024 data)
        result_df = apply_wage_caps(correlated_data, tax_year=2024)
        
        # 2024 entry should be capped
        entry_2024 = result_df[result_df['date'] == datetime(2024, 3, 15)].iloc[0]
        assert entry_2024['wage_cap_applied'] == True
        assert entry_2024['qualified_wages'] == wage_cap_2024
        
        # 2023 entry should not be affected (different year)
        entry_2023 = result_df[result_df['date'] == datetime(2023, 3, 15)].iloc[0]
        assert entry_2023['wage_cap_applied'] == False
        assert entry_2023['qualified_wages'] == 200000.00
