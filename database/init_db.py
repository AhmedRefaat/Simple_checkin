"""
Database Initialization Module
Handles initial database setup and seed data creation.

This module provides functions to:
- Initialize database schema
- Create default admin user
- Seed initial data
- Reset database (for development only)

Usage:
    python database/init_db.py
"""
# ==================== Path Setup ====================
# Add parent directory to Python path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== Imports ====================
from datetime import date
import bcrypt
from sqlalchemy.exc import IntegrityError

from database.db_manager import db_manager
from database.models import User, Holiday
from utils.constants import UserRole, DatabaseConstants
from utils.logger import get_logger
from config.config import Config

# Initialize logger
logger = get_logger(__name__)


class DatabaseInitializer:
    """
    Database initialization and setup utilities.
    
    Provides methods to initialize database schema and populate
    initial data required for application to function.
    """
    
    def __init__(self):
        """Initialize database initializer with database manager"""
        self.db = db_manager
        logger.info("DatabaseInitializer created")
    
    def initialize_database(self, create_admin: bool = True, seed_holidays: bool = True):
        """
        Initialize database with schema and initial data.
        
        This method:
        1. Creates all database tables
        2. Creates default admin user (if requested)
        3. Seeds holiday data (if requested)
        
        Args:
            create_admin: Whether to create default admin user
            seed_holidays: Whether to seed holiday data
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Starting database initialization")
        
        try:
            # Step 1: Create all tables
            logger.info("Creating database tables...")
            self.db.create_tables()
            logger.info("✓ Database tables created successfully")
            
            # Step 2: Create default admin user
            if create_admin:
                logger.info("Creating default admin user...")
                admin_created = self.create_default_admin()
                if admin_created:
                    logger.info("✓ Default admin user created successfully")
                else:
                    logger.warning("⚠ Admin user already exists or creation failed")
            
            # Step 3: Seed holiday data
            if seed_holidays:
                logger.info("Seeding holiday data...")
                holidays_count = self.seed_default_holidays()
                logger.info(f"✓ {holidays_count} holidays seeded successfully")
            
            logger.info("=" * 60)
            logger.info("Database initialization completed successfully!")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def create_default_admin(self, 
                           username: str = "admin_fatama", 
                           password: str = "Bata8595",
                           full_name: str = "System Administrator") -> bool:
        """
        Create default administrator account.
        
        Creates an admin user with the specified credentials.
        Password is securely hashed using bcrypt.
        
        Args:
            username: Admin username (default: "admin")
            password: Admin password (default: "admin123")
            full_name: Admin full name
            
        Returns:
            bool: True if created successfully, False if already exists
            
        Warning:
            Change default password in production!
        """
        logger.info(f"Creating admin user: {username}")
        
        try:
            with self.db.session_scope() as session:
                # Check if admin already exists
                existing_admin = session.query(User).filter_by(username=username).first()
                
                if existing_admin:
                    logger.warning(f"Admin user '{username}' already exists")
                    return False
                
                # Hash password using bcrypt
                password_bytes = password.encode('utf-8')
                salt = bcrypt.gensalt(rounds=Config.BCRYPT_ROUNDS)
                password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
                
                # Create admin user object
                admin_user = User(
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    role=UserRole.ADMIN.value,
                    minute_cost=0.0,  # Admin doesn't have salary calculations
                    vacation_days_allowed=DatabaseConstants.DEFAULT_VACATION_DAYS,
                    join_date=date.today(),
                    is_active=True
                )
                
                # Add to database
                session.add(admin_user)
                session.flush()  # Get the user_id
                
                logger.info(f"Admin user created with ID: {admin_user.user_id}")
                logger.warning(f"⚠ Default admin credentials - Username: {username}, Password: {password}")
                logger.warning("⚠ CHANGE THE DEFAULT PASSWORD IN PRODUCTION!")
                
                return True
                
        except IntegrityError as e:
            logger.error(f"Integrity error creating admin: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            raise
    
    def seed_default_holidays(self, year: int = 2025) -> int:
        """
        Seed database with default Egyptian public holidays.
        
        Populates the holidays table with common Egyptian holidays
        for the specified year.
        
        Args:
            year: Year for which to create holidays
            
        Returns:
            int: Number of holidays created
        """
        logger.info(f"Seeding holidays for year {year}")
        
        # Egyptian public holidays for 2025
        # Note: Islamic holidays vary by lunar calendar - these are approximate
        default_holidays = [
            # Fixed holidays
            {'date': date(year, 1, 1), 'name': 'New Year\'s Day', 'type': 'public_holiday'},
            {'date': date(year, 1, 25), 'name': 'Revolution Day (January 25)', 'type': 'public_holiday'},
            {'date': date(year, 4, 25), 'name': 'Sinai Liberation Day', 'type': 'public_holiday'},
            {'date': date(year, 5, 1), 'name': 'Labour Day', 'type': 'public_holiday'},
            {'date': date(year, 6, 30), 'name': 'June 30 Revolution', 'type': 'public_holiday'},
            {'date': date(year, 7, 23), 'name': 'Revolution Day (July 23)', 'type': 'public_holiday'},
            {'date': date(year, 10, 6), 'name': 'Armed Forces Day', 'type': 'public_holiday'},
            
            # Islamic holidays (approximate dates - adjust based on lunar calendar)
            {'date': date(year, 3, 30), 'name': 'Eid al-Fitr (Day 1)', 'type': 'public_holiday'},
            {'date': date(year, 3, 31), 'name': 'Eid al-Fitr (Day 2)', 'type': 'public_holiday'},
            {'date': date(year, 4, 1), 'name': 'Eid al-Fitr (Day 3)', 'type': 'public_holiday'},
            {'date': date(year, 6, 6), 'name': 'Eid al-Adha (Day 1)', 'type': 'public_holiday'},
            {'date': date(year, 6, 7), 'name': 'Eid al-Adha (Day 2)', 'type': 'public_holiday'},
            {'date': date(year, 6, 8), 'name': 'Eid al-Adha (Day 3)', 'type': 'public_holiday'},
            {'date': date(year, 6, 27), 'name': 'Islamic New Year', 'type': 'public_holiday'},
            {'date': date(year, 9, 5), 'name': 'Prophet\'s Birthday', 'type': 'public_holiday'},
            
            # Christian holidays
            {'date': date(year, 1, 7), 'name': 'Coptic Christmas', 'type': 'public_holiday'},
            {'date': date(year, 4, 20), 'name': 'Coptic Easter', 'type': 'public_holiday'},
            {'date': date(year, 4, 21), 'name': 'Sham El Nessim', 'type': 'public_holiday'},
        ]
        
        created_count = 0
        
        try:
            with self.db.session_scope() as session:
                for holiday_data in default_holidays:
                    try:
                        # Check if holiday already exists
                        existing = session.query(Holiday).filter_by(
                            holiday_date=holiday_data['date']
                        ).first()
                        
                        if not existing:
                            # Create new holiday
                            holiday = Holiday(
                                holiday_date=holiday_data['date'],
                                holiday_name=holiday_data['name'],
                                holiday_type=holiday_data['type']
                            )
                            session.add(holiday)
                            created_count += 1
                            logger.debug(f"Added holiday: {holiday_data['name']} on {holiday_data['date']}")
                        else:
                            logger.debug(f"Holiday already exists: {holiday_data['name']}")
                            
                    except IntegrityError:
                        logger.warning(f"Duplicate holiday date: {holiday_data['date']}")
                        continue
                
                session.flush()
                logger.info(f"Successfully seeded {created_count} holidays")
                
        except Exception as e:
            logger.error(f"Error seeding holidays: {e}")
            raise
        
        return created_count
    
    def create_sample_employee(self,
                              username: str,
                              password: str,
                              full_name: str,
                              minute_cost: float = 5.0,
                              join_date: date = None) -> bool:
        """
        Create a sample employee account (useful for testing).
        
        Args:
            username: Employee username
            password: Employee password
            full_name: Employee full name
            minute_cost: Cost per minute in EGP
            join_date: Join date (defaults to today)
            
        Returns:
            bool: True if created successfully
        """
        logger.info(f"Creating sample employee: {username}")
        
        if join_date is None:
            join_date = date.today()
        
        try:
            with self.db.session_scope() as session:
                # Check if user already exists
                existing_user = session.query(User).filter_by(username=username).first()
                
                if existing_user:
                    logger.warning(f"User '{username}' already exists")
                    return False
                
                # Check employee count limit
                employee_count = session.query(User).filter_by(
                    role=UserRole.EMPLOYEE.value
                ).count()
                
                if employee_count >= DatabaseConstants.MAX_EMPLOYEES:
                    logger.error(f"Maximum employee limit reached ({DatabaseConstants.MAX_EMPLOYEES})")
                    return False
                
                # Hash password
                password_bytes = password.encode('utf-8')
                salt = bcrypt.gensalt(rounds=Config.BCRYPT_ROUNDS)
                password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
                
                # Create employee user
                employee = User(
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    role=UserRole.EMPLOYEE.value,
                    minute_cost=minute_cost,
                    vacation_days_allowed=DatabaseConstants.DEFAULT_VACATION_DAYS,
                    join_date=join_date,
                    is_active=True
                )
                
                session.add(employee)
                session.flush()
                
                logger.info(f"Sample employee created with ID: {employee.user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating sample employee: {e}")
            return False
    
    def reset_database(self):
        """
        Reset database by dropping and recreating all tables.
        
        WARNING: This will delete ALL data!
        Only available in debug mode for development/testing.
        
        Raises:
            PermissionError: If not in debug mode
        """
        logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST!")
        
        if not Config.is_debug_mode():
            raise PermissionError("Database reset is only allowed in debug mode")
        
        try:
            # Drop all tables
            logger.info("Dropping all tables...")
            self.db.drop_tables()
            
            # Recreate tables
            logger.info("Recreating tables...")
            self.db.create_tables()
            
            logger.info("✓ Database reset completed successfully")
            
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            raise
    
    def check_database_status(self) -> dict:
        """
        Check database status and return statistics.
        
        Returns:
            dict: Database statistics including table counts
        """
        logger.info("Checking database status")
        
        try:
            with self.db.session_scope() as session:
                # Count records in each table
                user_count = session.query(User).count()
                admin_count = session.query(User).filter_by(role=UserRole.ADMIN.value).count()
                employee_count = session.query(User).filter_by(role=UserRole.EMPLOYEE.value).count()
                holiday_count = session.query(Holiday).count()
                
                status = {
                    'total_users': user_count,
                    'admins': admin_count,
                    'employees': employee_count,
                    'holidays': holiday_count,
                    'max_employees': DatabaseConstants.MAX_EMPLOYEES,
                    'remaining_slots': DatabaseConstants.MAX_EMPLOYEES - employee_count,
                }
                
                logger.info(f"Database status: {status}")
                return status
                
        except Exception as e:
            logger.error(f"Error checking database status: {e}")
            return {}


def main():
    """
    Main function for command-line database initialization.
    
    Run this script directly to initialize the database:
        python database/init_db.py
    """
    print("=" * 60)
    print("Employee Check-in System - Database Initialization")
    print("=" * 60)
    
    # Create initializer
    initializer = DatabaseInitializer()
    
    # Initialize database
    print("\nInitializing database...")
    success = initializer.initialize_database(
        create_admin=True,
        seed_holidays=True
    )
    
    if success:
        print("\n✓ Database initialized successfully!")
        
        # Show database status
        print("\nDatabase Status:")
        print("-" * 60)
        status = initializer.check_database_status()
        for key, value in status.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
        
        print("\n" + "=" * 60)
        print("Default Admin Credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("⚠ CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")
        print("=" * 60)
        
    else:
        print("\n✗ Database initialization failed!")
        print("Check the logs for more details.")


if __name__ == "__main__":
    main()