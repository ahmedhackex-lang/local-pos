"""
Product management API endpoints
CRUD operations, barcode lookup, search
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse
from auth import get_current_user, require_admin
from utils import paginate_query, check_low_stock

router = APIRouter()


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get paginated list of products
    
    Supports filtering by search term, category, active status, and stock level
    """
    query = db.query(Product)
    
    # Filter by active status
    if active_only:
        query = query.filter(Product.is_active == True)
    
    # Filter by category
    if category:
        query = query.filter(Product.category == category)
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) |
            (Product.barcode.ilike(search_term)) |
            (Product.category.ilike(search_term)) |
            (Product.brand.ilike(search_term))
        )
    
    # Low stock filter
    if low_stock_only:
        query = query.filter(Product.stock_quantity <= Product.reorder_alert_level)
    
    # Order by name
    query = query.order_by(Product.name)
    
    # Paginate
    products = query.offset(skip).limit(limit).all()
    
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/barcode/{barcode}", response_model=ProductResponse)
async def get_product_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Lookup product by barcode
    
    Used by cashier interface for scanning
    """
    product = db.query(Product).filter(
        Product.barcode == barcode,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with barcode '{barcode}' not found"
        )
    
    # Check stock
    if product.stock_quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Product '{product.name}' is out of stock"
        )
    
    return ProductResponse.model_validate(product)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse.model_validate(product)


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Create new product
    
    Requires admin role
    """
    # Check if barcode already exists
    existing = db.query(Product).filter(
        Product.barcode == product_data.barcode
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Product with barcode '{product_data.barcode}' already exists"
        )
    
    # Create product
    product = Product(
        **product_data.dict(),
        created_by=current_user.id
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Update product
    
    Requires admin role
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update fields
    update_data = product_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Soft delete product (set is_active = False)
    
    Requires admin role
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = False
    db.commit()
    
    return {"message": "Product deactivated successfully"}


@router.get("/categories/list")
async def get_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get list of all unique categories
    """
    categories = db.query(Product.category).distinct().filter(
        Product.category.isnot(None),
        Product.is_active == True
    ).all()
    
    return [cat[0] for cat in categories if cat[0]]


@router.get("/stock/alerts")
async def get_stock_alerts(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Get products with low stock
    
    Requires admin role
    """
    low_stock_products = db.query(Product).filter(
        Product.stock_quantity <= Product.reorder_alert_level,
        Product.is_active == True
    ).order_by(Product.stock_quantity).all()
    
    return {
        "count": len(low_stock_products),
        "products": [
            {
                "id": p.id,
                "barcode": p.barcode,
                "name": p.name,
                "current_stock": p.stock_quantity,
                "alert_level": p.reorder_alert_level,
                "status": "Out of Stock" if p.stock_quantity == 0 else "Low Stock"
            }
            for p in low_stock_products
        ]
    }