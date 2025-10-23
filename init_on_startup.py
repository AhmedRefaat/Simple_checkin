"""Initialize database on first run"""
import os
from pathlib import Path
from database.init_db import DatabaseInitializer

def ensure_database_exists():
    """Ensure database exists, initialize if needed"""
    db_path = Path("data/attendance.db")
    
    if not db_path.exists():
        print("⚠️ Database not found. Initializing...")
        initializer = DatabaseInitializer()
        initializer.initialize_database()
        print("✅ Database initialized successfully")
    else:
        print("✅ Database already exists")

if __name__ == "__main__":
    ensure_database_exists()
