from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


ShiftType = Literal["opening", "closing"]


class MaterialBase(BaseModel):
    name: str
    unit: str
    branch_id: int
    par_stock: float = 0
    alert_threshold: float = 0
    is_active: bool = True


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    branch_id: int | None = None
    par_stock: float | None = None
    alert_threshold: float | None = None
    is_active: bool | None = None


class MaterialOut(MaterialBase):
    id: int
    latest_opening_qty: float | None = None
    latest_closing_qty: float | None = None
    current_qty: float | None = None
    stock_status: str = "unknown"

    class Config:
        from_attributes = True


class MaterialOpnameItem(BaseModel):
    material_id: int
    qty: float = Field(ge=0)


class MaterialOpnameCreate(BaseModel):
    shift_type: ShiftType
    items: list[MaterialOpnameItem]
    checked_for_date: date | None = None
    note: str | None = None


class MaterialOpnameOut(BaseModel):
    id: int
    material_id: int
    material_name: str
    branch_id: int
    shift_type: ShiftType
    qty: float
    unit: str
    checked_for_date: date
    note: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ProductRecipeItemIn(BaseModel):
    material_id: int
    qty_per_unit: float = Field(ge=0)


class ProductRecipeSave(BaseModel):
    items: list[ProductRecipeItemIn]


class ProductRecipeItemOut(BaseModel):
    id: int
    material_id: int
    material_name: str
    unit: str
    qty_per_unit: float


class ProductRecipeOut(BaseModel):
    product_id: int
    product_name: str
    branch_id: int | None
    items: list[ProductRecipeItemOut]
