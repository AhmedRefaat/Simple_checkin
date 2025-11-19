"""
Configuration Module
Manages application configuration and environment variables.

This module handles all configuration settings for the application including:
- Database connection settings
- Security configurations
- Application-wide constants
- Environment-specific settings
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from utils.logger import get_logger
from utils.constants import DatabaseConstants

# Initialize logger for this module
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()


# ==================== Helper Function for Database URL ====================
# This function is defined OUTSIDE the class to avoid initialization issues
# It checks multiple sources for the database URL with proper priority
def _get_database_url_with_priority(db_path: Path) -> str:
    """
    Get database URL from multiple sources with priority order.
    
    Priority:
    1. Streamlit secrets (for Streamlit Cloud deployment)
    2. Environment variable (for local development with .env)
    3. SQLite fallback (default local development)
    
    Args:
        db_path: Path to SQLite database file (used as fallback)
        
    Returns:
        str: Database connection URL
        
    Note:
        This function uses lazy import for Streamlit to avoid initializing
        Streamlit during config module load. This ensures app.py can call
        set_page_config() as the first Streamlit command.
    """
    # Priority 1: Try Streamlit secrets (Streamlit Cloud)
    # Use lazy import to avoid premature Streamlit initialization
    try:
        # Check if we're in a Streamlit environment first
        # by checking sys.modules instead of importing
        import sys
        
        # Only try to access Streamlit if it's already been imported by app.py
        if 'streamlit' in sys.modules:
            # Streamlit is already imported (by app.py after set_page_config)
            # Safe to access it now
            st = sys.modules['streamlit']

            directory = "////workspaces/Simple_checkin"
            contents = os.listdir(directory)
            logger.info(f"Contents of {directory}: {contents}")

            directory_path = Path("////workspaces/Simple_checkin")
            contents = [item.name for item in directory_path.iterdir()]
            logger.info(f"Contents of {directory_path}: {contents}")
            
            if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
                db_url = st.secrets['DATABASE_URL']
                logger.debug("Using DATABASE_URL from Streamlit secrets")
                
                # Fix Heroku/Render postgres:// URLs (should be postgresql://)
                if db_url.startswith('postgres://'):
                    db_url = db_url.replace('postgres://', 'postgresql://', 1)
                    logger.debug("Fixed postgres:// to postgresql://")
                
                return db_url
        else:
            # Streamlit not yet imported, skip secrets check
            logger.debug("Streamlit not yet imported, skipping secrets check")
            
    except Exception as e:
        # Secrets not configured or other error
        logger.debug(f"Could not access Streamlit secrets: {e}")
    
    # Priority 2: Try environment variable (local development with .env)
    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        logger.debug("Using DATABASE_URL from environment variable")
        
        # Fix Heroku/Render postgres:// URLs (should be postgresql://)
        if env_db_url.startswith('postgres://'):
            env_db_url = env_db_url.replace('postgres://', 'postgresql://', 1)
            logger.debug("Fixed postgres:// to postgresql://")
        
        return env_db_url
    
    # Priority 3: SQLite fallback (default local development)
    sqlite_url = f"sqlite:///{db_path}"
    logger.debug(f"Using SQLite fallback: {sqlite_url}")
    return sqlite_url


class Config:
    """
    Application configuration class.
    
    This class centralizes all configuration settings and provides
    methods to access them safely with proper defaults.
    """
    
    # ==================== Path Configuration ====================
    # Base directory of the application
    BASE_DIR = Path(__file__).parent.parent
    
    # Database directory and file paths
    DATA_DIR = BASE_DIR / DatabaseConstants.DB_FOLDER
    DB_PATH = DATA_DIR / DatabaseConstants.DB_NAME
    
    # Logs directory
    LOGS_DIR = BASE_DIR / "logs"
    
    # ==================== Database Configuration ====================
    # Get database URL from environment/secrets or fallback to SQLite
    # Priority: Streamlit secrets > Environment variable > SQLite (local dev)
    DATABASE_URL = _get_database_url_with_priority(DB_PATH)
    
    # Database connection pool settings
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    
    # Database type detection
    IS_POSTGRESQL = DATABASE_URL.startswith('postgresql://')
    IS_SQLITE = DATABASE_URL.startswith('sqlite:///')

    @classmethod
    def is_postgresql(cls) -> bool:
        """
        Check if using PostgreSQL database.
        
        Returns:
            bool: True if PostgreSQL, False if SQLite
        """
        # Use the already-resolved DATABASE_URL (which has priority logic built in)
        return cls.IS_POSTGRESQL
    
    # ==================== Security Configuration ====================
    # Secret key for session management (load from environment in production)
    # SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
     # SECRET_KEY - Try Streamlit secrets first, then environment variable, then default
    try:
        import streamlit as st
        SECRET_KEY: str = st.secrets.get("SECRET_KEY", os.getenv('SECRET_KEY', '3GFUf5xNMCx-Jq85F3sEfwD0e_ZlEQquzX05dTSSdWA'))
    except (ImportError, FileNotFoundError, KeyError):
        # Fallback if not on Streamlit Cloud or secrets not configured
        SECRET_KEY: str = os.getenv('SECRET_KEY', '3GFUf5xNMCx-Jq85F3sEfwD0e_ZlEQquzX05dTSSdWA')
    
    # Password hashing rounds (higher = more secure but slower)
    BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))
    
    # Session timeout in hours
    SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "8"))
    
    # ==================== Application Configuration ====================
    # Application name and version
    APP_NAME = os.getenv("APP_NAME", "Employee Check-in System")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    
    # Maximum number of employees allowed
    MAX_EMPLOYEES = DatabaseConstants.MAX_EMPLOYEES
    
    # Default vacation days for new employees
    DEFAULT_VACATION_DAYS = DatabaseConstants.DEFAULT_VACATION_DAYS
    
    # ==================== Logging Configuration ====================
    # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Enable/disable logging
    LOGGING_ENABLED = os.getenv("LOGGING_ENABLED", "true").lower() == "true"
    
    # Enable/disable file logging
    FILE_LOGGING_ENABLED = os.getenv("FILE_LOGGING_ENABLED", "true").lower() == "true"
    
    # Log file retention days
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

    # ==================== Logging Configuration (Additional) ====================
    # Console logging
    LOG_TO_CONSOLE = os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"

    # File logging
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"

    # Log file path
    # Generate log file path with current date
    _current_date = datetime.now().strftime('%Y%m%d')
    LOG_FILE_PATH = LOGS_DIR / f"app_{_current_date}.log"

    # Rotating log settings
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB default
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))  # Keep 5 backup files
    
    # ==================== Feature Flags ====================
    # Enable/disable specific features
    ENABLE_EXCEL_EXPORT = os.getenv("ENABLE_EXCEL_EXPORT", "true").lower() == "true"
    ENABLE_EMAIL_NOTIFICATIONS = os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "false").lower() == "true"
    
    # ==================== Development Settings ====================
    # Debug mode (never enable in production)
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # Development mode flag
    DEVELOPMENT = os.getenv("ENVIRONMENT", "production") == "development"
    
    @classmethod
    def ensure_directories_exist(cls):
        """
        Create necessary directories if they don't exist.
        
        This method ensures that all required directories (data, logs, etc.)
        are created before the application starts.
        """
        logger.info("Ensuring required directories exist")
        
        try:
            # Create data directory for database
            cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Data directory ensured: {cls.DATA_DIR}")
            
            # Create logs directory
            cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Logs directory ensured: {cls.LOGS_DIR}")
            
            logger.info("All required directories created successfully")
            
        except Exception as e:
            logger.error(f"Error creating directories: {e}")
            raise
    
    @classmethod
    def get_database_url(cls) -> str:
        """
        Get the database connection URL.
        
        Returns:
            str: Database connection URL
        """
        return cls.DATABASE_URL
    
    @classmethod
    def is_debug_mode(cls) -> bool:
        """
        Check if application is in debug mode.
        
        Returns:
            bool: True if debug mode is enabled
        """
        return cls.DEBUG
    
    @classmethod
    def is_logging_enabled(cls) -> bool:
        """
        Check if logging is enabled.
        
        Returns:
            bool: True if logging is enabled
        """
        return cls.LOGGING_ENABLED
    
    @classmethod
    def validate_config(cls):
        """
        Validate configuration settings.
        
        This method checks if all required configuration values are present
        and valid. Raises exception if configuration is invalid.
        
        Raises:
            ValueError: If configuration is invalid
        """
        logger.info("Validating configuration")
        
        # Check if secret key is changed from default in production
        # if not cls.DEVELOPMENT and cls.SECRET_KEY == "your-secret-key-change-in-production":
        #     raise ValueError("SECRET_KEY must be changed in production environment")
        try:
            import streamlit as st
            has_streamlit_secret = "SECRET_KEY" in st.secrets
        except (ImportError, FileNotFoundError):
            has_streamlit_secret = False
        
        if not cls.DEVELOPMENT and not has_streamlit_secret:
            if cls.SECRET_KEY == 'change-this-secret-key-in-production':
                raise ValueError("SECRET_KEY must be changed in production environment. "
                            "Add it to Streamlit Cloud Secrets or set SECRET_KEY environment variable.")
        
        # Validate numeric values
        if cls.BCRYPT_ROUNDS < 4 or cls.BCRYPT_ROUNDS > 31:
            raise ValueError("BCRYPT_ROUNDS must be between 4 and 31")
        
        if cls.SESSION_TIMEOUT_HOURS < 1:
            raise ValueError("SESSION_TIMEOUT_HOURS must be at least 1")
        
        if cls.MAX_EMPLOYEES < 1:
            raise ValueError("MAX_EMPLOYEES must be at least 1")
        
        logger.info("Configuration validation successful")
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """
        Get a summary of current configuration.
        
        Returns:
            dict: Configuration summary (excluding sensitive data)
        """
        # Determine database type
        if cls.IS_POSTGRESQL:
            db_type = "PostgreSQL (Neon)"
            # Extract host from URL for display (hide password)
            try:
                from urllib.parse import urlparse
                parsed = urlparse(cls.DATABASE_URL)
                db_host = parsed.hostname
            except:
                db_host = "Unknown"
        else:
            db_type = "SQLite (Local)"
            db_host = str(cls.DB_PATH)
        
        return {
            "app_name": cls.APP_NAME,
            "app_version": cls.APP_VERSION,
            "database_type": db_type,
            "database_host": db_host,
            "debug_mode": cls.DEBUG,
            "development_mode": cls.DEVELOPMENT,
            "logging_enabled": cls.LOGGING_ENABLED,
            "max_employees": cls.MAX_EMPLOYEES,
            "default_vacation_days": cls.DEFAULT_VACATION_DAYS,
        }


# Initialize configuration on module load
try:
    Config.ensure_directories_exist()
    Config.validate_config()
    logger.info(f"Configuration loaded successfully: {Config.get_config_summary()}")
except Exception as e:
    logger.critical(f"Failed to initialize configuration: {e}")
    raise