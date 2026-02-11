from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut
from app.services.stock_service import ensure_daily_stock
from datetime import date
from app.core.roles import require_role
from app.core.security import get_current_user
from app.services.product_service import create_product as create_product_service


router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/", response_model=list[ProductOut],dependencies=[Depends(get_current_user)])
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active == True).all()

    for p in products:
        if not p.is_unlimited:
            ensure_daily_stock(db, p, user_id=1)

    db.commit()
    return products

@router.post("/", response_model=ProductOut,dependencies=[Depends(require_role("owner", "supervisor"))])
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    return create_product_service(db, payload)

@router.put("/{product_id}", response_model=ProductOut, dependencies=[Depends(require_role("owner", "supervisor"))])
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db)
):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in payload.dict(exclude_unset=True).items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}",  dependencies=[Depends(require_role("owner"))])
def deactivate_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    db.commit()
    return {"status": "deleted"}