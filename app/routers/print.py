from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db
from app.models.transaction import Transaction
from app.models.transaction_item import TransactionItem
from app.services.receipt_service import build_receipt_preview

router = APIRouter(prefix="/print", tags=["Print"])


@router.post("/{transaction_id}")
def print_receipt(transaction_id: int, db: Session = Depends(get_db)):
    # ==============================
    # 1️⃣ Ambil transaksi + relasi penting
    # ==============================
    tx = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.customer),
            joinedload(Transaction.point_histories),
            joinedload(Transaction.user),  # untuk tampilkan kasir
        )
        .filter(Transaction.id == transaction_id)
        .first()
    )

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # ==============================
    # 2️⃣ Ambil item + product
    # ==============================
    items = (
        db.query(TransactionItem)
        .options(joinedload(TransactionItem.product))
        .filter(TransactionItem.transaction_id == tx.id)
        .all()
    )

    if not items:
        raise HTTPException(status_code=400, detail="Transaction has no items")

    # ==============================
    # 3️⃣ Build receipt (PRO version)
    # ==============================
    receipt_text = build_receipt_preview(tx, items)

    # ==============================
    # 4️⃣ Return ke frontend
    # ==============================
    return {
        "printed": False,  # legacy flag (biarkan)
        "receipt": receipt_text,
    }