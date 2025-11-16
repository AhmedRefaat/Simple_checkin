"""
Database Manager Module
Provides database connection and session management.

This module handles all database operations including:
- Database engine creation and configuration
- Session management
- Connection pooling
- Transaction handling
- Database initialization

Usage:
    from database.db_manager import DatabaseManager
    
    db = DatabaseManager()
    session = db.get_session()
    # Perform database operations
    session.close()
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator, Optional

from config.config import Config
from database.models import Base
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class DatabaseManager:
    """
    Database manager class for handling all database operations.
    
    This class implements the singleton pattern to ensure only one
    database connection pool exists throughout the application lifecycle.
    
    Attributes:
        _instance: Singleton instance
        engine: SQLAlchemy engine
        session_factory: Session factory for creating new sessions
        Session: Scoped session class
    """
    
    # Singleton instance
    _instance: Optional['DatabaseManager'] = None
    
    def __new__(cls):
        """
        Implement singleton pattern.
        
        Ensures only one instance of DatabaseManager exists.
        
        Returns:
            DatabaseManager: The singleton instance
        """
        if cls._instance is None:
            logger.info("Creating new DatabaseManager instance")
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize database manager.
        
        Sets up database engine, session factory, and connection pool.
        Only runs once due to singleton pattern.
        """
        # Prevent re-initialization
        if self._initialized:
            return
        
        logger.info("Initializing DatabaseManager")
        
        try:
            # Get database URL from configuration
            database_url = Config.get_database_url()
            logger.debug(f"Database URL: {database_url}")
            
            # Create engine with appropriate settings based on database type
            if "sqlite" in database_url:
                # ============================================================
                # SQLite Configuration (Local Development)
                # ============================================================
                # SQLite stores data in a local file, perfect for development
                # but NOT suitable for Streamlit Cloud (ephemeral filesystem)
                # ============================================================
                logger.info("Configuring SQLite database engine")
                
                self.engine = create_engine(
                    database_url,
                    # SQLite-specific connection arguments
                    connect_args={
                        "check_same_thread": False,  # Allow multi-threaded access
                    },
                    poolclass=StaticPool,  # Single connection pool for SQLite
                    echo=Config.is_debug_mode(),  # Log SQL queries in debug mode
                )
                
                # Enable foreign key constraints for SQLite
                # SQLite has foreign keys disabled by default for backward compatibility
                @event.listens_for(self.engine, "connect")
                def set_sqlite_pragma(dbapi_conn, connection_record):
                    """
                    Enable foreign key constraints in SQLite.
                    
                    This ensures referential integrity (e.g., can't delete an employee
                    with existing attendance records without CASCADE).
                    """
                    cursor = dbapi_conn.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
                    logger.debug("Foreign key constraints enabled for SQLite")

            else:
                # ============================================================
                # PostgreSQL Configuration (Production - Streamlit Cloud)
                # ============================================================
                # PostgreSQL is a production-grade database hosted on Neon.tech
                # Data persists across app restarts (no data loss)
                # ============================================================
                logger.info("Configuring PostgreSQL database engine")
                
                # PostgreSQL-specific connection arguments
                # These are CRITICAL for Neon.tech compatibility
                postgres_connect_args = {
                    # SSL Mode: REQUIRED by Neon.tech for security
                    # Without this, connection will fail with "SSL required" error
                    "sslmode": "require",
                    
                    # Connection timeout: Prevent hanging on network issues
                    "connect_timeout": 18,
                    
                    # Application name: Helps identify connections in PostgreSQL logs
                    "application_name": "streamlit_attendance_app",

                    # Additional settings for unreliable networks
                    "keepalives": 1,  # Enable TCP keepalive
                    "keepalives_idle": 30,  # Seconds before sending keepalive
                    "keepalives_interval": 10,  # Seconds between keepalives
                    "keepalives_count": 5,  # Number of keepalives before giving up
                }
                
                self.engine = create_engine(
                    database_url,
                    
                    # ==================== Connection Pooling ====================
                    # Connection pooling reuses database connections instead of
                    # creating new ones for every query (much faster)
                    
                    pool_size=Config.DB_POOL_SIZE,  # Number of persistent connections (default: 5)
                    max_overflow=Config.DB_MAX_OVERFLOW,  # Additional connections when pool is full (default: 10)
                    pool_timeout=Config.DB_POOL_TIMEOUT,  # Seconds to wait for available connection (default: 30)
                    
                    # ==================== Connection Health ====================
                    
                    # Pool Pre-Ping: Test connection before using it
                    # Executes "SELECT 1" to check if connection is alive
                    # Prevents "connection already closed" errors
                    pool_pre_ping=True,
                    
                    # Pool Recycle: Refresh connections after 1 hour
                    # Cloud databases close idle connections after timeout
                    # This prevents using stale connections
                    # 3600 seconds = 1 hour (safe for Neon.tech)
                    pool_recycle=3600,
                    
                    # ==================== PostgreSQL-Specific ====================
                    
                    # Connect args: SSL and other PostgreSQL settings
                    connect_args=postgres_connect_args,
                    
                    # Echo SQL: Log all SQL queries (only in debug mode)
                    echo=Config.is_debug_mode(),
                    
                    # Isolation Level: Use default (READ COMMITTED)
                    # Ensures data consistency across concurrent transactions
                    # isolation_level="READ COMMITTED",  # Optional: explicitly set
                )
                
                logger.info("PostgreSQL engine configured with SSL and connection pooling")
                logger.debug(f"Pool config: size={Config.DB_POOL_SIZE}, "
                            f"max_overflow={Config.DB_MAX_OVERFLOW}, "
                            f"timeout={Config.DB_POOL_TIMEOUT}, "
                            f"recycle=3600s")
            
            # Create session factory
            logger.debug("Creating session factory")
            self.session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,  # Explicit transaction control
                autoflush=False,   # Manual flush control
                expire_on_commit=False  # Keep objects accessible after commit
            )
            
            # Create scoped session for thread-safety
            self.Session = scoped_session(self.session_factory)
            
            # Mark as initialized
            self._initialized = True
            logger.info("DatabaseManager initialized successfully")
            
        except Exception as e:
            logger.critical(f"Failed to initialize DatabaseManager: {e}")
            raise
    
    def create_tables(self):
        """
        Create all database tables defined in models.
        
        This method creates all tables that don't exist yet.
        Existing tables are not modified.
        
        Raises:
            Exception: If table creation fails
        """
        logger.info("Creating database tables")
        
        try:
            # Create all tables
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def drop_tables(self):
        """
        Drop all database tables.
        
        WARNING: This will delete all data! Use with caution.
        Should only be used in development/testing.
        
        Raises:
            Exception: If table deletion fails
        """
        logger.warning("Dropping all database tables")
        
        if not Config.is_debug_mode():
            logger.error("Cannot drop tables in production mode")
            raise PermissionError("Table dropping is disabled in production")
        
        try:
            Base.metadata.drop_all(self.engine)
            logger.info("All database tables dropped")
            
        except Exception as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            Session: SQLAlchemy session object
            
        Note:
            Remember to close the session when done:
            session.close()
        """
        logger.debug("Creating new database session")
        return self.Session()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations.
        
        This context manager automatically handles:
        - Session creation
        - Transaction commit on success
        - Transaction rollback on error
        - Session cleanup
        
        Yields:
            Session: Database session
            
        Example:
            with db.session_scope() as session:
                user = session.query(User).first()
                # Automatically commits on success
                # Automatically rolls back on exception
        """
        logger.debug("Starting database transaction")
        session = self.Session()
        
        try:
            # Yield session to caller
            yield session
            
            # Commit transaction if no exceptions
            session.commit()
            logger.debug("Transaction committed successfully")
            
        except Exception as e:
            # Rollback transaction on any exception
            session.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
            
        finally:
            # Always close session
            session.close()
            logger.debug("Database session closed")
    
    def close(self):
        """
        Close database connection and cleanup resources.
        
        Should be called when application shuts down.
        """
        logger.info("Closing DatabaseManager")
        
        try:
            # Remove scoped session
            self.Session.remove()
            
            # Dispose engine connection pool
            self.engine.dispose()
            
            logger.info("DatabaseManager closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing DatabaseManager: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        logger.info("Testing database connection")
        
        try:
            # Try to execute a simple query
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))
            
            logger.info("Database connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_engine_info(self) -> dict:
        """
        Get information about the database engine.
        
        Returns:
            dict: Engine configuration information
        """
        return {
            'url': str(self.engine.url),
            'driver': self.engine.driver,
            'pool_size': self.engine.pool.size() if hasattr(self.engine.pool, 'size') else 'N/A',
            'dialect': self.engine.dialect.name,
        }


# Create global database manager instance
logger.info("Creating global DatabaseManager instance")
db_manager = DatabaseManager()

# Log database engine information
logger.info(f"Database engine info: {db_manager.get_engine_info()}")