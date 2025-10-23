"""
Logging Utility Module
Provides centralized logging configuration with toggle capability.
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


class AppLogger:
    """
    Application logger with configurable output and levels.
    Can be enabled/disabled via configuration.
    """
    
    _loggers = {}
    _initialized = False
    
    # Default settings (can be overridden)
    _log_level = os.getenv("LOG_LEVEL", "INFO")
    _enable_logging = os.getenv("LOGGING_ENABLED", "true").lower() == "true"
    _log_to_console = os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"
    _log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    _log_dir = Path("logs")
    _log_max_bytes = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
    _log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    @classmethod
    def _initialize(cls) -> None:
        """Initialize logging configuration"""
        if cls._initialized:
            return
        
        # Set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, cls._log_level.upper(), logging.INFO))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        if cls._enable_logging:
            # Add console handler if enabled
            if cls._log_to_console:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
            
            # Add file handler if enabled
            if cls._log_to_file:
                # Ensure log directory exists
                cls._log_dir.mkdir(parents=True, exist_ok=True)
                
                log_file_path = cls._log_dir / "app.log"
                
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=cls._log_max_bytes,
                    backupCount=cls._log_backup_count,
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
        else:
            # Add null handler to suppress logging
            root_logger.addHandler(logging.NullHandler())
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance for the specified module.
        
        Args:
            name: Logger name (typically __name__ of the module)
        
        Returns:
            logging.Logger: Configured logger instance
        """
        if not cls._initialized:
            cls._initialize()
        
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if logging is enabled"""
        return cls._enable_logging
    
    @classmethod
    def set_level(cls, level: str) -> None:
        """
        Change logging level at runtime.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        cls._log_level = level.upper()
        logging.getLogger().setLevel(getattr(logging, cls._log_level, logging.INFO))
        if cls.is_enabled():
            logging.info(f"Logging level changed to {cls._log_level}")
    
    @classmethod
    def enable_logging(cls, enabled: bool = True):
        """
        Enable or disable logging at runtime.
        
        Args:
            enabled: True to enable, False to disable
        """
        cls._enable_logging = enabled
        cls._initialized = False  # Force reinitialization
        cls._initialize()


# Convenience function for getting loggers
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("This is a log message")
    
    Args:
        name: Logger name
    
    Returns:
        logging.Logger: Logger instance
    """
    return AppLogger.get_logger(name)