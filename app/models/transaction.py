from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String, unique=True, index=True, nullable=False)
    total_amount = Column(Integer, nullable=False)
    payment_method = Column(String, nullable=False)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    items = relationship("TransactionItem", back_populates="transaction")