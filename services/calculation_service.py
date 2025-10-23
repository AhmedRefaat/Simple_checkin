"""
Calculation Service Module
Handles all time and financial calculations for attendance tracking.

This service provides:
- Working time calculations
- Late arrival detection
- Salary computations
- Working days calculations

IMPORTANT NOTES:
- Overtime is NOT calculated automatically - it's manually set by admin
- Bonus is a fixed amount (EGP) set by admin per month, default 0
- Total working time per month = Sum of (daily working minutes + daily admin-set overtime)
- Salary = (Total working minutes × minute_cost) + Extra_Expenses + Bonus

Usage:
    from services.calculation_service import CalculationService
    
    calc = CalculationService()
    working_time = calc.calculate_working_time(check_in, check_out)
"""

from datetime import datetime, time, date, timedelta
from typing import Tuple, List, Optional
import calendar

from database.db_manager import db_manager
from database.models import Holiday
from utils.constants import WorkHours, TimeConstants
from utils.helpers import TimeHelper
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class CalculationService:
    """
    Service for performing attendance and salary calculations.
    
    This service handles all mathematical operations related to:
    - Time tracking (working hours only - NOT overtime)
    - Financial calculations (salary with separate bonus and overtime)
    - Calendar operations (working days, holidays)
    
    CRITICAL: 
    - Overtime is a MANUAL value set by admin (not calculated)
    - Bonus is a MANUAL value set by admin (not calculated)
    - Both are independent adjustments to base salary
    """
    
    def __init__(self):
        """Initialize calculation service with database manager"""
        self.db = db_manager
        logger.debug("CalculationService initialized")
    
    def calculate_working_time(self, check_in: time, check_out: time) -> int:
        """
        Calculate total working time in minutes between check-in and check-out.
        
        This method ONLY calculates the actual time between check-in and check-out.
        It does NOT calculate or suggest overtime - that's set by admin.
        
        Args:
            check_in: Check-in time
            check_out: Check-out time
            
        Returns:
            int: Actual working minutes (no overtime included)
            
        Example:
            >>> calc.calculate_working_time(time(9, 0), time(17, 0))
            480  # 8 hours = 480 minutes (just the time difference)
            >>> calc.calculate_working_time(time(9, 30), time(17, 0))
            450  # 7.5 hours = 450 minutes (admin will decide if overtime adjustment needed)
        """
        logger.debug(f"Calculating working time: {check_in} to {check_out}")
        
        # Use helper function to calculate difference
        working_minutes = TimeHelper.calculate_time_difference(check_in, check_out)
        
        logger.debug(f"Working time calculated: {working_minutes} minutes (overtime is separate admin value)")
        return working_minutes
    
    def is_late_arrival(self, check_in: time) -> bool:
        """
        Check if employee arrived late (after 9:30 AM).
        
        Late threshold is defined in WorkHours.LATE_THRESHOLD (9:30 AM).
        Any check-in after this time is considered late and will be highlighted.
        Admin can then decide whether to apply negative overtime adjustment.
        
        Args:
            check_in: Check-in time
            
        Returns:
            bool: True if late, False if on time
            
        Example:
            >>> calc.is_late_arrival(time(9, 15))
            False  # Not late (before 9:30)
            >>> calc.is_late_arrival(time(9, 45))
            True   # Late (after 9:30) - admin can apply penalty via overtime
        """
        is_late = check_in > WorkHours.LATE_THRESHOLD
        
        if is_late:
            logger.info(f"Late arrival detected: {check_in} (threshold: {WorkHours.LATE_THRESHOLD})")
        else:
            logger.debug(f"On-time arrival: {check_in}")
        
        return is_late
    
    def calculate_total_working_minutes_for_month(self,
                                                  daily_records: List[Tuple[int, int]]) -> int:
        """
        Calculate total working minutes for a month including overtime adjustments.
        
        Formula: Total = Sum of (daily_working_minutes + daily_overtime)
        
        Where:
        - daily_working_minutes = actual time worked (check_out - check_in)
        - daily_overtime = admin-set adjustment (can be positive or negative)
        
        Args:
            daily_records: List of tuples (working_minutes, overtime_minutes) for each day
            
        Returns:
            int: Total working minutes for the month
            
        Example:
            >>> records = [(480, 0), (450, 30), (500, -20)]
            >>> calc.calculate_total_working_minutes_for_month(records)
            1440  # (480+0) + (450+30) + (500-20) = 1440 minutes
        """
        logger.debug(f"Calculating total working minutes for {len(daily_records)} days")
        
        total = 0
        for working_mins, overtime_mins in daily_records:
            daily_total = working_mins + overtime_mins
            total += daily_total
            logger.debug(f"Day: {working_mins} min worked + {overtime_mins} OT = {daily_total} min")
        
        logger.info(f"Total working minutes for month: {total} minutes")
        return total
    
    def calculate_monthly_salary(self,
                                total_working_minutes: int,
                                minute_cost: float,
                                bonus: float = 0.0,
                                total_extra_expenses: float = 0.0) -> Tuple[float, float]:
        """
        Calculate monthly salary.
        
        Formula (as per requirements):
        Salary = (Total_Working_Minutes × Minute_Cost) + Extra_Expenses + Bonus
        
        Where:
        - Total_Working_Minutes = Sum of (daily working minutes + daily overtime)
        - Minute_Cost = cost per minute in EGP (set per employee)
        - Extra_Expenses = sum of all daily expenses
        - Bonus = fixed amount set by admin (default 0)
        
        Args:
            total_working_minutes: Total minutes worked in month (including overtime adjustments)
            minute_cost: Cost per minute in EGP
            bonus: Fixed bonus amount in EGP (admin-set, default 0)
            total_extra_expenses: Sum of all extra expenses in month
            
        Returns:
            Tuple of (base_salary, total_salary) in EGP
            
        Example:
            >>> # Employee worked 12,000 total minutes, 5 EGP/min, 1000 bonus, 500 expenses
            >>> calc.calculate_monthly_salary(12000, 5.0, 1000.0, 500.0)
            (60000.0, 61500.0)
            # Base: 12000×5=60000, Total: 60000+500+1000=61500
        """
        logger.info(f"Calculating monthly salary: {total_working_minutes} total minutes @ {minute_cost} EGP/min")
        
        # Base salary from total working time (which already includes overtime adjustments)
        base_salary = total_working_minutes * minute_cost
        
        # Total salary = base + expenses + bonus
        total_salary = base_salary + total_extra_expenses + bonus
        
        logger.info(f"Monthly salary breakdown:")
        logger.info(f"  Base (minutes × cost): {base_salary:.2f} EGP")
        logger.info(f"  Extra expenses: {total_extra_expenses:.2f} EGP")
        logger.info(f"  Bonus (admin-set): {bonus:.2f} EGP")
        logger.info(f"  TOTAL SALARY: {total_salary:.2f} EGP")
        
        return (round(base_salary, 2), round(total_salary, 2))
    
    def get_working_days_in_month(self, year: int, month: int) -> int:
        """
        Calculate number of working days in a month.
        
        Working days exclude:
        - Fridays (weekend in Egypt)
        - Public holidays from database
        
        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            
        Returns:
            int: Number of working days
            
        Example:
            >>> calc.get_working_days_in_month(2025, 1)
            26  # Example: January 2025 has 26 working days
        """
        logger.debug(f"Calculating working days for {year}-{month:02d}")
        
        try:
            # Get holidays from database
            holidays = self.get_holidays_for_month(year, month)
            holiday_dates = [h.holiday_date for h in holidays]
            
            # Use helper function to calculate working days
            working_days = TimeHelper.get_working_days_in_month(year, month, holiday_dates)
            
            logger.debug(f"Working days in {year}-{month:02d}: {working_days} "
                        f"(excluding {len(holiday_dates)} holidays)")
            
            return working_days
            
        except Exception as e:
            logger.error(f"Error calculating working days: {e}")
            # Fallback: calculate without holidays
            return TimeHelper.get_working_days_in_month(year, month, [])
    
    def get_holidays_for_month(self, year: int, month: int) -> List[Holiday]:
        """
        Get all holidays for a specific month.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            List of Holiday objects
        """
        logger.debug(f"Fetching holidays for {year}-{month:02d}")
        
        try:
            # Calculate month date range
            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)
            
            # Query holidays in date range
            with self.db.session_scope() as session:
                holidays = session.query(Holiday).filter(
                    Holiday.holiday_date >= first_day,
                    Holiday.holiday_date <= last_day
                ).all()
                
                # Detach from session
                for holiday in holidays:
                    session.expunge(holiday)
                
                logger.debug(f"Found {len(holidays)} holidays in {year}-{month:02d}")
                return holidays
                
        except Exception as e:
            logger.error(f"Error fetching holidays: {e}")
            return []
    
    def get_all_holidays(self) -> List[Holiday]:
        """
        Get all holidays from database.
        
        Returns:
            List of all Holiday objects
        """
        logger.debug("Fetching all holidays")
        
        try:
            with self.db.session_scope() as session:
                holidays = session.query(Holiday).order_by(Holiday.holiday_date).all()
                
                # Detach from session
                for holiday in holidays:
                    session.expunge(holiday)
                
                logger.debug(f"Retrieved {len(holidays)} total holidays")
                return holidays
                
        except Exception as e:
            logger.error(f"Error fetching all holidays: {e}")
            return []
    
    def is_holiday(self, check_date: date) -> Tuple[bool, Optional[str]]:
        """
        Check if a specific date is a holiday.
        
        Args:
            check_date: Date to check
            
        Returns:
            Tuple of (is_holiday: bool, holiday_name: str or None)
        """
        logger.debug(f"Checking if {check_date} is a holiday")
        
        try:
            with self.db.session_scope() as session:
                holiday = session.query(Holiday).filter_by(holiday_date=check_date).first()
                
                if holiday:
                    logger.debug(f"Date {check_date} is holiday: {holiday.holiday_name}")
                    return True, holiday.holiday_name
                else:
                    logger.debug(f"Date {check_date} is not a holiday")
                    return False, None
                    
        except Exception as e:
            logger.error(f"Error checking holiday status: {e}")
            return False, None
    
    def is_friday(self, check_date: date) -> bool:
        """
        Check if date is Friday (weekend in Egypt).
        
        Args:
            check_date: Date to check
            
        Returns:
            bool: True if Friday
        """
        is_friday = check_date.weekday() == TimeConstants.WEEKEND_DAY
        logger.debug(f"Date {check_date} is Friday: {is_friday}")
        return is_friday
    
    def is_working_day(self, check_date: date) -> bool:
        """
        Check if date is a working day (not Friday and not holiday).
        
        Args:
            check_date: Date to check
            
        Returns:
            bool: True if working day
        """
        logger.debug(f"Checking if {check_date} is working day")
        
        # Check if Friday
        if self.is_friday(check_date):
            logger.debug(f"{check_date} is Friday (weekend)")
            return False
        
        # Check if holiday
        is_hol, _ = self.is_holiday(check_date)
        if is_hol:
            logger.debug(f"{check_date} is a holiday")
            return False
        
        logger.debug(f"{check_date} is a working day")
        return True
    
    def get_last_n_working_days(self, 
                                reference_date: date, 
                                n: int,
                                include_reference: bool = False) -> List[date]:
        """
        Get last N working days before (or including) a reference date.
        
        Excludes Fridays and holidays.
        
        Args:
            reference_date: Reference date to count back from
            n: Number of working days to retrieve
            include_reference: Whether to include reference date in results
            
        Returns:
            List of working day dates (oldest to newest)
        """
        logger.debug(f"Getting last {n} working days before {reference_date}")
        
        try:
            # Get all holidays for efficient lookup
            holidays = self.get_all_holidays()
            holiday_dates = [h.holiday_date for h in holidays]
            
            # Use helper function
            working_days = TimeHelper.get_last_n_working_days(
                reference_date if not include_reference else reference_date + timedelta(days=1),
                n,
                holiday_dates
            )
            
            logger.debug(f"Retrieved {len(working_days)} working days")
            return working_days
            
        except Exception as e:
            logger.error(f"Error getting last working days: {e}")
            return []
    
    def format_minutes_to_hours_minutes(self, total_minutes: int) -> Tuple[int, int]:
        """
        Convert total minutes to hours and minutes.
        
        Args:
            total_minutes: Total minutes
            
        Returns:
            Tuple of (hours, minutes)
            
        Example:
            >>> calc.format_minutes_to_hours_minutes(545)
            (9, 5)  # 9 hours and 5 minutes
        """
        return TimeHelper.format_minutes_split(total_minutes)
    
    def get_month_name(self, month: int) -> str:
        """
        Get month name from month number.
        
        Args:
            month: Month number (1-12)
            
        Returns:
            str: Month name (e.g., "January")
        """
        return calendar.month_name[month]
    
    def validate_check_times(self, check_in: time, check_out: time) -> Tuple[bool, str]:
        """
        Validate that check-in and check-out times are logical.
        
        Ensures check-out is after check-in.
        
        Args:
            check_in: Check-in time
            check_out: Check-out time
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if check_out <= check_in:
            error_msg = "Check-out time must be after check-in time"
            logger.warning(f"Invalid check times: {check_in} to {check_out}")
            return False, error_msg
        
        return True, ""