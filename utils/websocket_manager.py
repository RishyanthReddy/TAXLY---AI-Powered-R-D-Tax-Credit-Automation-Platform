"""
WebSocket Connection Manager

This module provides a centralized manager for WebSocket connections,
enabling real-time bidirectional communication between the backend agents
and frontend clients.

Key Features:
- Connection lifecycle management (connect, disconnect)
- Broadcasting messages to all connected clients
- Individual client messaging
- Connection error handling
- Active connection tracking

Requirements: 5.2, 5.3
"""

import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime

from utils.logger import AgentLogger
from models.websocket_models import (
    StatusUpdateMessage,
    ErrorMessage,
    ProgressMessage
)

# Initialize logger
logger = AgentLogger.get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.
    
    This class maintains a list of active WebSocket connections and provides
    methods to broadcast messages to all clients or send to specific clients.
    
    Thread-safe for concurrent connection management.
    
    Example:
        manager = ConnectionManager()
        
        # In WebSocket endpoint
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                await manager.broadcast({"message": data})
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    """
    
    def __init__(self):
        """Initialize the connection manager with an empty connection list."""
        self.active_connections: List[WebSocket] = []
        logger.info("ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to register
            
        Example:
            await manager.connect(websocket)
        """
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info(
                f"WebSocket connection established. "
                f"Total active connections: {len(self.active_connections)}"
            )
            
            # Send welcome message to the newly connected client
            welcome_message = {
                "type": "connection_established",
                "message": "Connected to R&D Tax Credit Automation Agent",
                "timestamp": datetime.now().isoformat(),
                "connection_id": id(websocket)
            }
            await websocket.send_json(welcome_message)
            
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}", exc_info=True)
            raise
    
    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection from the active connections list.
        
        Args:
            websocket: The WebSocket connection to remove
            
        Example:
            manager.disconnect(websocket)
        """
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(
                    f"WebSocket connection closed. "
                    f"Total active connections: {len(self.active_connections)}"
                )
            else:
                logger.warning("Attempted to disconnect a non-existent WebSocket connection")
                
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}", exc_info=True)
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """
        Send a message to a specific WebSocket client.
        
        Args:
            message: Dictionary containing the message data
            websocket: The target WebSocket connection
            
        Example:
            await manager.send_personal_message(
                {"type": "notification", "text": "Processing complete"},
                websocket
            )
        """
        try:
            await websocket.send_json(message)
            logger.debug(f"Personal message sent to client {id(websocket)}: {message.get('type', 'unknown')}")
            
        except WebSocketDisconnect:
            logger.warning(f"Client {id(websocket)} disconnected while sending personal message")
            self.disconnect(websocket)
            
        except Exception as e:
            logger.error(
                f"Error sending personal message to client {id(websocket)}: {e}",
                exc_info=True
            )
            # Attempt to disconnect the problematic connection
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all active WebSocket connections.
        
        Handles connection errors gracefully by removing disconnected clients.
        
        Args:
            message: Dictionary containing the message data to broadcast
            
        Example:
            await manager.broadcast({
                "type": "status_update",
                "stage": "qualification",
                "status": "in_progress"
            })
        """
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return
        
        logger.info(
            f"Broadcasting message to {len(self.active_connections)} clients: "
            f"{message.get('type', 'unknown')}"
        )
        
        # Track disconnected clients to remove after iteration
        disconnected_clients = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                logger.debug(f"Message broadcast to client {id(connection)}")
                
            except WebSocketDisconnect:
                logger.warning(f"Client {id(connection)} disconnected during broadcast")
                disconnected_clients.append(connection)
                
            except Exception as e:
                logger.error(
                    f"Error broadcasting to client {id(connection)}: {e}",
                    exc_info=True
                )
                disconnected_clients.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected_clients:
            self.disconnect(connection)
        
        if disconnected_clients:
            logger.info(f"Removed {len(disconnected_clients)} disconnected clients")
    
    async def broadcast_status_update(self, status_message: StatusUpdateMessage) -> None:
        """
        Broadcast a status update message to all connected clients.
        
        Convenience method for broadcasting StatusUpdateMessage objects.
        
        Args:
            status_message: StatusUpdateMessage Pydantic model instance
            
        Example:
            status = StatusUpdateMessage(
                stage=AgentStage.QUALIFICATION,
                status=AgentStatus.IN_PROGRESS,
                details="Analyzing project: Alpha Development"
            )
            await manager.broadcast_status_update(status)
        """
        message = {
            "type": "status_update",
            **status_message.dict()
        }
        await self.broadcast(message)
        logger.info(
            f"Status update broadcast: {status_message.stage} - "
            f"{status_message.status} - {status_message.details}"
        )
    
    async def broadcast_error(self, error_message: ErrorMessage) -> None:
        """
        Broadcast an error message to all connected clients.
        
        Convenience method for broadcasting ErrorMessage objects.
        
        Args:
            error_message: ErrorMessage Pydantic model instance
            
        Example:
            error = ErrorMessage(
                error_type=ErrorType.API_CONNECTION,
                message="Failed to connect to Clockify API"
            )
            await manager.broadcast_error(error)
        """
        message = {
            "type": "error",
            **error_message.dict()
        }
        await self.broadcast(message)
        logger.error(
            f"Error broadcast: {error_message.error_type} - {error_message.message}"
        )
    
    async def broadcast_progress(self, progress_message: ProgressMessage) -> None:
        """
        Broadcast a progress update message to all connected clients.
        
        Convenience method for broadcasting ProgressMessage objects.
        
        Args:
            progress_message: ProgressMessage Pydantic model instance
            
        Example:
            progress = ProgressMessage(
                current_step=15,
                total_steps=50,
                percentage=30.0,
                description="Processing project 15 of 50"
            )
            await manager.broadcast_progress(progress)
        """
        message = {
            "type": "progress",
            **progress_message.dict()
        }
        await self.broadcast(message)
        logger.debug(
            f"Progress update broadcast: {progress_message.current_step}/"
            f"{progress_message.total_steps} ({progress_message.percentage:.1f}%)"
        )
    
    def get_connection_count(self) -> int:
        """
        Get the number of active WebSocket connections.
        
        Returns:
            int: Number of active connections
            
        Example:
            count = manager.get_connection_count()
            print(f"Active connections: {count}")
        """
        return len(self.active_connections)
    
    async def close_all_connections(self) -> None:
        """
        Close all active WebSocket connections gracefully.
        
        Useful during application shutdown or maintenance.
        
        Example:
            await manager.close_all_connections()
        """
        logger.info(f"Closing all {len(self.active_connections)} WebSocket connections")
        
        for connection in self.active_connections[:]:  # Create a copy to iterate
            try:
                await connection.close(code=1000, reason="Server shutdown")
                logger.debug(f"Closed connection {id(connection)}")
            except Exception as e:
                logger.error(f"Error closing connection {id(connection)}: {e}")
        
        self.active_connections.clear()
        logger.info("All WebSocket connections closed")


# Global connection manager instance
# This singleton instance is used across the application
connection_manager = ConnectionManager()
