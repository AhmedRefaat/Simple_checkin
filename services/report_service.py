"""
Report Service Module
Handles generation of attendance and salary reports.

This service provides:
- Monthly attendance reports
- Full historical reports
- Current month with last 5 working days from previous month
- Report data aggregation and formatting
- Export functionality support

Usage:
    from services.report_service import ReportService
    
    report = ReportService()
    monthly_data = report.get_monthly_report(user_id, 2025, 10)
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, func

from database.db_manager import db_manager
from database.models import Attendance, User, MonthlySummary
from services.calculation_service import CalculationService
from utils.constants import DayType, TimeConstants
from utils.helpers import TimeHelper, CurrencyHelper
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class ReportService:
    """
    Service for generating attendance and salary reports.
    
    This service aggregates attendance data and generates various
    reports for employees and administrators including:
    - Daily attendance records
    - Monthly summaries
    - Full employment history
    - Financial calculations
    """
    
    def __init__(self):
        """Initialize report service with database manager and calculator"""
        self.db = db_manager
        self.calculator = CalculationService()
        logger.debug("ReportService initialized")
    
    def get_current_month_with_last_days(self, 
                                         user_id: int,
                                         current_date: Optional[date] = None) -> List[Attendance]:
        """
        Get attendance records for current month and last 5 working days of previous month.
        
        According to requirements:
        - Show current month's attendance
        - Show last 5 working days from previous month
        - Last month data shown only until 8th of current month
        
        Args:
            user_id: User ID
            current_date: Reference date (defaults to today)
            
        Returns:
            List of Attendance records sorted by date
        """
        if current_date is None:
            current_date = date.today()
        
        logger.info(f"Getting current month + last 5 days for user {user_id} on {current_date}")
        
        try:
            records = []
            
            # Get current month records
            current_month_records = self._get_attendance_for_month(
                user_id, 
                current_date.year, 
                current_date.month
            )
            records.extend(current_month_records)
            logger.debug(f"Retrieved {len(current_month_records)} records from current month")
            
            # Check if we should show last month's data (only if day <= 8)
            if TimeHelper.should_show_last_month_data(current_date):
                logger.debug("Including last 5 working days from previous month")
                
                # Calculate previous month
                if current_date.month == 1:
                    prev_year = current_date.year - 1
                    prev_month = 12
                else:
                    prev_year = current_date.year
                    prev_month = current_date.month - 1
                
                # Get last day of previous month
                first_of_current = date(current_date.year, current_date.month, 1)
                last_of_previous = first_of_current - timedelta(days=1)
                
                # Get last 5 working days
                last_working_days = self.calculator.get_last_n_working_days(
                    last_of_previous, 
                    5,
                    include_reference=True
                )
                
                # Fetch attendance for these days
                for day in last_working_days:
                    attendance = self._get_attendance_by_date(user_id, day)
                    if attendance:
                        records.append(attendance)
                
                logger.debug(f"Added {len(last_working_days)} days from previous month")
            else:
                logger.debug("Not showing last month data (current day > 8)")
            
            # Sort by date
            records.sort(key=lambda x: x.attendance_date)
            
            logger.info(f"Total records retrieved: {len(records)}")
            return records
            
        except Exception as e:
            logger.error(f"Error getting current month with last days: {e}")
            return []
    
    def get_monthly_report(self, 
                          user_id: int, 
                          year: int, 
                          month: int) -> Dict:
        """
        Generate comprehensive monthly attendance report.
        
        Report includes:
        - All attendance records for the month
        - Working days count
        - Absence days count
        - Total working time (hours and minutes)
        - Total overtime
        - Extra expenses
        - Bonus (admin-set value)
        - Calculated salary
        
        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)
            
        Returns:
            Dictionary with monthly report data
        """
        logger.info(f"Generating monthly report for user {user_id}: {year}-{month:02d}")
        
        try:
            # Get user info
            user = self._get_user(user_id)
            if not user:
                logger.error(f"User not found: {user_id}")
                return {}
            
            # Get attendance records for the month
            attendance_records = self._get_attendance_for_month(user_id, year, month)
            
            # Calculate expected working days in month
            expected_working_days = self.calculator.get_working_days_in_month(year, month)
            
            # Initialize counters
            actual_working_days = 0
            absence_days = 0
            total_working_minutes = 0
            total_overtime_minutes = 0
            total_expenses = 0.0
            
            # Process each attendance record
            for record in attendance_records:
                # Count working days (excluding holidays, vacations, etc.)
                if record.day_type == DayType.WORKING_DAY.value:
                    if record.check_in_time and record.check_out_time:
                        actual_working_days += 1
                        total_working_minutes += record.total_working_minutes
                        total_overtime_minutes += record.overtime_minutes
                    else:
                        # Checked in but not out, or vice versa - count as absence
                        absence_days += 1
                elif record.day_type == DayType.ABSENCE.value:
                    absence_days += 1
                # Vacation and sick leave count as working days
                elif record.day_type in [DayType.NORMAL_VACATION.value, DayType.SICK_LEAVE.value]:
                    actual_working_days += 1
                    # Add standard working time for these days
                    total_working_minutes += WorkHours.STANDARD_WORK_MINUTES
                
                # Sum expenses
                total_expenses += record.extra_expenses
            
            # Calculate absence days (expected - actual - holidays/vacations)
            absence_days = max(0, expected_working_days - actual_working_days - absence_days)
            
            # Get or calculate monthly summary with bonus
            summary = self._get_or_create_monthly_summary(
                user_id, year, month,
                actual_working_days, absence_days,
                total_working_minutes, total_overtime_minutes,
                total_expenses, user.minute_cost
            )
            
            # Format time
            working_hours, working_mins = self.calculator.format_minutes_to_hours_minutes(
                total_working_minutes
            )
            
            # Prepare report
            report = {
                'user_id': user_id,
                'user_name': user.full_name,
                'month': month,
                'year': year,
                'month_name': self.calculator.get_month_name(month),
                'expected_working_days': expected_working_days,
                'actual_working_days': actual_working_days,
                'absence_days': absence_days,
                'working_hours': working_hours,
                'working_minutes': working_mins,
                'total_working_minutes': total_working_minutes,
                'overtime_minutes': total_overtime_minutes,
                'minute_cost': user.minute_cost,
                'bonus': summary.bonus if summary else 0.0,
                'extra_expenses': total_expenses,
                'salary': summary.salary if summary else 0.0,
                'attendance_records': attendance_records
            }
            
            logger.info(f"Monthly report generated: {actual_working_days} days, "
                       f"{total_working_minutes} minutes, {summary.salary if summary else 0} EGP")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")
            return {}
    
    def get_full_report(self, user_id: int) -> Dict:
        """
        Generate full employment history report since join date.
        
        Returns all monthly summaries with cumulative statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with full report data
        """
        logger.info(f"Generating full report for user {user_id}")
        
        try:
            # Get user info
            user = self._get_user(user_id)
            if not user:
                logger.error(f"User not found: {user_id}")
                return {}
            
            # Get all monthly summaries
            monthly_summaries = self._get_all_monthly_summaries(user_id)
            
            # Calculate cumulative totals
            total_working_days = 0
            total_absence_days = 0
            total_working_minutes = 0
            total_overtime_minutes = 0
            total_bonus = 0.0
            total_salary = 0.0
            
            for summary in monthly_summaries:
                total_working_days += summary.working_days
                total_absence_days += summary.absence_days
                total_working_minutes += (summary.total_working_hours * 60 + 
                                         summary.total_working_minutes)
                total_overtime_minutes += summary.overtime_minutes
                total_bonus += summary.bonus
                total_salary += summary.salary
            
            # Format cumulative time
            total_hours, total_mins = self.calculator.format_minutes_to_hours_minutes(
                total_working_minutes
            )
            
            # Prepare full report
            report = {
                'user_id': user_id,
                'user_name': user.full_name,
                'join_date': user.join_date,
                'minute_cost': user.minute_cost,
                'vacation_days_allowed': user.vacation_days_allowed,
                'monthly_summaries': [self._format_monthly_summary(s) for s in monthly_summaries],
                'cumulative_stats': {
                    'total_working_days': total_working_days,
                    'total_absence_days': total_absence_days,
                    'total_working_hours': total_hours,
                    'total_working_minutes': total_mins,
                    'total_overtime_minutes': total_overtime_minutes,
                    'total_bonus': total_bonus,
                    'total_salary': total_salary
                }
            }
            
            logger.info(f"Full report generated: {len(monthly_summaries)} months, "
                       f"{total_working_days} days, {total_salary:.2f} EGP total")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating full report: {e}")
            return {}
    
    def get_all_employees_report(self, year: int, month: int) -> List[Dict]:
        """
        Generate monthly reports for all employees.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            List of monthly report dictionaries for each employee
        """
        logger.info(f"Generating reports for all employees: {year}-{month:02d}")
        
        try:
            # Get all active employees
            with self.db.session_scope() as session:
                users = session.query(User).filter_by(is_active=True).all()
                user_ids = [u.user_id for u in users]
            
            # Generate report for each employee
            reports = []
            for user_id in user_ids:
                report = self.get_monthly_report(user_id, year, month)
                if report:
                    reports.append(report)
            
            logger.info(f"Generated {len(reports)} employee reports")
            return reports
            
        except Exception as e:
            logger.error(f"Error generating all employees report: {e}")
            return []
    
    def get_all_employees_full_report(self) -> List[Dict]:
        """
        Generate full reports for all employees.
        
        Returns:
            List of full report dictionaries for each employee
        """
        logger.info("Generating full reports for all employees")
        
        try:
            # Get all active employees
            with self.db.session_scope() as session:
                users = session.query(User).filter_by(is_active=True).all()
                user_ids = [u.user_id for u in users]
            
            # Generate full report for each employee
            reports = []
            for user_id in user_ids:
                report = self.get_full_report(user_id)
                if report:
                    reports.append(report)
            
            logger.info(f"Generated {len(reports)} full employee reports")
            return reports
            
        except Exception as e:
            logger.error(f"Error generating all employees full reports: {e}")
            return []
    
    # ==================== Private Helper Methods ====================
    
    def _get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            with self.db.session_scope() as session:
                user = session.query(User).filter_by(user_id=user_id).first()
                if user:
                    session.expunge(user)
                return user
        except Exception as e:
            logger.error(f"Error fetching user: {e}")
            return None
    
    def _get_attendance_by_date(self, user_id: int, attendance_date: date) -> Optional[Attendance]:
        """Get attendance record for specific date"""
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
        except Exception as e:
            logger.error(f"Error fetching attendance: {e}")
            return None
    
    def _get_attendance_for_month(self, user_id: int, year: int, month: int) -> List[Attendance]:
        """Get all attendance records for a month"""
        try:
            # Calculate month boundaries
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
                
                return records
        except Exception as e:
            logger.error(f"Error fetching monthly attendance: {e}")
            return []
    
    def _get_or_create_monthly_summary(self, 
                                      user_id: int, 
                                      year: int, 
                                      month: int,
                                      working_days: int,
                                      absence_days: int,
                                      total_minutes: int,
                                      overtime_minutes: int,
                                      expenses: float,
                                      minute_cost: float) -> Optional[MonthlySummary]:
        """Get existing or create new monthly summary"""
        try:
            with self.db.session_scope() as session:
                # Try to get existing summary
                summary = session.query(MonthlySummary).filter(
                    and_(
                        MonthlySummary.user_id == user_id,
                        MonthlySummary.year == year,
                        MonthlySummary.month == month
                    )
                ).first()
                
                # Split minutes into hours and minutes
                hours, mins = self.calculator.format_minutes_to_hours_minutes(total_minutes)
                
                # Calculate salary (bonus is stored separately, default 0)
                bonus = summary.bonus if summary else 0.0
                base_salary, total_salary = self.calculator.calculate_monthly_salary(
                    total_minutes, minute_cost, bonus, expenses
                )
                
                if summary:
                    # Update existing summary
                    summary.working_days = working_days
                    summary.absence_days = absence_days
                    summary.total_working_hours = hours
                    summary.total_working_minutes = mins
                    summary.overtime_minutes = overtime_minutes
                    # Note: bonus is NOT updated here - only admin can change it
                    summary.salary = total_salary
                else:
                    # Create new summary
                    summary = MonthlySummary(
                        user_id=user_id,
                        year=year,
                        month=month,
                        working_days=working_days,
                        absence_days=absence_days,
                        total_working_hours=hours,
                        total_working_minutes=mins,
                        overtime_minutes=overtime_minutes,
                        bonus=0.0,  # Default bonus is 0, admin sets it
                        salary=total_salary
                    )
                    session.add(summary)
                
                session.flush()
                session.expunge(summary)
                return summary
                
        except Exception as e:
            logger.error(f"Error creating/updating monthly summary: {e}")
            return None
    
    def _get_all_monthly_summaries(self, user_id: int) -> List[MonthlySummary]:
        """Get all monthly summaries for a user"""
        try:
            with self.db.session_scope() as session:
                summaries = session.query(MonthlySummary).filter_by(
                    user_id=user_id
                ).order_by(
                    MonthlySummary.year, 
                    MonthlySummary.month
                ).all()
                
                # Detach from session
                for summary in summaries:
                    session.expunge(summary)
                
                return summaries
        except Exception as e:
            logger.error(f"Error fetching monthly summaries: {e}")
            return []
    
    def _format_monthly_summary(self, summary: MonthlySummary) -> Dict:
        """Format monthly summary for display"""
        return {
            'month': summary.month,
            'year': summary.year,
            'month_name': self.calculator.get_month_name(summary.month),
            'working_days': summary.working_days,
            'absence_days': summary.absence_days,
            'working_hours': summary.total_working_hours,
            'working_minutes': summary.total_working_minutes,
            'total_minutes': (summary.total_working_hours * 60 + summary.total_working_minutes),
            'overtime_minutes': summary.overtime_minutes,
            'bonus': summary.bonus,
            'salary': summary.salary
        }