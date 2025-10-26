"""
Check-in/Check-out Service Module
Handles employee attendance check-in and check-out operations.

This service provides:
- Check-in functionality
- Check-out functionality
- Attendance record retrieval
- Daily attendance validation
- Comments and expenses management

Usage:
    from services.checkin_service import CheckinService
    
    checkin = CheckinService()
    success, record, msg = checkin.check_in(user_id)
"""

from datetime import datetime, date, time
from typing import Optional, Tuple, List
from sqlalchemy import and_

from database.db_manager import db_manager
from database.models import Attendance, User
from services.calculation_service import CalculationService
from utils.constants import DayType, ValidationMessages, LogMessages
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class CheckinService:
    """
    Service for managing employee check-in and check-out operations.
    
    This service handles all attendance-related operations including:
    - Recording check-ins and check-outs
    - Calculating working hours and overtime
    - Managing attendance records
    - Validating attendance constraints
    """
    
    def __init__(self):
        """Initialize check-in service with database manager and calculation service"""
        self.db = db_manager
        self.calculator = CalculationService()
        logger.debug("CheckinService initialized")
    
    def check_in(self, user_id: int, check_in_time: Optional[time] = None) -> Tuple[bool, Optional[Attendance], str]:
        """
        Record employee check-in for today.
        
        This method:
        1. Validates user hasn't already checked in today
        2. Uses current time if not specified
        3. Determines if arrival is late (after 9:30)
        4. Creates attendance record
        
        Args:
            user_id: ID of user checking in
            check_in_time: Check-in time (defaults to current time)
            
        Returns:
            Tuple of (success: bool, attendance: Attendance or None, message: str)
            
        Example:
            >>> checkin = CheckinService()
            >>> success, record, msg = checkin.check_in(user_id=1)
            >>> if success:
            ...     print(f"Checked in at {record.check_in_time}")
        """
        logger.info(f"Check-in request for user ID: {user_id}")
        
        try:
            # Use current time if not specified
            if check_in_time is None:
                check_in_time = datetime.now().time()
                logger.debug(f"Using current time for check-in: {check_in_time}")
            
            # Get today's date
            today = date.today()
            
            with self.db.session_scope() as session:
                # Step 1: Check if user exists
                user = session.query(User).filter_by(user_id=user_id).first()
                if not user:
                    logger.warning(f"User not found: {user_id}")
                    return False, None, "User not found"
                
                # Step 2: Check if already checked in today
                existing_record = session.query(Attendance).filter(
                    and_(
                        Attendance.user_id == user_id,
                        Attendance.attendance_date == today
                    )
                ).first()
                
                if existing_record and existing_record.check_in_time is not None:
                    logger.warning(f"User {user_id} already checked in today")
                    return False, None, ValidationMessages.ALREADY_CHECKED_IN
                
                # Step 3: Check if arrival is late
                is_late = self.calculator.is_late_arrival(check_in_time)
                
                # Step 4: Create or update attendance record
                if existing_record:
                    # Update existing record (if created by admin but not checked in yet)
                    logger.debug(f"Updating existing record for user {user_id}")
                    existing_record.check_in_time = check_in_time
                    existing_record.is_late = is_late
                    existing_record.day_type = DayType.WORKING_DAY.value
                    existing_record.updated_at = datetime.utcnow()
                    attendance = existing_record
                else:
                    # Create new record
                    logger.debug(f"Creating new attendance record for user {user_id}")
                    attendance = Attendance(
                        user_id=user_id,
                        attendance_date=today,
                        check_in_time=check_in_time,
                        check_out_time=None,
                        total_working_minutes=0,
                        overtime_minutes=0,
                        extra_expenses=0.0,
                        comments=None,
                        day_type=DayType.WORKING_DAY.value,
                        is_late=is_late
                    )
                    session.add(attendance)
                
                session.flush()  # Get attendance_id
                
                # Detach from session
                session.expunge(attendance)
                
                # Log the check-in
                logger.info(LogMessages.CHECKIN.format(user_id=user_id, time=check_in_time))
                
                # Prepare response message
                status_msg = " (LATE - after 9:30)" if is_late else " (On time)"
                message = f"Checked in successfully at {check_in_time.strftime('%H:%M')}{status_msg}"
                
                return True, attendance, message
                
        except Exception as e:
            logger.error(f"Error during check-in for user {user_id}: {e}")
            return False, None, f"Check-in failed: {str(e)}"
    
    def check_out(self, user_id: int, check_out_time: Optional[time] = None) -> Tuple[bool, Optional[Attendance], str]:
        """
        Record employee check-out for today.
        
        This method:
        1. Validates user has checked in today
        2. Uses current time if not specified
        3. Calculates total working time
        4. Calculates overtime (positive or negative)
        5. Updates attendance record
        
        Args:
            user_id: ID of user checking out
            check_out_time: Check-out time (defaults to current time)
            
        Returns:
            Tuple of (success: bool, attendance: Attendance or None, message: str)
            
        Example:
            >>> success, record, msg = checkin.check_out(user_id=1)
            >>> if success:
            ...     hours, mins = record.total_working_minutes // 60, record.total_working_minutes % 60
            ...     print(f"Worked: {hours}h {mins}m, Overtime: {record.overtime_minutes}m")
        """
        logger.info(f"Check-out request for user ID: {user_id}")
        
        try:
            # Use current time if not specified
            if check_out_time is None:
                check_out_time = datetime.now().time()
                logger.debug(f"Using current time for check-out: {check_out_time}")
            
            # Get today's date
            today = date.today()
            
            with self.db.session_scope() as session:
                # Step 1: Get today's attendance record
                attendance = session.query(Attendance).filter(
                    and_(
                        Attendance.user_id == user_id,
                        Attendance.attendance_date == today
                    )
                ).first()
                
                # Step 2: Validate check-in exists
                if not attendance or attendance.check_in_time is None:
                    logger.warning(f"No check-in found for user {user_id} today")
                    return False, None, ValidationMessages.NOT_CHECKED_IN
                
                # Step 3: Check if already checked out
                if attendance.check_out_time is not None:
                    logger.warning(f"User {user_id} already checked out today")
                    return False, None, "You have already checked out today"
                
                # Step 4: Validate check-out time is after check-in
                is_valid, error_msg = self.calculator.validate_check_times(
                    attendance.check_in_time, 
                    check_out_time
                )
                if not is_valid:
                    logger.warning(f"Invalid check-out time: {error_msg}")
                    return False, None, error_msg
                
                # Step 5: Calculate working time
                total_minutes = self.calculator.calculate_working_time(
                    attendance.check_in_time,
                    check_out_time
                )
                logger.debug(f"Total working time: {total_minutes} minutes")
                
                # bugfix: comment the overtime calc fn becasuse no implementaion for overtime calc 
                # Also the overtime is set only by admin in this app
                # Step 6: Calculate overtime
                overtime = 0
                # overtime = self.calculator.calculate_overtime(total_minutes)
                # logger.debug(f"Overtime calculated: {overtime} minutes")
                
                # Step 7: Update attendance record
                attendance.check_out_time = check_out_time
                attendance.total_working_minutes = total_minutes
                attendance.overtime_minutes = overtime
                attendance.updated_at = datetime.now()
                
                session.flush()
                
                # Detach from session
                session.expunge(attendance)
                
                # Log the check-out
                logger.info(LogMessages.CHECKOUT.format(user_id=user_id, time=check_out_time))
                
                # Prepare response message with working time breakdown
                hours, minutes = self.calculator.format_minutes_to_hours_minutes(total_minutes)
                overtime_sign = "-" if overtime < 0 else "+"
                overtime_hours, overtime_mins = self.calculator.format_minutes_to_hours_minutes(abs(overtime))
                
                message = (f"Checked out successfully at {check_out_time.strftime('%H:%M')}. "
                          f"Worked: {hours}h {minutes}m. "
                          f"Overtime: {overtime_sign}{overtime_hours}h {overtime_mins}m")
                
                return True, attendance, message
                
        except Exception as e:
            logger.error(f"Error during check-out for user {user_id}: {e}")
            return False, None, f"Check-out failed: {str(e)}"
    
    def get_today_attendance(self, user_id: int) -> Optional[Attendance]:
        """
        Get today's attendance record for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Attendance object or None if no record exists
        """
        logger.debug(f"Fetching today's attendance for user: {user_id}")
        
        try:
            today = date.today()
            
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter(
                    and_(
                        Attendance.user_id == user_id,
                        Attendance.attendance_date == today
                    )
                ).first()
                
                if attendance:
                    session.expunge(attendance)
                    logger.debug(f"Found today's attendance record: {attendance.attendance_id}")
                    return attendance
                else:
                    logger.debug(f"No attendance record found for today")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching today's attendance: {e}")
            return None
    
    def get_attendance_by_date(self, user_id: int, attendance_date: date) -> Optional[Attendance]:
        """
        Get attendance record for a specific date.
        
        Args:
            user_id: User ID
            attendance_date: Date to query
            
        Returns:
            Attendance object or None
        """
        logger.debug(f"Fetching attendance for user {user_id} on {attendance_date}")
        
        try:
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter(
                    and_(
                        Attendance.user_id == user_id,
                        Attendance.attendance_date == attendance_date
                    )
                ).first()
                
                if attendance:
                    session.expunge(attendance)
                    return attendance
                return None
                
        except Exception as e:
            logger.error(f"Error fetching attendance: {e}")
            return None
    
    def get_attendance_for_month(self, user_id: int, year: int, month: int) -> List[Attendance]:
        """
        Get all attendance records for a user in a specific month.
        
        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)
            
        Returns:
            List of Attendance objects sorted by date
        """
        logger.debug(f"Fetching attendance for user {user_id} in {year}-{month:02d}")
        
        try:
            # Calculate month boundaries
            from datetime import timedelta
            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)
            
            with self.db.session_scope() as session:
                records = session.query(Attendance).filter(
                    and_(
                        Attendance.user_id == user_id,
                        Attendance.attendance_date >= first_day,
                        Attendance.attendance_date <= last_day
                    )
                ).order_by(Attendance.attendance_date).all()
                
                # Detach from session
                for record in records:
                    session.expunge(record)
                
                logger.debug(f"Found {len(records)} attendance records")
                return records
                
        except Exception as e:
            logger.error(f"Error fetching monthly attendance: {e}")
            return []
    
    def add_comments(self, attendance_id: int, comments: str) -> Tuple[bool, str]:
        """
        Add or update comments on an attendance record.
        
        Args:
            attendance_id: Attendance record ID
            comments: Comments text
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Adding comments to attendance {attendance_id}")
        
        try:
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter_by(
                    attendance_id=attendance_id
                ).first()
                
                if not attendance:
                    logger.warning(f"Attendance record not found: {attendance_id}")
                    return False, "Attendance record not found"
                
                attendance.comments = comments
                attendance.updated_at = datetime.utcnow()
                
                logger.info(f"Comments added to attendance {attendance_id}")
                return True, "Comments added successfully"
                
        except Exception as e:
            logger.error(f"Error adding comments: {e}")
            return False, f"Failed to add comments: {str(e)}"
    
    def add_extra_expenses(self, attendance_id: int, amount: float) -> Tuple[bool, str]:
        """
        Add or update extra expenses on an attendance record.
        
        Args:
            attendance_id: Attendance record ID
            amount: Expense amount in EGP
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Adding extra expenses to attendance {attendance_id}: {amount} EGP")
        
        try:
            if amount < 0:
                return False, "Extra expenses cannot be negative"
            
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter_by(
                    attendance_id=attendance_id
                ).first()
                
                if not attendance:
                    logger.warning(f"Attendance record not found: {attendance_id}")
                    return False, "Attendance record not found"
                
                attendance.extra_expenses = amount
                attendance.updated_at = datetime.utcnow()
                
                logger.info(f"Extra expenses added: {amount} EGP")
                return True, f"Extra expenses of {amount} EGP added successfully"
                
        except Exception as e:
            logger.error(f"Error adding extra expenses: {e}")
            return False, f"Failed to add expenses: {str(e)}"
    
    def is_checked_in_today(self, user_id: int) -> bool:
        """
        Check if user has checked in today.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if checked in today
        """
        attendance = self.get_today_attendance(user_id)
        return attendance is not None and attendance.check_in_time is not None
    
    def is_checked_out_today(self, user_id: int) -> bool:
        """
        Check if user has checked out today.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if checked out today
        """
        attendance = self.get_today_attendance(user_id)
        return attendance is not None and attendance.check_out_time is not None
    
    def get_current_status(self, user_id: int) -> dict:
        """
        Get current attendance status for user.
        
        Returns dictionary with check-in status, times, and working hours.
        
        Args:
            user_id: User ID
            
        Returns:
            dict: Status information
        """
        logger.debug(f"Getting current status for user: {user_id}")
        
        attendance = self.get_today_attendance(user_id)
        
        if not attendance or not attendance.check_in_time:
            return {
                'checked_in': False,
                'checked_out': False,
                'check_in_time': None,
                'check_out_time': None,
                'is_late': False,
                'working_hours': 0,
                'working_minutes': 0,
                'overtime_minutes': 0
            }
        
        # Calculate current working time if checked in but not out
        working_minutes = 0
        if attendance.check_out_time:
            working_minutes = attendance.total_working_minutes
        else:
            # Calculate current working time
            current_time = datetime.now().time()
            working_minutes = self.calculator.calculate_working_time(
                attendance.check_in_time,
                current_time
            )
        
        hours, mins = self.calculator.format_minutes_to_hours_minutes(working_minutes)
        
        return {
            'checked_in': True,
            'checked_out': attendance.check_out_time is not None,
            'check_in_time': attendance.check_in_time,
            'check_out_time': attendance.check_out_time,
            'is_late': attendance.is_late,
            'working_hours': hours,
            'working_minutes': mins,
            'overtime_minutes': attendance.overtime_minutes if attendance.check_out_time else 0
        }