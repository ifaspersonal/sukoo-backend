from sqlalchemy import Column, Integer, String, ForeignKey
from app.models.base import Base, TimestampMixin

class StockMovement(Base, TimestampMixin):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    type = Column(String, nullable=False)  # IN | OUT | OPNAME
    qty = Column(Integer, nullable=False)
    note = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"))