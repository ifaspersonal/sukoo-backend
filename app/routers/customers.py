from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.models.customer import Customer
from app.core.security import get_current_user

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get("/by-phone/{phone}")
def get_customer_by_phone(
    phone: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    customer = db.query(Customer).filter(Customer.phone == phone).first()

    if not customer:
        return {"exists": False}

    return {
        "exists": True,
        "id": customer.id,
        "name": customer.name,
        "points": customer.points or 0,
    }