from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.models.transaction import Transaction
from app.models.transaction_item import TransactionItem
from app.models.product import Product
from app.models.customer import Customer
from app.models.point_history import PointHistory
from app.models.stock_movement import StockMovement
from app.services.stock_service import ensure_daily_stock


REDEEM_RATE = 10  # 🔥 10 poin = 1 minuman


def generate_invoice_no() -> str:
    return f"SK-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def create_transaction(
    db: Session,
    items: list,
    payment_method: str,
    customer_phone: str | None,
    customer_name: str | None,
    created_by: int,
    redeem_points: int = 0,
):
    if not items:
        raise ValueError("Items cannot be empty")

    invoice_no = generate_invoice_no()
    total_amount = 0
    total_points = 0
    tx_items: list[TransactionItem] = []

    # ==============================
    # OPTIONAL CUSTOMER (LOCK)
    # ==============================
    customer = None
    if customer_phone:
        customer = (
            db.query(Customer)
            .filter(Customer.phone == customer_phone)
            .with_for_update()
            .first()
        )

        if not customer:
            customer = Customer(
                phone=customer_phone,
                name=customer_name,
                points=0,
            )
            db.add(customer)
            db.flush()

    # ==============================
    # LOCK PRODUCTS
    # ==============================
    products = (
        db.query(Product)
        .filter(Product.id.in_([i.product_id for i in items]))
        .with_for_update()
        .all()
    )

    product_map = {p.id: p for p in products}

    total_qty = 0

    for item in items:
        product = product_map.get(item.product_id)

        if not product or not product.is_active:
            raise ValueError("Invalid product")

        ensure_daily_stock(db, product, created_by)

        if not product.is_unlimited and product.stock < item.qty:
            raise ValueError(f"Stock not enough for {product.name}")

        subtotal = product.price * item.qty
        total_amount += subtotal
        total_qty += item.qty

        # 🔥 INTEGER LOYALTY SYSTEM
        if product.loyalty_point_value and product.loyalty_point_value > 0:
            total_points += product.loyalty_point_value * item.qty

        tx_items.append(
            TransactionItem(
                product_id=product.id,
                price=product.price,
                cost_price=product.cost_price,
                qty=item.qty,
                subtotal=subtotal,
            )
        )

    # ==============================
    # 🔁 REDEEM LOGIC (10 poin = 1 item)
    # ==============================
    is_full_redeem = False
    redeem_history = None

    if redeem_points and redeem_points > 0:

        if not customer:
            raise ValueError("Redeem requires customer")

        if redeem_points % REDEEM_RATE != 0:
            raise ValueError("Redeem must be multiple of 10 points")

        if customer.points < redeem_points:
            raise ValueError("Insufficient points")

        redeem_qty = redeem_points // REDEEM_RATE

        if redeem_qty > total_qty:
            raise ValueError("Redeem exceeds item quantity")

        # Kurangi poin
        customer.points -= redeem_points

        # Jika semua item diredeem → full redeem
        if redeem_qty == total_qty:
            total_amount = 0
            payment_method = "redeem"
            is_full_redeem = True

        # Simpan redeem history (tx_id diisi nanti)
        redeem_history = PointHistory(
            customer_id=customer.id,
            transaction_id=None,
            points=-redeem_points,
            type="redeem",
            description=f"Redeem on {invoice_no}",
        )

        db.add(redeem_history)

    # ==============================
    # CREATE TRANSACTION
    # ==============================
    tx = Transaction(
        invoice_no=invoice_no,
        total=total_amount,
        payment_method=payment_method,
        customer_id=customer.id if customer else None,
        created_by=created_by,
    )

    db.add(tx)
    db.flush()

    # ==============================
    # ATTACH ITEMS + STOCK MOVEMENT
    # ==============================
    for item, tx_item in zip(items, tx_items):
        tx_item.transaction_id = tx.id
        db.add(tx_item)

        product = product_map[item.product_id]

        if not product.is_unlimited:
            product.stock -= item.qty

            db.add(
                StockMovement(
                    product_id=product.id,
                    type="OUT",
                    qty=item.qty,
                    note=f"TX {invoice_no}",
                    created_by=created_by,
                )
            )

    # ==============================
    # FIX redeem history tx_id
    # ==============================
    if redeem_history:
        redeem_history.transaction_id = tx.id

    # ==============================
    # APPLY EARN POINTS
    # (NO earn if full redeem)
    # ==============================
    if customer and total_points > 0 and not is_full_redeem:
        customer.points += total_points

        db.add(
            PointHistory(
                customer_id=customer.id,
                transaction_id=tx.id,
                points=total_points,
                type="earn",
                description=f"Earn from {invoice_no}",
            )
        )

    db.commit()
    db.refresh(tx)

    return tx