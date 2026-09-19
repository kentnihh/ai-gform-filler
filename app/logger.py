import os
import sys
from loguru import logger

def setup_logger() -> None:
    """Configures the Loguru logger for the application.
    
    Creates a 'logs' directory if it doesn't exist. Sets up a console handler 
    with a specific format and a file handler that rotates daily at midnight.
    """
    os.makedirs("logs", exist_ok=True)
    logger.remove() # Remove default handler
    
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Console handler
    logger.add(sys.stderr, format=log_format, level="INFO")
    
    # File handler (auto rotating daily)
    logger.add("logs/app_{time:YYYYMMDD}.log", format=log_format, level="INFO", rotation="00:00")

setup_logger()