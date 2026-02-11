from sqlalchemy import Column, Integer, String, Boolean, Date
from datetime import date
from app.models.base import Base, TimestampMixin

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    cost_price = Column(Integer, nullable=False)

    stock = Column(Integer, default=0)
    daily_stock = Column(Integer, default=0)
    stock_date = Column(Date, default=date.today)

    is_unlimited = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)