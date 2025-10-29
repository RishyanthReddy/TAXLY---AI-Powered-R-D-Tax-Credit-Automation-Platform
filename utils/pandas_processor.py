"""
Pandas-based data processing utilities for R&D Tax Credit Automation Agent.

This module provides functions for correlating costs with time entries,
calculating qualified wages, and aggregating data by project and cost type.
Uses Pandas for efficient data manipulation and analysis.
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.financial_models import EmployeeTimeEntry, ProjectCost
from models.tax_models import QualifiedProject
from utils.logger import AgentLogger

logger = AgentLogger.get_logger(__name__)


def correlate_costs(
    time_entries: List[EmployeeTimeEntry],
    payroll_costs: List[ProjectCost],
    filter_rd_only: bool = True
) -> pd.DataFrame:
    """
    Correlate time entries with payroll data to calculate qualified wages.
    
    This function merges time tracking data with payroll/cost data on employee_id,
    calculates qualified wages by multiplying hours by hourly rates, and aggregates
    results by project and cost type. This is a core function for determining
    qualified research expenditures (QREs) for R&D tax credit calculations.
    
    Args:
        time_entries: List of EmployeeTimeEntry objects from time tracking systems
        payroll_costs: List of ProjectCost objects from HRIS/payroll systems
        filter_rd_only: If True, only include entries where is_rd_classified=True
    
    Returns:
        DataFrame with columns:
            - project_name: Name of the project
            - employee_id: Employee identifier (or None for non-payroll costs)
            - employee_name: Employee name
            - cost_type: Type of cost (Payroll, Contractor, Materials, Cloud, Other)
            - total_hours: Total hours spent on the project
            - hourly_rate: Hourly compensation rate
            - qualified_wages: Calculated wages (hours × hourly_rate)
            - other_costs: Non-payroll costs (contractor, materials, cloud, etc.)
            - total_qualified_cost: Sum of qualified_wages and other_costs
    
    Raises:
        ValueError: If input lists are empty or data validation fails
        
    Example:
        >>> from models.financial_models import EmployeeTimeEntry, ProjectCost
        >>> from datetime import datetime
        >>> 
        >>> time_entries = [
        ...     EmployeeTimeEntry(
        ...         employee_id="EMP001",
        ...         employee_name="Alice Johnson",
        ...         project_name="Alpha Development",
        ...         task_description="Algorithm development",
        ...         hours_spent=8.5,
        ...         date=datetime(2024, 3, 15),
        ...         is_rd_classified=True
        ...     )
        ... ]
        >>> 
        >>> payroll_costs = [
        ...     ProjectCost(
        ...         cost_id="PAY001",
        ...         cost_type="Payroll",
        ...         amount=12500.00,
        ...         project_name="Alpha Development",
        ...         employee_id="EMP001",
        ...         date=datetime(2024, 3, 31),
        ...         is_rd_classified=True,
        ...         metadata={"hourly_rate": 72.12}
        ...     )
        ... ]
        >>> 
        >>> result_df = correlate_costs(time_entries, payroll_costs)
        >>> print(result_df[['project_name', 'total_hours', 'qualified_wages']])
    """
    logger.info(
        f"Starting cost correlation: {len(time_entries)} time entries, "
        f"{len(payroll_costs)} cost entries"
    )
    
    # Validate inputs
    if not time_entries:
        raise ValueError("time_entries list cannot be empty")
    
    if not payroll_costs:
        raise ValueError("payroll_costs list cannot be empty")
    
    # Convert time entries to DataFrame
    time_data = []
    for entry in time_entries:
        # Filter by R&D classification if requested
        if filter_rd_only and not entry.is_rd_classified:
            continue
        
        time_data.append({
            'employee_id': entry.employee_id,
            'employee_name': entry.employee_name,
            'project_name': entry.project_name,
            'task_description': entry.task_description,
            'hours_spent': entry.hours_spent,
            'date': entry.date,
            'is_rd_classified': entry.is_rd_classified
        })
    
    if not time_data:
        logger.warning("No R&D-classified time entries found after filtering")
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=[
            'project_name', 'employee_id', 'employee_name', 'cost_type',
            'total_hours', 'hourly_rate', 'qualified_wages', 'other_costs',
            'total_qualified_cost'
        ])
    
    time_df = pd.DataFrame(time_data)
    logger.info(f"Created time DataFrame with {len(time_df)} R&D-classified entries")
    
    # Convert payroll costs to DataFrame
    cost_data = []
    for cost in payroll_costs:
        # Filter by R&D classification if requested
        if filter_rd_only and not cost.is_rd_classified:
            continue
        
        cost_data.append({
            'cost_id': cost.cost_id,
            'cost_type': cost.cost_type,
            'amount': cost.amount,
            'project_name': cost.project_name,
            'employee_id': cost.employee_id,
            'date': cost.date,
            'is_rd_classified': cost.is_rd_classified,
            'hourly_rate': cost.hourly_rate,  # Uses computed field
            'metadata': cost.metadata
        })
    
    if not cost_data:
        logger.warning("No R&D-classified cost entries found after filtering")
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=[
            'project_name', 'employee_id', 'employee_name', 'cost_type',
            'total_hours', 'hourly_rate', 'qualified_wages', 'other_costs',
            'total_qualified_cost'
        ])
    
    cost_df = pd.DataFrame(cost_data)
    logger.info(f"Created cost DataFrame with {len(cost_df)} R&D-classified entries")
    
    # Separate payroll costs from other costs
    payroll_df = cost_df[cost_df['cost_type'] == 'Payroll'].copy()
    other_costs_df = cost_df[cost_df['cost_type'] != 'Payroll'].copy()
    
    logger.info(
        f"Split costs: {len(payroll_df)} payroll entries, "
        f"{len(other_costs_df)} other cost entries"
    )
    
    # Aggregate time entries by employee and project
    time_agg = time_df.groupby(['employee_id', 'employee_name', 'project_name']).agg({
        'hours_spent': 'sum'
    }).reset_index()
    time_agg.rename(columns={'hours_spent': 'total_hours'}, inplace=True)
    
    logger.info(f"Aggregated time entries: {len(time_agg)} unique employee-project combinations")
    
    # Merge time entries with payroll costs on employee_id
    if not payroll_df.empty:
        # For payroll, we need to match employee_id
        merged_df = time_agg.merge(
            payroll_df[['employee_id', 'project_name', 'hourly_rate']],
            on=['employee_id', 'project_name'],
            how='left'
        )
        
        # Calculate qualified wages (hours × hourly_rate)
        merged_df['qualified_wages'] = merged_df['total_hours'] * merged_df['hourly_rate']
        merged_df['cost_type'] = 'Payroll'
        merged_df['other_costs'] = 0.0
        
        logger.info(f"Merged time and payroll data: {len(merged_df)} records")
        
        # Handle missing hourly rates
        missing_rates = merged_df['hourly_rate'].isna().sum()
        if missing_rates > 0:
            logger.warning(
                f"{missing_rates} employee-project combinations missing hourly rate data. "
                f"Setting qualified_wages to 0 for these entries."
            )
            merged_df['hourly_rate'].fillna(0.0, inplace=True)
            merged_df['qualified_wages'].fillna(0.0, inplace=True)
    else:
        # No payroll data, create empty merged DataFrame
        merged_df = pd.DataFrame(columns=[
            'project_name', 'employee_id', 'employee_name', 'cost_type',
            'total_hours', 'hourly_rate', 'qualified_wages', 'other_costs'
        ])
        logger.warning("No payroll data available for correlation")
    
    # Process other costs (contractor, materials, cloud, etc.)
    other_costs_records = []
    if not other_costs_df.empty:
        for _, cost_row in other_costs_df.iterrows():
            other_costs_records.append({
                'project_name': cost_row['project_name'],
                'employee_id': cost_row['employee_id'],  # May be None
                'employee_name': None,  # Not applicable for non-payroll costs
                'cost_type': cost_row['cost_type'],
                'total_hours': 0.0,  # Not applicable
                'hourly_rate': 0.0,  # Not applicable
                'qualified_wages': 0.0,
                'other_costs': cost_row['amount']
            })
        
        logger.info(f"Processed {len(other_costs_records)} non-payroll cost entries")
    
    # Combine payroll and other costs
    if other_costs_records:
        other_costs_df_processed = pd.DataFrame(other_costs_records)
        result_df = pd.concat([merged_df, other_costs_df_processed], ignore_index=True)
    else:
        result_df = merged_df
    
    # Calculate total qualified cost
    result_df['total_qualified_cost'] = result_df['qualified_wages'] + result_df['other_costs']
    
    # Sort by project name and cost type for readability
    result_df.sort_values(['project_name', 'cost_type'], inplace=True)
    result_df.reset_index(drop=True, inplace=True)
    
    logger.info(
        f"Cost correlation complete: {len(result_df)} total records, "
        f"${result_df['total_qualified_cost'].sum():.2f} total qualified cost"
    )
    
    return result_df


def aggregate_by_project(correlated_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate correlated cost data by project.
    
    This function takes the output of correlate_costs() and aggregates it by project,
    summing hours, wages, and costs to provide a project-level view of qualified
    research expenditures.
    
    Args:
        correlated_df: DataFrame output from correlate_costs()
    
    Returns:
        DataFrame with columns:
            - project_name: Name of the project
            - total_hours: Total qualified hours for the project
            - total_qualified_wages: Total qualified wages (payroll only)
            - total_other_costs: Total non-payroll costs
            - total_qualified_cost: Total qualified cost (wages + other costs)
            - employee_count: Number of unique employees on the project
    
    Example:
        >>> correlated_df = correlate_costs(time_entries, payroll_costs)
        >>> project_summary = aggregate_by_project(correlated_df)
        >>> print(project_summary)
    """
    if correlated_df.empty:
        logger.warning("Cannot aggregate empty DataFrame")
        return pd.DataFrame(columns=[
            'project_name', 'total_hours', 'total_qualified_wages',
            'total_other_costs', 'total_qualified_cost', 'employee_count'
        ])
    
    logger.info(f"Aggregating {len(correlated_df)} records by project")
    
    # Aggregate by project
    project_agg = correlated_df.groupby('project_name').agg({
        'total_hours': 'sum',
        'qualified_wages': 'sum',
        'other_costs': 'sum',
        'total_qualified_cost': 'sum',
        'employee_id': lambda x: x.dropna().nunique()  # Count unique non-null employee IDs
    }).reset_index()
    
    # Rename columns for clarity
    project_agg.rename(columns={
        'qualified_wages': 'total_qualified_wages',
        'other_costs': 'total_other_costs',
        'employee_id': 'employee_count'
    }, inplace=True)
    
    # Sort by total qualified cost (descending)
    project_agg.sort_values('total_qualified_cost', ascending=False, inplace=True)
    project_agg.reset_index(drop=True, inplace=True)
    
    logger.info(
        f"Project aggregation complete: {len(project_agg)} projects, "
        f"${project_agg['total_qualified_cost'].sum():.2f} total qualified cost"
    )
    
    return project_agg


def aggregate_by_cost_type(correlated_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate correlated cost data by cost type.
    
    This function provides a breakdown of qualified costs by type (Payroll, Contractor,
    Materials, Cloud, Other), which is useful for IRS reporting and analysis.
    
    Args:
        correlated_df: DataFrame output from correlate_costs()
    
    Returns:
        DataFrame with columns:
            - cost_type: Type of cost
            - total_hours: Total hours (for Payroll only)
            - total_cost: Total cost for this type
            - percentage: Percentage of total qualified costs
    
    Example:
        >>> correlated_df = correlate_costs(time_entries, payroll_costs)
        >>> cost_type_summary = aggregate_by_cost_type(correlated_df)
        >>> print(cost_type_summary)
    """
    if correlated_df.empty:
        logger.warning("Cannot aggregate empty DataFrame")
        return pd.DataFrame(columns=[
            'cost_type', 'total_hours', 'total_cost', 'percentage'
        ])
    
    logger.info(f"Aggregating {len(correlated_df)} records by cost type")
    
    # Aggregate by cost type
    cost_type_agg = correlated_df.groupby('cost_type').agg({
        'total_hours': 'sum',
        'total_qualified_cost': 'sum'
    }).reset_index()
    
    # Rename columns
    cost_type_agg.rename(columns={
        'total_qualified_cost': 'total_cost'
    }, inplace=True)
    
    # Calculate percentage of total
    total_cost = cost_type_agg['total_cost'].sum()
    if total_cost > 0:
        cost_type_agg['percentage'] = (cost_type_agg['total_cost'] / total_cost * 100).round(2)
    else:
        cost_type_agg['percentage'] = 0.0
    
    # Sort by total cost (descending)
    cost_type_agg.sort_values('total_cost', ascending=False, inplace=True)
    cost_type_agg.reset_index(drop=True, inplace=True)
    
    logger.info(
        f"Cost type aggregation complete: {len(cost_type_agg)} cost types, "
        f"${cost_type_agg['total_cost'].sum():.2f} total cost"
    )
    
    return cost_type_agg


def apply_wage_caps(
    correlated_df: pd.DataFrame,
    tax_year: int = 2024
) -> pd.DataFrame:
    """
    Apply IRS wage caps to qualified wages per employee per year.
    
    This function enforces the Social Security wage base limits as specified in
    Form 6765 instructions. The wage cap is applied per employee per tax year,
    ensuring compliance with IRS regulations for R&D tax credit calculations.
    
    According to IRS Form 6765, qualified wages are subject to the Social Security
    wage base limitation. This function:
    1. Groups wages by employee and tax year
    2. Applies the appropriate wage cap for the tax year
    3. Adjusts qualified wages and total costs accordingly
    4. Logs all capped amounts for transparency and audit purposes
    
    Args:
        correlated_df: DataFrame output from correlate_costs() containing qualified wages
        tax_year: Tax year for determining the applicable wage cap (default: 2024)
    
    Returns:
        DataFrame with the same structure as input, but with capped wages:
            - qualified_wages: Adjusted to not exceed wage cap per employee per year
            - total_qualified_cost: Recalculated with capped wages
            - wage_cap_applied: Boolean flag indicating if cap was applied
            - original_qualified_wages: Original wages before capping (for transparency)
            - capped_amount: Amount reduced due to wage cap
    
    Raises:
        ValueError: If tax_year is not supported or correlated_df is invalid
    
    Example:
        >>> correlated_df = correlate_costs(time_entries, payroll_costs)
        >>> capped_df = apply_wage_caps(correlated_df, tax_year=2024)
        >>> # Check which employees had wages capped
        >>> capped_employees = capped_df[capped_df['wage_cap_applied'] == True]
        >>> print(f"Capped {len(capped_employees)} employee records")
        >>> print(f"Total capped amount: ${capped_df['capped_amount'].sum():.2f}")
    
    Notes:
        - Wage caps are applied per employee per year, not per project
        - Non-payroll costs (Contractor, Materials, Cloud, Other) are not subject to wage caps
        - The function preserves original wage data for audit trail purposes
        - Wage cap values are sourced from utils.constants.IRSWageCap
    """
    from utils.constants import IRSWageCap
    
    if correlated_df.empty:
        logger.warning("Cannot apply wage caps to empty DataFrame")
        return correlated_df
    
    # Validate tax year and get appropriate wage cap
    if tax_year == 2024:
        wage_cap = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2024
    elif tax_year == 2023:
        wage_cap = IRSWageCap.SOCIAL_SECURITY_WAGE_BASE_2023
    else:
        raise ValueError(
            f"Unsupported tax year: {tax_year}. "
            f"Supported years: 2023, 2024. "
            f"Please update constants.py with wage cap for {tax_year}."
        )
    
    logger.info(
        f"Applying IRS wage caps for tax year {tax_year}: "
        f"${wage_cap:,.2f} per employee"
    )
    
    # Create a copy to avoid modifying the original DataFrame
    result_df = correlated_df.copy()
    
    # Add columns for tracking wage cap application
    result_df['wage_cap_applied'] = False
    result_df['original_qualified_wages'] = result_df['qualified_wages']
    result_df['capped_amount'] = 0.0
    
    # Only apply wage caps to Payroll cost type
    payroll_mask = result_df['cost_type'] == 'Payroll'
    
    if not payroll_mask.any():
        logger.info("No payroll entries found. Wage caps not applicable.")
        return result_df
    
    # Extract year from date column if it exists
    if 'date' in result_df.columns:
        result_df['year'] = pd.to_datetime(result_df['date']).dt.year
    else:
        # If no date column, assume all entries are for the specified tax year
        result_df['year'] = tax_year
        logger.warning(
            "No 'date' column found in DataFrame. "
            f"Assuming all entries are for tax year {tax_year}."
        )
    
    # Group by employee_id and year to calculate total wages per employee per year
    payroll_df = result_df[payroll_mask].copy()
    
    # Calculate cumulative wages per employee per year
    employee_year_totals = payroll_df.groupby(['employee_id', 'year'])['qualified_wages'].sum()
    
    logger.info(
        f"Analyzing wages for {len(employee_year_totals)} unique employee-year combinations"
    )
    
    # Track capping statistics
    employees_capped = 0
    total_capped_amount = 0.0
    
    # Apply wage caps per employee per year
    for (employee_id, year), total_wages in employee_year_totals.items():
        # Only apply cap if this is the specified tax year
        if year != tax_year:
            continue
            
        if total_wages > wage_cap:
            # Calculate the reduction factor
            reduction_factor = wage_cap / total_wages
            
            # Find all records for this employee in this year
            mask = (
                (result_df['employee_id'] == employee_id) &
                (result_df['year'] == year) &
                (result_df['cost_type'] == 'Payroll')
            )
            
            # Apply proportional reduction to maintain project distribution
            original_wages = result_df.loc[mask, 'qualified_wages'].copy()
            capped_wages = original_wages * reduction_factor
            capped_amount = original_wages - capped_wages
            
            # Update the DataFrame
            result_df.loc[mask, 'qualified_wages'] = capped_wages
            result_df.loc[mask, 'wage_cap_applied'] = True
            result_df.loc[mask, 'capped_amount'] = capped_amount
            
            # Recalculate total qualified cost
            result_df.loc[mask, 'total_qualified_cost'] = (
                result_df.loc[mask, 'qualified_wages'] + 
                result_df.loc[mask, 'other_costs']
            )
            
            # Log the capping action
            employee_capped_amount = capped_amount.sum()
            total_capped_amount += employee_capped_amount
            employees_capped += 1
            
            logger.info(
                f"Applied wage cap to employee {employee_id} for year {year}: "
                f"Original wages: ${total_wages:,.2f}, "
                f"Capped wages: ${wage_cap:,.2f}, "
                f"Reduction: ${employee_capped_amount:,.2f} "
                f"({(1 - reduction_factor) * 100:.1f}%)"
            )
    
    # Log summary statistics
    if employees_capped > 0:
        logger.warning(
            f"Wage cap applied to {employees_capped} employee(s) for tax year {tax_year}. "
            f"Total wages reduced by ${total_capped_amount:,.2f}. "
            f"This is normal for high-earning employees and ensures IRS compliance."
        )
    else:
        logger.info(
            f"No wage caps applied. All employee wages are within the "
            f"${wage_cap:,.2f} limit for tax year {tax_year}."
        )
    
    # Clean up temporary year column if we added it
    if 'date' not in correlated_df.columns and 'year' in result_df.columns:
        result_df.drop('year', axis=1, inplace=True)
    
    logger.info(
        f"Wage cap application complete: "
        f"{employees_capped} employees capped, "
        f"${total_capped_amount:,.2f} total reduction"
    )
    
    return result_df
