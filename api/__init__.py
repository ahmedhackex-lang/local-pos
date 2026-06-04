"""
API router aggregation
Exports all route modules
"""

from .auth import router as auth_router
from .products import router as products_router
from .sales import router as sales_router
from .inventory import router as inventory_router
from .reports import router as reports_router
from .sync import router as sync_router
from .users import router as users_router
from .system import router as system_router

__all__ = [
    'auth_router',
    'products_router',
    'sales_router',
    'inventory_router',
    'reports_router',
    'sync_router',
    'users_router',
    'system_router'
]