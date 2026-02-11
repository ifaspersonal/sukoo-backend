from pydantic import BaseModel

class StockAdjust(BaseModel):
    qty: int
    note: str | None = None