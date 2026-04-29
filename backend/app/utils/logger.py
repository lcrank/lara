"""
Logging setup and configuration
"""

import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(
    level: str = "INFO",
    log_file: str = "logs/app.log"
) -> logging.Logger:
    """
    Configure logging with both console and file output
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    
    Returns:
        Configured logger instance
    """
    
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file) or "logs", exist_ok=True)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

# Security event logger
security_logger = logging.getLogger("security")

def log_security_event(event: str, **kwargs):
    """Log security-relevant events"""
    security_logger.warning(f"SECURITY_EVENT: {event} | {kwargs}")
