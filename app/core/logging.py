"""
Logging configuration for the application.
"""

import logging
from typing import Dict, Any, Optional

def setup_logging(level: str = "INFO") -> None:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Map string level to logging level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    numeric_level = level_map.get(level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter to add context to log messages.
    """
    def __init__(self, logger: logging.Logger, prefix: str = "", extra: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter with a logger and optional prefix and context.
        
        Args:
            logger: Base logger to adapt
            prefix: Prefix for all log messages
            extra: Additional context to add to all log messages
        """
        super().__init__(logger, extra or {})
        self.prefix = prefix

    def process(self, msg, kwargs):
        """
        Process the log message by adding the prefix and context.
        
        Args:
            msg: Log message
            kwargs: Keyword arguments for the log message
            
        Returns:
            Processed message and keyword arguments
        """
        if self.prefix:
            msg = f"{self.prefix}: {msg}"
        return msg, kwargs

def get_logger(name: str, prefix: str = "", extra: Optional[Dict[str, Any]] = None) -> LoggerAdapter:
    """
    Get a logger with optional prefix and context.
    
    Args:
        name: Logger name
        prefix: Prefix for all log messages
        extra: Additional context to add to all log messages
        
    Returns:
        Logger adapter
    """
    return LoggerAdapter(logging.getLogger(name), prefix, extra)