from pydantic import BaseModel
from typing import Optional


# ======================
# BASE
# ======================
class ProductBase(BaseModel):
    name: str
    price: int
    cost_price: int
    is_unlimited: bool = False
    is_active: bool = True

    # 🔥 NEW INTEGER LOYALTY SYSTEM
    category: str = "drink"
    loyalty_point_value: int = 1


# ======================
# CREATE
# ======================
class ProductCreate(ProductBase):
    daily_stock: int  # 🔥 kapasitas stok per hari (WAJIB saat create)


# ======================
# UPDATE
# ======================
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    cost_price: Optional[int] = None
    daily_stock: Optional[int] = None
    stock: Optional[int] = None  # opsional (admin/manual)
    is_unlimited: Optional[bool] = None
    is_active: Optional[bool] = None

    # 🔥 NEW FIELDS (optional saat update)
    category: Optional[str] = None
    loyalty_point_value: Optional[int] = None


# ======================
# OUTPUT
# ======================
class ProductOut(ProductBase):
    id: int
    daily_stock: int
    stock: int

    class Config:
        from_attributes = True