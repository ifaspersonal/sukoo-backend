from datetime import date
from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.stock_movement import StockMovement

def ensure_daily_stock(db: Session, product: Product, user_id: int):
    today = date.today()

    if product.stock_date != today:
        diff = product.daily_stock - product.stock

        product.stock = product.daily_stock
        product.stock_date = today

        db.add(
            StockMovement(
                product_id=product.id,
                type="RESET",
                qty=diff,
                note=f"Daily reset {today}",
                created_by=user_id,
            )
        )

def reset_daily_stock(db: Session):
    products = (
        db.query(Product)
        .filter(Product.is_unlimited == False)
        .all()
    )

    for p in products:
        if p.daily_stock and p.daily_stock > 0:
            p.stock = p.daily_stock

    db.commit()
    return products