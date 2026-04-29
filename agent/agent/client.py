"""
Agent WebSocket Client
Maintains connection to backend and receives/executes commands
"""

import asyncio
import json
import logging
import websockets
from typing import Optional
import os
from dotenv import load_dotenv

from agent.executor import CommandExecutor

load_dotenv()

logger = logging.getLogger(__name__)

class AgentClient:
    """
    WebSocket client for connecting to backend server
    Handles command reception and execution
    """
    
    def __init__(self):
        self.server_url = os.getenv("SERVER_WS_URL", "ws://localhost:8000/ws/agent")
        self.agent_id = os.getenv("AGENT_ID", "laptop-1")
        self.agent_token = os.getenv("AGENT_TOKEN", "default-token")
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.executor = CommandExecutor()
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
    
    async def connect(self):
        """Establish WebSocket connection to backend"""
        
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                logger.info(f"Connecting to {self.server_url}...")
                
                self.websocket = await websockets.connect(self.server_url)
                logger.info("WebSocket connected")
                
                # Send authentication
                await self._authenticate()
                
                # Reset reconnect counter on successful connection
                self.reconnect_attempts = 0
                self.connected = True
                
                # Start listening for commands
                await self._listen_for_commands()
            
            except websockets.exceptions.WebSocketException as e:
                logger.warning(f"WebSocket error: {str(e)}")
                await self._handle_disconnect()
            
            except Exception as e:
                logger.error(f"Connection error: {str(e)}", exc_info=e)
                await self._handle_disconnect()
    
    async def _authenticate(self):
        """Send authentication message to backend"""
        
        auth_message = {
            "type": "auth",
            "token": self.agent_token,
            "device_id": self.agent_id,
            "platform": "windows"  # Platform detection
        }
        
        await self.websocket.send(json.dumps(auth_message))
        logger.info("Authentication message sent")
        
        # Wait for welcome message
        welcome = await self.websocket.recv()
        welcome_data = json.loads(welcome)
        
        if welcome_data.get("type") == "welcome":
            logger.info("Authentication successful")
        else:
            raise Exception("Unexpected response to auth")
    
    async def _listen_for_commands(self):
        """Listen for incoming commands from backend"""
        
        while self.connected:
            try:
                # Receive message
                message_str = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=60.0  # 60 second timeout
                )
                
                message = json.loads(message_str)
                await self._handle_message(message)
            
            except asyncio.TimeoutError:
                # No message for 60 seconds - send heartbeat
                await self._send_heartbeat()
            
            except websockets.exceptions.ConnectionClosed:
                logger.info("Connection closed by server")
                break
            
            except Exception as e:
                logger.error(f"Error in listen loop: {str(e)}", exc_info=e)
                break
    
    async def _handle_message(self, message: dict):
        """Process incoming message from backend"""
        
        message_type = message.get("type")
        
        if message_type == "execute_command":
            command_id = message.get("command_id")
            payload = message.get("payload")
            logger.info(f"Received command: {command_id}")
            
            # Run in background so WebSocket stays alive
            asyncio.create_task(self._execute_and_respond(command_id, payload))
        
        elif message_type == "ping":
            await self.websocket.send(json.dumps({"type": "pong"}))
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def _execute_and_respond(self, command_id: str, payload: dict):
        """Execute a command and send the result back to the server"""
        try:
            result = await self.executor.execute(payload)
            response = {
                "type": "response",
                "command_id": command_id,
                "success": result.success,
                "details": result.details,
                "error": result.error_message,
                "execution_time_ms": result.execution_time_ms,
                "data": result.response_data
            }
        except Exception as e:
            logger.error(f"Command execution error: {str(e)}", exc_info=e)
            response = {
                "type": "response",
                "command_id": command_id,
                "success": False,
                "error": str(e),
                "details": "",
                "execution_time_ms": 0,
                "data": {}
            }
        
        try:
            if self.websocket and self.websocket.open:
                await self.websocket.send(json.dumps(response))
                logger.info(f"Command response sent: {command_id}")
            else:
                logger.warning(f"WebSocket closed before response could be sent for {command_id}")
        except Exception as e:
            logger.error(f"Failed to send response: {str(e)}")
    
    async def _send_heartbeat(self):
        """Send heartbeat to keep connection alive"""
        
        if self.websocket and self.connected:
            try:
                await self.websocket.send(json.dumps({
                    "type": "heartbeat",
                    "device_id": self.agent_id
                }))
                logger.debug("Heartbeat sent")
            except Exception as e:
                logger.warning(f"Error sending heartbeat: {e}")
    
    async def _handle_disconnect(self):
        """Handle disconnection and attempt reconnection"""
        
        self.connected = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        self.reconnect_attempts += 1
        logger.warning(
            f"Disconnected. Reconnect attempt {self.reconnect_attempts}/"
            f"{self.max_reconnect_attempts} after {self.reconnect_delay}s"
        )
        
        await asyncio.sleep(self.reconnect_delay)
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            # Exponential backoff
            self.reconnect_delay = min(self.reconnect_delay * 1.5, 60)
            await self.connect()
        else:
            logger.error("Max reconnection attempts reached")
    
    async def disconnect(self):
        """Gracefully disconnect from server"""
        
        self.connected = False
        
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("Disconnected from backend")
            except:
                pass
