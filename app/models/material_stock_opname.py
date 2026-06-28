from datetime import date

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class MaterialStockOpname(Base, TimestampMixin):
    __tablename__ = "material_stock_opnames"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    branch_id = Column(Integer, nullable=False, index=True)
    shift_type = Column(String, nullable=False)  # opening | closing
    qty = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    checked_for_date = Column(Date, default=date.today, index=True)
    note = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    material = relationship("Material")
