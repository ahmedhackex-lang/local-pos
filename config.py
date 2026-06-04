"""
Configuration management for Grocery POS System
Handles environment variables and application constants
"""

from pydantic import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    APP_NAME: str = "Grocery POS System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/grocery_pos.db"
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_TO_RANDOM_SECRET_KEY_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    
    # Cloud Sync
    SYNC_ENABLED: bool = False
    SYNC_API_ENDPOINT: Optional[str] = None
    SYNC_API_KEY: Optional[str] = None
    SYNC_INTERVAL_SECONDS: int = 60
    
    # Printer
    PRINTER_ENABLED: bool = True
    PRINTER_TYPE: str = "windows"  # windows, usb, serial, network
    PRINTER_NAME: Optional[str] = None
    
    # Business
    STORE_NAME: str = "GROCERY STORE"
    STORE_ADDRESS: str = "123 Main Street"
    STORE_CITY: str = "Islamabad, Pakistan"
    STORE_PHONE: str = "051-1234567"
    CURRENCY: str = "PKR"
    TAX_RATE: float = 0.00
    
    # Locale
    DATE_FORMAT: str = "%d/%m/%Y"
    TIME_FORMAT: str = "%I:%M:%S %p"
    DATETIME_FORMAT: str = "%d/%m/%Y %I:%M:%S %p"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Application Constants
class Constants:
    """Application-wide constants"""
    
    # Roles
    ROLE_CASHIER = "cashier"
    ROLE_ADMIN = "admin"
    ROLE_OWNER = "owner"
    ROLE_DEVELOPER = "developer"
    
    ROLES = [ROLE_CASHIER, ROLE_ADMIN, ROLE_OWNER, ROLE_DEVELOPER]
    
    # Payment Methods
    PAYMENT_CASH = "Cash"
    PAYMENT_CARD = "Card"
    PAYMENT_ONLINE = "Online"
    PAYMENT_CREDIT = "Credit"
    
    PAYMENT_METHODS = [PAYMENT_CASH, PAYMENT_CARD, PAYMENT_ONLINE, PAYMENT_CREDIT]
    
    # Pakistani Currency Denominations
    CURRENCY_DENOMINATIONS = [10, 20, 50, 100, 500, 1000, 5000]
    
    # Invoice Prefix
    INVOICE_PREFIX = "PK-POS"
    
    # Pagination
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 500
    
    # File Upload
    MAX_UPLOAD_SIZE_MB = 10
    ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}
    
    # Sync
    SYNC_BATCH_SIZE = 50
    SYNC_RETRY_ATTEMPTS = 3
    SYNC_RETRY_DELAY_SECONDS = 5


constants = Constants()