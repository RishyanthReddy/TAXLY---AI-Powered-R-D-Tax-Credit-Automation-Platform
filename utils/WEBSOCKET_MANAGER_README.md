# WebSocket Connection Manager

## Overview

The WebSocket Connection Manager provides centralized management of WebSocket connections for real-time bidirectional communication between backend agents and frontend clients. It enables live status updates, progress tracking, and error notifications during agent execution.

**Requirements:** 5.2, 5.3

## Features

- **Connection Lifecycle Management**: Automatic handling of connection establishment and cleanup
- **Broadcasting**: Send messages to all connected clients simultaneously
- **Personal Messaging**: Send messages to specific clients
- **Error Handling**: Graceful handling of connection errors and disconnections
- **Active Connection Tracking**: Monitor the number of active connections
- **Type-Safe Messaging**: Integration with Pydantic models for structured messages

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ConnectionManager                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Active Connections List                     │    │
│  │  [WebSocket1, WebSocket2, WebSocket3, ...]         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Methods:                                                    │
│  • connect(websocket)         - Register new connection     │
│  • disconnect(websocket)      - Remove connection           │
│  • broadcast(message)         - Send to all clients         │
│  • send_personal_message()    - Send to specific client     │
│  • broadcast_status_update()  - Broadcast status            │
│  • broadcast_error()          - Broadcast error             │
│  • broadcast_progress()       - Broadcast progress          │
│  • get_connection_count()     - Get active count            │
│  • close_all_connections()    - Shutdown all                │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Setup

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from utils.websocket_manager import ConnectionManager

app = FastAPI()
manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages
            await manager.send_personal_message(
                {"type": "echo", "message": data},
                websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### Broadcasting Status Updates

```python
from models.websocket_models import (
    StatusUpdateMessage,
    AgentStage,
    AgentStatus
)

# During agent execution
status = StatusUpdateMessage(
    stage=AgentStage.QUALIFICATION,
    status=AgentStatus.IN_PROGRESS,
    details="Analyzing project: Alpha Development"
)

await manager.broadcast_status_update(status)
```

### Broadcasting Progress Updates

```python
from models.websocket_models import ProgressMessage

# During batch processing
for i, project in enumerate(projects, 1):
    # Process project
    process_project(project)
    
    # Send progress update
    progress = ProgressMessage(
        current_step=i,
        total_steps=len(projects),
        percentage=(i / len(projects)) * 100,
        description=f"Processing project {i} of {len(projects)}"
    )
    
    await manager.broadcast_progress(progress)
```

### Broadcasting Error Messages

```python
from models.websocket_models import ErrorMessage, ErrorType

try:
    # Agent operation
    result = await fetch_data()
except Exception as e:
    # Broadcast error to all clients
    error = ErrorMessage(
        error_type=ErrorType.API_CONNECTION,
        message=f"Failed to fetch data: {str(e)}",
        traceback=traceback.format_exc()
    )
    
    await manager.broadcast_error(error)
```

### Integration with Agents

```python
from agents.data_ingestion_agent import DataIngestionAgent
from utils.websocket_manager import connection_manager

async def run_data_ingestion(date_range, credentials):
    """Run data ingestion with real-time updates"""
    
    # Notify start
    await connection_manager.broadcast_status_update(
        StatusUpdateMessage(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.IN_PROGRESS,
            details="Starting data ingestion"
        )
    )
    
    try:
        # Run agent
        agent = DataIngestionAgent()
        result = await agent.run(date_range, credentials)
        
        # Notify completion
        await connection_manager.broadcast_status_update(
            StatusUpdateMessage(
                stage=AgentStage.DATA_INGESTION,
                status=AgentStatus.COMPLETED,
                details=f"Ingested {len(result)} records"
            )
        )
        
        return result
        
    except Exception as e:
        # Notify error
        await connection_manager.broadcast_error(
            ErrorMessage(
                error_type=ErrorType.AGENT_EXECUTION,
                message=str(e)
            )
        )
        raise
```

## Message Types

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

### Connection Established Message

```json
{
  "type": "connection_established",
  "message": "Connected to R&D Tax Credit Automation Agent",
  "timestamp": "2025-01-15T10:30:45.123456",
  "connection_id": 140234567890123
}
```

## Frontend Integration

### JavaScript/TypeScript Client

```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:8000/ws");

// Handle connection open
ws.onopen = (event) => {
    console.log("WebSocket connected");
};

// Handle incoming messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case "status_update":
            updateWorkflowVisualization(data);
            break;
        case "progress":
            updateProgressBar(data);
            break;
        case "error":
            showErrorNotification(data);
            break;
        case "connection_established":
            console.log("Connection established:", data.message);
            break;
    }
};

// Handle connection close
ws.onclose = (event) => {
    console.log("WebSocket disconnected");
    // Implement reconnection logic
};

// Handle errors
ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};
```

### React Hook Example

```typescript
import { useEffect, useState } from 'react';

interface WebSocketMessage {
    type: string;
    [key: string]: any;
}

export function useWebSocket(url: string) {
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [messages, setMessages] = useState<WebSocketMessage[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    
    useEffect(() => {
        const websocket = new WebSocket(url);
        
        websocket.onopen = () => {
            setIsConnected(true);
            console.log("WebSocket connected");
        };
        
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMessages(prev => [...prev, data]);
        };
        
        websocket.onclose = () => {
            setIsConnected(false);
            console.log("WebSocket disconnected");
        };
        
        setWs(websocket);
        
        return () => {
            websocket.close();
        };
    }, [url]);
    
    return { ws, messages, isConnected };
}
```

## API Reference

### ConnectionManager Class

#### `__init__()`
Initialize the connection manager with an empty connection list.

#### `async connect(websocket: WebSocket) -> None`
Accept and register a new WebSocket connection.

**Parameters:**
- `websocket`: The WebSocket connection to register

**Raises:**
- `Exception`: If connection acceptance fails

#### `disconnect(websocket: WebSocket) -> None`
Remove a WebSocket connection from the active connections list.

**Parameters:**
- `websocket`: The WebSocket connection to remove

#### `async send_personal_message(message: Dict[str, Any], websocket: WebSocket) -> None`
Send a message to a specific WebSocket client.

**Parameters:**
- `message`: Dictionary containing the message data
- `websocket`: The target WebSocket connection

#### `async broadcast(message: Dict[str, Any]) -> None`
Broadcast a message to all active WebSocket connections.

**Parameters:**
- `message`: Dictionary containing the message data to broadcast

#### `async broadcast_status_update(status_message: StatusUpdateMessage) -> None`
Broadcast a status update message to all connected clients.

**Parameters:**
- `status_message`: StatusUpdateMessage Pydantic model instance

#### `async broadcast_error(error_message: ErrorMessage) -> None`
Broadcast an error message to all connected clients.

**Parameters:**
- `error_message`: ErrorMessage Pydantic model instance

#### `async broadcast_progress(progress_message: ProgressMessage) -> None`
Broadcast a progress update message to all connected clients.

**Parameters:**
- `progress_message`: ProgressMessage Pydantic model instance

#### `get_connection_count() -> int`
Get the number of active WebSocket connections.

**Returns:**
- `int`: Number of active connections

#### `async close_all_connections() -> None`
Close all active WebSocket connections gracefully.

## Error Handling

The ConnectionManager handles various error scenarios:

1. **Connection Errors**: Logged and connection removed from active list
2. **Disconnections**: Automatically detected and cleaned up
3. **Broadcast Failures**: Individual client failures don't affect other clients
4. **Message Send Errors**: Logged with client identification

## Best Practices

1. **Always use try-except blocks** when handling WebSocket connections
2. **Disconnect on WebSocketDisconnect exception** to clean up resources
3. **Use typed message models** (StatusUpdateMessage, etc.) for consistency
4. **Monitor connection count** to detect potential issues
5. **Implement reconnection logic** on the frontend
6. **Close connections gracefully** during shutdown

## Performance Considerations

- **Concurrent Broadcasting**: Messages are sent sequentially to avoid race conditions
- **Connection Cleanup**: Failed connections are automatically removed
- **Memory Management**: No message history is stored (stateless)
- **Scalability**: For high-scale deployments, consider Redis pub/sub

## Testing

Run the example server to test WebSocket functionality:

```bash
cd rd_tax_agent
python examples/websocket_manager_usage_example.py
```

Then open http://localhost:8000 in your browser and use the test endpoints:

- `POST /simulate/status-update` - Test status updates
- `POST /simulate/error` - Test error broadcasting
- `POST /simulate/progress` - Test progress updates
- `POST /simulate/agent-workflow` - Test complete workflow
- `GET /connections` - Check active connections

## Related Components

- **WebSocket Models**: `models/websocket_models.py`
- **FastAPI Main**: `main.py` (WebSocket endpoint)
- **Status Broadcaster**: `utils/status_broadcaster.py` (Task 127)
- **Frontend Client**: `frontend/src/utils/websocketClient.ts` (Task 136)

## Requirements Satisfied

- **5.2**: Real-time status updates via WebSocket
- **5.3**: Error handling and connection management
