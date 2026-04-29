"""
Configuration management for WhatsApp Agent Backend
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Server
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", 8000))
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # WhatsApp Configuration
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    whatsapp_business_account_id: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    
    # Groq Configuration
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    
    # WebSocket/Agent Configuration
    agent_websocket_url: str = os.getenv("AGENT_WEBSOCKET_URL", "ws://localhost:8001")
    agent_token: str = os.getenv("AGENT_TOKEN", "default-insecure-token-change-me")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./agent.db")
    
    # Webhook Security
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "your-webhook-secret")
    
    # API Limits
    rate_limit_messages_per_minute: int = 30
    command_timeout_seconds: int = 30
    max_audio_size_mb: int = 16  # WhatsApp limit
    
    # Authorized Users (CSV or as list)
    authorized_phone_numbers: list = [
        os.getenv("AUTHORIZED_PHONE_NUMBER_1", "+1234567890"),
        os.getenv("AUTHORIZED_PHONE_NUMBER_2", "+0987654321"),
    ]
    
    # Command Whitelist
    allowed_commands: dict = {
        "open_app": {
            "apps": ["notepad", "calculator", "chrome", "firefox", "opera"]
        },
        "type_text": {
            "max_length": 1000
        },
        "screenshot": {
            "return_as_media": True
        },
        "search_web": {
            "engines": ["google", "duckduckgo"]
        },
        "read_file": {
            "extensions": [".txt", ".md", ".pdf"],
            "max_size_mb": 10
        }
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

# Create global settings instance
settings = Settings()

# Validation
def validate_settings():
    """Validate that all required settings are present"""
    required = [
        settings.whatsapp_phone_number_id,
        settings.whatsapp_access_token,
        settings.groq_api_key,
    ]
    
    for req in required:
        if not req:
            raise ValueError(f"Missing required setting")
    
    return True
