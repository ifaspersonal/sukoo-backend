from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String, unique=True, index=True, nullable=False)

    # 🔥 Total tetap dipakai (tidak diubah)
    total = Column(Integer, nullable=False)

    payment_method = Column(String, nullable=False)

    # 🔥 NEW: transaction type
    # sale = normal transaksi
    # redeem = tukar poin (tidak masuk revenue)
    type = Column(String, nullable=False, default="sale")

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

    customer = relationship(
        "Customer",
        back_populates="transactions"
    )

    user = relationship("User")

    point_histories = relationship(
        "PointHistory",
        back_populates="transaction",
        cascade="all, delete-orphan"
    )