from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate

def create_product(db: Session, payload: ProductCreate) -> Product:
    product = Product(
        name=payload.name,
        price=payload.price,
        cost_price=payload.cost_price,
        daily_stock=payload.daily_stock,
        stock=0,  # stock runtime, di-reset harian
        is_unlimited=payload.is_unlimited,
        is_active=True,
    )

    db.add(product)
    db.commit()
    db.refresh(product)
    return product