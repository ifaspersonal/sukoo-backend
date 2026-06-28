"""add product material recipes

Revision ID: b31c6e9a7d42
Revises: a9f4d2c7b8e1
Create Date: 2026-06-28 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b31c6e9a7d42"
down_revision: Union[str, Sequence[str], None] = "a9f4d2c7b8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_material_recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("qty_per_unit", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_material_recipes_branch_id"), "product_material_recipes", ["branch_id"], unique=False)
    op.create_index(op.f("ix_product_material_recipes_id"), "product_material_recipes", ["id"], unique=False)
    op.create_index(op.f("ix_product_material_recipes_material_id"), "product_material_recipes", ["material_id"], unique=False)
    op.create_index(op.f("ix_product_material_recipes_product_id"), "product_material_recipes", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_material_recipes_product_id"), table_name="product_material_recipes")
    op.drop_index(op.f("ix_product_material_recipes_material_id"), table_name="product_material_recipes")
    op.drop_index(op.f("ix_product_material_recipes_id"), table_name="product_material_recipes")
    op.drop_index(op.f("ix_product_material_recipes_branch_id"), table_name="product_material_recipes")
    op.drop_table("product_material_recipes")
