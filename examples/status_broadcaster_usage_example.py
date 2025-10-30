"""
Status Broadcaster Usage Examples

This script demonstrates how to use the status broadcaster module
to send real-time updates to connected WebSocket clients.

Requirements: 5.2, 5.3
"""

import asyncio
from datetime import datetime

from utils.status_broadcaster import (
    send_status_update,
    send_error_notification,
    send_progress_update,
    send_agent_started,
    send_agent_completed,
    send_agent_error,
    get_active_connection_count,
    broadcast_custom_message
)
from models.websocket_models import (
    AgentStage,
    AgentStatus,
    ErrorType
)


async def example_basic_status_update():
    """Example: Send a basic status update"""
    print("\n=== Example 1: Basic Status Update ===")
    
    await send_status_update(
        stage=AgentStage.DATA_INGESTION,
        status=AgentStatus.IN_PROGRESS,
        details="Fetching time entries from Clockify API"
    )
    print("✓ Status update sent")


async def example_agent_lifecycle():
    """Example: Agent lifecycle status updates"""
    print("\n=== Example 2: Agent Lifecycle ===")
    
    # Agent started
    await send_agent_started(
        stage=AgentStage.QUALIFICATION,
        details="Starting R&D qualification analysis"
    )
    print("✓ Agent started notification sent")
    
    # Simulate some work
    await asyncio.sleep(1)
    
    # Agent completed
    await send_agent_completed(
        stage=AgentStage.QUALIFICATION,
        details="Successfully qualified 15 projects"
    )
    print("✓ Agent completed notification sent")


async def example_progress_updates():
    """Example: Progress updates during batch processing"""
    print("\n=== Example 3: Progress Updates ===")
    
    total_projects = 10
    
    for i in range(1, total_projects + 1):
        # Simulate processing
        await asyncio.sleep(0.2)
        
        # Send progress update
        await send_progress_update(
            current_step=i,
            total_steps=total_projects,
            description=f"Processing project {i} of {total_projects}"
        )
        print(f"✓ Progress update sent: {i}/{total_projects}")


async def example_error_notification():
    """Example: Send error notification"""
    print("\n=== Example 4: Error Notification ===")
    
    try:
        # Simulate an error
        raise ConnectionError("Failed to connect to Clockify API")
        
    except Exception as e:
        import traceback
        
        await send_error_notification(
            error_type=ErrorType.API_CONNECTION,
            message=f"API connection failed: {str(e)}",
            traceback=traceback.format_exc()
        )
        print("✓ Error notification sent")


async def example_connection_monitoring():
    """Example: Check active connections before expensive operations"""
    print("\n=== Example 5: Connection Monitoring ===")
    
    connection_count = get_active_connection_count()
    print(f"Active WebSocket connections: {connection_count}")
    
    if connection_count > 0:
        print("Clients are connected - sending detailed updates")
        await send_status_update(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.IN_PROGRESS,
            details="Generating comprehensive audit report with detailed narratives"
        )
    else:
        print("No clients connected - skipping detailed updates")


async def example_custom_message():
    """Example: Broadcast custom application-specific message"""
    print("\n=== Example 6: Custom Message ===")
    
    await broadcast_custom_message(
        message_type="credit_calculation",
        total_credit=125000.50,
        qualified_projects=15,
        qualified_hours=2340.5,
        tax_year=2024,
        calculation_date=datetime.now().isoformat()
    )
    print("✓ Custom message broadcast")


async def example_complete_workflow():
    """Example: Complete agent workflow with status updates"""
    print("\n=== Example 7: Complete Workflow ===")
    
    # Stage 1: Data Ingestion
    await send_agent_started(
        stage=AgentStage.DATA_INGESTION,
        details="Starting data ingestion from external APIs"
    )
    
    # Simulate fetching data with progress
    data_sources = ["Clockify", "Unified.to HRIS", "Unified.to Payroll"]
    for i, source in enumerate(data_sources, start=1):
        await send_progress_update(
            current_step=i,
            total_steps=len(data_sources),
            description=f"Fetching data from {source}"
        )
        await asyncio.sleep(0.5)
    
    await send_agent_completed(
        stage=AgentStage.DATA_INGESTION,
        details="Successfully ingested 1,234 time entries and 567 payroll records"
    )
    
    # Stage 2: Qualification
    await send_agent_started(
        stage=AgentStage.QUALIFICATION,
        details="Starting R&D qualification analysis"
    )
    
    # Simulate qualifying projects
    projects = ["Project Alpha", "Project Beta", "Project Gamma"]
    for i, project in enumerate(projects, start=1):
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.IN_PROGRESS,
            details=f"Analyzing project: {project}"
        )
        await asyncio.sleep(0.5)
    
    await send_agent_completed(
        stage=AgentStage.QUALIFICATION,
        details=f"Successfully qualified {len(projects)} projects"
    )
    
    # Stage 3: Audit Trail
    await send_agent_started(
        stage=AgentStage.AUDIT_TRAIL,
        details="Generating audit-ready documentation"
    )
    
    # Simulate report generation steps
    report_steps = [
        "Aggregating qualified data",
        "Generating project narratives",
        "Creating executive summary",
        "Formatting PDF report"
    ]
    for i, step in enumerate(report_steps, start=1):
        await send_progress_update(
            current_step=i,
            total_steps=len(report_steps),
            description=step
        )
        await asyncio.sleep(0.5)
    
    await send_agent_completed(
        stage=AgentStage.AUDIT_TRAIL,
        details="Audit report generated successfully"
    )
    
    # Send final summary
    await broadcast_custom_message(
        message_type="workflow_complete",
        total_credit=125000.50,
        qualified_projects=len(projects),
        report_path="/outputs/reports/rd_tax_credit_2024.pdf"
    )
    
    print("✓ Complete workflow finished")


async def example_error_handling():
    """Example: Error handling during agent execution"""
    print("\n=== Example 8: Error Handling ===")
    
    await send_agent_started(
        stage=AgentStage.DATA_INGESTION,
        details="Attempting to fetch data from Clockify"
    )
    
    try:
        # Simulate an API failure
        raise TimeoutError("Clockify API request timed out after 30 seconds")
        
    except Exception as e:
        import traceback
        
        # Send error notification
        await send_error_notification(
            error_type=ErrorType.API_CONNECTION,
            message=f"Data ingestion failed: {str(e)}",
            traceback=traceback.format_exc()
        )
        
        # Update agent status to error
        await send_agent_error(
            stage=AgentStage.DATA_INGESTION,
            details="Failed to connect to Clockify API after 3 retries"
        )
        
        print("✓ Error handled and notifications sent")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Status Broadcaster Usage Examples")
    print("=" * 60)
    
    # Note: These examples will work even without active WebSocket connections
    # The messages will be logged but not broadcast to any clients
    
    await example_basic_status_update()
    await example_agent_lifecycle()
    await example_progress_updates()
    await example_error_notification()
    await example_connection_monitoring()
    await example_custom_message()
    await example_complete_workflow()
    await example_error_handling()
    
    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
