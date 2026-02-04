"""Centralized logging configuration for PCAN_Auto."""

import logging
import logging.handlers
from pathlib import Path


def configure_logging(log_level=logging.INFO, log_file=None):
    """Configure logging for the entire application.
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Optional log file path (default: pcan_auto.log in app directory)
    """
    if log_file is None:
        log_file = Path(__file__).parent.parent / "pcan_auto.log"
    
    # Ensure log file directory exists (skip file logging if disabled)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (with rotation)
    if log_file:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)  # File always logs debug
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Could not setup file logging: {e}")
    
    root_logger.info(f"Logging configured: level={log_level}, file={log_file}")


def get_logger(name):
    """Get a logger for a module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)
