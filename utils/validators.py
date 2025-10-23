"""
Validators Module
Provides input validation functions for the application.
"""

from datetime import datetime, time, date
from typing import Optional, Tuple
import re

from utils.logger import get_logger
from utils.constants import ValidationMessages, WorkHours

logger = get_logger(__name__)


class Validators:
    """Input validation utilities"""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        Validate username format.
        
        Args:
            username: Username to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating username: {username}")
        
        if not username or len(username.strip()) < 3:
            return False, ValidationMessages.INVALID_USERNAME
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validate password format.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug("Validating password")
        
        if not password or len(password) < 6:
            return False, ValidationMessages.INVALID_PASSWORD
        
        return True, ""
    
    @staticmethod
    def validate_time(time_str: str) -> Tuple[bool, str]:
        """
        Validate time string format (HH:MM:SS or HH:MM).
        
        Args:
            time_str: Time string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating time: {time_str}")
        
        if not time_str:
            return False, ValidationMessages.REQUIRED_FIELD
        
        try:
            # Try parsing with seconds
            datetime.strptime(time_str, "%H:%M:%S")
            return True, ""
        except ValueError:
            try:
                # Try parsing without seconds
                datetime.strptime(time_str, "%H:%M")
                return True, ""
            except ValueError:
                return False, ValidationMessages.INVALID_TIME
    
    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, str]:
        """
        Validate date string format (YYYY-MM-DD).
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating date: {date_str}")
        
        if not date_str:
            return False, ValidationMessages.REQUIRED_FIELD
        
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True, ""
        except ValueError:
            return False, ValidationMessages.INVALID_DATE
    
    @staticmethod
    def validate_minute_cost(cost: float) -> Tuple[bool, str]:
        """
        Validate minute cost value.
        
        Args:
            cost: Cost per minute
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating minute cost: {cost}")
        
        if cost < 0:
            return False, "Minute cost cannot be negative"
        
        if cost > 1000:  # Reasonable upper limit
            return False, "Minute cost seems too high (max 1000 EGP)"
        
        return True, ""
    
    @staticmethod
    def validate_vacation_days(days: int) -> Tuple[bool, str]:
        """
        Validate vacation days count.
        
        Args:
            days: Number of vacation days
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating vacation days: {days}")
        
        if days < 0:
            return False, "Vacation days cannot be negative"
        
        if days > 60:  # Reasonable upper limit
            return False, "Vacation days seem too high (max 60 days)"
        
        return True, ""
    
    @staticmethod
    def validate_overtime(minutes: int) -> Tuple[bool, str]:
        """
        Validate overtime minutes.
        
        Args:
            minutes: Overtime minutes (can be negative)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating overtime: {minutes}")
        
        if abs(minutes) > 720:  # Max 12 hours overtime
            return False, "Overtime cannot exceed ±12 hours (720 minutes)"
        
        return True, ""
    
    @staticmethod
    def validate_required_field(value: any, field_name: str) -> Tuple[bool, str]:
        """
        Validate required field is not empty.
        
        Args:
            value: Field value
            field_name: Name of the field
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.debug(f"Validating required field: {field_name}")
        
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, f"{field_name} is required"
        
        return True, ""