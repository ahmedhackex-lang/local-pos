"""
Sales transaction API endpoints
Create sales, retrieve history, void transactions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from database import get_db
from models import Sale, SaleItem, Product, User
from schemas import SaleCreate, SaleResponse, SaleItemResponse
from auth import get_current_user, require_admin
from utils import generate_invoice_number, calculate_change
from printer import printer_manager
from config import constants

router = APIRouter()


@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_data: SaleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create new sale transaction
    
    1. Validate products and stock
    2. Calculate totals
    3. Create sale record
    4. Update inventory
    5. Print receipt
    """
    try:
        # Generate invoice number
        invoice_number = generate_invoice_number(db)
        
        # Prepare sale items and validate
        sale_items = []
        total_amount = Decimal('0')
        
        for item_data in sale_data.items:
            # Get product
            product = db.query(Product).filter(
                Product.id == item_data.product_id,
                Product.is_active == True
            ).first()
            
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product ID {item_data.product_id} not found"
                )
            
            # Check stock
            if product.stock_quantity < item_data.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}"
                )
            
            # Calculate line item totals
            line_subtotal = product.retail_price * item_data.quantity
            
            # Apply discount
            discount_amount = Decimal('0')
            if item_data.discount_percent > 0:
                discount_amount = line_subtotal * (item_data.discount_percent / Decimal('100'))
                discount_amount = discount_amount.quantize(Decimal('0.01'))
            
            # Calculate tax
            tax_amount = Decimal('0')
            if product.tax_rate > 0:
                taxable_amount = line_subtotal - discount_amount
                tax_amount = taxable_amount * (product.tax_rate / Decimal('100'))
                tax_amount = tax_amount.quantize(Decimal('0.01'))
            
            # Final subtotal
            final_subtotal = line_subtotal - discount_amount + tax_amount
            
            # Create sale item
            sale_item = SaleItem(
                product_id=product.id,
                barcode=product.barcode,
                product_name=product.name,
                quantity=item_data.quantity,
                cost_price_at_sale=product.cost_price,
                retail_price_at_sale=product.retail_price,
                discount_percent=item_data.discount_percent,
                discount_amount=discount_amount,
                tax_rate=product.tax_rate,
                tax_amount=tax_amount,
                subtotal=final_subtotal
            )
            
            sale_items.append(sale_item)
            total_amount += final_subtotal
            
            # Update product stock
            product.stock_quantity -= item_data.quantity
        
        # Apply transaction-level discount
        transaction_discount = sale_data.discount
        
        # Calculate net amount
        net_amount = total_amount - transaction_discount
        
        # Calculate change
        change_returned = Decimal('0')
        if sale_data.payment_method == constants.PAYMENT_CASH and sale_data.amount_tendered:
            change_returned = calculate_change(net_amount, sale_data.amount_tendered)
            
            if sale_data.amount_tendered < net_amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient payment. Required: {net_amount}, Received: {sale_data.amount_tendered}"
                )
        
        # Create sale record
        sale = Sale(
            invoice_number=invoice_number,
            cashier_id=current_user.id,
            customer_name=sale_data.customer_name,
            customer_phone=sale_data.customer_phone,
            total_amount=total_amount,
            discount=transaction_discount,
            tax_amount=sum(item.tax_amount for item in sale_items),
            net_amount=net_amount,
            payment_method=sale_data.payment_method,
            amount_tendered=sale_data.amount_tendered,
            change_returned=change_returned,
            notes=sale_data.notes
        )
        
        db.add(sale)
        db.flush()  # Get sale ID
        
        # Associate items with sale
        for sale_item in sale_items:
            sale_item.sale_id = sale.id
            db.add(sale_item)
        
        # Commit transaction
        db.commit()
        db.refresh(sale)
        
        # Print receipt
        try:
            receipt_data = {
                'invoice_number': sale.invoice_number,
                'date': datetime.now().strftime("%d/%m/%Y %I:%M %p"),
                'cashier_name': current_user.full_name or current_user.username,
                'customer_name': sale.customer_name,
                'total_amount': sale.total_amount,
                'discount': sale.discount,
                'tax_amount': sale.tax_amount,
                'net_amount': sale.net_amount,
                'payment_method': sale.payment_method,
                'amount_tendered': sale.amount_tendered,
                'change_returned': sale.change_returned,
                'items': [
                    {
                        'name': item.product_name,
                        'quantity': item.quantity,
                        'price': item.retail_price_at_sale,
                        'subtotal': item.subtotal
                    }
                    for item in sale_items
                ]
            }
            
            printer_manager.print_receipt(receipt_data)
        except Exception as e:
            # Log print error but don't fail transaction
            print(f"Print error: {e}")
        
        # Prepare response
        return SaleResponse(
            id=sale.id,
            invoice_number=sale.invoice_number,
            cashier_id=sale.cashier_id,
            cashier_name=current_user.full_name or current_user.username,
            total_amount=sale.total_amount,
            discount=sale.discount,
            tax_amount=sale.tax_amount,
            net_amount=sale.net_amount,
            payment_method=sale.payment_method,
            amount_tendered=sale.amount_tendered,
            change_returned=sale.change_returned,
            is_voided=sale.is_voided,
            created_at=sale.created_at,
            items=[SaleItemResponse.from_orm(item) for item in sale_items]
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[SaleResponse])
async def get_sales(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    cashier_id: Optional[int] = None,
    payment_method: Optional[str] = None,
    include_voided: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get sales history
    
    Cashiers can only see their own sales
    Admins can see all sales
    """
    query = db.query(Sale)
    
    # Role-based filtering
    if current_user.role == constants.ROLE_CASHIER:
        query = query.filter(Sale.cashier_id == current_user.id)
    
    # Date range filter
    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)
    
    # Cashier filter (admin only)
    if cashier_id and current_user.role in [constants.ROLE_ADMIN, constants.ROLE_OWNER]:
        query = query.filter(Sale.cashier_id == cashier_id)
    
    # Payment method filter
    if payment_method:
        query = query.filter(Sale.payment_method == payment_method)
    
    # Voided filter
    if not include_voided:
        query = query.filter(Sale.is_voided == False)
    
    # Order by date descending
    query = query.order_by(Sale.created_at.desc())
    
    # Paginate
    sales = query.offset(skip).limit(limit).all()
    
    # Build responses
    result = []
    for sale in sales:
        items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
        cashier = db.query(User).filter(User.id == sale.cashier_id).first()
        
        result.append(SaleResponse(
            id=sale.id,
            invoice_number=sale.invoice_number,
            cashier_id=sale.cashier_id,
            cashier_name=cashier.full_name if cashier else "Unknown",
            total_amount=sale.total_amount,
            discount=sale.discount,
            tax_amount=sale.tax_amount,
            net_amount=sale.net_amount,
            payment_method=sale.payment_method,
            amount_tendered=sale.amount_tendered,
            change_returned=sale.change_returned,
            is_voided=sale.is_voided,
            created_at=sale.created_at,
            items=[SaleItemResponse.from_orm(item) for item in items]
        ))
    
    return result


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get sale by ID"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    # Authorization check
    if current_user.role == constants.ROLE_CASHIER and sale.cashier_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
    cashier = db.query(User).filter(User.id == sale.cashier_id).first()
    
    return SaleResponse(
        id=sale.id,
        invoice_number=sale.invoice_number,
        cashier_id=sale.cashier_id,
        cashier_name=cashier.full_name if cashier else "Unknown",
        total_amount=sale.total_amount,
        discount=sale.discount,
        tax_amount=sale.tax_amount,
        net_amount=sale.net_amount,
        payment_method=sale.payment_method,
        amount_tendered=sale.amount_tendered,
        change_returned=sale.change_returned,
        is_voided=sale.is_voided,
        created_at=sale.created_at,
        items=[SaleItemResponse.from_orm(item) for item in items]
    )


@router.post("/{sale_id}/void")
async def void_sale(
    sale_id: int,
    void_reason: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Void a sale transaction
    
    Requires admin role
    Restores product stock
    """
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if sale.is_voided:
        raise HTTPException(status_code=400, detail="Sale already voided")
    
    # Get sale items
    items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
    
    # Restore stock
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock_quantity += item.quantity
    
    # Mark as voided
    sale.is_voided = True
    sale.void_reason = void_reason
    sale.voided_by = current_user.id
    sale.voided_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Sale voided successfully", "invoice_number": sale.invoice_number}


@router.post("/{sale_id}/reprint")
async def reprint_receipt(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Reprint receipt for a sale
    """
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    # Authorization check
    if current_user.role == constants.ROLE_CASHIER and sale.cashier_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get sale items
    items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
    cashier = db.query(User).filter(User.id == sale.cashier_id).first()
    
    # Prepare receipt data
    receipt_data = {
        'invoice_number': sale.invoice_number,
        'date': sale.created_at.strftime("%d/%m/%Y %I:%M %p"),
        'cashier_name': cashier.full_name if cashier else "Unknown",
        'customer_name': sale.customer_name,
        'total_amount': sale.total_amount,
        'discount': sale.discount,
        'tax_amount': sale.tax_amount,
        'net_amount': sale.net_amount,
        'payment_method': sale.payment_method,
        'amount_tendered': sale.amount_tendered,
        'change_returned': sale.change_returned,
        'items': [
            {
                'name': item.product_name,
                'quantity': item.quantity,
                'price': item.retail_price_at_sale,
                'subtotal': item.subtotal
            }
            for item in items
        ]
    }
    
    # Print
    success = printer_manager.print_receipt(receipt_data)
    
    if success:
        return {"message": "Receipt reprinted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Print failed")