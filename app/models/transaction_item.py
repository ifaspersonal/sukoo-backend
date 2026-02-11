from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    price = Column(Integer, nullable=False)       # snapshot harga jual
    cost_price = Column(Integer, nullable=False)  # snapshot modal
    qty = Column(Integer, nullable=False)
    subtotal = Column(Integer, nullable=False)

    # relasi ke transaksi
    transaction = relationship("Transaction", back_populates="items")

    # 🔥 RELASI KE PRODUCT (INI YANG HILANG)
    product = relationship("Product")