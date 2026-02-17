from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime

from app.core.deps import get_db
from app.models.transaction import Transaction
from app.models.transaction_item import TransactionItem
from app.models.product import Product
from app.core.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


# =========================================
# DATE RANGE HELPER
# =========================================
def get_date_range(period: str):
    today = date.today()

    if period == "weekly":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == "monthly":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
    else:
        start = today
        end = today

    return start, end


# =========================================
# REPORT SUMMARY
# =========================================
@router.get("", dependencies=[Depends(get_current_user)])
def report_summary(
    period: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(get_db),
):

    # ==============================
    # DATE LOGIC
    # ==============================
    if start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    else:
        start_date, end_date = get_date_range(period)

    base_filter = (
        func.date(Transaction.created_at) >= start_date,
        func.date(Transaction.created_at) <= end_date,
    )

    # ==============================
    # TOTAL REVENUE
    # ==============================
    total_revenue = (
        db.query(func.sum(TransactionItem.subtotal))
        .join(Transaction)
        .filter(*base_filter)
        .scalar()
        or 0
    )

    total_cost = (
        db.query(func.sum(TransactionItem.cost_price * TransactionItem.qty))
        .join(Transaction)
        .filter(*base_filter)
        .scalar()
        or 0
    )

    total_transactions = (
        db.query(Transaction)
        .filter(*base_filter)
        .count()
    )

    profit = total_revenue - total_cost

    # ==============================
    # PAYMENT BREAKDOWN
    # ==============================
    def payment_total(method):
        return (
            db.query(func.sum(TransactionItem.subtotal))
            .join(Transaction)
            .filter(*base_filter, Transaction.payment_method == method)
            .scalar()
            or 0
        )

    cash_total = payment_total("cash")
    qris_total = payment_total("qris")

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
        .filter(*base_filter)
        .group_by(Product.name)
        .order_by(func.sum(TransactionItem.qty).desc())
        .limit(5)
        .all()
    )

    # ==============================
    # HOURLY SALES (ONLY DAILY)
    # ==============================
    hourly_sales = []

    if period == "daily" and not (start and end):
        hourly = (
            db.query(
                func.extract("hour", Transaction.created_at).label("hour"),
                func.sum(TransactionItem.subtotal).label("total")
            )
            .join(TransactionItem)
            .filter(*base_filter)
            .group_by("hour")
            .order_by("hour")
            .all()
        )

        hourly_sales = [
            {"hour": int(h.hour), "total": int(h.total)}
            for h in hourly
        ]

    # ==============================
    # TRANSACTION LIST
    # ==============================
    transactions = (
        db.query(Transaction)
        .filter(*base_filter)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    tx_list = [
        {
            "id": tx.id,
            "created_at": tx.created_at,
            "payment_method": tx.payment_method,
        }
        for tx in transactions
    ]

    return {
        "period": period,
        "start_date": str(start_date),
        "end_date": str(end_date),
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
        "hourly_sales": hourly_sales,
        "transactions": tx_list,
    }


# =========================================
# TRANSACTION DETAIL
# =========================================
@router.get("/transaction/{transaction_id}",
            dependencies=[Depends(get_current_user)])
def transaction_detail(transaction_id: int, db: Session = Depends(get_db)):

    tx = db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    items = (
        db.query(TransactionItem)
        .filter(TransactionItem.transaction_id == transaction_id)
        .all()
    )

    return {
        "id": tx.id,
        "created_at": tx.created_at,
        "payment_method": tx.payment_method,
        "items": [
            {
                "product_name": item.product.name if item.product else "-",
                "qty": item.qty,
                "subtotal": item.subtotal,
            }
            for item in items
        ]
    }