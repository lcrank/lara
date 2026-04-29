"""
Command Executor - Sends commands to laptop agent via WebSocket
"""

import logging
import asyncio
import json
from typing import NamedTuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ExecutionResult(NamedTuple):
    success: bool
    details: str = ""
    error_message: str = ""
    execution_time_ms: float = 0.0
    response_data: dict = {}

class CommandExecutor:
    """
    Manages sending commands to the laptop agent
    This is a placeholder - will be connected to WebSocket manager in main app
    """
    
    def __init__(self):
        self.active_agents = {}  # device_id -> websocket connection
    
    async def execute(
        self,
        command,
        sender: str,
        timeout: int = 30
    ) -> ExecutionResult:
        """
        Send command to agent and wait for result
        
        Args:
            command: CommandPayload instance
            sender: Phone number of user (for audit log)
            timeout: How long to wait for response (seconds)
        
        Returns:
            ExecutionResult with success/failure info
        """
        
        try:
            # For now, this will fail (no agent connected)
            # In production, this queries the WebSocket connection pool
            # and sends the command to the appropriate agent
            
            logger.info(f"Executing command {command.command_type} from {sender}")
            
            if command.confidence < 0.8:
                return ExecutionResult(
                    success=False,
                    error_message=f"Low confidence command ({command.confidence:.1%}). Requires manual confirmation."
                )
            
            # This would normally go:
            # 1. Serialize command to JSON
            # 2. Send to agent via active WebSocket
            # 3. Wait for response (with timeout)
            # 4. Parse response
            # 5. Return ExecutionResult
            
            # For development, return mock response
            logger.warning("No agent connected - returning mock response")
            return ExecutionResult(
                success=True,
                details=f"Mock execution of {command.command_type} (no agent connected)",
                execution_time_ms=100.0
            )
        
        except asyncio.TimeoutError:
            logger.error(f"Command timeout: {command.command_type}")
            return ExecutionResult(
                success=False,
                error_message="Command timed out. Is your laptop agent online?"
            )
        
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}", exc_info=e)
            return ExecutionResult(
                success=False,
                error_message=str(e)[:100]
            )

class WebSocketConnectionManager:
    """
    Manages WebSocket connections from multiple laptop agents
    Enables sending commands to specific agents
    """
    
    def __init__(self):
        self.active_connections: dict = {}  # device_id -> websocket
        self.pending_commands: dict = {}    # command_id -> Future
    
    def register(self, device_id: str, websocket):
        """Register a new agent connection"""
        self.active_connections[device_id] = websocket
        logger.info(f"Agent registered: {device_id}")
    
    def unregister(self, device_id: str):
        """Remove agent connection"""
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"Agent unregistered: {device_id}")
    
    async def send_command(
        self,
        device_id: str,
        command,
        timeout: int = 30
    ) -> ExecutionResult:
        """
        Send command to specific device and wait for response
        """
        
        if device_id not in self.active_connections:
            return ExecutionResult(
                success=False,
                error_message=f"Device '{device_id}' not connected"
            )
        
        websocket = self.active_connections[device_id]
        
        try:
            # Generate command ID for tracking
            command_id = f"{device_id}_{datetime.utcnow().timestamp()}"
            
            # Create future for response
            response_future = asyncio.Future()
            self.pending_commands[command_id] = response_future
            
            # Build message payload
            if isinstance(command, dict):
                payload = command
            else:
                payload = {
                    "command_type": command.command_type,
                    "parameters": command.parameters
                }
            
            # Build message
            message = {
                "type": "execute_command",
                "command_id": command_id,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload
            }
            
            # Send to agent
            await websocket.send_text(json.dumps(message))
            logger.info(f"Sent command {command_id} to {device_id}")
            
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)
            
            return response
        
        except asyncio.TimeoutError:
            logger.error(f"Command {command_id} timed out")
            if command_id in self.pending_commands:
                del self.pending_commands[command_id]
            return ExecutionResult(
                success=False,
                error_message="Command execution timed out"
            )
        
        except Exception as e:
            logger.error(f"Error sending command: {str(e)}", exc_info=e)
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
    
    async def handle_response(self, device_id: str, response: dict):
        """
        Process response from agent
        Called when agent sends back execution result
        """
        
        command_id = response.get("command_id")
        
        if command_id and command_id in self.pending_commands:
            future = self.pending_commands[command_id]
            
            result = ExecutionResult(
                success=response.get("success", False),
                details=response.get("details", ""),
                error_message=response.get("error", ""),
                execution_time_ms=response.get("execution_time_ms", 0),
                response_data=response.get("data", {})
            )
            
            if not future.done():
                future.set_result(result)
            
            del self.pending_commands[command_id]
            logger.info(f"Response received for {command_id}: success={result.success}")
