/**
 * WebSocket Connection Manager
 * Handles real-time communication with the backend
 * 
 * Requirements: 5.2, 5.3
 */

class WebSocketManager {
    constructor(url = 'ws://localhost:8000/ws') {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // Start with 2 seconds
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.isConnecting = false;
        this.isIntentionallyClosed = false;
        
        // Event handlers
        this.onStatusUpdate = null;
        this.onError = null;
        this.onProgress = null;
        this.onConnectionChange = null;
        this.onCustomMessage = null;
        
        // Connection state
        this.isConnected = false;
        this.connectionId = null;
    }
    
    /**
     * Connect to the WebSocket server
     */
    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            console.log('WebSocket: Already connected or connecting');
            return;
        }
        
        this.isConnecting = true;
        this.isIntentionallyClosed = false;
        
        console.log(`WebSocket: Connecting to ${this.url}...`);
        
        try {
            this.ws = new WebSocket(this.url);
            
            // Connection opened
            this.ws.onopen = (event) => {
                console.log('WebSocket: Connected successfully');
                this.isConnected = true;
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                this.reconnectDelay = 2000; // Reset delay
                
                if (this.onConnectionChange) {
                    this.onConnectionChange(true);
                }
            };
            
            // Message received
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('WebSocket: Error parsing message:', error);
                }
            };
            
            // Connection closed
            this.ws.onclose = (event) => {
                console.log('WebSocket: Connection closed', event.code, event.reason);
                this.isConnected = false;
                this.isConnecting = false;
                
                if (this.onConnectionChange) {
                    this.onConnectionChange(false);
                }
                
                // Attempt to reconnect if not intentionally closed
                if (!this.isIntentionallyClosed) {
                    this.attemptReconnect();
                }
            };
            
            // Connection error
            this.ws.onerror = (error) => {
                console.error('WebSocket: Connection error:', error);
                this.isConnecting = false;
                
                if (this.onError) {
                    this.onError({
                        error_type: 'connection',
                        message: 'WebSocket connection error',
                        timestamp: new Date().toISOString()
                    });
                }
            };
            
        } catch (error) {
            console.error('WebSocket: Failed to create connection:', error);
            this.isConnecting = false;
            this.attemptReconnect();
        }
    }
    
    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(data) {
        console.log('WebSocket: Received message:', data);
        
        const messageType = data.type;
        
        switch (messageType) {
            case 'connection_established':
                console.log('WebSocket: Connection established', data.message);
                this.connectionId = data.connection_id;
                break;
                
            case 'status_update':
                if (this.onStatusUpdate) {
                    this.onStatusUpdate({
                        stage: data.stage,
                        status: data.status,
                        details: data.details,
                        timestamp: data.timestamp
                    });
                }
                break;
                
            case 'error':
                if (this.onError) {
                    this.onError({
                        error_type: data.error_type,
                        message: data.message,
                        traceback: data.traceback,
                        timestamp: data.timestamp
                    });
                }
                break;
                
            case 'progress':
                if (this.onProgress) {
                    this.onProgress({
                        current_step: data.current_step,
                        total_steps: data.total_steps,
                        percentage: data.percentage,
                        description: data.description,
                        timestamp: data.timestamp
                    });
                }
                break;
                
            case 'echo':
                console.log('WebSocket: Echo received:', data.message);
                break;
                
            default:
                // Custom message type
                if (this.onCustomMessage) {
                    this.onCustomMessage(data);
                }
                break;
        }
    }
    
    /**
     * Attempt to reconnect to the WebSocket server
     */
    attemptReconnect() {
        if (this.isIntentionallyClosed) {
            return;
        }
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('WebSocket: Max reconnection attempts reached');
            if (this.onError) {
                this.onError({
                    error_type: 'connection',
                    message: 'Failed to reconnect after multiple attempts',
                    timestamp: new Date().toISOString()
                });
            }
            return;
        }
        
        this.reconnectAttempts++;
        
        console.log(
            `WebSocket: Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) ` +
            `in ${this.reconnectDelay / 1000} seconds...`
        );
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
        
        // Exponential backoff with max delay
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }
    
    /**
     * Send a message to the server
     */
    send(message) {
        if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.warn('WebSocket: Cannot send message - not connected');
            return false;
        }
        
        try {
            const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
            this.ws.send(messageStr);
            console.log('WebSocket: Message sent:', message);
            return true;
        } catch (error) {
            console.error('WebSocket: Error sending message:', error);
            return false;
        }
    }
    
    /**
     * Close the WebSocket connection
     */
    close() {
        console.log('WebSocket: Closing connection...');
        this.isIntentionallyClosed = true;
        
        if (this.ws) {
            this.ws.close(1000, 'Client closed connection');
            this.ws = null;
        }
        
        this.isConnected = false;
        this.connectionId = null;
    }
    
    /**
     * Get connection status
     */
    getStatus() {
        return {
            isConnected: this.isConnected,
            connectionId: this.connectionId,
            reconnectAttempts: this.reconnectAttempts,
            readyState: this.ws ? this.ws.readyState : null
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WebSocketManager;
}
