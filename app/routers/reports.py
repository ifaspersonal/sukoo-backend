from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta

from app.core.deps import get_db
from app.models.transaction import Transaction
from app.models.transaction_item import TransactionItem
from app.models.product import Product
from app.core.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", dependencies=[Depends(get_current_user)])
def sales_report(
    period: str = Query("daily"),
    start: str | None = None,
    end: str | None = None,
    db: Session = Depends(get_db)
):

    # ===============================
    # DATE RANGE LOGIC
    # ===============================

    today = date.today()

    if start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    else:
        if period == "weekly":
            start_date = today - timedelta(days=6)
            end_date = today
        elif period == "monthly":
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = today
            end_date = today

    # ===============================
    # BASE QUERY
    # ===============================

    tx_query = db.query(Transaction).filter(
        func.date(Transaction.created_at) >= start_date,
        func.date(Transaction.created_at) <= end_date
    )

    total_transactions = tx_query.count()

    # ===============================
    # REVENUE
    # ===============================

    total_revenue = (
        db.query(func.sum(TransactionItem.subtotal))
        .join(Transaction)
        .filter(
            func.date(Transaction.created_at) >= start_date,
            func.date(Transaction.created_at) <= end_date
        )
        .scalar() or 0
    )

    total_cost = (
        db.query(func.sum(TransactionItem.cost_price * TransactionItem.qty))
        .join(Transaction)
        .filter(
            func.date(Transaction.created_at) >= start_date,
            func.date(Transaction.created_at) <= end_date
        )
        .scalar() or 0
    )

    profit = total_revenue - total_cost

    # ===============================
    # PAYMENT BREAKDOWN
    # ===============================

    def payment_total(method):
        return (
            db.query(func.sum(TransactionItem.subtotal))
            .join(Transaction)
            .filter(
                func.date(Transaction.created_at) >= start_date,
                func.date(Transaction.created_at) <= end_date,
                Transaction.payment_method == method
            )
            .scalar() or 0
        )

    cash_total = payment_total("cash")
    qris_total = payment_total("qris")

    # ===============================
    # TRANSACTION LIST (DETAIL VIEW)
    # ===============================

    transactions = tx_query.order_by(Transaction.created_at.desc()).all()

    transaction_list = [
        {
            "id": tx.id,
            "created_at": tx.created_at,
            "payment_method": tx.payment_method,
        }
        for tx in transactions
    ]

    return {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "total_revenue": int(total_revenue),
        "total_cost": int(total_cost),
        "profit": int(profit),
        "total_transactions": total_transactions,
        "cash_total": int(cash_total),
        "qris_total": int(qris_total),
        "transactions": transaction_list,
    }