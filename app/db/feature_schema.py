import logging

from sqlalchemy import inspect

from app.db.session import engine
from app.models.base import Base
from app.models.material import Material
from app.models.material_stock_opname import MaterialStockOpname
from app.models.product_material_recipe import ProductMaterialRecipe


logger = logging.getLogger(__name__)


FEATURE_TABLES = [
    Material.__table__,
    MaterialStockOpname.__table__,
    ProductMaterialRecipe.__table__,
]


def ensure_feature_tables() -> None:
    """Create only the new opname/recipe feature tables when missing.

    This intentionally does not run seed data and does not alter existing
    business tables such as transactions, products, customers, or users.
    """

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    missing_tables = [
        table for table in FEATURE_TABLES if table.name not in existing_tables
    ]

    if not missing_tables:
        logger.info("Feature schema already available")
        return

    Base.metadata.create_all(
        bind=engine,
        tables=missing_tables,
        checkfirst=True,
    )
    logger.info(
        "Created feature tables: %s",
        ", ".join(table.name for table in missing_tables),
    )
