"""add material opname

Revision ID: a9f4d2c7b8e1
Revises: 34672bd9acfc
Create Date: 2026-06-28 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9f4d2c7b8e1"
down_revision: Union[str, Sequence[str], None] = "34672bd9acfc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("par_stock", sa.Float(), nullable=True),
        sa.Column("alert_threshold", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_materials_branch_id"), "materials", ["branch_id"], unique=False)
    op.create_index(op.f("ix_materials_id"), "materials", ["id"], unique=False)

    op.create_table(
        "material_stock_opnames",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("shift_type", sa.String(), nullable=False),
        sa.Column("qty", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("checked_for_date", sa.Date(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_material_stock_opnames_branch_id"),
        "material_stock_opnames",
        ["branch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_opnames_checked_for_date"),
        "material_stock_opnames",
        ["checked_for_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_opnames_id"),
        "material_stock_opnames",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_stock_opnames_material_id"),
        "material_stock_opnames",
        ["material_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_material_stock_opnames_material_id"), table_name="material_stock_opnames")
    op.drop_index(op.f("ix_material_stock_opnames_id"), table_name="material_stock_opnames")
    op.drop_index(op.f("ix_material_stock_opnames_checked_for_date"), table_name="material_stock_opnames")
    op.drop_index(op.f("ix_material_stock_opnames_branch_id"), table_name="material_stock_opnames")
    op.drop_table("material_stock_opnames")
    op.drop_index(op.f("ix_materials_id"), table_name="materials")
    op.drop_index(op.f("ix_materials_branch_id"), table_name="materials")
    op.drop_table("materials")
