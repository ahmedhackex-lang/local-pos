"""
Pydantic schemas for request/response validation
Type-safe API contracts
"""

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ===== USER SCHEMAS =====

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(..., pattern="^(cashier|admin|owner|developer)$")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ===== PRODUCT SCHEMAS =====

class ProductBase(BaseModel):
    barcode: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    name_urdu: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    unit_of_measure: str = "piece"
    cost_price: Decimal = Field(..., ge=0)
    retail_price: Decimal = Field(..., gt=0)
    stock_quantity: int = Field(default=0, ge=0)
    reorder_alert_level: int = 5
    tax_rate: Decimal = Field(default=0, ge=0, le=100)
    is_weighable: bool = False
    shelf_location: Optional[str] = None
    supplier_name: Optional[str] = None
    notes: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    cost_price: Optional[Decimal] = Field(None, ge=0)
    retail_price: Optional[Decimal] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    reorder_alert_level: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ===== SALE SCHEMAS =====

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0)
    discount_percent: Decimal = Field(default=0, ge=0, le=100)


class SaleItemResponse(BaseModel):
    id: int
    product_id: int
    barcode: str
    product_name: str
    quantity: Decimal
    retail_price_at_sale: Decimal
    discount_amount: Decimal
    subtotal: Decimal
    
    model_config = ConfigDict(from_attributes=True)


class SaleCreate(BaseModel):
    items: List[SaleItemCreate] = Field(..., min_items=1)
    payment_method: str = Field(..., regex="^(Cash|Card|Online|Credit)$")
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    discount: Decimal = Field(default=0, ge=0)
    amount_tendered: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None


class SaleResponse(BaseModel):
    id: int
    invoice_number: str
    cashier_id: int
    cashier_name: str
    total_amount: Decimal
    discount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    payment_method: str
    amount_tendered: Optional[Decimal]
    change_returned: Optional[Decimal]
    is_voided: bool
    created_at: datetime
    items: List[SaleItemResponse]
    
    model_config = ConfigDict(from_attributes=True)


# ===== AUTH SCHEMAS =====

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: int
    username: str
    role: str


# ===== REPORT SCHEMAS =====

class SalesReportParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    cashier_id: Optional[int] = None
    payment_method: Optional[str] = None


class DailySalesReport(BaseModel):
    date: str
    total_sales: Decimal
    total_transactions: int
    cash_sales: Decimal
    card_sales: Decimal
    online_sales: Decimal
    total_discount: Decimal
    total_profit: Decimal


# ===== SYNC SCHEMAS =====

class SyncStatus(BaseModel):
    last_sync: Optional[datetime]
    pending_records: int
    sync_enabled: bool
    last_sync_status: Optional[str]