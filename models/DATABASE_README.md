# Database Models Documentation

This document describes the database models used for workflow state persistence and audit logging in the R&D Tax Credit Automation Agent.

## Overview

The database layer provides:
- **Session State Persistence**: Resume capability for interrupted workflows
- **Audit Logging**: Immutable compliance tracking for IRS audit defense
- **Type Safety**: SQLAlchemy ORM with full type hints

## Requirements

- SQLAlchemy 2.0.36+
- Python 3.10+

## Database Models

### SessionState

Stores the current state of a user's R&D tax credit workflow session.

**Key Fields:**
- `session_id`: Unique identifier for the workflow session
- `user_id`: User/client identifier
- `tax_year`: Tax year for the R&D credit claim
- `current_stage`: Current workflow stage (data_ingestion, qualification, audit_trail)
- `status`: Execution status (pending, in_progress, completed, error, paused)
- `ingested_data_count`: Number of records ingested
- `qualified_projects_count`: Number of projects qualified
- `report_id`: Generated report identifier
- `state_data`: JSON field for intermediate results

**Methods:**
- `update_stage(stage, status)`: Update workflow stage and status
- `mark_stage_completed(stage)`: Mark a stage as completed
- `set_error(error_message)`: Set error status
- `is_resumable()`: Check if session can be resumed
- `to_dict()`: Convert to dictionary for JSON serialization

### AuditLog

Maintains an immutable record of all system actions for compliance tracking.

**Key Fields:**
- `log_id`: Unique identifier (auto-increment)
- `session_id`: Associated workflow session
- `user_id`: User who performed the action
- `action`: Type of action (session_created, qualification_completed, etc.)
- `timestamp`: When the action occurred
- `stage`: Workflow stage when action occurred
- `details`: JSON field with action-specific details
- `success`: Whether the action completed successfully
- `error_message`: Error details if action failed

**Methods:**
- `create_log(...)`: Factory method to create audit log entries
- `to_dict()`: Convert to dictionary for JSON serialization

## Database Configuration

### DatabaseConfig

Manages database connections and session lifecycle.

**Initialization:**
```python
from models.database_models import DatabaseConfig

# SQLite (development)
db = DatabaseConfig("sqlite:///./rd_tax_agent.db")

# PostgreSQL (production)
db = DatabaseConfig("postgresql://user:pass@localhost/rd_tax_agent")

# MySQL (production)
db = DatabaseConfig("mysql+pymysql://user:pass@localhost/rd_tax_agent")
```

**Methods:**
- `create_tables()`: Create all database tables
- `drop_tables()`: Drop all tables (WARNING: deletes all data)
- `get_session()`: Context manager for database sessions
- `get_session_direct()`: Get session without context manager

## Usage Examples

### Initialize Database

```python
from models.database_models import initialize_database

# Initialize with default SQLite
db = initialize_database()

# Initialize with custom database URL
db = initialize_database("postgresql://user:pass@localhost/rd_tax_agent")
```

### Create Session State

```python
from models.database_models import create_session_state

with db.get_session() as session:
    session_state = create_session_state(
        session=session,
        session_id="sess_123abc",
        user_id="user_456",
        tax_year=2024
    )
    print(f"Created session: {session_state.session_id}")
```

### Update Session State

```python
from models.database_models import SessionState, WorkflowStage, WorkflowStatus

with db.get_session() as session:
    # Retrieve existing session
    session_state = session.query(SessionState).filter_by(
        session_id="sess_123abc"
    ).first()
    
    # Update stage
    session_state.update_stage(WorkflowStage.QUALIFICATION, WorkflowStatus.IN_PROGRESS)
    
    # Mark stage completed
    session_state.mark_stage_completed(WorkflowStage.DATA_INGESTION)
    
    # Update metrics
    session_state.ingested_data_count = 1234
    session_state.qualified_projects_count = 15
    
    session.commit()
```

### Create Audit Log

```python
from models.database_models import log_action, AuditLogAction, WorkflowStage

with db.get_session() as session:
    audit_log = log_action(
        session=session,
        session_id="sess_123abc",
        user_id="user_456",
        action=AuditLogAction.QUALIFICATION_COMPLETED,
        stage=WorkflowStage.QUALIFICATION,
        details={
            "qualified_projects": 15,
            "total_qualified_hours": 5280,
            "estimated_credit": 125000.00
        }
    )
    print(f"Created audit log: {audit_log.log_id}")
```

### Query Audit Logs

```python
from models.database_models import AuditLog

with db.get_session() as session:
    # Get all logs for a session
    logs = session.query(AuditLog).filter_by(
        session_id="sess_123abc"
    ).order_by(AuditLog.timestamp).all()
    
    for log in logs:
        print(f"[{log.timestamp}] {log.action.value}")
        if log.details:
            print(f"  Details: {log.details}")
```

### Handle Errors

```python
from models.database_models import SessionState, AuditLogAction

with db.get_session() as session:
    session_state = session.query(SessionState).filter_by(
        session_id="sess_123abc"
    ).first()
    
    # Record error
    session_state.set_error("API connection failed")
    session.commit()
    
    # Log error to audit trail
    log_action(
        session=session,
        session_id="sess_123abc",
        user_id="user_456",
        action=AuditLogAction.ERROR_OCCURRED,
        details={"error_type": "APIConnectionError"},
        success=False,
        error_message="API connection failed"
    )
```

### Resume Workflow

```python
from models.database_models import SessionState

with db.get_session() as session:
    # Find resumable sessions
    resumable_sessions = session.query(SessionState).filter(
        SessionState.status.in_(['paused', 'error', 'in_progress'])
    ).all()
    
    for sess in resumable_sessions:
        if sess.is_resumable():
            print(f"Session {sess.session_id} can be resumed")
            print(f"  Last stage: {sess.current_stage.value}")
            print(f"  Status: {sess.status.value}")
```

## Enumerations

### WorkflowStage
- `DATA_INGESTION`: Data collection from APIs
- `QUALIFICATION`: R&D qualification analysis
- `AUDIT_TRAIL`: Report generation
- `COMPLETED`: Workflow finished

### WorkflowStatus
- `PENDING`: Not yet started
- `IN_PROGRESS`: Currently executing
- `COMPLETED`: Successfully finished
- `ERROR`: Failed with error
- `PAUSED`: Temporarily paused

### AuditLogAction
- `SESSION_CREATED`: New session started
- `DATA_INGESTION_STARTED`: Data ingestion began
- `DATA_INGESTION_COMPLETED`: Data ingestion finished
- `QUALIFICATION_STARTED`: Qualification began
- `QUALIFICATION_COMPLETED`: Qualification finished
- `AUDIT_TRAIL_STARTED`: Report generation began
- `AUDIT_TRAIL_COMPLETED`: Report generation finished
- `REPORT_GENERATED`: PDF report created
- `REPORT_DOWNLOADED`: Report downloaded by user
- `USER_CLASSIFICATION`: User classified project as R&D
- `ERROR_OCCURRED`: Error during execution
- `API_CALL`: External API called
- `RAG_QUERY`: RAG system queried
- `LLM_INFERENCE`: LLM inference performed

## Production Considerations

### Database Selection

**Development:**
- SQLite: Simple, file-based, no setup required
- Good for testing and local development

**Production:**
- PostgreSQL: Recommended for production
- MySQL: Alternative production option
- Ensure proper connection pooling and timeout settings

### Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost/rd_tax_agent",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)
```

### Migrations

For production, use Alembic for database migrations:

```bash
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Backup and Recovery

- Regular database backups (daily recommended)
- Point-in-time recovery for audit compliance
- Immutable audit logs (never delete)
- Archive old sessions after retention period

### Security

- Use environment variables for database credentials
- Enable SSL/TLS for database connections
- Implement row-level security if needed
- Regular security audits
- Encrypt sensitive data in `state_data` JSON field

## Testing

Run the example script to verify database functionality:

```bash
cd rd_tax_agent
python examples/database_usage_example.py
```

This will create a test database and demonstrate all database operations.

## Integration with Agents

The database models integrate with the agent workflow:

1. **Data Ingestion Agent**: Creates session state, logs ingestion actions
2. **Qualification Agent**: Updates session with qualified projects, logs qualification decisions
3. **Audit Trail Agent**: Marks workflow complete, logs report generation
4. **FastAPI Backend**: Provides session state to frontend, enables resume capability

## Troubleshooting

### Connection Issues

```python
# Test database connection
try:
    db = DatabaseConfig("postgresql://user:pass@localhost/rd_tax_agent")
    db.create_tables()
    print("Database connection successful")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Migration Issues

If tables don't match models, drop and recreate (development only):

```python
db = DatabaseConfig("sqlite:///./rd_tax_agent.db")
db.drop_tables()  # WARNING: Deletes all data
db.create_tables()
```

### Query Performance

Add indexes for frequently queried fields:

```python
from sqlalchemy import Index

# Add index to SessionState
Index('idx_session_user_tax_year', SessionState.user_id, SessionState.tax_year)

# Add index to AuditLog
Index('idx_audit_session_timestamp', AuditLog.session_id, AuditLog.timestamp)
```

## References

- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Requirements: 8.5 (Logging and audit trail)
- Design Document: See `design.md` for architecture details
