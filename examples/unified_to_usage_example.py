"""
Example usage of UnifiedToConnector for fetching employee data.

This example demonstrates how to use the UnifiedToConnector to fetch
employee profiles from HRIS systems via the Unified.to API.

NOTE: Currently returns mock data for development/testing purposes.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.api_connectors import UnifiedToConnector
from utils.logger import get_tool_logger

# Initialize logger
logger = get_tool_logger("unified_to_example")


def main():
    """Demonstrate UnifiedToConnector usage."""
    
    logger.info("=== Unified.to Employee Fetching Example ===\n")
    
    # Initialize connector
    # In production, these would come from environment variables
    connector = UnifiedToConnector(
        api_key="test_api_key",
        workspace_id="test_workspace_id"
    )
    
    try:
        # Fetch employees (returns mock data)
        logger.info("Fetching employees from Unified.to...")
        employees = connector.fetch_employees()
        
        logger.info(f"\nSuccessfully fetched {len(employees)} employees\n")
        
        # Display employee summary
        logger.info("Employee Summary:")
        logger.info("-" * 80)
        
        for emp in employees:
            logger.info(
                f"ID: {emp['id']:<10} | "
                f"Name: {emp['name']:<25} | "
                f"Title: {emp['job_title']:<30} | "
                f"Dept: {emp['department']:<20}"
            )
        
        logger.info("-" * 80)
        
        # Display department breakdown
        departments = {}
        for emp in employees:
            dept = emp['department']
            departments[dept] = departments.get(dept, 0) + 1
        
        logger.info("\nDepartment Breakdown:")
        for dept, count in sorted(departments.items()):
            logger.info(f"  {dept}: {count} employees")
        
        # Display compensation statistics
        compensations = [emp['compensation'] for emp in employees]
        avg_comp = sum(compensations) / len(compensations)
        min_comp = min(compensations)
        max_comp = max(compensations)
        
        logger.info("\nCompensation Statistics:")
        logger.info(f"  Average: ${avg_comp:,.2f}")
        logger.info(f"  Minimum: ${min_comp:,.2f}")
        logger.info(f"  Maximum: ${max_comp:,.2f}")
        
        # Display manager hierarchy
        managers = [emp for emp in employees if emp['manager_id'] is None]
        logger.info(f"\nManagers: {len(managers)}")
        for mgr in managers:
            logger.info(f"  {mgr['name']} - {mgr['job_title']}")
        
        logger.info("\n=== Example Complete ===")
        
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        raise
    
    finally:
        # Clean up
        connector.close()


if __name__ == "__main__":
    main()
