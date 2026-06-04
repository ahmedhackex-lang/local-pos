"""
Inventory management API endpoints
Excel/CSV import, stock updates, bulk operations
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
from io import BytesIO
import os

from database import get_db
from models import Product
from auth import require_admin
from utils import allowed_file, get_file_extension
from config import constants

router = APIRouter()


@router.post("/upload")
async def upload_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Bulk import products from Excel/CSV file
    
    Requires admin role
    
    Expected columns:
    - Barcode (required)
    - Product Name or Name (required)
    - Category (optional)
    - Cost Price or Wholesale Price (required)
    - Retail Price or Sale Price (required)
    - Stock or Quantity (optional, default 0)
    - Alert Level or Reorder Level (optional, default 5)
    """
    # Validate file type
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {', '.join(constants.ALLOWED_EXTENSIONS)}"
        )
    
    # Read file
    contents = await file.read()
    file_ext = get_file_extension(file.filename)
    
    try:
        # Parse based on extension
        if file_ext == '.csv':
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents), engine='openpyxl')
        
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        
        # Column mapping
        column_mapping = {
            'barcode': 'barcode',
            'product name': 'name',
            'name': 'name',
            'category': 'category',
            'cost price': 'cost_price',
            'wholesale price': 'cost_price',
            'retail price': 'retail_price',
            'sale price': 'retail_price',
            'stock': 'stock_quantity',
            'quantity': 'stock_quantity',
            'alert level': 'reorder_alert_level',
            'reorder level': 'reorder_alert_level',
            'brand': 'brand',
            'unit': 'unit_of_measure'
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Validate required columns
        required_cols = ['barcode', 'name', 'cost_price', 'retail_price']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_cols)}"
            )
        
        # Fill optional columns
        if 'stock_quantity' not in df.columns:
            df['stock_quantity'] = 0
        if 'reorder_alert_level' not in df.columns:
            df['reorder_alert_level'] = 5
        if 'category' not in df.columns:
            df['category'] = 'Uncategorized'
        if 'brand' not in df.columns:
            df['brand'] = None
        if 'unit_of_measure' not in df.columns:
            df['unit_of_measure'] = 'piece'
        
        # Process rows
        results = {
            'total': len(df),
            'inserted': 0,
            'updated': 0,
            'errors': []
        }
        
        for index, row in df.iterrows():
            try:
                # Check if product exists
                existing = db.query(Product).filter(
                    Product.barcode == str(row['barcode'])
                ).first()
                
                if existing:
                    # Update existing
                    existing.name = str(row['name'])
                    existing.category = str(row.get('category', 'Uncategorized'))
                    existing.brand = str(row.get('brand', '')) if pd.notna(row.get('brand')) else None
                    existing.cost_price = float(row['cost_price'])
                    existing.retail_price = float(row['retail_price'])
                    existing.stock_quantity += int(row.get('stock_quantity', 0))
                    existing.reorder_alert_level = int(row.get('reorder_alert_level', 5))
                    existing.unit_of_measure = str(row.get('unit_of_measure', 'piece'))
                    
                    results['updated'] += 1
                else:
                    # Create new
                    new_product = Product(
                        barcode=str(row['barcode']),
                        name=str(row['name']),
                        category=str(row.get('category', 'Uncategorized')),
                        brand=str(row.get('brand', '')) if pd.notna(row.get('brand')) else None,
                        cost_price=float(row['cost_price']),
                        retail_price=float(row['retail_price']),
                        stock_quantity=int(row.get('stock_quantity', 0)),
                        reorder_alert_level=int(row.get('reorder_alert_level', 5)),
                        unit_of_measure=str(row.get('unit_of_measure', 'piece')),
                        created_by=current_user.id
                    )
                    db.add(new_product)
                    
                    results['inserted'] += 1
                
                # Commit every 100 rows for performance
                if (index + 1) % 100 == 0:
                    db.commit()
            
            except Exception as e:
                results['errors'].append({
                    'row': index + 2,  # Excel row (1-indexed + header)
                    'barcode': str(row.get('barcode', 'N/A')),
                    'error': str(e)
                })
                db.rollback()
        
        # Final commit
        db.commit()
        
        return {
            'success': True,
            'results': results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/stock/adjust")
async def adjust_stock(
    product_id: int,
    quantity_change: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Manually adjust product stock
    
    Requires admin role
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    old_quantity = product.stock_quantity
    new_quantity = old_quantity + quantity_change
    
    if new_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Stock adjustment would result in negative quantity"
        )
    
    product.stock_quantity = new_quantity
    db.commit()
    
    # TODO: Log stock adjustment in audit table
    
    return {
        'success': True,
        'product_id': product.id,
        'barcode': product.barcode,
        'name': product.name,
        'old_quantity': old_quantity,
        'new_quantity': new_quantity,
        'change': quantity_change,
        'reason': reason
    }


@router.get("/export")
async def export_inventory(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Export current inventory to Excel
    
    Requires admin role
    """
    products = db.query(Product).filter(Product.is_active == True).all()
    
    # Prepare data
    data = []
    for p in products:
        data.append({
            'Barcode': p.barcode,
            'Product Name': p.name,
            'Category': p.category,
            'Brand': p.brand,
            'Unit': p.unit_of_measure,
            'Cost Price': float(p.cost_price),
            'Retail Price': float(p.retail_price),
            'Stock': p.stock_quantity,
            'Reorder Level': p.reorder_alert_level,
            'Supplier': p.supplier_name
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save to Excel
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    filename = f"inventory_export_{timestamp}.xlsx"
    filepath = f"./data/exports/{filename}"
    
    df.to_excel(filepath, index=False, engine='openpyxl')
    
    return {
        'success': True,
        'filename': filename,
        'filepath': filepath,
        'record_count': len(data)
    }