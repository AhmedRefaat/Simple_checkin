"""
Database Package
Handles all database operations, models, and initialization.

This package provides:
- SQLAlchemy ORM models
- Database connection management
- Database initialization utilities
"""

from database.db_manager import db_manager, DatabaseManager
from database.models import User, Attendance, MonthlySummary, Holiday, Base

__all__ = [
    'db_manager',
    'DatabaseManager',
    'User',
    'Attendance',
    'MonthlySummary',
    'Holiday',
    'Base'
]