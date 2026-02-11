from sqlalchemy import Column, Integer, ForeignKey
from app.models.base import Base, TimestampMixin

class PointHistory(Base, TimestampMixin):
    __tablename__ = "point_histories"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    points = Column(Integer, nullable=False)