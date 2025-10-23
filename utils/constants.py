"""
Constants Module
Defines all constant values used throughout the application.
"""

from enum import Enum
from datetime import time


class UserRole(Enum):
    """User roles in the system"""
    EMPLOYEE = "employee"
    ADMIN = "admin"


class DayType(Enum):
    """Types of days for attendance tracking"""
    WORKING_DAY = "working_day"
    HOLIDAY = "holiday"
    NORMAL_VACATION = "normal_vacation"
    SICK_LEAVE = "sick_leave"
    ABSENCE = "absence"


class SessionKeys(Enum):
    """Session storage keys"""
    USER_ID = "user_id"
    USERNAME = "username"
    FULL_NAME = "full_name"
    ROLE = "role"
    AUTHENTICATED = "authenticated"
    LOGIN_TIME = "login_time"


class WorkHours:
    """Working hours constants"""
    WORK_START = time(9, 0)  # 9:00 AM
    WORK_END = time(17, 0)    # 5:00 PM
    LATE_THRESHOLD = time(9, 30)  # 9:30 AM
    STANDARD_WORK_MINUTES = 480  # 8 hours * 60 minutes
    STANDARD_WORK_HOURS = 8


class TimeConstants:
    """Time-related constants"""
    MINUTES_PER_HOUR = 60
    HOURS_PER_DAY = 24
    DAYS_PER_WEEK = 7
    MONTHS_PER_YEAR = 12
    WEEKEND_DAY = 4  # Friday (0=Monday, 4=Friday)
    LAST_MONTH_DISPLAY_CUTOFF = 8  # Show last month data until 8th


class DatabaseConstants:
    """Database configuration constants"""
    DB_NAME = "attendance.db"
    DB_FOLDER = "data"
    DEFAULT_VACATION_DAYS = 21
    MAX_EMPLOYEES = 15


class UIConstants:
    """UI-related constants"""
    PAGE_TITLE = "Employee Check-in System"
    PAGE_ICON = "👤"
    LAYOUT = "wide"
    CURRENCY = "EGP"
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M:%S"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class ValidationMessages:
    """Validation error messages"""
    INVALID_USERNAME = "Username must be at least 3 characters"
    INVALID_PASSWORD = "Password must be at least 6 characters"
    INVALID_TIME = "Invalid time format"
    INVALID_DATE = "Invalid date format"
    REQUIRED_FIELD = "This field is required"
    ALREADY_CHECKED_IN = "You have already checked in today"
    NOT_CHECKED_IN = "You must check in before checking out"
    INVALID_CREDENTIALS = "Invalid username or password"
    UNAUTHORIZED_ACCESS = "You don't have permission to access this resource"
    USER_ALREADY_EXISTS = "Username already exists"
    INVALID_EMPLOYEE_ID = "Invalid employee ID"
    INVALID_DATE_RANGE = "Invalid date range"
    MAX_EMPLOYEES_REACHED = f"Maximum {DatabaseConstants.MAX_EMPLOYEES} employees allowed"


class SuccessMessages:
    """Success messages"""
    LOGIN_SUCCESS = "Login successful"
    LOGOUT_SUCCESS = "Logged out successfully"
    CHECKIN_SUCCESS = "Checked in successfully"
    CHECKOUT_SUCCESS = "Checked out successfully"
    UPDATE_SUCCESS = "Updated successfully"
    DELETE_SUCCESS = "Deleted successfully"
    CREATE_SUCCESS = "Created successfully"


class LogMessages:
    """Logging message templates"""
    USER_LOGIN = "User {username} logged in"
    USER_LOGOUT = "User {username} logged out"
    CHECKIN = "User {user_id} checked in at {time}"
    CHECKOUT = "User {user_id} checked out at {time}"
    DB_ERROR = "Database error: {error}"
    VALIDATION_ERROR = "Validation error: {error}"
    CALCULATION_ERROR = "Calculation error: {error}"