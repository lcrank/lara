"""
Laptop Agent Client - Main Entry Point
Connects to backend server and executes commands from WhatsApp
"""

import asyncio
import logging
import signal
from agent.client import AgentClient
from agent.utils.logger import setup_logging

# Setup logging
logger = setup_logging()

class AgentManager:
    """Manages agent lifecycle"""
    
    def __init__(self):
        self.client = None
        self.running = True
    
    async def start(self):
        """Start the agent"""
        logger.info("=== Laptop Agent Starting ===")
        
        self.client = AgentClient()
        
        try:
            await self.client.connect()
            logger.info("Agent connected to backend")
            
            # Keep agent running
            while self.running:
                await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Agent error: {str(e)}", exc_info=e)
            await self.stop()
    
    async def stop(self):
        """Stop the agent gracefully"""
        logger.info("=== Agent Shutting Down ===")
        self.running = False
        
        if self.client:
            await self.client.disconnect()

async def main():
    """Main entry point"""
    
    manager = AgentManager()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(manager.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start agent
    await manager.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=e)
        exit(1)
