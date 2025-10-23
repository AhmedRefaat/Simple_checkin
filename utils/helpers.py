"""
Helper Functions Module
Provides utility functions used throughout the application.
"""

from datetime import datetime, date, time, timedelta
from typing import List, Tuple, Optional
import calendar

from utils.logger import get_logger
from utils.constants import WorkHours, TimeConstants, UIConstants

logger = get_logger(__name__)


class TimeHelper:
    """Time-related helper functions"""
    
    @staticmethod
    def format_minutes_to_hours(minutes: int) -> str:
        """
        Format minutes into HH:MM format.
        
        Args:
            minutes: Total minutes
            
        Returns:
            Formatted string (e.g., "8:30")
        """
        hours = abs(minutes) // TimeConstants.MINUTES_PER_HOUR
        mins = abs(minutes) % TimeConstants.MINUTES_PER_HOUR
        sign = "-" if minutes < 0 else ""
        return f"{sign}{hours}:{mins:02d}"
    
    @staticmethod
    def format_minutes_split(minutes: int) -> Tuple[int, int]:
        """
        Split minutes into hours and minutes.
        
        Args:
            minutes: Total minutes
            
        Returns:
            Tuple of (hours, minutes)
        """
        hours = minutes // TimeConstants.MINUTES_PER_HOUR
        mins = minutes % TimeConstants.MINUTES_PER_HOUR
        return hours, mins
    
    @staticmethod
    def calculate_time_difference(start_time: time, end_time: time) -> int:
        """
        Calculate difference between two times in minutes.
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            Difference in minutes
        """
        start_datetime = datetime.combine(date.today(), start_time)
        end_datetime = datetime.combine(date.today(), end_time)
        
        # Handle overnight shift (shouldn't happen in this app but good to have)
        if end_datetime < start_datetime:
            end_datetime += timedelta(days=1)
        
        difference = end_datetime - start_datetime
        return int(difference.total_seconds() / 60)
    
    @staticmethod
    def is_late(check_in_time: time) -> bool:
        """
        Check if check-in time is late.
        
        Args:
            check_in_time: Check-in time
            
        Returns:
            True if late, False otherwise
        """
        return check_in_time > WorkHours.LATE_THRESHOLD
    
    @staticmethod
    def get_current_month_name(month: int) -> str:
        """
        Get month name from month number.
        
        Args:
            month: Month number (1-12)
            
        Returns:
            Month name
        """
        return calendar.month_name[month]
    
    @staticmethod
    def get_working_days_in_month(year: int, month: int, holidays: List[date] = None) -> int:
        """
        Calculate working days in a month (excluding Fridays and holidays).
        
        Args:
            year: Year
            month: Month
            holidays: List of holiday dates
            
        Returns:
            Number of working days
        """
        logger.debug(f"Calculating working days for {year}-{month:02d}")
        
        if holidays is None:
            holidays = []
        
        # Get first and last day of month
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        working_days = 0
        current_day = first_day
        
        while current_day <= last_day:
            # Skip Fridays (weekday 4)
            if current_day.weekday() != TimeConstants.WEEKEND_DAY:
                # Skip holidays
                if current_day not in holidays:
                    working_days += 1
            current_day += timedelta(days=1)
        
        logger.debug(f"Working days in {year}-{month:02d}: {working_days}")
        return working_days
    
    @staticmethod
    def get_last_n_working_days(reference_date: date, n: int, holidays: List[date] = None) -> List[date]:
        """
        Get last N working days before a reference date.
        
        Args:
            reference_date: Reference date
            n: Number of working days to get
            holidays: List of holiday dates
            
        Returns:
            List of working day dates
        """
        if holidays is None:
            holidays = []
        
        working_days = []
        current_day = reference_date - timedelta(days=1)
        
        while len(working_days) < n and current_day >= date(2020, 1, 1):  # Reasonable lower bound
            if current_day.weekday() != TimeConstants.WEEKEND_DAY and current_day not in holidays:
                working_days.append(current_day)
            current_day -= timedelta(days=1)
        
        return list(reversed(working_days))
    
    @staticmethod
    def should_show_last_month_data(current_date: date) -> bool:
        """
        Determine if last month's data should be shown.
        
        Args:
            current_date: Current date
            
        Returns:
            True if should show, False otherwise
        """
        return current_date.day <= TimeConstants.LAST_MONTH_DISPLAY_CUTOFF


class CurrencyHelper:
    """Currency formatting helpers"""
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """
        Format amount as currency.
        
        Args:
            amount: Amount to format
            
        Returns:
            Formatted currency string
        """
        return f"{amount:,.2f} {UIConstants.CURRENCY}"
    
    @staticmethod
    def parse_currency(currency_str: str) -> Optional[float]:
        """
        Parse currency string to float.
        
        Args:
            currency_str: Currency string
            
        Returns:
            Float value or None if invalid
        """
        try:
            # Remove currency symbol and commas
            clean_str = currency_str.replace(UIConstants.CURRENCY, "").replace(",", "").strip()
            return float(clean_str)
        except (ValueError, AttributeError):
            return None


class DateHelper:
    """Date-related helper functions"""
    
    @staticmethod
    def format_date(date_obj: date) -> str:
        """
        Format date object to string.
        
        Args:
            date_obj: Date object
            
        Returns:
            Formatted date string
        """
        return date_obj.strftime(UIConstants.DATE_FORMAT)
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[date]:
        """
        Parse date string to date object.
        
        Args:
            date_str: Date string
            
        Returns:
            Date object or None if invalid
        """
        try:
            return datetime.strptime(date_str, UIConstants.DATE_FORMAT).date()
        except ValueError:
            return None
    
    @staticmethod
    def get_month_range(year: int, month: int) -> Tuple[date, date]:
        """
        Get first and last day of a month.
        
        Args:
            year: Year
            month: Month
            
        Returns:
            Tuple of (first_day, last_day)
        """
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        return first_day, last_day