from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.schemas.stock import StockAdjust
from app.core.roles import require_role
from app.services.stock_service import reset_daily_stock

router = APIRouter(prefix="/stocks", tags=["Stock"])

@router.post("/{product_id}/in", dependencies=[Depends(require_role("owner", "supervisor"))])
def stock_in(
    product_id: int,
    payload: StockAdjust,
    db: Session = Depends(get_db)
):
    product = db.query(Product).get(product_id)
    if not product or product.is_unlimited:
        raise HTTPException(status_code=400, detail="Invalid product")

    product.stock += payload.qty

    movement = StockMovement(
        product_id=product_id,
        type="IN",
        qty=payload.qty,
        note=payload.note,
        created_by=1,  # TEMP (kasir id)
    )

    db.add(movement)
    db.commit()
    return {"status": "stock added"}

@router.post("/{product_id}/opname", dependencies=[Depends(require_role("owner", "supervisor"))])
def stock_opname(
    product_id: int,
    payload: StockAdjust,
    db: Session = Depends(get_db)
):
    product = db.query(Product).get(product_id)
    if not product or product.is_unlimited:
        raise HTTPException(status_code=400, detail="Invalid product")

    diff = payload.qty - product.stock
    product.stock = payload.qty

    movement = StockMovement(
        product_id=product_id,
        type="OPNAME",
        qty=diff,
        note=payload.note,
        created_by=1,
    )

    db.add(movement)
    db.commit()
    return {"status": "stock adjusted"}


@router.post("/reset-daily")
def reset_stock_daily(db: Session = Depends(get_db)):
    products = reset_daily_stock(db)
    return {
        "message": "Daily stock reset",
        "count": len(products),
    }