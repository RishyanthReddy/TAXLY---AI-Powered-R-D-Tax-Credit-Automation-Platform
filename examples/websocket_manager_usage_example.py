"""
WebSocket Connection Manager Usage Example

This example demonstrates how to use the ConnectionManager class
for real-time communication between backend agents and frontend clients.

Requirements: 5.2, 5.3
"""

import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from utils.websocket_manager import ConnectionManager
from models.websocket_models import (
    StatusUpdateMessage,
    ErrorMessage,
    ProgressMessage,
    AgentStage,
    AgentStatus,
    ErrorType
)


# Initialize FastAPI app and connection manager
app = FastAPI()
manager = ConnectionManager()


# HTML client for testing
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Test Client</title>
    </head>
    <body>
        <h1>WebSocket Connection Manager Test</h1>
        <div id="status">Disconnected</div>
        <div id="messages"></div>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            
            ws.onopen = function(event) {
                document.getElementById("status").innerHTML = "Connected";
            };
            
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var message = document.createElement('div');
                var data = JSON.parse(event.data);
                message.innerHTML = '<strong>' + data.type + ':</strong> ' + JSON.stringify(data);
                messages.appendChild(message);
            };
            
            ws.onclose = function(event) {
                document.getElementById("status").innerHTML = "Disconnected";
            };
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    """Serve test HTML client"""
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication.
    
    Example usage:
        # Connect from JavaScript
        const ws = new WebSocket("ws://localhost:8000/ws");
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Received:", data);
        };
    """
    await manager.connect(websocket)
    
    try:
        # Keep connection alive and listen for messages
        while True:
            data = await websocket.receive_text()
            print(f"Received from client: {data}")
            
            # Echo back to the specific client
            await manager.send_personal_message(
                {"type": "echo", "message": data},
                websocket
            )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")


@app.post("/simulate/status-update")
async def simulate_status_update():
    """
    Simulate broadcasting a status update to all connected clients.
    
    Example:
        curl -X POST http://localhost:8000/simulate/status-update
    """
    status_message = StatusUpdateMessage(
        stage=AgentStage.QUALIFICATION,
        status=AgentStatus.IN_PROGRESS,
        details="Analyzing project: Alpha Development"
    )
    
    await manager.broadcast_status_update(status_message)
    
    return {
        "message": "Status update broadcast",
        "active_connections": manager.get_connection_count()
    }


@app.post("/simulate/error")
async def simulate_error():
    """
    Simulate broadcasting an error message to all connected clients.
    
    Example:
        curl -X POST http://localhost:8000/simulate/error
    """
    error_message = ErrorMessage(
        error_type=ErrorType.API_CONNECTION,
        message="Failed to connect to Clockify API after 3 retries",
        traceback="Traceback (most recent call last):\n  File 'api_connector.py', line 42..."
    )
    
    await manager.broadcast_error(error_message)
    
    return {
        "message": "Error broadcast",
        "active_connections": manager.get_connection_count()
    }


@app.post("/simulate/progress")
async def simulate_progress():
    """
    Simulate broadcasting progress updates to all connected clients.
    
    Example:
        curl -X POST http://localhost:8000/simulate/progress
    """
    # Simulate processing 50 items
    total_items = 50
    
    for i in range(1, total_items + 1):
        progress_message = ProgressMessage(
            current_step=i,
            total_steps=total_items,
            percentage=(i / total_items) * 100,
            description=f"Processing project {i} of {total_items}"
        )
        
        await manager.broadcast_progress(progress_message)
        await asyncio.sleep(0.1)  # Simulate processing time
    
    return {
        "message": "Progress simulation complete",
        "active_connections": manager.get_connection_count()
    }


@app.post("/simulate/agent-workflow")
async def simulate_agent_workflow():
    """
    Simulate a complete agent workflow with status updates.
    
    This demonstrates how agents would send status updates during execution.
    
    Example:
        curl -X POST http://localhost:8000/simulate/agent-workflow
    """
    # Stage 1: Data Ingestion
    await manager.broadcast_status_update(
        StatusUpdateMessage(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.IN_PROGRESS,
            details="Fetching time entries from Clockify API"
        )
    )
    await asyncio.sleep(1)
    
    await manager.broadcast_progress(
        ProgressMessage(
            current_step=50,
            total_steps=100,
            percentage=50.0,
            description="Retrieved 500 time entries"
        )
    )
    await asyncio.sleep(1)
    
    await manager.broadcast_status_update(
        StatusUpdateMessage(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.COMPLETED,
            details="Data ingestion complete: 1,000 entries retrieved"
        )
    )
    await asyncio.sleep(1)
    
    # Stage 2: Qualification
    await manager.broadcast_status_update(
        StatusUpdateMessage(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.IN_PROGRESS,
            details="Analyzing R&D projects with RAG system"
        )
    )
    await asyncio.sleep(1)
    
    await manager.broadcast_progress(
        ProgressMessage(
            current_step=15,
            total_steps=30,
            percentage=50.0,
            description="Qualified 15 of 30 projects"
        )
    )
    await asyncio.sleep(1)
    
    await manager.broadcast_status_update(
        StatusUpdateMessage(
            stage=AgentStage.QUALIFICATION,
            status=AgentStatus.COMPLETED,
            details="Qualification complete: 28 projects qualified"
        )
    )
    await asyncio.sleep(1)
    
    # Stage 3: Audit Trail
    await manager.broadcast_status_update(
        StatusUpdateMessage(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.IN_PROGRESS,
            details="Generating technical narratives"
        )
    )
    await asyncio.sleep(1)
    
    await manager.broadcast_progress(
        ProgressMessage(
            current_step=28,
            total_steps=28,
            percentage=100.0,
            description="All narratives generated"
        )
    )
    await asyncio.sleep(1)
    
    await manager.broadcast_status_update(
        StatusUpdateMessage(
            stage=AgentStage.AUDIT_TRAIL,
            status=AgentStatus.COMPLETED,
            details="PDF report generated: report_2025_01_15.pdf"
        )
    )
    
    return {
        "message": "Agent workflow simulation complete",
        "active_connections": manager.get_connection_count()
    }


@app.get("/connections")
async def get_connections():
    """
    Get the number of active WebSocket connections.
    
    Example:
        curl http://localhost:8000/connections
    """
    return {
        "active_connections": manager.get_connection_count(),
        "timestamp": datetime.now().isoformat()
    }


# Example: Using ConnectionManager in an agent
async def example_agent_with_websocket():
    """
    Example of how an agent would use the ConnectionManager
    to send real-time updates during execution.
    """
    # Start agent execution
    await manager.broadcast_status_update(
        StatusUpdateMessage(
            stage=AgentStage.DATA_INGESTION,
            status=AgentStatus.IN_PROGRESS,
            details="Starting data ingestion"
        )
    )
    
    try:
        # Simulate data fetching
        total_records = 1000
        batch_size = 100
        
        for i in range(0, total_records, batch_size):
            # Process batch
            await asyncio.sleep(0.5)  # Simulate API call
            
            # Send progress update
            current = min(i + batch_size, total_records)
            await manager.broadcast_progress(
                ProgressMessage(
                    current_step=current,
                    total_steps=total_records,
                    percentage=(current / total_records) * 100,
                    description=f"Fetched {current} of {total_records} records"
                )
            )
        
        # Complete successfully
        await manager.broadcast_status_update(
            StatusUpdateMessage(
                stage=AgentStage.DATA_INGESTION,
                status=AgentStatus.COMPLETED,
                details=f"Successfully ingested {total_records} records"
            )
        )
        
    except Exception as e:
        # Handle errors
        await manager.broadcast_error(
            ErrorMessage(
                error_type=ErrorType.AGENT_EXECUTION,
                message=f"Data ingestion failed: {str(e)}",
                traceback=str(e)
            )
        )
        
        await manager.broadcast_status_update(
            StatusUpdateMessage(
                stage=AgentStage.DATA_INGESTION,
                status=AgentStatus.ERROR,
                details="Data ingestion failed"
            )
        )


if __name__ == "__main__":
    import uvicorn
    
    print("Starting WebSocket test server...")
    print("Open http://localhost:8000 in your browser to test")
    print("\nTest endpoints:")
    print("  - POST /simulate/status-update")
    print("  - POST /simulate/error")
    print("  - POST /simulate/progress")
    print("  - POST /simulate/agent-workflow")
    print("  - GET /connections")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
