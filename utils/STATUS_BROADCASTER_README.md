# Status Broadcaster

## Overview

The Status Broadcaster module provides a high-level interface for broadcasting status updates, error notifications, and progress messages to all connected WebSocket clients. It simplifies real-time communication between backend agents and the frontend UI.

## Features

- **Simple API**: Easy-to-use functions for common status update scenarios
- **Type Safety**: Full Pydantic model validation for all messages
- **Automatic Logging**: All broadcasts are logged for debugging and audit trails
- **Error Handling**: Graceful error handling that doesn't break agent execution
- **Convenience Functions**: Pre-configured functions for common agent lifecycle events

## Requirements

- Requirements: 5.2, 5.3

## Core Functions

### send_status_update()

Primary function for broadcasting agent status changes.

```python
from utils.status_broadcaster import send_status_update
from models.websocket_models import AgentStage, AgentStatus

await send_status_update(
    stage=AgentStage.QUALIFICATION,
    status=AgentStatus.IN_PROGRESS,
    details="Analyzing project: Alpha Development"
)
```

**Parameters:**
- `stage` (AgentStage): Pipeline stage (data_ingestion, qualification, audit_trail)
- `status` (AgentStatus): Execution status (pending, in_progress, completed, error)
- `details` (str): Human-readable status description

### send_error_notification()

Broadcast error messages to all connected clients.

```python
from utils.status_broadcaster import send_error_notification
from models.websocket_models import ErrorType
import traceback

try:
    # Some operation that might fail
    result = await risky_operation()
except Exception as e:
    await send_error_notification(
        error_type=ErrorType.API_CONNECTION,
        message=f"Failed to connect to API: {str(e)}",
        traceback=traceback.format_exc()
    )
```

**Parameters:**
- `error_type` (ErrorType): Category of error
- `message` (str): Human-readable error message
- `traceback` (Optional[str]): Full error traceback for debugging

### send_progress_update()

Send progress updates during long-running operations.

```python
from utils.status_broadcaster import send_progress_update

total_projects = 50
for i, project in enumerate(projects, start=1):
    # Process project
    process_project(project)
    
    # Send progress update
    await send_progress_update(
        current_step=i,
        total_steps=total_projects,
        description=f"Processing project {i} of {total_projects}"
    )
```

**Parameters:**
- `current_step` (int): Current step number
- `total_steps` (int): Total number of steps
- `description` (Optional[str]): Progress description

## Convenience Functions

### Agent Lifecycle Functions

```python
from utils.status_broadcaster import (
    send_agent_started,
    send_agent_completed,
    send_agent_error
)
from models.websocket_models import AgentStage

# Agent started
await send_agent_started(
    stage=AgentStage.DATA_INGESTION,
    details="Starting data ingestion from Clockify and Unified.to"
)

# Agent completed
await send_agent_completed(
    stage=AgentStage.DATA_INGESTION,
    details="Successfully ingested 1,234 time entries"
)

# Agent error
await send_agent_error(
    stage=AgentStage.DATA_INGESTION,
    details="Failed to connect to Clockify API"
)
```

### Connection Monitoring

```python
from utils.status_broadcaster import get_active_connection_count

# Check if any clients are connected
if get_active_connection_count() > 0:
    # Perform expensive status update preparation
    await send_status_update(...)
else:
    # Skip status updates if no clients are listening
    pass
```

### Custom Messages

```python
from utils.status_broadcaster import broadcast_custom_message

# Broadcast application-specific messages
await broadcast_custom_message(
    message_type="credit_calculation",
    total_credit=125000.50,
    qualified_projects=15,
    tax_year=2024
)
```

## Integration with Agents

### Data Ingestion Agent Example

```python
from agents.data_ingestion_agent import DataIngestionAgent
from utils.status_broadcaster import (
    send_agent_started,
    send_agent_completed,
    send_progress_update
)
from models.websocket_models import AgentStage

async def run_data_ingestion():
    # Notify start
    await send_agent_started(
        stage=AgentStage.DATA_INGESTION,
        details="Fetching time entries from Clockify"
    )
    
    # Run agent
    agent = DataIngestionAgent()
    time_entries = await agent.fetch_time_entries()
    
    # Send progress updates
    total = len(time_entries)
    for i, entry in enumerate(time_entries, start=1):
        # Process entry
        await agent.process_entry(entry)
        
        # Update progress every 10 entries
        if i % 10 == 0:
            await send_progress_update(
                current_step=i,
                total_steps=total,
                description=f"Processed {i} of {total} time entries"
            )
    
    # Notify completion
    await send_agent_completed(
        stage=AgentStage.DATA_INGESTION,
        details=f"Successfully ingested {total} time entries"
    )
```

### Qualification Agent Example

```python
from agents.qualification_agent import QualificationAgent
from utils.status_broadcaster import (
    send_status_update,
    send_error_notification
)
from models.websocket_models import AgentStage, AgentStatus, ErrorType

async def run_qualification(projects):
    agent = QualificationAgent()
    
    for project in projects:
        # Update status for current project
        await send_status_update(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.IN_PROGRESS,
            details=f"Analyzing project: {project.name}"
        )
        
        try:
            # Qualify project
            result = await agent.qualify_project(project)
            
        except Exception as e:
            # Send error notification
            await send_error_notification(
                error_type=ErrorType.AGENT_EXECUTION,
                message=f"Failed to qualify project {project.name}: {str(e)}"
            )
            continue
    
    # Final status
    await send_status_update(
        stage=AgentStage.QUALIFICATION,
        status=AgentStatus.COMPLETED,
        details=f"Qualified {len(projects)} projects"
    )
```

## Message Format

All messages broadcast to WebSocket clients follow this structure:

### Status Update Message
```json
{
  "type": "status_update",
  "stage": "qualification",
  "status": "in_progress",
  "details": "Analyzing project: Alpha Development",
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

### Error Message
```json
{
  "type": "error",
  "error_type": "api_connection",
  "message": "Failed to connect to Clockify API after 3 retries",
  "traceback": "Traceback (most recent call last):\n  File...",
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

### Progress Message
```json
{
  "type": "progress",
  "current_step": 15,
  "total_steps": 50,
  "percentage": 30.0,
  "description": "Processing project 15 of 50",
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

## Error Handling

The status broadcaster is designed to fail gracefully:

1. **Validation Errors**: Invalid parameters are logged and raised as ValueError
2. **Broadcast Errors**: Errors during broadcasting are logged but don't raise exceptions
3. **No Connected Clients**: Messages are logged even if no clients are connected
4. **Disconnected Clients**: Automatically removed from the connection pool

This ensures that status update failures don't break agent execution.

## Logging

All status broadcasts are logged with appropriate levels:

- **INFO**: Status updates, progress updates
- **ERROR**: Error notifications, broadcast failures
- **DEBUG**: Successful broadcasts, connection counts

Example log output:
```
2025-01-15 10:30:45 - utils.status_broadcaster - INFO - Status Update - Stage: qualification, Status: in_progress, Details: Analyzing project: Alpha Development
2025-01-15 10:30:45 - utils.status_broadcaster - DEBUG - Status update broadcast successful to 3 clients
```

## Testing

See `tests/test_status_broadcaster.py` for comprehensive unit tests covering:
- Status update broadcasting
- Error notification broadcasting
- Progress update broadcasting
- Convenience functions
- Connection count monitoring
- Custom message broadcasting
- Error handling scenarios

## Dependencies

- `utils.logger`: Structured logging
- `utils.websocket_manager`: WebSocket connection management
- `models.websocket_models`: Message models and enums

## Best Practices

1. **Use Convenience Functions**: Prefer `send_agent_started()` over manual `send_status_update()` calls
2. **Include Context**: Provide detailed descriptions in status updates
3. **Progress Updates**: Send progress updates for operations > 5 seconds
4. **Error Details**: Include full tracebacks in error notifications for debugging
5. **Check Connections**: Use `get_active_connection_count()` before expensive operations
6. **Don't Block**: Status updates are async - always await them
7. **Fail Gracefully**: Don't wrap status updates in try-except unless necessary

## Related Modules

- `utils/websocket_manager.py`: Low-level WebSocket connection management
- `models/websocket_models.py`: Message model definitions
- `main.py`: WebSocket endpoint implementation
