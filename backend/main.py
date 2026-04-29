"""
WhatsApp Agent Backend - Main Entry Point
Receives voice messages from WhatsApp, processes them, and sends commands to local agent
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.utils.logger import setup_logging
from app.routes import webhook, health
from app.handlers.websocket import setup_websocket_handlers

# Setup logging
logger = setup_logging()

# Global state
app_state = {
    "agent_connected": False,
    "active_websocket": None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle - startup and shutdown"""
    logger.info("=== Backend Starting ===")
    logger.info(f"WhatsApp Phone Number ID: {settings.whatsapp_phone_number_id}")
    logger.info(f"Server listening on {settings.server_host}:{settings.server_port}")
    
    yield
    
    logger.info("=== Backend Shutting Down ===")
    if app_state["active_websocket"]:
        await app_state["active_websocket"].close()

# Create FastAPI app
app = FastAPI(
    title="WhatsApp Agent Backend",
    description="Voice-controlled laptop via WhatsApp",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for development (restrict in production)
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routes
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
app.include_router(health.router, tags=["health"])

# Setup WebSocket handlers
setup_websocket_handlers(app, app_state)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "ok",
        "service": "WhatsApp Agent Backend",
        "agent_connected": app_state["agent_connected"]
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
