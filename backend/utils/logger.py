"""Logging configuration for the application."""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(app=None, log_level=logging.INFO):
    """
    Set up logging configuration for the application.
    
    Args:
        app: Flask app instance (optional)
        log_level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with color formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - rotating log files (10MB max, keep 5 backups)
    log_file = log_dir / f'tp_generator_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error log file - only errors and critical
    error_log_file = log_dir / f'errors_{datetime.now().strftime("%Y%m%d")}.log'
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Reduce noise from some libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Set up application logger if Flask app provided
    if app:
        app.logger.setLevel(log_level)
        app.logger.info("Logging configured successfully")
        app.logger.info(f"Log files location: {log_dir}")
    
    return root_logger

def get_logger(name):
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
