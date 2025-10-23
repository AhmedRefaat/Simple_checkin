"""
Admin Service Module
Handles administrative operations for attendance management.

This service provides admin-only functionality:
- Modify attendance records (all fields)
- Set/adjust overtime values (per day)
- Set/adjust bonus values (per month)
- Change day types (holiday, vacation, sick leave, etc.)
- Update employee settings (vacation days, minute cost)
- Manage holidays
- Recalculate monthly summaries
- Full access to all employee data

Usage:
    from services.admin_service import AdminService
    
    admin = AdminService()
    success, msg = admin.update_overtime(attendance_id, 30)  # Add 30 min overtime
"""

from datetime import date, datetime, time
from typing import Optional, Tuple, List, Dict
from sqlalchemy import and_

from database.db_manager import db_manager
from database.models import Attendance, User, MonthlySummary, Holiday
from services.calculation_service import CalculationService
from services.report_service import ReportService
from utils.constants import DayType, WorkHours
from utils.validators import Validators
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class AdminService:
    """
    Service for administrative operations.
    
    Provides full control over:
    - Attendance records (create, read, update, delete)
    - Overtime adjustments (manual per-day values)
    - Bonus settings (manual per-month values)
    - Day type management (holidays, vacations, sick leave)
    - Employee settings (vacation allowance, minute cost)
    - Holiday calendar management
    - Monthly summary recalculations
    """
    
    def __init__(self):
        """Initialize admin service with database manager and other services"""
        self.db = db_manager
        self.calculator = CalculationService()
        self.report_service = ReportService()
        logger.debug("AdminService initialized")
    
    # ==================== Attendance Management ====================
    
    def update_attendance_field(self,
                               attendance_id: int,
                               field_name: str,
                               value: any) -> Tuple[bool, str]:
        """
        Update a specific field in an attendance record.
        
        Admin has full access to modify any field in attendance records.
        
        Args:
            attendance_id: Attendance record ID
            field_name: Field name to update
            value: New value
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin updating attendance {attendance_id}: {field_name} = {value}")
        
        try:
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter_by(
                    attendance_id=attendance_id
                ).first()
                
                if not attendance:
                    logger.warning(f"Attendance record not found: {attendance_id}")
                    return False, "Attendance record not found"
                
                # Update the field
                if hasattr(attendance, field_name):
                    setattr(attendance, field_name, value)
                    attendance.updated_at = datetime.utcnow()
                    
                    logger.info(f"Attendance {attendance_id} updated: {field_name} = {value}")
                    return True, f"Field '{field_name}' updated successfully"
                else:
                    logger.warning(f"Invalid field name: {field_name}")
                    return False, f"Invalid field name: {field_name}"
                    
        except Exception as e:
            logger.error(f"Error updating attendance field: {e}")
            return False, f"Failed to update: {str(e)}"
    
    def update_overtime(self, attendance_id: int, overtime_minutes: int) -> Tuple[bool, str]:
        """
        Set overtime value for a specific attendance record.
        
        IMPORTANT: Overtime is a MANUAL adjustment value set by admin.
        It can be positive (bonus time) or negative (penalty time).
        This value is added to actual working minutes in salary calculations.
        
        Args:
            attendance_id: Attendance record ID
            overtime_minutes: Overtime in minutes (can be positive or negative)
            
        Returns:
            Tuple of (success: bool, message: str)
            
        Example:
            >>> # Employee worked 450 min but admin gives +30 min credit
            >>> admin.update_overtime(123, 30)
            >>> # Total for day = 450 + 30 = 480 minutes
        """
        logger.info(f"Admin setting overtime for attendance {attendance_id}: {overtime_minutes} minutes")
        
        # Validate overtime value
        is_valid, error_msg = Validators.validate_overtime(overtime_minutes)
        if not is_valid:
            logger.warning(f"Invalid overtime value: {error_msg}")
            return False, error_msg
        
        try:
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter_by(
                    attendance_id=attendance_id
                ).first()
                
                if not attendance:
                    logger.warning(f"Attendance record not found: {attendance_id}")
                    return False, "Attendance record not found"
                
                # Set overtime (admin-controlled value)
                attendance.overtime_minutes = overtime_minutes
                attendance.updated_at = datetime.utcnow()
                
                logger.info(f"Overtime set: {overtime_minutes} minutes for attendance {attendance_id}")
                
                # Trigger recalculation of monthly summary
                self._trigger_monthly_recalculation(
                    attendance.user_id,
                    attendance.attendance_date.year,
                    attendance.attendance_date.month
                )
                
                sign = "+" if overtime_minutes >= 0 else ""
                return True, f"Overtime set to {sign}{overtime_minutes} minutes"
                
        except Exception as e:
            logger.error(f"Error setting overtime: {e}")
            return False, f"Failed to set overtime: {str(e)}"
    
    def update_bonus(self, user_id: int, year: int, month: int, bonus: float) -> Tuple[bool, str]:
        """
        Set bonus value for a user's monthly summary.
        
        IMPORTANT: Bonus is a FIXED amount (in EGP) set by admin per month.
        It is NOT calculated from overtime - it's an independent value.
        Default is 0 EGP.
        
        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)
            bonus: Bonus amount in EGP (can be positive or negative)
            
        Returns:
            Tuple of (success: bool, message: str)
            
        Example:
            >>> # Give employee 1000 EGP bonus for January 2025
            >>> admin.update_bonus(5, 2025, 1, 1000.0)
        """
        logger.info(f"Admin setting bonus for user {user_id}, {year}-{month:02d}: {bonus} EGP")
        
        try:
            with self.db.session_scope() as session:
                # Get or create monthly summary
                summary = session.query(MonthlySummary).filter(
                    and_(
                        MonthlySummary.user_id == user_id,
                        MonthlySummary.year == year,
                        MonthlySummary.month == month
                    )
                ).first()
                
                if not summary:
                    # Create new summary with bonus
                    logger.debug(f"Creating new monthly summary with bonus")
                    summary = MonthlySummary(
                        user_id=user_id,
                        year=year,
                        month=month,
                        working_days=0,
                        absence_days=0,
                        total_working_hours=0,
                        total_working_minutes=0,
                        overtime_minutes=0,
                        bonus=bonus,
                        salary=0.0
                    )
                    session.add(summary)
                else:
                    # Update existing summary
                    summary.bonus = bonus
                
                session.flush()
                
                logger.info(f"Bonus set: {bonus} EGP for {year}-{month:02d}")
                
                # Recalculate salary with new bonus
                self._trigger_monthly_recalculation(user_id, year, month)
                
                return True, f"Bonus set to {bonus} EGP for {year}-{month:02d}"
                
        except Exception as e:
            logger.error(f"Error setting bonus: {e}")
            return False, f"Failed to set bonus: {str(e)}"
    
    def change_day_type(self,
                       attendance_id: int,
                       day_type: str) -> Tuple[bool, str]:
        """
        Change the type of day for an attendance record.
        
        Day types:
        - working_day: Normal working day
        - holiday: Public or company holiday
        - normal_vacation: Employee vacation
        - sick_leave: Sick leave
        - absence: Employee absence
        
        Args:
            attendance_id: Attendance record ID
            day_type: New day type (use DayType enum values)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin changing day type for attendance {attendance_id}: {day_type}")
        
        # Validate day type
        valid_types = [dt.value for dt in DayType]
        if day_type not in valid_types:
            logger.warning(f"Invalid day type: {day_type}")
            return False, f"Invalid day type. Must be one of: {', '.join(valid_types)}"
        
        try:
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter_by(
                    attendance_id=attendance_id
                ).first()
                
                if not attendance:
                    logger.warning(f"Attendance record not found: {attendance_id}")
                    return False, "Attendance record not found"
                
                old_type = attendance.day_type
                attendance.day_type = day_type
                attendance.updated_at = datetime.utcnow()
                
                logger.info(f"Day type changed from {old_type} to {day_type}")
                
                # Trigger recalculation
                self._trigger_monthly_recalculation(
                    attendance.user_id,
                    attendance.attendance_date.year,
                    attendance.attendance_date.month
                )
                
                return True, f"Day type changed to: {day_type}"
                
        except Exception as e:
            logger.error(f"Error changing day type: {e}")
            return False, f"Failed to change day type: {str(e)}"
    
    def update_check_times(self,
                          attendance_id: int,
                          check_in: Optional[time] = None,
                          check_out: Optional[time] = None) -> Tuple[bool, str]:
        """
        Update check-in and/or check-out times for an attendance record.
        
        Args:
            attendance_id: Attendance record ID
            check_in: New check-in time (None to keep existing)
            check_out: New check-out time (None to keep existing)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin updating check times for attendance {attendance_id}")
        
        try:
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter_by(
                    attendance_id=attendance_id
                ).first()
                
                if not attendance:
                    logger.warning(f"Attendance record not found: {attendance_id}")
                    return False, "Attendance record not found"
                
                # Update check-in if provided
                if check_in is not None:
                    attendance.check_in_time = check_in
                    attendance.is_late = self.calculator.is_late_arrival(check_in)
                    logger.debug(f"Check-in updated to {check_in}")
                
                # Update check-out if provided
                if check_out is not None:
                    attendance.check_out_time = check_out
                    logger.debug(f"Check-out updated to {check_out}")
                
                # Recalculate working time if both times are set
                if attendance.check_in_time and attendance.check_out_time:
                    # Validate times
                    is_valid, error_msg = self.calculator.validate_check_times(
                        attendance.check_in_time,
                        attendance.check_out_time
                    )
                    
                    if not is_valid:
                        return False, error_msg
                    
                    # Recalculate working time
                    working_time = self.calculator.calculate_working_time(
                        attendance.check_in_time,
                        attendance.check_out_time
                    )
                    attendance.total_working_minutes = working_time
                    logger.debug(f"Working time recalculated: {working_time} minutes")
                
                attendance.updated_at = datetime.utcnow()
                
                # Trigger monthly recalculation
                self._trigger_monthly_recalculation(
                    attendance.user_id,
                    attendance.attendance_date.year,
                    attendance.attendance_date.month
                )
                
                return True, "Check times updated successfully"
                
        except Exception as e:
            logger.error(f"Error updating check times: {e}")
            return False, f"Failed to update check times: {str(e)}"
    
    def delete_attendance_record(self, attendance_id: int) -> Tuple[bool, str]:
        """
        Delete an attendance record.
        
        Args:
            attendance_id: Attendance record ID
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin deleting attendance record: {attendance_id}")
        
        try:
            with self.db.session_scope() as session:
                attendance = session.query(Attendance).filter_by(
                    attendance_id=attendance_id
                ).first()
                
                if not attendance:
                    logger.warning(f"Attendance record not found: {attendance_id}")
                    return False, "Attendance record not found"
                
                user_id = attendance.user_id
                year = attendance.attendance_date.year
                month = attendance.attendance_date.month
                
                session.delete(attendance)
                logger.info(f"Attendance record {attendance_id} deleted")
                
                # Trigger recalculation
                self._trigger_monthly_recalculation(user_id, year, month)
                
                return True, "Attendance record deleted successfully"
                
        except Exception as e:
            logger.error(f"Error deleting attendance record: {e}")
            return False, f"Failed to delete record: {str(e)}"
    
    def create_attendance_record(self,
                                user_id: int,
                                attendance_date: date,
                                check_in: Optional[time] = None,
                                check_out: Optional[time] = None,
                                day_type: str = DayType.WORKING_DAY.value) -> Tuple[bool, Optional[Attendance], str]:
        """
        Create a new attendance record manually (admin function).
        
        Args:
            user_id: User ID
            attendance_date: Date of attendance
            check_in: Check-in time (optional)
            check_out: Check-out time (optional)
            day_type: Type of day
            
        Returns:
            Tuple of (success: bool, attendance: Attendance or None, message: str)
        """
        logger.info(f"Admin creating attendance record for user {user_id} on {attendance_date}")
        
        try:
            with self.db.session_scope() as session:
                # Check if record already exists
                existing = session.query(Attendance).filter(
                    and_(
                        Attendance.user_id == user_id,
                        Attendance.attendance_date == attendance_date
                    )
                ).first()
                
                if existing:
                    logger.warning(f"Attendance record already exists for {attendance_date}")
                    return False, None, "Attendance record already exists for this date"
                
                # Calculate working time if both times provided
                total_minutes = 0
                is_late = False
                
                if check_in and check_out:
                    is_valid, error_msg = self.calculator.validate_check_times(check_in, check_out)
                    if not is_valid:
                        return False, None, error_msg
                    
                    total_minutes = self.calculator.calculate_working_time(check_in, check_out)
                    is_late = self.calculator.is_late_arrival(check_in)
                elif check_in:
                    is_late = self.calculator.is_late_arrival(check_in)
                
                # Create attendance record
                attendance = Attendance(
                    user_id=user_id,
                    attendance_date=attendance_date,
                    check_in_time=check_in,
                    check_out_time=check_out,
                    total_working_minutes=total_minutes,
                    overtime_minutes=0,  # Admin can set this separately
                    extra_expenses=0.0,
                    comments=None,
                    day_type=day_type,
                    is_late=is_late
                )
                
                session.add(attendance)
                session.flush()
                
                # Detach from session
                session.expunge(attendance)
                
                logger.info(f"Attendance record created: ID {attendance.attendance_id}")
                
                # Trigger recalculation
                self._trigger_monthly_recalculation(user_id, attendance_date.year, attendance_date.month)
                
                return True, attendance, "Attendance record created successfully"
                
        except Exception as e:
            logger.error(f"Error creating attendance record: {e}")
            return False, None, f"Failed to create record: {str(e)}"
    
    # ==================== Employee Management ====================
    
    def update_vacation_allowance(self, user_id: int, vacation_days: int) -> Tuple[bool, str]:
        """
        Update employee's vacation days allowance.
        
        Args:
            user_id: User ID
            vacation_days: New vacation days allowance
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin updating vacation allowance for user {user_id}: {vacation_days} days")
        
        # Validate vacation days
        is_valid, error_msg = Validators.validate_vacation_days(vacation_days)
        if not is_valid:
            logger.warning(f"Invalid vacation days: {error_msg}")
            return False, error_msg
        
        try:
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    logger.warning(f"User not found: {user_id}")
                    return False, "User not found"
                
                user.vacation_days_allowed = vacation_days
                user.updated_at = datetime.utcnow()
                
                logger.info(f"Vacation allowance updated to {vacation_days} days")
                return True, f"Vacation allowance set to {vacation_days} days"
                
        except Exception as e:
            logger.error(f"Error updating vacation allowance: {e}")
            return False, f"Failed to update: {str(e)}"
    
    def update_minute_cost(self, user_id: int, minute_cost: float) -> Tuple[bool, str]:
        """
        Update employee's minute cost (salary rate).
        
        Args:
            user_id: User ID
            minute_cost: New cost per minute in EGP
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin updating minute cost for user {user_id}: {minute_cost} EGP/min")
        
        # Validate minute cost
        is_valid, error_msg = Validators.validate_minute_cost(minute_cost)
        if not is_valid:
            logger.warning(f"Invalid minute cost: {error_msg}")
            return False, error_msg
        
        try:
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    logger.warning(f"User not found: {user_id}")
                    return False, "User not found"
                
                old_cost = user.minute_cost
                user.minute_cost = minute_cost
                user.updated_at = datetime.utcnow()
                
                logger.info(f"Minute cost updated from {old_cost} to {minute_cost} EGP/min")
                return True, f"Minute cost set to {minute_cost} EGP/minute"
                
        except Exception as e:
            logger.error(f"Error updating minute cost: {e}")
            return False, f"Failed to update: {str(e)}"
    
    # ==================== Holiday Management ====================
    
    def add_holiday(self,
                   holiday_date: date,
                   holiday_name: str,
                   holiday_type: str = "public_holiday") -> Tuple[bool, str]:
        """
        Add a new holiday to the calendar.
        
        Args:
            holiday_date: Date of the holiday
            holiday_name: Name of the holiday
            holiday_type: Type of holiday
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin adding holiday: {holiday_name} on {holiday_date}")
        
        try:
            with self.db.session_scope() as session:
                # Check if holiday already exists
                existing = session.query(Holiday).filter_by(holiday_date=holiday_date).first()
                
                if existing:
                    logger.warning(f"Holiday already exists on {holiday_date}")
                    return False, f"Holiday already exists on {holiday_date}"
                
                # Create new holiday
                holiday = Holiday(
                    holiday_date=holiday_date,
                    holiday_name=holiday_name,
                    holiday_type=holiday_type
                )
                
                session.add(holiday)
                logger.info(f"Holiday added: {holiday_name} on {holiday_date}")
                
                return True, f"Holiday '{holiday_name}' added successfully"
                
        except Exception as e:
            logger.error(f"Error adding holiday: {e}")
            return False, f"Failed to add holiday: {str(e)}"
    
    def remove_holiday(self, holiday_date: date) -> Tuple[bool, str]:
        """
        Remove a holiday from the calendar.
        
        Args:
            holiday_date: Date of the holiday to remove
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin removing holiday on {holiday_date}")
        
        try:
            with self.db.session_scope() as session:
                holiday = session.query(Holiday).filter_by(holiday_date=holiday_date).first()
                
                if not holiday:
                    logger.warning(f"Holiday not found on {holiday_date}")
                    return False, f"No holiday found on {holiday_date}"
                
                holiday_name = holiday.holiday_name
                session.delete(holiday)
                
                logger.info(f"Holiday removed: {holiday_name} on {holiday_date}")
                return True, f"Holiday '{holiday_name}' removed successfully"
                
        except Exception as e:
            logger.error(f"Error removing holiday: {e}")
            return False, f"Failed to remove holiday: {str(e)}"
    
    # ==================== Recalculation ====================
    
    def recalculate_monthly_summary(self, user_id: int, year: int, month: int) -> Tuple[bool, str]:
        """
        Manually trigger recalculation of monthly summary.
        
        This recalculates working days, total time, and salary based on
        current attendance records and settings.
        
        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Admin triggering recalculation for user {user_id}: {year}-{month:02d}")
        
        try:
            # Use report service to regenerate monthly report
            # This will automatically update the monthly summary
            report = self.report_service.get_monthly_report(user_id, year, month)
            
            if report:
                logger.info(f"Monthly summary recalculated successfully")
                return True, f"Monthly summary recalculated: {report['salary']:.2f} EGP"
            else:
                logger.warning("Failed to generate report for recalculation")
                return False, "Failed to recalculate summary"
                
        except Exception as e:
            logger.error(f"Error recalculating monthly summary: {e}")
            return False, f"Failed to recalculate: {str(e)}"
    
    # ==================== Private Helper Methods ====================
    
    def _trigger_monthly_recalculation(self, user_id: int, year: int, month: int):
        """
        Internal method to trigger monthly summary recalculation.
        
        Called automatically when attendance data changes.
        """
        try:
            logger.debug(f"Triggering auto-recalculation for user {user_id}, {year}-{month:02d}")
            self.recalculate_monthly_summary(user_id, year, month)
        except Exception as e:
            logger.error(f"Error in auto-recalculation: {e}")