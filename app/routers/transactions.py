from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.services.transaction_service import create_transaction

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("/", response_model=TransactionOut)
def create_pos_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        # 🔥 BLOCK OWNER
        if user.role == "owner":
            raise HTTPException(status_code=403, detail="Owner tidak boleh transaksi")

        # 🔥 VALIDASI BRANCH
        if not user.branch_id:
            raise HTTPException(status_code=400, detail="User belum punya branch")

        # 🔥 CALL SERVICE
        tx = create_transaction(
            db=db,
            items=payload.items,
            payment_method=payload.payment_method,
            customer_phone=payload.customer_phone,
            customer_name=payload.customer_name,
            created_by=user.id,
            redeem_points=payload.redeem_points or 0,
            branch_id=user.branch_id,  # ✅ TAMBAH INI
        )

        return tx

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        db.rollback()
        print("TRANSACTION ERROR:", e)
        raise HTTPException(status_code=500, detail="Transaction failed")