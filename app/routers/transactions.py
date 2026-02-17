from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.services.transaction_service import create_transaction

from app.models.customer import Customer
from app.models.point_history import PointHistory
from app.models.transaction_item import TransactionItem

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/", response_model=TransactionOut)
def create_pos_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        # ==============================
        # 1️⃣ CREATE TRANSACTION
        # ==============================
        tx = create_transaction(
            db=db,
            items=payload.items,
            payment_method=payload.payment_method,
            customer_phone=payload.customer_phone,
            customer_name=payload.customer_name,
            created_by=user.id,
        )

        # ==============================
        # 2️⃣ HANDLE LOYALTY POINTS
        # ==============================
        if tx.customer_id:

            customer = db.get(Customer, tx.customer_id)
            if customer:

                # hitung total qty item
                total_qty = (
                    db.query(TransactionItem)
                    .filter(TransactionItem.transaction_id == tx.id)
                    .with_entities(TransactionItem.qty)
                    .all()
                )

                total_points = sum(q[0] for q in total_qty)

                if total_points > 0:
                    # tambah poin ke customer
                    customer.points = (customer.points or 0) + total_points

                    # insert history
                    history = PointHistory(
                        customer_id=customer.id,
                        transaction_id=tx.id,
                        points=total_points,
                        type="earn",
                    )

                    db.add(history)

        db.commit()
        db.refresh(tx)

        return tx

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        db.rollback()
        print("TRANSACTION ERROR:", e)
        raise HTTPException(status_code=500, detail="Transaction failed")