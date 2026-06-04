"""
Database configuration and session management
SQLite with WAL mode for better concurrency
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from config import settings
import os


# Ensure data directory exists
os.makedirs("./data", exist_ok=True)
os.makedirs("./data/uploads", exist_ok=True)
os.makedirs("./data/exports", exist_ok=True)
os.makedirs("./logs", exist_ok=True)
os.makedirs("./backups", exist_ok=True)


# Create SQLite engine with optimal settings
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Allow multiple threads
        "timeout": 30,  # 30 second lock timeout
    },
    poolclass=StaticPool,  # Single connection pool for SQLite
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)


# Enable WAL mode and other optimizations
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance and concurrency"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
    cursor.execute("PRAGMA cache_size=10000")  # 10000 pages cache
    cursor.execute("PRAGMA foreign_keys=ON")  # Enforce foreign keys
    cursor.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in RAM
    cursor.close()


event.listen(engine, "connect", _set_sqlite_pragma)


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Declarative base for models
Base = declarative_base()


# Dependency for FastAPI routes
def get_db():
    """
    Database session dependency
    Yields a database session and ensures it's closed after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database (create all tables)
def init_db():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized successfully")


# Database backup utility
def backup_database():
    """Create a backup of the database"""
    import shutil
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"./backups/grocery_pos_{timestamp}.db"
    
    try:
        shutil.copy2("./data/grocery_pos.db", backup_path)
        print(f"✓ Database backed up to {backup_path}")
        return backup_path
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return None