from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class ProductMaterialRecipe(Base, TimestampMixin):
    __tablename__ = "product_material_recipes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    branch_id = Column(Integer, nullable=False, index=True)
    qty_per_unit = Column(Float, nullable=False)

    product = relationship("Product")
    material = relationship("Material")
