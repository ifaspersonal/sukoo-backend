from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String, unique=True, index=True, nullable=False)

    # 🔥 rename dari total_amount ➜ total
    total = Column(Integer, nullable=False)

    payment_method = Column(String, nullable=False)

    # optional customer (loyalty)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    # user yang buat transaksi
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # ==============================
    # RELATIONSHIPS
    # ==============================
    items = relationship(
        "TransactionItem",
        back_populates="transaction",
        cascade="all, delete-orphan"
    )

    customer = relationship("Customer", back_populates="transactions")
    user = relationship("User")