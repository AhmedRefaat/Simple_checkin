"""
Database Models Module
Defines SQLAlchemy ORM models for all database tables.

This module contains the object-relational mapping (ORM) models that represent
the database schema. Each class corresponds to a table in the database.

Models:
    - User: Employee and admin user accounts
    - Attendance: Daily check-in/check-out records
    - MonthlySummary: Aggregated monthly attendance data
    - Holiday: Public and company holidays
"""

from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, Time, 
    DateTime, Text, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from utils.logger import get_logger
from utils.constants import UserRole, DayType, WorkHours, DatabaseConstants
import pytz #fix to pound any timezone in DB to UTC and UI to Cairo

# Initialize logger
logger = get_logger(__name__)

# Create base class for declarative models
Base = declarative_base()


class User(Base):
    """
    User model representing employees and administrators.
    
    This model stores all user information including authentication credentials,
    personal details, and employment-related data.
    
    Attributes:
        user_id: Primary key, auto-incrementing
        username: Unique username for login
        password_hash: Bcrypt hashed password
        full_name: Employee's full name
        role: User role (employee or admin)
        minute_cost: Cost per minute in EGP for salary calculation
        vacation_days_allowed: Total vacation days allowed per year
        join_date: Date when employee joined company
        is_active: Account active status
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """
    
    __tablename__ = 'users'
    
    # ==================== Primary Key ====================
    user_id = Column(
        Integer, 
        primary_key=True, 
        autoincrement=True,
        comment="Unique user identifier"
    )
    
    # ==================== Authentication Fields ====================
    username = Column(
        String(50), 
        unique=True, 
        nullable=False,
        comment="Unique username for login"
    )
    
    password_hash = Column(
        String(255), 
        nullable=False,
        comment="Bcrypt hashed password"
    )
    
    # ==================== Personal Information ====================
    full_name = Column(
        String(100), 
        nullable=False,
        comment="Employee's full name"
    )
    
    # ==================== Role and Permissions ====================
    role = Column(
        String(20), 
        nullable=False, 
        default=UserRole.EMPLOYEE.value,
        comment="User role: employee or admin"
    )
    
    # ==================== Employment Details ====================
    minute_cost = Column(
        Float, 
        default=0.0,
        comment="Cost per minute in EGP for salary calculation"
    )
    
    vacation_days_allowed = Column(
        Integer, 
        default=DatabaseConstants.DEFAULT_VACATION_DAYS,
        comment="Total vacation days allowed per year"
    )
    
    join_date = Column(
        Date, 
        nullable=False,
        comment="Date when employee joined company"
    )
    
    # ==================== Account Status ====================
    is_active = Column(
        Boolean, 
        default=True,
        comment="Account active status"
    )
    
    # ==================== Audit Fields ====================
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(pytz.utc), #fix to pound any timezone in DB to UTC and UI to Cairo
        comment="Record creation timestamp (UTC)"
    )
    
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(pytz.utc), #fix to pound any timezone in DB to UTC and UI to Cairo
        onupdate=lambda: datetime.now(pytz.utc), #fix to pound any timezone in DB to UTC and UI to Cairo
        comment="Record last update timestamp"
    )
    
    # ==================== Relationships ====================
    # One-to-many: User has many attendance records
    attendance_records = relationship(
        "Attendance", 
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # One-to-many: User has many monthly summaries
    monthly_summaries = relationship(
        "MonthlySummary",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # ==================== Constraints ====================
    __table_args__ = (
        CheckConstraint(
            f"role IN ('{UserRole.EMPLOYEE.value}', '{UserRole.ADMIN.value}')",
            name='check_user_role'
        ),
        CheckConstraint(
            'minute_cost >= 0',
            name='check_minute_cost_positive'
        ),
        CheckConstraint(
            'vacation_days_allowed >= 0',
            name='check_vacation_days_positive'
        ),
    )
    
    def __repr__(self):
        """String representation of User object"""
        return f"<User(id={self.user_id}, username='{self.username}', role='{self.role}')>"
    
    def to_dict(self) -> dict:
        """
        Convert User object to dictionary.
        
        Returns:
            dict: User data as dictionary (excluding password_hash)
        """
        return {
            'user_id': self.user_id,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'minute_cost': self.minute_cost,
            'vacation_days_allowed': self.vacation_days_allowed,
            'join_date': self.join_date.isoformat() if self.join_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def is_admin(self) -> bool:
        """Check if user is an administrator"""
        return self.role == UserRole.ADMIN.value


class Attendance(Base):
    """
    Attendance model for daily check-in/check-out records.
    
    This model stores individual attendance records including check-in/out times,
    calculated working hours, overtime, expenses, and comments.
    
    Attributes:
        attendance_id: Primary key, auto-incrementing
        user_id: Foreign key to User table
        attendance_date: Date of attendance
        check_in_time: Time when employee checked in
        check_out_time: Time when employee checked out
        total_working_minutes: Calculated total working time
        overtime_minutes: Overtime (positive or negative)
        extra_expenses: Additional expenses for the day
        comments: Employee comments
        day_type: Type of day (working_day, holiday, vacation, etc.)
        is_late: Flag indicating if check-in was after 9:30
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """
    
    __tablename__ = 'attendance'
    
    # ==================== Primary Key ====================
    attendance_id = Column(
        Integer, 
        primary_key=True, 
        autoincrement=True,
        comment="Unique attendance record identifier"
    )
    
    # ==================== Foreign Keys ====================
    user_id = Column(
        Integer, 
        ForeignKey('users.user_id', ondelete='CASCADE'),
        nullable=False,
        comment="Reference to user who owns this attendance record"
    )
    
    # ==================== Date Information ====================
    attendance_date = Column(
        Date, 
        nullable=False,
        comment="Date of attendance"
    )
    
    # ==================== Time Tracking ====================
    check_in_time = Column(
        Time,
        nullable=True,
        comment="Time when employee checked in"
    )
    
    check_out_time = Column(
        Time,
        nullable=True,
        comment="Time when employee checked out"
    )
    
    # ==================== Calculated Fields ====================
    total_working_minutes = Column(
        Integer, 
        default=0,
        comment="Total working time in minutes (calculated)"
    )
    
    overtime_minutes = Column(
        Integer, 
        default=0,
        comment="Overtime in minutes (can be negative for undertime)"
    )
    
    # ==================== Additional Information ====================
    extra_expenses = Column(
        Float, 
        default=0.0,
        comment="Extra expenses for the day in EGP"
    )
    
    comments = Column(
        Text,
        nullable=True,
        comment="Employee comments or notes"
    )
    
    # ==================== Day Classification ====================
    day_type = Column(
        String(20), 
        default=DayType.WORKING_DAY.value,
        comment="Type of day: working_day, holiday, vacation, sick_leave, absence"
    )
    
    is_late = Column(
        Boolean, 
        default=False,
        comment="True if checked in after 9:30 AM"
    )
    
    # ==================== Audit Fields ====================
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(pytz.utc), #fix to pound any timezone in DB to UTC and UI to Cairo
        comment="Record creation timestamp"
    )
    
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(pytz.utc), #fix to pound any timezone in DB to UTC and UI to Cairo 
        onupdate=lambda: datetime.now(pytz.utc), #fix to pound any timezone in DB to UTC and UI to Cairo
        comment="Record last update timestamp"
    )
    
    # ==================== Relationships ====================
    # Many-to-one: Many attendance records belong to one user
    user = relationship(
        "User",
        back_populates="attendance_records"
    )
    
    # ==================== Constraints ====================
    __table_args__ = (
        # Ensure one attendance record per user per day
        UniqueConstraint(
            'user_id', 
            'attendance_date',
            name='unique_user_date'
        ),
        # Validate day type
        CheckConstraint(
            f"day_type IN ("
            f"'{DayType.WORKING_DAY.value}', "
            f"'{DayType.HOLIDAY.value}', "
            f"'{DayType.NORMAL_VACATION.value}', "
            f"'{DayType.SICK_LEAVE.value}', "
            f"'{DayType.ABSENCE.value}')",
            name='check_day_type'
        ),
        # Ensure extra expenses are not negative
        CheckConstraint(
            'extra_expenses >= 0',
            name='check_expenses_positive'
        ),
    )
    
    def __repr__(self):
        """String representation of Attendance object"""
        return (f"<Attendance(id={self.attendance_id}, user_id={self.user_id}, "
                f"date={self.attendance_date}, type={self.day_type})>")
    
    def to_dict(self) -> dict:
        """
        Convert Attendance object to dictionary.
        
        Returns:
            dict: Attendance data as dictionary
        """
        return {
            'attendance_id': self.attendance_id,
            'user_id': self.user_id,
            'attendance_date': self.attendance_date.isoformat() if self.attendance_date else None,
            'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
            'check_out_time': self.check_out_time.isoformat() if self.check_out_time else None,
            'total_working_minutes': self.total_working_minutes,
            'overtime_minutes': self.overtime_minutes,
            'extra_expenses': self.extra_expenses,
            'comments': self.comments,
            'day_type': self.day_type,
            'is_late': self.is_late,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def has_checked_in(self) -> bool:
        """Check if user has checked in for this record"""
        return self.check_in_time is not None
    
    def has_checked_out(self) -> bool:
        """Check if user has checked out for this record"""
        return self.check_out_time is not None
    
    def is_complete(self) -> bool:
        """Check if both check-in and check-out are recorded"""
        return self.has_checked_in() and self.has_checked_out()


class MonthlySummary(Base):
    """
    Monthly summary model for aggregated attendance data.
    
    This model stores pre-calculated monthly statistics for each employee,
    including working days, overtime, bonus, and salary calculations.
    
    Attributes:
        summary_id: Primary key, auto-incrementing
        user_id: Foreign key to User table
        month: Month number (1-12)
        year: Year
        working_days: Number of days worked
        absence_days: Number of days absent
        total_working_hours: Total hours worked
        total_working_minutes: Remaining minutes after hours
        overtime_minutes: Total overtime for the month
        bonus: Calculated bonus in EGP
        salary: Calculated total salary in EGP
        created_at: Record creation timestamp
    """
    
    __tablename__ = 'monthly_summary'
    
    # ==================== Primary Key ====================
    summary_id = Column(
        Integer, 
        primary_key=True, 
        autoincrement=True,
        comment="Unique monthly summary identifier"
    )
    
    # ==================== Foreign Keys ====================
    user_id = Column(
        Integer, 
        ForeignKey('users.user_id', ondelete='CASCADE'),
        nullable=False,
        comment="Reference to user"
    )
    
    # ==================== Period Information ====================
    month = Column(
        Integer, 
        nullable=False,
        comment="Month number (1-12)"
    )
    
    year = Column(
        Integer, 
        nullable=False,
        comment="Year"
    )
    
    # ==================== Attendance Statistics ====================
    working_days = Column(
        Integer, 
        default=0,
        comment="Number of days actually worked"
    )
    
    absence_days = Column(
        Integer, 
        default=0,
        comment="Number of days absent"
    )
    
    # ==================== Time Tracking ====================
    total_working_hours = Column(
        Integer, 
        default=0,
        comment="Total hours worked in the month"
    )
    
    total_working_minutes = Column(
        Integer, 
        default=0,
        comment="Remaining minutes after hours (0-59)"
    )
    
    overtime_minutes = Column(
        Integer, 
        default=0,
        comment="Total overtime minutes (positive or negative)"
    )
    
    # ==================== Financial Calculations ====================
    bonus = Column(
        Float, 
        default=0.0,
        comment="Calculated bonus in EGP (can be negative for penalties)"
    )
    
    salary = Column(
        Float, 
        default=0.0,
        comment="Total calculated salary in EGP"
    )
    
    # ==================== Audit Fields ====================
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(pytz.utc), #fix to pound any timezone in DB to UTC and UI to Cairo
        comment="Record creation timestamp"
    )
    
    # ==================== Relationships ====================
    # Many-to-one: Many summaries belong to one user
    user = relationship(
        "User",
        back_populates="monthly_summaries"
    )
    
    # ==================== Constraints ====================
    __table_args__ = (
        # Ensure one summary per user per month
        UniqueConstraint(
            'user_id', 
            'month', 
            'year',
            name='unique_user_month_year'
        ),
        # Validate month range
        CheckConstraint(
            'month >= 1 AND month <= 12',
            name='check_valid_month'
        ),
        # Validate year range (reasonable bounds)
        CheckConstraint(
            'year >= 2020 AND year <= 2100',
            name='check_valid_year'
        ),
        # Ensure counts are not negative
        CheckConstraint(
            'working_days >= 0',
            name='check_working_days_positive'
        ),
        CheckConstraint(
            'absence_days >= 0',
            name='check_absence_days_positive'
        ),
    )
    
    def __repr__(self):
        """String representation of MonthlySummary object"""
        return (f"<MonthlySummary(id={self.summary_id}, user_id={self.user_id}, "
                f"period={self.year}-{self.month:02d})>")
    
    def to_dict(self) -> dict:
        """
        Convert MonthlySummary object to dictionary.
        
        Returns:
            dict: Monthly summary data as dictionary
        """
        return {
            'summary_id': self.summary_id,
            'user_id': self.user_id,
            'month': self.month,
            'year': self.year,
            'working_days': self.working_days,
            'absence_days': self.absence_days,
            'total_working_hours': self.total_working_hours,
            'total_working_minutes': self.total_working_minutes,
            'overtime_minutes': self.overtime_minutes,
            'bonus': self.bonus,
            'salary': self.salary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Holiday(Base):
    """
    Holiday model for storing public and company holidays.
    
    This model tracks all holidays to exclude them from working day calculations.
    
    Attributes:
        holiday_id: Primary key, auto-incrementing
        holiday_date: Date of the holiday
        holiday_name: Name or description of the holiday
        holiday_type: Type of holiday (public, company, etc.)
        created_at: Record creation timestamp
    """
    
    __tablename__ = 'holidays'
    
    # ==================== Primary Key ====================
    holiday_id = Column(
        Integer, 
        primary_key=True, 
        autoincrement=True,
        comment="Unique holiday identifier"
    )
    
    # ==================== Holiday Information ====================
    holiday_date = Column(
        Date, 
        unique=True, 
        nullable=False,
        comment="Date of the holiday"
    )
    
    holiday_name = Column(
        String(100), 
        nullable=False,
        comment="Name or description of the holiday"
    )
    
    holiday_type = Column(
        String(20), 
        default='public_holiday',
        comment="Type of holiday: public_holiday, company_holiday, etc."
    )
    
    # ==================== Audit Fields ====================
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(pytz.utc), #fix to pound any timezone in DB to UTC and UI to Cairo
        comment="Record creation timestamp"
    )
    
    def __repr__(self):
        """String representation of Holiday object"""
        return f"<Holiday(id={self.holiday_id}, name='{self.holiday_name}', date={self.holiday_date})>"
    
    def to_dict(self) -> dict:
        """
        Convert Holiday object to dictionary.
        
        Returns:
            dict: Holiday data as dictionary
        """
        return {
            'holiday_id': self.holiday_id,
            'holiday_date': self.holiday_date.isoformat() if self.holiday_date else None,
            'holiday_name': self.holiday_name,
            'holiday_type': self.holiday_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# Log module initialization
logger.info("Database models module loaded successfully")