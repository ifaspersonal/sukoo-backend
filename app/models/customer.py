from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)

    # 🔥 Phone bisa tetap required kalau mau loyalty wajib phone
    phone = Column(String, unique=True, index=True, nullable=False)

    points = Column(Integer, default=0)

    # ==============================
    # RELATIONSHIPS
    # ==============================
    transactions = relationship(
        "Transaction",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    point_histories = relationship(
        "PointHistory",
        back_populates="customer",
        cascade="all, delete-orphan"
    )