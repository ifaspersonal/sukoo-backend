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

    # Filter transaksi hari ini
    tx_today = db.query(Transaction).filter(
        func.date(Transaction.created_at) == today
    )

    total_revenue = tx_today.with_entities(func.sum(Transaction.total)).scalar() or 0
    total_transactions = tx_today.count()

    # Total cost
    total_cost = (
        db.query(func.sum(TransactionItem.cost_price * TransactionItem.qty))
        .join(Transaction)
        .filter(func.date(Transaction.created_at) == today)
        .scalar()
        or 0
    )

    profit = total_revenue - total_cost

    # Breakdown payment
    cash_total = (
        tx_today.filter(Transaction.payment_method == "cash")
        .with_entities(func.sum(Transaction.total))
        .scalar()
        or 0
    )

    qris_total = (
        tx_today.filter(Transaction.payment_method == "qris")
        .with_entities(func.sum(Transaction.total))
        .scalar()
        or 0
    )

    # Top products
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

    # Hourly sales
    hourly_sales = (
        db.query(
            func.extract("hour", Transaction.created_at).label("hour"),
            func.sum(Transaction.total).label("total")
        )
        .filter(func.date(Transaction.created_at) == today)
        .group_by("hour")
        .order_by("hour")
        .all()
    )

    return {
        "date": str(today),
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "profit": profit,
        "total_transactions": total_transactions,
        "cash_total": cash_total,
        "qris_total": qris_total,
        "top_products": [
            {"name": p.name, "qty": int(p.qty)}
            for p in top_products
        ],
        "hourly_sales": [
            {"hour": int(h.hour), "total": int(h.total)}
            for h in hourly_sales
        ]
    }