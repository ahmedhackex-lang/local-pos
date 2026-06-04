"""
Cloud synchronization API endpoints
Manual sync triggers, sync status
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Sale, SyncLog
from auth import require_developer
from sync_service import sync_service

router = APIRouter()


@router.post("/manual")
async def trigger_manual_sync(current_user = Depends(require_developer)):
    """
    Trigger manual synchronization
    
    Requires developer role
    """
    result = await sync_service.manual_sync()
    return result


@router.get("/status")
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user = Depends(require_developer)
):
    """
    Get synchronization status
    
    Requires developer role
    """
    # Count pending records
    pending_sales = db.query(Sale).filter(
        Sale.synced == False,
        Sale.is_voided == False
    ).count()
    
    # Get last sync log
    last_sync = db.query(SyncLog).order_by(
        SyncLog.started_at.desc()
    ).first()
    
    return {
        'enabled': sync_service.enabled,
        'is_running': sync_service.is_running,
        'pending_records': pending_sales,
        'last_sync': {
            'timestamp': last_sync.started_at if last_sync else None,
            'status': last_sync.status if last_sync else None,
            'records_synced': last_sync.records_succeeded if last_sync else 0,
            'errors': last_sync.records_failed if last_sync else 0
        } if last_sync else None
    }


@router.get("/history")
async def get_sync_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(require_developer)
):
    """
    Get synchronization history
    
    Requires developer role
    """
    logs = db.query(SyncLog).order_by(
        SyncLog.started_at.desc()
    ).limit(limit).all()
    
    return [
        {
            'id': log.id,
            'sync_type': log.sync_type,
            'started_at': log.started_at,
            'completed_at': log.completed_at,
            'status': log.status,
            'records_attempted': log.records_attempted,
            'records_succeeded': log.records_succeeded,
            'records_failed': log.records_failed,
            'error_message': log.error_message
        }
        for log in logs
    ]