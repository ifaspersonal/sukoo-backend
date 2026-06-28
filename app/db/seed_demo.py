from datetime import date, datetime, timedelta, timezone

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.branch import Branch
from app.models.customer import Customer
from app.models.material import Material
from app.models.material_stock_opname import MaterialStockOpname
from app.models.point_history import PointHistory
from app.models.product import Product
from app.models.product_material_recipe import ProductMaterialRecipe
from app.models.transaction import Transaction
from app.models.transaction_item import TransactionItem
from app.models.user import User
from app.utils.password import hash_password


PRODUCTS = [
    ("Kopi Lembayung Arabica 250ml", 25000, 12000, "drink", 24, False),
    ("Kopi Susu Sukoo", 18000, 8500, "drink", 30, False),
    ("Americano", 15000, 5500, "drink", 25, False),
    ("Cafe Latte", 22000, 9500, "drink", 20, False),
    ("Caramel Macchiato", 25000, 11000, "drink", 18, False),
    ("Matcha Latte", 24000, 10500, "drink", 15, False),
    ("Chocolate", 22000, 9500, "drink", 15, False),
    ("Es Teh Lemon", 14000, 5000, "drink", 20, False),
    ("Croissant Butter", 18000, 9000, "food", 12, False),
    ("Roti Bakar Cokelat", 17000, 7500, "food", 10, False),
    ("Air Mineral", 8000, 3000, "other", 0, True),
]

MATERIALS = [
    ("Biji Kopi House Blend", "gram", 2500, 600),
    ("Susu Full Cream", "ml", 6000, 1200),
    ("Gula Aren", "gram", 1800, 300),
    ("Creamer", "gram", 1200, 250),
    ("Cup 16oz", "pcs", 120, 30),
    ("Sedotan", "pcs", 140, 35),
    ("Plastik Takeaway", "pcs", 100, 25),
    ("Matcha Powder", "gram", 900, 180),
]


def reset_demo_database() -> None:
    if not str(engine.url).startswith("sqlite"):
        raise RuntimeError("Demo seed hanya boleh dijalankan pada database SQLite lokal")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        branches = [
            Branch(id=1, name="Cipinang"),
            Branch(id=2, name="Cawang"),
            Branch(id=3, name="BKT"),
        ]
        db.add_all(branches)

        owner = User(
            username="owner",
            password=hash_password("owner123"),
            role="owner",
            is_active=True,
        )
        cashier = User(
            username="kasir",
            password=hash_password("kasir123"),
            role="kasir",
            branch_id=1,
            is_active=True,
        )
        supervisor = User(
            username="supervisor",
            password=hash_password("supervisor123"),
            role="supervisor",
            branch_id=1,
            is_active=True,
        )
        db.add_all([owner, cashier, supervisor])
        db.flush()

        products: list[Product] = []
        for branch_id in (1, 2, 3):
            for name, price, cost, category, stock, unlimited in PRODUCTS:
                product = Product(
                    name=name,
                    price=price + ((branch_id - 1) * 1000),
                    cost_price=cost,
                    category=category,
                    loyalty_point_value=1 if category == "drink" else 0,
                    stock=stock,
                    daily_stock=stock,
                    stock_date=date.today(),
                    is_unlimited=unlimited,
                    is_active=True,
                    branch_id=branch_id,
                )
                products.append(product)
                db.add(product)
        db.flush()

        materials: list[Material] = []
        for branch_id in (1, 2, 3):
            for name, unit, par_stock, alert_threshold in MATERIALS:
                material = Material(
                    name=name,
                    unit=unit,
                    branch_id=branch_id,
                    par_stock=par_stock,
                    alert_threshold=alert_threshold,
                    is_active=True,
                )
                materials.append(material)
                db.add(material)
        db.flush()

        products_by_branch_name = {
            (product.branch_id, product.name): product for product in products
        }
        materials_by_branch_name = {
            (material.branch_id, material.name): material for material in materials
        }

        recipe_templates = {
            "Kopi Lembayung Arabica 250ml": [
                ("Biji Kopi House Blend", 20),
                ("Cup 16oz", 1),
                ("Susu Full Cream", 20),
                ("Gula Aren", 20),
                ("Creamer", 20),
                ("Sedotan", 1),
                ("Plastik Takeaway", 1),
            ],
            "Kopi Susu Sukoo": [
                ("Biji Kopi House Blend", 18),
                ("Cup 16oz", 1),
                ("Susu Full Cream", 90),
                ("Gula Aren", 18),
                ("Sedotan", 1),
            ],
            "Americano": [
                ("Biji Kopi House Blend", 18),
                ("Cup 16oz", 1),
                ("Sedotan", 1),
            ],
            "Cafe Latte": [
                ("Biji Kopi House Blend", 18),
                ("Cup 16oz", 1),
                ("Susu Full Cream", 120),
                ("Sedotan", 1),
            ],
            "Matcha Latte": [
                ("Matcha Powder", 18),
                ("Cup 16oz", 1),
                ("Susu Full Cream", 120),
                ("Sedotan", 1),
            ],
        }

        for branch_id in (1, 2, 3):
            for product_name, recipe_items in recipe_templates.items():
                product = products_by_branch_name.get((branch_id, product_name))
                if not product:
                    continue

                for material_name, qty_per_unit in recipe_items:
                    material = materials_by_branch_name.get((branch_id, material_name))
                    if not material:
                        continue

                    db.add(
                        ProductMaterialRecipe(
                            product_id=product.id,
                            material_id=material.id,
                            branch_id=branch_id,
                            qty_per_unit=qty_per_unit,
                        )
                    )

        customer = Customer(
            name="Pelanggan Demo",
            phone="081234567890",
            points=16,
        )
        db.add(customer)
        db.flush()

        branch_one_products = [p for p in products if p.branch_id == 1]
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        for index in range(12):
            first = branch_one_products[index % 7]
            second = branch_one_products[(index + 2) % 7]
            qty_first = 1 + (index % 2)
            qty_second = 1
            total = (first.price * qty_first) + second.price
            created_at = now - timedelta(days=index % 6, hours=(index * 2) % 10)

            transaction = Transaction(
                invoice_no=f"DEMO-{index + 1:04d}",
                total=total,
                payment_method="cash" if index % 2 == 0 else "qris",
                type="sale",
                customer_id=customer.id if index % 3 == 0 else None,
                created_by=cashier.id,
                branch_id=1 + (index % 3),
                created_at=created_at,
            )
            db.add(transaction)
            db.flush()

            db.add_all(
                [
                    TransactionItem(
                        transaction_id=transaction.id,
                        product_id=first.id,
                        price=first.price,
                        cost_price=first.cost_price,
                        qty=qty_first,
                        subtotal=first.price * qty_first,
                    ),
                    TransactionItem(
                        transaction_id=transaction.id,
                        product_id=second.id,
                        price=second.price,
                        cost_price=second.cost_price,
                        qty=qty_second,
                        subtotal=second.price,
                    ),
                ]
            )

            if transaction.customer_id:
                db.add(
                    PointHistory(
                        customer_id=customer.id,
                        transaction_id=transaction.id,
                        points=qty_first + qty_second,
                        type="earn",
                        description=f"Demo points from {transaction.invoice_no}",
                        created_at=created_at,
                    )
                )

        today = date.today()
        branch_one_materials = [m for m in materials if m.branch_id == 1]
        for index, material in enumerate(branch_one_materials):
            opening_qty = max(
                float((material.alert_threshold or 0) + 50),
                float((material.par_stock or 0) - (index * 20)),
            )
            estimated_usage = min(opening_qty * 0.45, 120 + index * 8)
            closing_qty = max(0, opening_qty - estimated_usage)
            db.add_all(
                [
                    MaterialStockOpname(
                        material_id=material.id,
                        branch_id=material.branch_id,
                        shift_type="opening",
                        qty=opening_qty,
                        unit=material.unit,
                        checked_for_date=today,
                        note="Dummy stok awal shift",
                        created_by=cashier.id,
                        created_at=now.replace(hour=2, minute=0, second=0, microsecond=0),
                    ),
                    MaterialStockOpname(
                        material_id=material.id,
                        branch_id=material.branch_id,
                        shift_type="closing",
                        qty=closing_qty,
                        unit=material.unit,
                        checked_for_date=today,
                        note="Dummy stok akhir shift",
                        created_by=cashier.id,
                        created_at=now.replace(hour=13, minute=0, second=0, microsecond=0),
                    ),
                ]
            )

        db.commit()
    finally:
        db.close()

    print("Demo database siap.")
    print("Owner : owner / owner123")
    print("Kasir : kasir / kasir123")


if __name__ == "__main__":
    reset_demo_database()
