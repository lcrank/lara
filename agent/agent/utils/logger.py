"""
Logging setup for agent
"""

import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(
    level: str = "INFO",
    log_file: str = "logs/agent.log"
) -> logging.Logger:
    """
    Setup logging for the agent
    
    Args:
        level: Logging level
        log_file: Path to log file
    
    Returns:
        Configured logger
    """
    
    # Create logs directory
    os.makedirs(os.path.dirname(log_file) or "logs", exist_ok=True)
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Console formatter
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File formatter
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    
    # File handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5_000_000,  # 5MB
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger
