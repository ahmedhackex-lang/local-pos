"""
System utilities API endpoints
Printer discovery, health checks, diagnostics
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db, backup_database
from auth import require_developer
from printer import printer_manager
from config import settings

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    System health check
    
    Checks database connectivity and basic system status
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "online",
        "database": db_status,
        "printer": "configured" if printer_manager.is_available else "not configured",
        "version": settings.APP_VERSION
    }


@router.get("/printers/discover")
async def discover_printers(current_user = Depends(require_developer)):
    """
    Discover available printers
    
    Requires developer role
    """
    printers = printer_manager.discover_windows_printers()
    
    return {
        "count": len(printers),
        "printers": printers,
        "current": printer_manager.printer_config.get('printer_name') if printer_manager.is_available else None
    }


@router.post("/printers/test")
async def test_printer(current_user = Depends(require_developer)):
    """
    Print test receipt
    
    Requires developer role
    """
    success = printer_manager.print_test_receipt()
    
    if success:
        return {"message": "Test receipt printed successfully"}
    else:
        return {"message": "Print test failed", "status": "error"}


@router.post("/printers/cash-drawer")
async def open_cash_drawer(current_user = Depends(require_developer)):
    """
    Open cash drawer
    
    Requires developer role
    """
    success = printer_manager.open_cash_drawer()
    
    if success:
        return {"message": "Cash drawer opened"}
    else:
        return {"message": "Failed to open cash drawer", "status": "error"}


@router.post("/database/backup")
async def create_backup(current_user = Depends(require_developer)):
    """
    Create database backup
    
    Requires developer role
    """
    backup_path = backup_database()
    
    if backup_path:
        return {
            "success": True,
            "message": "Backup created successfully",
            "path": backup_path
        }
    else:
        return {
            "success": False,
            "message": "Backup failed"
        }


@router.get("/info")
async def system_info(current_user = Depends(require_developer)):
    """
    Get system information
    
    Requires developer role
    """
    import platform
    import sys
    
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "python_version": sys.version,
        "platform": platform.platform(),
        "database_url": settings.DATABASE_URL,
        "sync_enabled": settings.SYNC_ENABLED,
        "printer_enabled": settings.PRINTER_ENABLED
    }