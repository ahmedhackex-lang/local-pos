"""
Reporting API endpoints
Sales reports, inventory reports, analytics
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from database import get_db
from models import Sale, SaleItem, Product, User
from auth import get_current_user, require_admin, require_owner
from config import constants

router = APIRouter()


@router.get("/sales/daily")
async def daily_sales_report(
    report_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Daily sales summary report
    
    Requires admin/owner role
    """
    if report_date is None:
        report_date = date.today()
    
    # Get sales for the day
    sales = db.query(Sale).filter(
        func.date(Sale.created_at) == report_date,
        Sale.is_voided == False
    ).all()
    
    # Calculate metrics
    total_sales = sum(s.net_amount for s in sales)
    total_transactions = len(sales)
    total_discount = sum(s.discount for s in sales)
    
    # Payment method breakdown
    cash_sales = sum(s.net_amount for s in sales if s.payment_method == constants.PAYMENT_CASH)
    card_sales = sum(s.net_amount for s in sales if s.payment_method == constants.PAYMENT_CARD)
    online_sales = sum(s.net_amount for s in sales if s.payment_method == constants.PAYMENT_ONLINE)
    credit_sales = sum(s.net_amount for s in sales if s.payment_method == constants.PAYMENT_CREDIT)
    
    # Calculate profit
    total_profit = Decimal('0')
    for sale in sales:
        items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
        for item in items:
            profit = (item.retail_price_at_sale - item.cost_price_at_sale) * item.quantity
            total_profit += profit
    
    return {
        'date': report_date.strftime("%d/%m/%Y"),
        'total_sales': float(total_sales),
        'total_transactions': total_transactions,
        'total_discount': float(total_discount),
        'total_profit': float(total_profit),
        'average_transaction': float(total_sales / total_transactions) if total_transactions > 0 else 0,
        'payment_breakdown': {
            'cash': float(cash_sales),
            'card': float(card_sales),
            'online': float(online_sales),
            'credit': float(credit_sales)
        }
    }


@router.get("/sales/range")
async def sales_range_report(
    start_date: date,
    end_date: date,
    cashier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Sales report for date range
    
    Requires admin/owner role
    """
    query = db.query(Sale).filter(
        Sale.created_at >= start_date,
        Sale.created_at <= end_date,
        Sale.is_voided == False
    )
    
    if cashier_id:
        query = query.filter(Sale.cashier_id == cashier_id)
    
    sales = query.all()
    
    # Daily breakdown
    daily_stats = {}
    for sale in sales:
        day = sale.created_at.date()
        day_str = day.strftime("%d/%m/%Y")
        
        if day_str not in daily_stats:
            daily_stats[day_str] = {
                'date': day_str,
                'sales': Decimal('0'),
                'transactions': 0,
                'profit': Decimal('0')
            }
        
        daily_stats[day_str]['sales'] += sale.net_amount
        daily_stats[day_str]['transactions'] += 1
        
        # Calculate profit
        items = db.query(SaleItem).filter(SaleItem.sale_id == sale.id).all()
        for item in items:
            profit = (item.retail_price_at_sale - item.cost_price_at_sale) * item.quantity
            daily_stats[day_str]['profit'] += profit
    
    # Convert to list
    daily_breakdown = [
        {
            'date': v['date'],
            'sales': float(v['sales']),
            'transactions': v['transactions'],
            'profit': float(v['profit'])
        }
        for v in daily_stats.values()
    ]
    
    # Overall totals
    total_sales = sum(s.net_amount for s in sales)
    total_transactions = len(sales)
    total_profit = sum(d['profit'] for d in daily_breakdown)
    
    return {
        'start_date': start_date.strftime("%d/%m/%Y"),
        'end_date': end_date.strftime("%d/%m/%Y"),
        'total_sales': float(total_sales),
        'total_transactions': total_transactions,
        'total_profit': total_profit,
        'daily_breakdown': daily_breakdown
    }


@router.get("/inventory/valuation")
async def inventory_valuation_report(
    db: Session = Depends(get_db),
    current_user = Depends(require_owner)
):
    """
    Inventory valuation report
    
    Requires owner role (sensitive financial data)
    """
    products = db.query(Product).filter(Product.is_active == True).all()
    
    total_cost_value = Decimal('0')
    total_retail_value = Decimal('0')
    total_potential_profit = Decimal('0')
    
    category_breakdown = {}
    
    for product in products:
        cost_value = product.cost_price * product.stock_quantity
        retail_value = product.retail_price * product.stock_quantity
        potential_profit = retail_value - cost_value
        
        total_cost_value += cost_value
        total_retail_value += retail_value
        total_potential_profit += potential_profit
        
        # Category breakdown
        category = product.category or 'Uncategorized'
        if category not in category_breakdown:
            category_breakdown[category] = {
                'cost_value': Decimal('0'),
                'retail_value': Decimal('0'),
                'items': 0
            }
        
        category_breakdown[category]['cost_value'] += cost_value
        category_breakdown[category]['retail_value'] += retail_value
        category_breakdown[category]['items'] += 1
    
    return {
        'total_products': len(products),
        'total_cost_value': float(total_cost_value),
        'total_retail_value': float(total_retail_value),
        'total_potential_profit': float(total_potential_profit),
        'category_breakdown': [
            {
                'category': k,
                'cost_value': float(v['cost_value']),
                'retail_value': float(v['retail_value']),
                'items': v['items']
            }
            for k, v in category_breakdown.items()
        ]
    }


@router.get("/products/top-selling")
async def top_selling_products(
    limit: int = Query(10, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Top selling products report
    
    Requires admin/owner role
    """
    query = db.query(
        SaleItem.product_id,
        SaleItem.product_name,
        func.sum(SaleItem.quantity).label('total_quantity'),
        func.sum(SaleItem.subtotal).label('total_revenue'),
        func.count(SaleItem.id).label('transaction_count')
    ).join(Sale, SaleItem.sale_id == Sale.id).filter(
        Sale.is_voided == False
    )
    
    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)
    
    results = query.group_by(
        SaleItem.product_id,
        SaleItem.product_name
    ).order_by(
        func.sum(SaleItem.quantity).desc()
    ).limit(limit).all()
    
    return [
        {
            'product_id': r.product_id,
            'product_name': r.product_name,
            'total_quantity': float(r.total_quantity),
            'total_revenue': float(r.total_revenue),
            'transaction_count': r.transaction_count
        }
        for r in results
    ]


@router.get("/cashier/performance")
async def cashier_performance_report(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_owner)
):
    """
    Cashier performance report
    
    Requires owner role
    """
    query = db.query(
        Sale.cashier_id,
        func.count(Sale.id).label('transaction_count'),
        func.sum(Sale.net_amount).label('total_sales')
    ).filter(Sale.is_voided == False)
    
    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)
    
    results = query.group_by(Sale.cashier_id).all()
    
    performance = []
    for r in results:
        cashier = db.query(User).filter(User.id == r.cashier_id).first()
        
        performance.append({
            'cashier_id': r.cashier_id,
            'cashier_name': cashier.full_name if cashier else 'Unknown',
            'transaction_count': r.transaction_count,
            'total_sales': float(r.total_sales),
            'average_transaction': float(r.total_sales / r.transaction_count) if r.transaction_count > 0 else 0
        })
    
    # Sort by total sales
    performance.sort(key=lambda x: x['total_sales'], reverse=True)
    
    return performance


@router.get("/executive/dashboard")
async def executive_dashboard(
    db: Session = Depends(get_db),
    current_user = Depends(require_owner)
):
    """
    Executive dashboard with key business metrics
    
    Requires owner role
    """
    today = date.today()
    
    # Today's sales
    today_sales = db.query(Sale).filter(
        func.date(Sale.created_at) == today,
        Sale.is_voided == False
    ).all()
    
    today_revenue = sum(s.net_amount for s in today_sales)
    today_transactions = len(today_sales)
    
    # Month to date
    month_start = today.replace(day=1)
    month_sales = db.query(Sale).filter(
        Sale.created_at >= month_start,
        Sale.is_voided == False
    ).all()
    
    month_revenue = sum(s.net_amount for s in month_sales)
    month_transactions = len(month_sales)
    
    # Year to date
    year_start = today.replace(month=1, day=1)
    year_sales = db.query(Sale).filter(
        Sale.created_at >= year_start,
        Sale.is_voided == False
    ).all()
    
    year_revenue = sum(s.net_amount for s in year_sales)
    year_transactions = len(year_sales)
    
    # Low stock alerts
    low_stock = db.query(Product).filter(
        Product.stock_quantity <= Product.reorder_alert_level,
        Product.is_active == True
    ).count()
    
    # Out of stock
    out_of_stock = db.query(Product).filter(
        Product.stock_quantity == 0,
        Product.is_active == True
    ).count()
    
    return {
        'today': {
            'revenue': float(today_revenue),
            'transactions': today_transactions
        },
        'month': {
            'revenue': float(month_revenue),
            'transactions': month_transactions
        },
        'year': {
            'revenue': float(year_revenue),
            'transactions': year_transactions
        },
        'inventory_alerts': {
            'low_stock': low_stock,
            'out_of_stock': out_of_stock
        }
    }