"""
Utility functions for Grocery POS System
Date formatting, calculations, invoice generation, etc.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from config import settings, constants
import re


# ===== DATE/TIME FORMATTING =====

def format_date(dt: datetime) -> str:
    """Format datetime to DD/MM/YYYY"""
    if not dt:
        return ""
    return dt.strftime(settings.DATE_FORMAT)


def format_time(dt: datetime) -> str:
    """Format datetime to 12-hour time"""
    if not dt:
        return ""
    return dt.strftime(settings.TIME_FORMAT)


def format_datetime(dt: datetime) -> str:
    """Format datetime to DD/MM/YYYY HH:MM:SS AM/PM"""
    if not dt:
        return ""
    return dt.strftime(settings.DATETIME_FORMAT)


# ===== CURRENCY FORMATTING =====

def format_currency(amount: Decimal, currency: str = None) -> str:
    """
    Format decimal amount as currency string
    
    Args:
        amount: Decimal amount
        currency: Currency code (default: PKR)
    
    Returns:
        Formatted string like "PKR 1,234.56"
    """
    if currency is None:
        currency = settings.CURRENCY
    
    # Format with comma separators and 2 decimal places
    formatted = f"{currency} {amount:,.2f}"
    return formatted


def parse_currency(amount_str: str) -> Decimal:
    """
    Parse currency string to Decimal
    
    Args:
        amount_str: String like "1,234.56" or "PKR 1234.56"
    
    Returns:
        Decimal value
    """
    # Remove currency symbol and commas
    cleaned = re.sub(r'[^\d.]', '', amount_str)
    return Decimal(cleaned)


# ===== INVOICE NUMBER GENERATION =====

def generate_invoice_number(db_session) -> str:
    """
    Generate unique invoice number
    Format: PK-POS-YYYYMMDD-XXXX
    
    Args:
        db_session: SQLAlchemy database session
    
    Returns:
        Invoice number string
    """
    from models import Sale
    
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    prefix = f"{constants.INVOICE_PREFIX}-{date_str}-"
    
    # Find last invoice for today
    last_sale = db_session.query(Sale).filter(
        Sale.invoice_number.like(f"{prefix}%")
    ).order_by(Sale.id.desc()).first()
    
    if last_sale:
        # Extract sequence number and increment
        last_seq = int(last_sale.invoice_number.split('-')[-1])
        new_seq = last_seq + 1
    else:
        # First invoice of the day
        new_seq = 1
    
    # Format with leading zeros (4 digits)
    invoice_number = f"{prefix}{new_seq:04d}"
    
    return invoice_number


# ===== BARCODE VALIDATION =====

def validate_ean13(barcode: str) -> bool:
    """
    Validate EAN-13 barcode checksum
    
    Args:
        barcode: 13-digit barcode string
    
    Returns:
        True if valid, False otherwise
    """
    if not barcode.isdigit() or len(barcode) != 13:
        return False
    
    # Calculate checksum
    odd_sum = sum(int(barcode[i]) for i in range(0, 12, 2))
    even_sum = sum(int(barcode[i]) for i in range(1, 12, 2))
    total = odd_sum + (even_sum * 3)
    checksum = (10 - (total % 10)) % 10
    
    return checksum == int(barcode[12])


def validate_upca(barcode: str) -> bool:
    """
    Validate UPC-A barcode checksum
    
    Args:
        barcode: 12-digit barcode string
    
    Returns:
        True if valid, False otherwise
    """
    if not barcode.isdigit() or len(barcode) != 12:
        return False
    
    # Calculate checksum
    odd_sum = sum(int(barcode[i]) for i in range(0, 11, 2))
    even_sum = sum(int(barcode[i]) for i in range(1, 11, 2))
    total = (odd_sum * 3) + even_sum
    checksum = (10 - (total % 10)) % 10
    
    return checksum == int(barcode[11])


def validate_barcode(barcode: str) -> bool:
    """
    Validate barcode (supports EAN-13, UPC-A, or any format)
    
    Args:
        barcode: Barcode string
    
    Returns:
        True if valid format
    """
    # Remove spaces and hyphens
    cleaned = barcode.replace(" ", "").replace("-", "")
    
    if len(cleaned) == 13:
        return validate_ean13(cleaned)
    elif len(cleaned) == 12:
        return validate_upca(cleaned)
    else:
        # Accept any other format (QR codes, custom codes)
        return len(cleaned) > 0


# ===== CALCULATION HELPERS =====

def calculate_change(net_amount: Decimal, tendered: Decimal) -> Decimal:
    """Calculate change to return"""
    change = tendered - net_amount
    return max(change, Decimal('0'))


def calculate_discount_amount(price: Decimal, quantity: Decimal, discount_percent: Decimal) -> Decimal:
    """Calculate discount amount from percentage"""
    subtotal = price * quantity
    discount = subtotal * (discount_percent / Decimal('100'))
    return discount.quantize(Decimal('0.01'))


def calculate_tax_amount(amount: Decimal, tax_rate: Decimal) -> Decimal:
    """Calculate tax amount from rate"""
    tax = amount * (tax_rate / Decimal('100'))
    return tax.quantize(Decimal('0.01'))


def calculate_profit(retail_price: Decimal, cost_price: Decimal, quantity: Decimal) -> Decimal:
    """Calculate profit for line item"""
    profit_per_unit = retail_price - cost_price
    total_profit = profit_per_unit * quantity
    return total_profit


# ===== DATA SANITIZATION =====

def sanitize_phone(phone: str) -> str:
    """
    Sanitize phone number to standard format
    
    Args:
        phone: Raw phone number string
    
    Returns:
        Sanitized phone number
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Pakistani phone format
    if digits.startswith('92'):
        # International format
        return f"+{digits}"
    elif digits.startswith('0'):
        # National format
        return digits
    else:
        # Add leading 0
        return f"0{digits}"


def sanitize_string(text: str, max_length: int = None) -> str:
    """
    Sanitize string input (remove extra spaces, trim)
    
    Args:
        text: Raw string input
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    cleaned = " ".join(text.split())
    
    # Trim to max length
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned


# ===== FILE HELPERS =====

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if '.' not in filename:
        return False
    
    ext = f".{filename.rsplit('.', 1)[1].lower()}"
    return ext in constants.ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """Get file extension"""
    if '.' not in filename:
        return ""
    
    return f".{filename.rsplit('.', 1)[1].lower()}"


# ===== PAGINATION HELPERS =====

def paginate_query(query, page: int = 1, page_size: int = None):
    """
    Paginate SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        page_size: Items per page
    
    Returns:
        Tuple of (items, total_items, total_pages)
    """
    if page_size is None:
        page_size = constants.DEFAULT_PAGE_SIZE
    
    # Enforce max page size
    page_size = min(page_size, constants.MAX_PAGE_SIZE)
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Get total count
    total_items = query.count()
    
    # Get page items
    items = query.limit(page_size).offset(offset).all()
    
    # Calculate total pages
    total_pages = (total_items + page_size - 1) // page_size
    
    return items, total_items, total_pages


# ===== STOCK ALERT CHECKER =====

def check_low_stock(product) -> bool:
    """
    Check if product is low on stock
    
    Args:
        product: Product model instance
    
    Returns:
        True if stock is at or below alert level
    """
    return product.stock_quantity <= product.reorder_alert_level


def get_stock_status(product) -> str:
    """
    Get human-readable stock status
    
    Args:
        product: Product model instance
    
    Returns:
        Status string: "Out of Stock", "Low Stock", "In Stock"
    """
    if product.stock_quantity == 0:
        return "Out of Stock"
    elif check_low_stock(product):
        return "Low Stock"
    else:
        return "In Stock"