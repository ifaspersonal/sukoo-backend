from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class PointHistory(Base, TimestampMixin):
    __tablename__ = "point_histories"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )

    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 🔥 jumlah poin (+ earn, - redeem)
    points = Column(Integer, nullable=False)

    # 🔥 type history: earn / redeem / adjustment
    type = Column(String, nullable=False, default="earn")

    # optional audit note
    description = Column(String, nullable=True)

    # ==============================
    # RELATIONSHIPS
    # ==============================
    customer = relationship("Customer", back_populates="point_histories")
    transaction = relationship("Transaction")