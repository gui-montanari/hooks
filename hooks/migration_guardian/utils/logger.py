"""
Simple logger for Migration Guardian
"""

import logging
from datetime import datetime
from pathlib import Path


def setup_logger():
    """Setup logger with file and console handlers"""
    logger = logging.getLogger('migration_guardian')
    logger.setLevel(logging.DEBUG)
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # File handler
    log_file = log_dir / f"migration_guardian_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Create logger instance
logger = setup_logger()