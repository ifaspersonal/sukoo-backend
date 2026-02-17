from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from app.core.deps import get_db
from app.models.transaction import Transaction
from app.models.transaction_item import TransactionItem
from app.models.product import Product
from app.core.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily", dependencies=[Depends(get_current_user)])
def daily_report(db: Session = Depends(get_db)):

    today = date.today()

    # ==============================
    # TOTAL REVENUE (dari item)
    # ==============================
    total_revenue = (
        db.query(func.sum(TransactionItem.subtotal))
        .join(Transaction)
        .filter(func.date(Transaction.created_at) == today)
        .scalar()
        or 0
    )

    total_transactions = (
        db.query(Transaction)
        .filter(func.date(Transaction.created_at) == today)
        .count()
    )

    # ==============================
    # TOTAL COST
    # ==============================
    total_cost = (
        db.query(func.sum(TransactionItem.cost_price * TransactionItem.qty))
        .join(Transaction)
        .filter(func.date(Transaction.created_at) == today)
        .scalar()
        or 0
    )

    profit = total_revenue - total_cost

    # ==============================
    # PAYMENT BREAKDOWN
    # ==============================
    cash_total = (
        db.query(func.sum(TransactionItem.subtotal))
        .join(Transaction)
        .filter(
            func.date(Transaction.created_at) == today,
            Transaction.payment_method == "cash"
        )
        .scalar()
        or 0
    )

    qris_total = (
        db.query(func.sum(TransactionItem.subtotal))
        .join(Transaction)
        .filter(
            func.date(Transaction.created_at) == today,
            Transaction.payment_method == "qris"
        )
        .scalar()
        or 0
    )

    # ==============================
    # TOP PRODUCTS
    # ==============================
    top_products = (
        db.query(
            Product.name,
            func.sum(TransactionItem.qty).label("qty")
        )
        .join(TransactionItem)
        .join(Transaction)
        .filter(func.date(Transaction.created_at) == today)
        .group_by(Product.name)
        .order_by(func.sum(TransactionItem.qty).desc())
        .limit(5)
        .all()
    )

    # ==============================
    # HOURLY SALES
    # ==============================
    hourly_sales = (
        db.query(
            func.extract("hour", Transaction.created_at).label("hour"),
            func.sum(TransactionItem.subtotal).label("total")
        )
        .join(TransactionItem)
        .filter(func.date(Transaction.created_at) == today)
        .group_by("hour")
        .order_by("hour")
        .all()
    )

    return {
        "date": str(today),
        "total_revenue": int(total_revenue),
        "total_cost": int(total_cost),
        "profit": int(profit),
        "total_transactions": total_transactions,
        "cash_total": int(cash_total),
        "qris_total": int(qris_total),
        "top_products": [
            {"name": p.name, "qty": int(p.qty)}
            for p in top_products
        ],
        "hourly_sales": [
            {"hour": int(h.hour), "total": int(h.total)}
            for h in hourly_sales
        ]
    }