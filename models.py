"""
Database models for Grocery POS System
Complete schema implementation with all tables
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, CheckConstraint, Index, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """User authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Relationships
    sales = relationship("Sale", back_populates="cashier", foreign_keys="Sale.cashier_id")
    voided_sales = relationship("Sale", back_populates="voider", foreign_keys="Sale.voided_by")
    sessions = relationship("Session", back_populates="cashier")
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('cashier', 'admin', 'owner', 'developer')",
            name="check_user_role"
        ),
    )


class Product(Base):
    """Product master catalog"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    barcode = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    name_urdu = Column(String(255))
    category = Column(String(100), index=True)
    brand = Column(String(100))
    unit_of_measure = Column(String(20), default="piece")
    cost_price = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    retail_price = Column(DECIMAL(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    reorder_alert_level = Column(Integer, default=5)
    minimum_order_quantity = Column(Integer, default=1)
    maximum_discount_percent = Column(DECIMAL(5, 2), default=0.00)
    tax_rate = Column(DECIMAL(5, 2), default=0.00)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_weighable = Column(Boolean, default=False)
    shelf_location = Column(String(50))
    supplier_name = Column(String(100))
    supplier_code = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Relationships
    sale_items = relationship("SaleItem", back_populates="product")
    
    __table_args__ = (
        Index("idx_products_stock_alert", "stock_quantity", "reorder_alert_level"),
    )


class Sale(Base):
    """Sales transaction header"""
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    cashier_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_name = Column(String(100))
    customer_phone = Column(String(20))
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    discount = Column(DECIMAL(10, 2), default=0.00)
    tax_amount = Column(DECIMAL(10, 2), default=0.00)
    net_amount = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(String(30), nullable=False, index=True)
    amount_tendered = Column(DECIMAL(10, 2))
    change_returned = Column(DECIMAL(10, 2))
    notes = Column(Text)
    is_voided = Column(Boolean, default=False, nullable=False, index=True)
    void_reason = Column(Text)
    voided_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    voided_at = Column(DateTime(timezone=True))
    synced = Column(Boolean, default=False, nullable=False, index=True)
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    cashier = relationship("User", back_populates="sales", foreign_keys=[cashier_id])
    voider = relationship("User", back_populates="voided_sales", foreign_keys=[voided_by])
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "payment_method IN ('Cash', 'Card', 'Online', 'Credit')",
            name="check_payment_method"
        ),
    )


class SaleItem(Base):
    """Sales transaction line items"""
    __tablename__ = "sale_items"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    barcode = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    quantity = Column(DECIMAL(10, 3), nullable=False)
    cost_price_at_sale = Column(DECIMAL(10, 2), nullable=False)
    retail_price_at_sale = Column(DECIMAL(10, 2), nullable=False)
    discount_percent = Column(DECIMAL(5, 2), default=0.00)
    discount_amount = Column(DECIMAL(10, 2), default=0.00)
    tax_rate = Column(DECIMAL(5, 2), default=0.00)
    tax_amount = Column(DECIMAL(10, 2), default=0.00)
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")


class Session(Base):
    """Cashier shift tracking"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cashier_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    closed_at = Column(DateTime(timezone=True))
    opening_cash = Column(DECIMAL(10, 2), nullable=False)
    closing_cash = Column(DECIMAL(10, 2))
    expected_cash = Column(DECIMAL(10, 2))
    cash_difference = Column(DECIMAL(10, 2))
    total_sales = Column(DECIMAL(10, 2))
    total_transactions = Column(Integer)
    notes = Column(Text)
    
    # Relationships
    cashier = relationship("User", back_populates="sessions")


class SyncLog(Base):
    """Cloud synchronization audit trail"""
    __tablename__ = "sync_log"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sync_type = Column(String(50), nullable=False)
    records_attempted = Column(Integer, default=0)
    records_succeeded = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(20), index=True)
    error_message = Column(Text)
    details = Column(Text)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'partial', 'failed')",
            name="check_sync_status"
        ),
    )


class Category(Base):
    """Product categories (future enhancement)"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    name_urdu = Column(String(100))
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())