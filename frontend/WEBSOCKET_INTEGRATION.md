# WebSocket Integration Documentation

## Overview

The frontend now includes real-time WebSocket integration with the backend server, enabling live updates during workflow execution. This replaces the previous simulation-based approach with actual backend communication.

**Requirements**: 5.2, 5.3

## Architecture

### Backend WebSocket Server

- **Endpoint**: `ws://localhost:8000/ws`
- **Framework**: FastAPI WebSocket
- **Manager**: `ConnectionManager` class in `utils/websocket_manager.py`
- **Broadcaster**: `status_broadcaster.py` for sending updates

### Frontend WebSocket Client

- **Manager**: `WebSocketManager` class in `js/websocket.js`
- **Integration**: `workflow.js` uses WebSocket for real-time updates
- **Test Page**: `test_websocket.html` for connection testing

## Message Types

### 1. Connection Established

Sent by backend when client connects successfully.

```json
{
  "type": "connection_established",
  "message": "Connected to R&D Tax Credit Automation Agent",
  "timestamp": "2025-01-15T10:30:45.123456",
  "connection_id": 12345
}
```

### 2. Status Update

Sent during agent execution to update workflow stage status.

```json
{
  "type": "status_update",
  "stage": "data_ingestion",
  "status": "in_progress",
  "details": "Fetching time entries from Clockify...",
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

**Stage Values**:
- `data_ingestion` - Data Ingestion Agent
- `qualification` - Qualification Agent
- `audit_trail` - Audit Trail Agent

**Status Values**:
- `pending` - Stage not started
- `in_progress` - Stage currently executing
- `completed` - Stage finished successfully
- `error` - Stage encountered an error

### 3. Error Message

Sent when an error occurs during execution.

```json
{
  "type": "error",
  "error_type": "api_connection",
  "message": "Failed to connect to Clockify API after 3 retries",
  "traceback": "Traceback (most recent call last)...",
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

**Error Types**:
- `api_connection` - External API connection failure
- `validation` - Data validation error
- `rag_retrieval` - RAG knowledge base error
- `agent_execution` - Agent runtime error
- `pdf_generation` - PDF generation error
- `unknown` - Unclassified error

### 4. Progress Update

Sent during long-running operations to show incremental progress.

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

### 5. Echo (Test)

Echo message for testing connectivity.

```json
{
  "type": "echo",
  "message": "Server received: test message",
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

## Frontend Implementation

### WebSocketManager Class

Located in `js/websocket.js`, this class manages the WebSocket connection lifecycle.

**Key Features**:
- Automatic connection management
- Reconnection with exponential backoff
- Event-driven message handling
- Connection state tracking

**Usage Example**:

```javascript
// Create WebSocket manager
const wsManager = new WebSocketManager('ws://localhost:8000/ws');

// Set up event handlers
wsManager.onStatusUpdate = (update) => {
    console.log('Status:', update.stage, update.status, update.details);
};

wsManager.onError = (error) => {
    console.error('Error:', error.message);
};

wsManager.onProgress = (progress) => {
    console.log('Progress:', progress.percentage + '%');
};

wsManager.onConnectionChange = (isConnected) => {
    console.log('Connected:', isConnected);
};

// Connect to server
wsManager.connect();

// Send message
wsManager.send({ type: 'test', message: 'Hello!' });

// Close connection
wsManager.close();
```

### Workflow Integration

The `workflow.js` file integrates WebSocket updates with the workflow visualization.

**Stage Mapping**:

Backend stages are mapped to frontend visualization stages:

```javascript
const STAGE_MAPPING = {
    'data_ingestion': { id: 1, name: 'Data Ingestion' },
    'qualification': { id: 3, name: 'Project Qualification' },
    'audit_trail': { id: 6, name: 'PDF Generation' }
};
```

**Status Update Handler**:

```javascript
function handleStatusUpdate(update) {
    const { stage, status, details } = update;
    const stageInfo = STAGE_MAPPING[stage];
    
    // Update stage visualization
    updateStageStatus(stageInfo.id, status, details);
    
    // Log the update
    addLogEntry(status === 'error' ? 'error' : 'success', 
                `${stageInfo.name}: ${details}`);
}
```

## Connection Management

### Automatic Reconnection

The WebSocket manager automatically attempts to reconnect on connection loss:

- **Max Attempts**: 5
- **Initial Delay**: 2 seconds
- **Max Delay**: 30 seconds
- **Backoff**: Exponential (2x multiplier)

### Connection States

The connection can be in one of four states:

1. **CONNECTING (0)**: Connection is being established
2. **OPEN (1)**: Connection is active and ready
3. **CLOSING (2)**: Connection is being closed
4. **CLOSED (3)**: Connection is closed

### Error Handling

Connection errors are handled gracefully:

- Automatic reconnection attempts
- User notification via UI
- Fallback to simulation mode if backend unavailable
- Detailed error logging

## Testing

### Test Page

Open `test_websocket.html` in a browser to test the WebSocket connection:

1. Start the backend server: `python main.py`
2. Open `http://localhost:8000/frontend/test_websocket.html`
3. Observe connection status and messages
4. Use controls to test connection/disconnection
5. Send test messages to verify bidirectional communication

### Manual Testing

1. **Start Backend**:
   ```bash
   cd rd_tax_agent
   python main.py
   ```

2. **Open Workflow Page**:
   ```
   http://localhost:8000/frontend/workflow.html
   ```

3. **Verify Connection**:
   - Backend status should show "Connected" (green)
   - Log should show "Connected to backend successfully"

4. **Trigger Workflow**:
   - Click "Start Workflow" button
   - Observe real-time stage updates
   - Check log for detailed messages

### Backend Testing

Test the backend WebSocket endpoint directly:

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Receive welcome message
        message = await websocket.recv()
        print(f"Received: {message}")
        
        # Send test message
        await websocket.send(json.dumps({
            "type": "test",
            "message": "Hello from Python!"
        }))
        
        # Receive echo
        response = await websocket.recv()
        print(f"Echo: {response}")

asyncio.run(test_websocket())
```

## Troubleshooting

### Connection Fails

**Problem**: WebSocket connection fails to establish

**Solutions**:
1. Verify backend is running: `python main.py`
2. Check backend logs for errors
3. Verify WebSocket URL is correct: `ws://localhost:8000/ws`
4. Check CORS configuration in `main.py`
5. Ensure no firewall blocking port 8000

### No Messages Received

**Problem**: Connected but no status updates

**Solutions**:
1. Verify workflow is actually running
2. Check backend logs for status broadcast calls
3. Ensure `send_status_update()` is being called in agents
4. Verify message handlers are set up correctly
5. Check browser console for JavaScript errors

### Frequent Disconnections

**Problem**: Connection drops frequently

**Solutions**:
1. Check network stability
2. Increase reconnection delay
3. Verify backend is not crashing
4. Check for memory leaks in backend
5. Monitor backend resource usage

### Messages Not Updating UI

**Problem**: Messages received but UI not updating

**Solutions**:
1. Check message handler functions are defined
2. Verify stage mapping is correct
3. Check for JavaScript errors in console
4. Ensure DOM elements exist with correct IDs
5. Verify CSS classes are applied correctly

## Performance Considerations

### Message Frequency

- Status updates: ~1-5 per second during active execution
- Progress updates: ~10-20 per second during batch operations
- Error messages: As needed
- Connection overhead: Minimal (~1KB per message)

### Scalability

- Single backend can handle 100+ concurrent connections
- Each connection uses ~10KB memory
- Message broadcasting is O(n) where n = number of connections
- Consider load balancing for >1000 concurrent users

### Optimization Tips

1. **Throttle Updates**: Limit status updates to significant changes
2. **Batch Messages**: Combine multiple updates when possible
3. **Compress Data**: Use shorter field names for high-frequency messages
4. **Connection Pooling**: Reuse connections when possible
5. **Lazy Loading**: Only connect when workflow page is active

## Security Considerations

### Authentication

Currently, WebSocket connections are unauthenticated. For production:

1. Implement token-based authentication
2. Validate tokens on connection
3. Use secure WebSocket (wss://) in production
4. Implement rate limiting per connection
5. Add connection timeout policies

### Data Validation

All incoming messages should be validated:

```javascript
function validateMessage(data) {
    if (!data.type) return false;
    if (!data.timestamp) return false;
    // Add more validation as needed
    return true;
}
```

### CORS Configuration

Ensure CORS is properly configured in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Future Enhancements

1. **Authentication**: Add JWT token authentication
2. **Compression**: Implement message compression for large payloads
3. **Persistence**: Store connection state for reconnection
4. **Multiplexing**: Support multiple workflows per connection
5. **Binary Protocol**: Use binary format for better performance
6. **Heartbeat**: Implement ping/pong for connection health
7. **Message Queue**: Add message queuing for offline support
8. **Encryption**: End-to-end encryption for sensitive data

## References

- **Backend WebSocket Manager**: `rd_tax_agent/utils/websocket_manager.py`
- **Backend Status Broadcaster**: `rd_tax_agent/utils/status_broadcaster.py`
- **Backend Main App**: `rd_tax_agent/main.py` (WebSocket endpoint)
- **Frontend WebSocket Manager**: `rd_tax_agent/frontend/js/websocket.js`
- **Frontend Workflow Integration**: `rd_tax_agent/frontend/js/workflow.js`
- **Test Page**: `rd_tax_agent/frontend/test_websocket.html`
- **WebSocket Models**: `rd_tax_agent/models/websocket_models.py`

## Support

For issues or questions:
1. Check backend logs: `rd_tax_agent/logs/agent_*.log`
2. Check browser console for JavaScript errors
3. Review this documentation
4. Test with `test_websocket.html` page
5. Verify backend is running and accessible
