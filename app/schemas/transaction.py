from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ===============================
# ITEM INPUT
# ===============================
class TransactionItemIn(BaseModel):
    product_id: int
    qty: int


# ===============================
# CREATE TRANSACTION
# ===============================
class TransactionCreate(BaseModel):
    items: List[TransactionItemIn]
    payment_method: str  # cash | qris | ewallet

    # optional loyalty (earn)
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None

    # 🔁 optional redeem
    redeem_points: Optional[int] = 0

    # 🔥 NEW (optional, default sale)
    # frontend tidak wajib kirim
    type: Optional[str] = "sale"


# ===============================
# OUTPUT (POS RESPONSE)
# ===============================
class TransactionOut(BaseModel):
    id: int
    invoice_no: str
    total: int
    payment_method: str
    created_at: datetime

    # 🔥 NEW
    type: str

    # optional customer
    customer_id: Optional[int] = None

    class Config:
        from_attributes = True