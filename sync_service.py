"""
Background cloud synchronization service
Automatically uploads sales data to remote server
"""

import asyncio
import httpx
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Sale, SaleItem, SyncLog
from datetime import datetime
from config import settings, constants
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class SyncService:
    """
    Background service for cloud synchronization
    Runs in separate async task
    """
    
    def __init__(self):
        self.is_running = False
        self.sync_interval = settings.SYNC_INTERVAL_SECONDS
        self.api_endpoint = settings.SYNC_API_ENDPOINT
        self.api_key = settings.SYNC_API_KEY
        self.enabled = settings.SYNC_ENABLED
    
    async def start(self):
        """Start the background sync loop"""
        if not self.enabled:
            logger.info("Sync service disabled in settings")
            return
        
        if not self.api_endpoint or not self.api_key:
            logger.warning("Sync service not configured (missing endpoint or API key)")
            return
        
        self.is_running = True
        logger.info(f"Sync service started (interval: {self.sync_interval}s)")
        
        while self.is_running:
            try:
                await self.sync_sales()
            except Exception as e:
                logger.error(f"Sync error: {e}")
            
            # Wait for next sync interval
            await asyncio.sleep(self.sync_interval)
    
    def stop(self):
        """Stop the sync service"""
        self.is_running = False
        logger.info("Sync service stopped")
    
    async def sync_sales(self):
        """
        Sync unsynced sales to cloud server
        """
        db = SessionLocal()
        
        try:
            # Find unsynced sales
            unsynced_sales = db.query(Sale).filter(
                Sale.synced == False,
                Sale.is_voided == False
            ).limit(constants.SYNC_BATCH_SIZE).all()
            
            if not unsynced_sales:
                # Nothing to sync
                return
            
            logger.info(f"Found {len(unsynced_sales)} unsynced sales")
            
            # Prepare payload
            payload = self._prepare_sales_payload(db, unsynced_sales)
            
            # Send to cloud
            success = await self._upload_to_cloud(payload)
            
            if success:
                # Mark as synced
                for sale in unsynced_sales:
                    sale.synced = True
                    sale.synced_at = datetime.utcnow()
                
                db.commit()
                
                # Log success
                self._log_sync_result(db, 'sales_upload', len(unsynced_sales), len(unsynced_sales), 0, 'success')
                
                logger.info(f"Successfully synced {len(unsynced_sales)} sales")
            else:
                # Log failure
                self._log_sync_result(db, 'sales_upload', len(unsynced_sales), 0, len(unsynced_sales), 'failed')
        
        except Exception as e:
            logger.error(f"Sync exception: {e}")
            db.rollback()
        
        finally:
            db.close()
    
    def _prepare_sales_payload(self, db: Session, sales: List[Sale]) -> List[Dict]:
        """
        Prepare sales data for cloud upload
        
        Args:
            db: Database session
            sales: List of Sale objects
        
        Returns:
            List of sale dictionaries
        """
        payload = []
        
        for sale in sales:
            # Get sale items
            items = db.query(SaleItem).filter(
                SaleItem.sale_id == sale.id
            ).all()
            
            sale_dict = {
                'invoice_number': sale.invoice_number,
                'cashier_id': sale.cashier_id,
                'customer_name': sale.customer_name,
                'customer_phone': sale.customer_phone,
                'total_amount': float(sale.total_amount),
                'discount': float(sale.discount),
                'tax_amount': float(sale.tax_amount),
                'net_amount': float(sale.net_amount),
                'payment_method': sale.payment_method,
                'amount_tendered': float(sale.amount_tendered) if sale.amount_tendered else None,
                'change_returned': float(sale.change_returned) if sale.change_returned else None,
                'notes': sale.notes,
                'created_at': sale.created_at.isoformat(),
                'items': [
                    {
                        'product_id': item.product_id,
                        'barcode': item.barcode,
                        'product_name': item.product_name,
                        'quantity': float(item.quantity),
                        'cost_price': float(item.cost_price_at_sale),
                        'retail_price': float(item.retail_price_at_sale),
                        'discount_amount': float(item.discount_amount),
                        'tax_amount': float(item.tax_amount),
                        'subtotal': float(item.subtotal)
                    }
                    for item in items
                ]
            }
            
            payload.append(sale_dict)
        
        return payload
    
    async def _upload_to_cloud(self, payload: List[Dict]) -> bool:
        """
        Upload sales data to cloud server
        
        Args:
            payload: List of sale dictionaries
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_endpoint}/sync/sales",
                    json=payload,
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json'
                    }
                )
                
                if response.status_code == 200:
                    logger.info("Cloud upload successful")
                    return True
                else:
                    logger.error(f"Cloud upload failed: {response.status_code} - {response.text}")
                    return False
        
        except httpx.TimeoutException:
            logger.error("Cloud upload timeout")
            return False
        
        except Exception as e:
            logger.error(f"Cloud upload error: {e}")
            return False
    
    def _log_sync_result(self, db: Session, sync_type: str, attempted: int, 
                         succeeded: int, failed: int, status: str):
        """
        Log sync operation result
        
        Args:
            db: Database session
            sync_type: Type of sync operation
            attempted: Number of records attempted
            succeeded: Number of successful records
            failed: Number of failed records
            status: Overall status
        """
        sync_log = SyncLog(
            sync_type=sync_type,
            records_attempted=attempted,
            records_succeeded=succeeded,
            records_failed=failed,
            completed_at=datetime.utcnow(),
            status=status
        )
        db.add(sync_log)
        db.commit()
    
    async def manual_sync(self) -> Dict:
        """
        Trigger manual sync (called from API endpoint)
        
        Returns:
            Dictionary with sync results
        """
        db = SessionLocal()
        
        try:
            # Count pending records
            pending_count = db.query(Sale).filter(
                Sale.synced == False,
                Sale.is_voided == False
            ).count()
            
            if pending_count == 0:
                return {
                    'success': True,
                    'message': 'No records to sync',
                    'pending': 0,
                    'synced': 0
                }
            
            # Sync all pending
            await self.sync_sales()
            
            # Check remaining
            remaining = db.query(Sale).filter(
                Sale.synced == False,
                Sale.is_voided == False
            ).count()
            
            synced = pending_count - remaining
            
            return {
                'success': True,
                'message': f'Synced {synced} of {pending_count} records',
                'pending': remaining,
                'synced': synced
            }
        
        finally:
            db.close()


# Global sync service instance
sync_service = SyncService()


async def start_sync_service():
    """
    Start sync service in background
    Called during application startup
    """
    if settings.SYNC_ENABLED:
        asyncio.create_task(sync_service.start())
        logger.info("Sync service task created")