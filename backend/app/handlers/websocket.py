"""
WebSocket handlers for managing laptop agent connections
"""

import logging
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.config import settings
from app.services.command_executor import WebSocketConnectionManager

logger = logging.getLogger(__name__)

# Global connection manager
connection_manager = WebSocketConnectionManager()

def setup_websocket_handlers(app, app_state):
    """Register WebSocket endpoints with FastAPI app"""
    
    @app.websocket("/ws/agent")
    async def websocket_agent_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for laptop agents
        
        Protocol:
        1. Agent connects and sends auth message with token
        2. Server validates token
        3. Agent receives commands as JSON messages
        4. Agent responds with execution results
        """
        
        device_id = None
        
        try:
            # Wait for connection
            await websocket.accept()
            logger.info(f"WebSocket connection received")
            
            # Wait for authentication message
            auth_message = await websocket.receive_json()
            
            if auth_message.get("type") != "auth":
                logger.warning("First message was not auth")
                await websocket.close(code=1008, reason="Invalid message type")
                return
            
            # Validate token
            token = auth_message.get("token")
            device_id = auth_message.get("device_id", "unknown")
            
            if token != settings.agent_token:
                logger.warning(f"Invalid agent token from {device_id}")
                await websocket.close(code=1008, reason="Invalid credentials")
                return
            
            # Register agent
            connection_manager.register(device_id, websocket)
            app_state["agent_connected"] = True
            app_state["active_websocket"] = websocket
            logger.info(f"Agent authenticated: {device_id}")
            
            # Send welcome message
            await websocket.send_json({
                "type": "welcome",
                "message": f"Connected to WhatsApp Agent Server",
                "device_id": device_id
            })
            
            # Listen for messages
            while True:
                data = await websocket.receive_json()
                await handle_agent_message(device_id, data, connection_manager)
        
        except WebSocketDisconnect:
            logger.info(f"Agent disconnected: {device_id}")
            if device_id:
                connection_manager.unregister(device_id)
            app_state["agent_connected"] = False
            app_state["active_websocket"] = None
        
        except Exception as e:
            logger.error(f"WebSocket error for {device_id}: {str(e)}", exc_info=e)
            if device_id:
                connection_manager.unregister(device_id)
            try:
                await websocket.close(code=1011, reason=f"Server error: {str(e)}")
            except:
                pass

async def handle_agent_message(device_id: str, message: dict, manager: WebSocketConnectionManager):
    """
    Process message from agent
    
    Message types:
    - "response": Result of command execution
    - "heartbeat": Keep-alive ping
    - "status": Agent status update
    """
    
    message_type = message.get("type")
    
    if message_type == "response":
        # Command execution result
        await manager.handle_response(device_id, message)
        logger.debug(f"Response handled: {message.get('command_id')}")
    
    elif message_type == "heartbeat":
        # Keep-alive - acknowledge
        logger.debug(f"Heartbeat from {device_id}")
    
    elif message_type == "status":
        # Agent status update
        status = message.get("status", "unknown")
        logger.info(f"Agent status update: {device_id} -> {status}")
    
    else:
        logger.warning(f"Unknown message type from {device_id}: {message_type}")
