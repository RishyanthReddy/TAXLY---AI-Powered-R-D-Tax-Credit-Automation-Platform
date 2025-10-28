"""
Database Models Usage Example

This script demonstrates how to use the database models for:
- Session state persistence
- Audit logging
- Database initialization

Requirements: 8.5
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.database_models import (
    initialize_database,
    create_session_state,
    log_action,
    SessionState,
    AuditLog,
    WorkflowStage,
    WorkflowStatus,
    AuditLogAction,
)


def main():
    """Demonstrate database model usage"""
    
    print("=" * 60)
    print("Database Models Usage Example")
    print("=" * 60)
    
    # Initialize database (creates tables if they don't exist)
    print("\n1. Initializing database...")
    db = initialize_database("sqlite:///./example_rd_tax_agent.db")
    print("   ✓ Database initialized with tables created")
    
    # Create a new session state
    print("\n2. Creating a new workflow session...")
    with db.get_session() as session:
        session_state = create_session_state(
            session=session,
            session_id="sess_demo_001",
            user_id="user_demo",
            tax_year=2024
        )
        print(f"   ✓ Session created: {session_state.session_id}")
        print(f"   - User: {session_state.user_id}")
        print(f"   - Tax Year: {session_state.tax_year}")
        print(f"   - Current Stage: {session_state.current_stage.value}")
        print(f"   - Status: {session_state.status.value}")
    
    # Log session creation
    print("\n3. Creating audit log entry...")
    with db.get_session() as session:
        audit_log = log_action(
            session=session,
            session_id="sess_demo_001",
            user_id="user_demo",
            action=AuditLogAction.SESSION_CREATED,
            stage=WorkflowStage.DATA_INGESTION,
            details={
                "tax_year": 2024,
                "created_via": "example_script"
            }
        )
        print(f"   ✓ Audit log created: ID {audit_log.log_id}")
        print(f"   - Action: {audit_log.action.value}")
        print(f"   - Timestamp: {audit_log.timestamp}")
        print(f"   - Details: {audit_log.details}")
    
    # Update session state (simulate data ingestion completion)
    print("\n4. Updating session state (data ingestion completed)...")
    with db.get_session() as session:
        # Retrieve existing session
        session_state = session.query(SessionState).filter_by(
            session_id="sess_demo_001"
        ).first()
        
        # Update state
        session_state.mark_stage_completed(WorkflowStage.DATA_INGESTION)
        session_state.ingested_data_count = 1234
        session_state.update_stage(WorkflowStage.QUALIFICATION, WorkflowStatus.IN_PROGRESS)
        session.commit()
        
        print(f"   ✓ Session updated")
        print(f"   - Data Ingestion Completed: {session_state.data_ingestion_completed}")
        print(f"   - Ingested Records: {session_state.ingested_data_count}")
        print(f"   - Current Stage: {session_state.current_stage.value}")
    
    # Log data ingestion completion
    print("\n5. Logging data ingestion completion...")
    with db.get_session() as session:
        log_action(
            session=session,
            session_id="sess_demo_001",
            user_id="user_demo",
            action=AuditLogAction.DATA_INGESTION_COMPLETED,
            stage=WorkflowStage.DATA_INGESTION,
            details={
                "records_ingested": 1234,
                "time_entries": 1000,
                "payroll_records": 234
            }
        )
        print("   ✓ Audit log created for data ingestion completion")
    
    # Simulate qualification completion
    print("\n6. Simulating qualification stage completion...")
    with db.get_session() as session:
        session_state = session.query(SessionState).filter_by(
            session_id="sess_demo_001"
        ).first()
        
        session_state.mark_stage_completed(WorkflowStage.QUALIFICATION)
        session_state.qualified_projects_count = 15
        session_state.update_stage(WorkflowStage.AUDIT_TRAIL, WorkflowStatus.IN_PROGRESS)
        session.commit()
        
        print(f"   ✓ Qualification completed")
        print(f"   - Qualified Projects: {session_state.qualified_projects_count}")
        print(f"   - Current Stage: {session_state.current_stage.value}")
    
    # Log qualification completion
    with db.get_session() as session:
        log_action(
            session=session,
            session_id="sess_demo_001",
            user_id="user_demo",
            action=AuditLogAction.QUALIFICATION_COMPLETED,
            stage=WorkflowStage.QUALIFICATION,
            details={
                "qualified_projects": 15,
                "total_qualified_hours": 5280,
                "estimated_credit": 125000.00
            }
        )
        print("   ✓ Audit log created for qualification completion")
    
    # Simulate report generation
    print("\n7. Simulating report generation...")
    with db.get_session() as session:
        session_state = session.query(SessionState).filter_by(
            session_id="sess_demo_001"
        ).first()
        
        session_state.mark_stage_completed(WorkflowStage.AUDIT_TRAIL)
        session_state.report_id = "report_2024_demo_001"
        session_state.update_stage(WorkflowStage.COMPLETED, WorkflowStatus.COMPLETED)
        session.commit()
        
        print(f"   ✓ Report generated")
        print(f"   - Report ID: {session_state.report_id}")
        print(f"   - Status: {session_state.status.value}")
    
    # Log report generation
    with db.get_session() as session:
        log_action(
            session=session,
            session_id="sess_demo_001",
            user_id="user_demo",
            action=AuditLogAction.REPORT_GENERATED,
            stage=WorkflowStage.AUDIT_TRAIL,
            details={
                "report_id": "report_2024_demo_001",
                "pdf_path": "./outputs/reports/report_2024_demo_001.pdf",
                "total_pages": 42
            }
        )
        print("   ✓ Audit log created for report generation")
    
    # Query and display all audit logs for this session
    print("\n8. Retrieving all audit logs for session...")
    with db.get_session() as session:
        logs = session.query(AuditLog).filter_by(
            session_id="sess_demo_001"
        ).order_by(AuditLog.timestamp).all()
        
        print(f"   ✓ Found {len(logs)} audit log entries:")
        for log in logs:
            print(f"   - [{log.timestamp.strftime('%H:%M:%S')}] {log.action.value}")
            if log.details:
                print(f"     Details: {log.details}")
    
    # Display final session state
    print("\n9. Final session state:")
    with db.get_session() as session:
        session_state = session.query(SessionState).filter_by(
            session_id="sess_demo_001"
        ).first()
        
        state_dict = session_state.to_dict()
        print("   " + "-" * 56)
        for key, value in state_dict.items():
            if value is not None and key != 'state_data':
                print(f"   {key:30s}: {value}")
        print("   " + "-" * 56)
    
    # Demonstrate error handling
    print("\n10. Demonstrating error handling...")
    with db.get_session() as session:
        session_state = session.query(SessionState).filter_by(
            session_id="sess_demo_001"
        ).first()
        
        # Simulate an error
        session_state.set_error("Simulated API connection failure")
        session.commit()
        
        print(f"   ✓ Error recorded")
        print(f"   - Status: {session_state.status.value}")
        print(f"   - Error: {session_state.error_message}")
        print(f"   - Is Resumable: {session_state.is_resumable()}")
    
    # Log the error
    with db.get_session() as session:
        log_action(
            session=session,
            session_id="sess_demo_001",
            user_id="user_demo",
            action=AuditLogAction.ERROR_OCCURRED,
            stage=WorkflowStage.AUDIT_TRAIL,
            details={
                "error_type": "APIConnectionError",
                "error_message": "Simulated API connection failure"
            },
            success=False,
            error_message="Simulated API connection failure"
        )
        print("   ✓ Error logged to audit trail")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("Database file: example_rd_tax_agent.db")
    print("=" * 60)


if __name__ == "__main__":
    main()
