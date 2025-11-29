"""
Timezone Helper Module
Provides timezone-aware datetime utilities for Cairo, Egypt.

This module centralizes all timezone operations to ensure consistent
time handling across the application.
"""

from datetime import datetime, date, time
from typing import Optional
import pytz

# Cairo timezone (handles EET/EEST automatically)
CAIRO_TZ = pytz.timezone('Africa/Cairo')


def get_current_cairo_datetime() -> datetime:
    """
    Get current datetime in Cairo timezone.
    
    Returns:
        datetime: Current Cairo time (timezone-aware)
    """
    return datetime.now(CAIRO_TZ)


def get_current_cairo_date() -> date:
    """
    Get current date in Cairo timezone.
    
    Returns:
        date: Current Cairo date
    """
    return get_current_cairo_datetime().date()


def get_current_cairo_time() -> time:
    """
    Get current time in Cairo timezone.
    
    Returns:
        time: Current Cairo time (without timezone info)
    """
    return get_current_cairo_datetime().time()


def utc_to_cairo(utc_dt: datetime) -> datetime:
    """
    Convert UTC datetime to Cairo timezone.
    
    Args:
        utc_dt: UTC datetime (can be naive or aware)
        
    Returns:
        datetime: Cairo timezone datetime
    """
    if utc_dt is None:
        return None
    
    # If naive, assume UTC
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    
    return utc_dt.astimezone(CAIRO_TZ)


def cairo_to_utc(cairo_dt: datetime) -> datetime:
    """
    Convert Cairo datetime to UTC.
    
    Args:
        cairo_dt: Cairo datetime (can be naive or aware)
        
    Returns:
        datetime: UTC datetime
    """
    if cairo_dt is None:
        return None
    
    # If naive, assume Cairo timezone
    if cairo_dt.tzinfo is None:
        cairo_dt = CAIRO_TZ.localize(cairo_dt)
    
    return cairo_dt.astimezone(pytz.utc)


def make_cairo_aware(naive_dt: datetime) -> datetime:
    """
    Make a naive datetime timezone-aware (Cairo).
    
    Args:
        naive_dt: Naive datetime to convert
        
    Returns:
        datetime: Timezone-aware Cairo datetime
    """
    if naive_dt is None:
        return None
    
    if naive_dt.tzinfo is not None:
        return naive_dt.astimezone(CAIRO_TZ)
    
    return CAIRO_TZ.localize(naive_dt)


def format_cairo_datetime(dt: datetime, include_timezone: bool = False) -> str:
    """
    Format datetime for display in Cairo timezone.
    
    Args:
        dt: Datetime to format (UTC or naive)
        include_timezone: Whether to include timezone abbreviation
        
    Returns:
        str: Formatted datetime string
    """
    if dt is None:
        return ""
    
    cairo_dt = utc_to_cairo(dt)
    
    if include_timezone:
        return cairo_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    else:
        return cairo_dt.strftime("%Y-%m-%d %H:%M:%S")


def get_cairo_now_for_display() -> str:
    """
    Get current Cairo time formatted for UI display.
    
    Returns:
        str: Formatted current time (e.g., "2025-11-29 14:30:45")
    """
    return get_current_cairo_datetime().strftime("%Y-%m-%d %H:%M:%S")