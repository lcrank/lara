"""
Input validation utilities
"""

import logging
from app.config import settings

logger = logging.getLogger(__name__)

def validate_command(command) -> bool:
    """
    Validate that command is allowed
    
    Checks:
    1. Command type is in whitelist
    2. Parameters conform to constraints
    3. No obvious injection attempts
    
    Args:
        command: CommandPayload instance
    
    Returns:
        True if command is allowed, False otherwise
    """
    
    command_type = command.command_type
    parameters = command.parameters or {}
    
    # Check if command type is allowed
    allowed = settings.allowed_commands.get(command_type)
    if allowed is None:
        logger.warning(f"Command type not allowed: {command_type}")
        return False
    
    # Validate parameters based on command type
    if command_type == "open_app":
        app = parameters.get("app", "").lower()
        allowed_apps = allowed.get("apps", [])
        if app not in allowed_apps:
            logger.warning(f"App not allowed: {app}")
            return False
    
    elif command_type == "type_text":
        text = parameters.get("text", "")
        max_length = allowed.get("max_length", 1000)
        if len(text) > max_length:
            logger.warning(f"Text too long: {len(text)} > {max_length}")
            return False
    
    elif command_type == "search_web":
        query = parameters.get("query", "")
        if len(query) > 500:
            logger.warning("Search query too long")
            return False
    
    elif command_type == "read_file":
        path = parameters.get("path", "")
        # Prevent directory traversal
        if ".." in path or "~" in path:
            logger.warning(f"Path traversal detected: {path}")
            return False
    
    logger.debug(f"Command validated: {command_type}")
    return True

def sanitize_log(text: str, max_length: int = 500) -> str:
    """
    Remove sensitive information from logs
    
    Masks:
    - Passwords
    - API keys
    - Tokens
    - Phone numbers (partially)
    """
    
    import re
    
    text = re.sub(
        r'(?i)(password|pwd|passwd)\s*[:=]\s*[^\s,}]+',
        r'\1=***',
        text
    )
    
    text = re.sub(
        r'(?i)(api[_-]?key|token|secret)\s*[:=]\s*[^\s,}]+',
        r'\1=***',
        text
    )
    
    # Mask phone numbers
    text = re.sub(r'\+?1?\d{10,}', lambda m: m.group(0)[:-4] + '****', text)
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text
