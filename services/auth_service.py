"""
Authentication Service Module
Handles user authentication, authorization, and session management.

This service provides:
- User login and logout
- Password hashing and verification
- User creation and management
- Role-based access control
- Session validation

Usage:
    from services.auth_service import AuthService
    
    auth = AuthService()
    user = auth.authenticate("username", "password")
"""

import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.exc import IntegrityError

from database.db_manager import db_manager
from database.models import User
from utils.constants import UserRole, ValidationMessages, LogMessages, SessionKeys
from utils.validators import Validators
from utils.logger import get_logger
from config.config import Config

# Initialize logger
logger = get_logger(__name__)


class AuthService:
    """
    Authentication and authorization service.
    
    Provides methods for user authentication, password management,
    and access control throughout the application.
    """
    
    def __init__(self):
        """Initialize authentication service with database manager"""
        self.db = db_manager
        logger.debug("AuthService initialized")
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """
        Authenticate user with username and password.
        
        This method:
        1. Validates input credentials
        2. Looks up user in database
        3. Verifies password hash
        4. Checks if account is active
        
        Args:
            username: User's username
            password: User's plain-text password
            
        Returns:
            Tuple of (success: bool, user: User or None, message: str)
            
        Example:
            success, user, message = auth.authenticate("john", "pass123")
            if success:
                print(f"Welcome {user.full_name}")
            else:
                print(f"Login failed: {message}")
        """
        #Bugfix: ensure that username is handled in "lowercase" only
        username = username.lower().strip()

        logger.info(f"Authentication attempt for user: {username}")
        
        try:
            # Step 1: Validate input
            is_valid, error_msg = Validators.validate_username(username)
            if not is_valid:
                logger.warning(f"Invalid username format: {username}")
                return False, None, error_msg
            
            is_valid, error_msg = Validators.validate_password(password)
            if not is_valid:
                logger.warning(f"Invalid password format for user: {username}")
                return False, None, error_msg
            
            # Step 2: Query user from database
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(username=username).first()
                
                # Check if user exists
                if not user:
                    logger.warning(f"User not found: {username}")
                    return False, None, ValidationMessages.INVALID_CREDENTIALS
                
                # Check if account is active
                if not user.is_active:
                    logger.warning(f"Inactive account login attempt: {username}")
                    return False, None, "Account is inactive. Contact administrator."
                
                # Step 3: Verify password
                password_bytes = password.encode('utf-8')
                password_hash_bytes = user.password_hash.encode('utf-8')
                
                if bcrypt.checkpw(password_bytes, password_hash_bytes):
                    # Authentication successful
                    logger.info(LogMessages.USER_LOGIN.format(username=username))
                    
                    # Detach user from session to use outside context
                    session.expunge(user)
                    
                    return True, user, "Login successful"
                else:
                    # Invalid password
                    logger.warning(f"Invalid password for user: {username}")
                    return False, None, ValidationMessages.INVALID_CREDENTIALS
                    
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            return False, None, "Authentication system error. Please try again."
    
    def create_user(self,
                   username: str,
                   password: str,
                   full_name: str,
                   role: str = UserRole.EMPLOYEE.value,
                   minute_cost: float = 0.0,
                   vacation_days: int = None,
                   join_date: datetime = None) -> Tuple[bool, Optional[User], str]:
        """
        Create a new user account.
        
        This method:
        1. Validates all input data
        2. Checks for duplicate username
        3. Verifies employee count limit
        4. Hashes password securely
        5. Creates user record in database
        
        Args:
            username: Unique username for login
            password: Plain-text password (will be hashed)
            full_name: User's full name
            role: User role (employee or admin)
            minute_cost: Cost per minute in EGP
            vacation_days: Allowed vacation days (defaults to config value)
            join_date: Date joined (defaults to today)
            
        Returns:
            Tuple of (success: bool, user: User or None, message: str)
        """
        #bugfix: ensure that username is handled in "lowercase" only
        username = username.lower().strip()

        logger.info(f"Creating new user: {username}")
        
        try:
            # Step 1: Validate inputs
            is_valid, error_msg = Validators.validate_username(username)
            if not is_valid:
                logger.warning(f"Invalid username: {error_msg}")
                return False, None, error_msg
            
            is_valid, error_msg = Validators.validate_password(password)
            if not is_valid:
                logger.warning(f"Invalid password: {error_msg}")
                return False, None, error_msg
            
            is_valid, error_msg = Validators.validate_required_field(full_name, "Full name")
            if not is_valid:
                logger.warning(f"Invalid full name: {error_msg}")
                return False, None, error_msg
            
            is_valid, error_msg = Validators.validate_minute_cost(minute_cost)
            if not is_valid:
                logger.warning(f"Invalid minute cost: {error_msg}")
                return False, None, error_msg
            
            # Set defaults
            if vacation_days is None:
                vacation_days = Config.DEFAULT_VACATION_DAYS
            
            if join_date is None:
                join_date = datetime.now().date()
            
            # Validate vacation days
            is_valid, error_msg = Validators.validate_vacation_days(vacation_days)
            if not is_valid:
                logger.warning(f"Invalid vacation days: {error_msg}")
                return False, None, error_msg
            
            # Step 2: Check if username already exists and employee limit
            with self.db.session_scope() as session:
                # Check for duplicate username
                existing_user = session.query(User).filter_by(username=username).first()
                if existing_user:
                    logger.warning(f"Username already exists: {username}")
                    return False, None, ValidationMessages.USER_ALREADY_EXISTS
                
                # Check employee count limit (only for employees, not admins)
                if role == UserRole.EMPLOYEE.value:
                    employee_count = session.query(User).filter_by(
                        role=UserRole.EMPLOYEE.value,
                        is_active=True
                    ).count()
                    
                    if employee_count >= Config.MAX_EMPLOYEES:
                        logger.warning(f"Maximum employee limit reached: {Config.MAX_EMPLOYEES}")
                        return False, None, ValidationMessages.MAX_EMPLOYEES_REACHED
                
                # Step 3: Hash password securely
                password_bytes = password.encode('utf-8')
                salt = bcrypt.gensalt(rounds=Config.BCRYPT_ROUNDS)
                password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
                logger.debug(f"Password hashed for user: {username}")
                
                # Step 4: Create user object
                new_user = User(
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    role=role,
                    minute_cost=minute_cost,
                    vacation_days_allowed=vacation_days,
                    join_date=join_date,
                    is_active=True
                )
                
                # Step 5: Add to database
                session.add(new_user)
                session.flush()  # Get the generated user_id
                
                logger.info(f"User created successfully: {username} (ID: {new_user.user_id})")
                
                # Detach from session
                session.expunge(new_user)
                
                return True, new_user, "User created successfully"
                
        except IntegrityError as e:
            logger.error(f"Database integrity error creating user: {e}")
            return False, None, "Username already exists or database constraint violated"
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return False, None, f"Failed to create user: {str(e)}"
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user's password.
        
        Verifies old password before setting new one.
        
        Args:
            user_id: ID of user changing password
            old_password: Current password for verification
            new_password: New password to set
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Password change request for user ID: {user_id}")
        
        try:
            # Validate new password
            is_valid, error_msg = Validators.validate_password(new_password)
            if not is_valid:
                return False, error_msg
            
            with self.db.session_scope() as session:
                # Get user
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    logger.warning(f"User not found for password change: {user_id}")
                    return False, "User not found"
                
                # Verify old password
                old_password_bytes = old_password.encode('utf-8')
                password_hash_bytes = user.password_hash.encode('utf-8')
                
                if not bcrypt.checkpw(old_password_bytes, password_hash_bytes):
                    logger.warning(f"Invalid old password for user: {user_id}")
                    return False, "Current password is incorrect"
                
                # Hash new password
                new_password_bytes = new_password.encode('utf-8')
                salt = bcrypt.gensalt(rounds=Config.BCRYPT_ROUNDS)
                new_password_hash = bcrypt.hashpw(new_password_bytes, salt).decode('utf-8')
                
                # Update password
                user.password_hash = new_password_hash
                user.updated_at = datetime.utcnow()
                
                logger.info(f"Password changed successfully for user: {user_id}")
                return True, "Password changed successfully"
                
        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {e}")
            return False, "Failed to change password"
    
    def reset_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """
        Reset user's password (admin function).
        
        Does not require old password - admin only.
        
        Args:
            user_id: ID of user whose password to reset
            new_password: New password to set
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Password reset for user ID: {user_id}")
        
        try:
            # Validate new password
            is_valid, error_msg = Validators.validate_password(new_password)
            if not is_valid:
                return False, error_msg
            
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    logger.warning(f"User not found for password reset: {user_id}")
                    return False, "User not found"
                
                # Hash new password
                password_bytes = new_password.encode('utf-8')
                salt = bcrypt.gensalt(rounds=Config.BCRYPT_ROUNDS)
                password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
                
                # Update password
                user.password_hash = password_hash
                user.updated_at = datetime.utcnow()
                
                logger.info(f"Password reset successfully for user: {user_id}")
                return True, "Password reset successfully"
                
        except Exception as e:
            logger.error(f"Error resetting password for user {user_id}: {e}")
            return False, "Failed to reset password"
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None if not found
        """
        logger.debug(f"Fetching user by ID: {user_id}")
        
        try:
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if user:
                    session.expunge(user)
                    return user
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User object or None if not found
        """
        #bugfix: ensure that username is handled in "lowercase" only
        username = username.lower().strip()
        
        logger.debug(f"Fetching user by username: {username}")
        
        try:
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(username=username).first()
                
                if user:
                    session.expunge(user)
                    return user
                return None
                
        except Exception as e:
            logger.error(f"Error fetching user {username}: {e}")
            return None
    
    def is_admin(self, user_id: int) -> bool:
        """
        Check if user is an administrator.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user is admin, False otherwise
        """
        user = self.get_user_by_id(user_id)
        return user is not None and user.is_admin()
    
    def deactivate_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Deactivate user account.
        
        Args:
            user_id: ID of user to deactivate
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Deactivating user: {user_id}")
        
        try:
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    return False, "User not found"
                
                user.is_active = False
                user.updated_at = datetime.utcnow()
                
                logger.info(f"User deactivated: {user_id}")
                return True, "User deactivated successfully"
                
        except Exception as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            return False, "Failed to deactivate user"
    
    def activate_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Activate user account.
        
        Args:
            user_id: ID of user to activate
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Activating user: {user_id}")
        
        try:
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    return False, "User not found"
                
                user.is_active = True
                user.updated_at = datetime.utcnow()
                
                logger.info(f"User activated: {user_id}")
                return True, "User activated successfully"
                
        except Exception as e:
            logger.error(f"Error activating user {user_id}: {e}")
            return False, "Failed to activate user"
    
    def get_all_users(self, include_inactive: bool = False) -> list[User]:
        """
        Get all users.
        
        Args:
            include_inactive: Whether to include inactive users
            
        Returns:
            List of User objects
        """
        logger.debug(f"Fetching all users (include_inactive={include_inactive})")
        
        try:
            with self.db.session_scope() as session:
                query = session.query(User)
                
                if not include_inactive:
                    query = query.filter_by(is_active=True)
                
                users = query.all()
                
                # Detach all users from session
                for user in users:
                    session.expunge(user)
                
                logger.debug(f"Retrieved {len(users)} users")
                return users
                
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            return []
    
    def get_all_employees(self, include_inactive: bool = False) -> list[User]:
        """
        Get all employee users (excluding admins).
        
        Args:
            include_inactive: Whether to include inactive users
            
        Returns:
            List of User objects with employee role
        """
        logger.debug(f"Fetching all employees (include_inactive={include_inactive})")
        
        try:
            with self.db.session_scope() as session:
                query = session.query(User).filter_by(role=UserRole.EMPLOYEE.value)
                
                if not include_inactive:
                    query = query.filter_by(is_active=True)
                
                employees = query.all()
                
                # Detach all from session
                for emp in employees:
                    session.expunge(emp)
                
                logger.debug(f"Retrieved {len(employees)} employees")
                return employees
                
        except Exception as e:
            logger.error(f"Error fetching employees: {e}")
            return []
    
    def update_user_profile(self, user_id: int, **kwargs) -> Tuple[bool, str]:
        """
        Update user profile information.
        
        Args:
            user_id: User ID
            **kwargs: Fields to update (full_name, minute_cost, vacation_days_allowed, etc.)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Updating profile for user: {user_id}")
        
        try:
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    return False, "User not found"
                
                # Update allowed fields
                allowed_fields = ['full_name', 'minute_cost', 'vacation_days_allowed', 'join_date']
                
                for field, value in kwargs.items():
                    if field in allowed_fields and value is not None:
                        setattr(user, field, value)
                        logger.debug(f"Updated {field} for user {user_id}")
                
                user.updated_at = datetime.utcnow()
                
                logger.info(f"Profile updated for user: {user_id}")
                return True, "Profile updated successfully"
                
        except Exception as e:
            logger.error(f"Error updating profile for user {user_id}: {e}")
            return False, "Failed to update profile"
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        """
        Change user password after verifying old password.
        
        Args:
            user_id: User ID
            old_password: Current password for verification
            new_password: New password to set
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Get user
            user = self.db.get_session().query(User).filter_by(user_id=user_id).first()
            
            if not user:
                logger.warning(f"Password change failed: User {user_id} not found")
                return False, "User not found"
            
            # Verify old password
            old_password_bytes = old_password.encode('utf-8')
            password_hash_bytes = user.password_hash.encode('utf-8')

            if not bcrypt.checkpw(old_password_bytes, password_hash_bytes):
                logger.warning(f"Invalid old password for user: {user_id}")
                return False, "Current password is incorrect"
            
            # Validate new password
            if len(new_password) < 6:
                return False, "New password must be at least 6 characters long"
            
            if old_password == new_password:
                return False, "New password must be different from current password"
            
            # Hash and update password
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            user.password_hash = password_hash.decode('utf-8')
            user.updated_at = datetime.now()
            
            self.db.get_session().commit()
            logger.info(f"Password changed successfully for user {user_id}")
            
            return True, "Password changed successfully"
            
        except Exception as e:
            self.db.get_session().rollback()
            logger.error(f"Error changing password for user {user_id}: {str(e)}")
            return False, f"Failed to change password: {str(e)}"