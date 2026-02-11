from pydantic import BaseModel
from typing import List, Optional

class TransactionItemIn(BaseModel):
    product_id: int
    qty: int

class TransactionCreate(BaseModel):
    items: List[TransactionItemIn]
    payment_method: str  # cash | qris | ewallet
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None

class TransactionOut(BaseModel):
    id: int
    invoice_no: str
    total_amount: int
    payment_method: str

    class Config:
        from_attributes = True