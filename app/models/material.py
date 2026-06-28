from sqlalchemy import Boolean, Column, Float, Integer, String

from app.models.base import Base, TimestampMixin


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    branch_id = Column(Integer, nullable=False, index=True)
    par_stock = Column(Float, default=0)
    alert_threshold = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
