from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime

from app.core.deps import get_db
from app.core.security import get_current_user

from app.models.user import User
from app.models.transaction import Transaction
from app.models.transaction_item import TransactionItem
from app.models.product import Product
from app.models.point_history import PointHistory
from app.models.material import Material
from app.models.material_stock_opname import MaterialStockOpname
from app.models.product_material_recipe import ProductMaterialRecipe

router = APIRouter(prefix="/reports", tags=["Reports"])


# =========================================
# DATE RANGE HELPER
# =========================================
def get_date_range(period: str):
    today = date.today()

    if period == "weekly":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)

    elif period == "monthly":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)

    else:
        start = today
        end = today

    return start, end


def previous_date_range(start_date: date, end_date: date):
    days = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    return previous_start, previous_end


def percent_change(current: int | float, previous: int | float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def sales_filter_for_range(
    start_date: date,
    end_date: date,
    branch_id: int | None = None,
):
    filters = [
        Transaction.type == "sale",
        func.date(Transaction.created_at) >= start_date,
        func.date(Transaction.created_at) <= end_date,
    ]

    if branch_id:
        filters.append(Transaction.branch_id == branch_id)

    return filters


def summarize_sales(db: Session, start_date: date, end_date: date, branch_id: int | None):
    filters = sales_filter_for_range(start_date, end_date, branch_id)

    revenue = (
        db.query(func.sum(TransactionItem.subtotal))
        .join(Transaction)
        .filter(*filters)
        .scalar()
        or 0
    )

    cost = (
        db.query(func.sum(TransactionItem.cost_price * TransactionItem.qty))
        .join(Transaction)
        .filter(*filters)
        .scalar()
        or 0
    )

    transactions = db.query(Transaction).filter(*filters).count()
    qty = (
        db.query(func.sum(TransactionItem.qty))
        .join(Transaction)
        .filter(*filters)
        .scalar()
        or 0
    )

    return {
        "revenue": int(revenue),
        "cost": int(cost),
        "profit": int(revenue - cost),
        "transactions": int(transactions),
        "items_sold": int(qty),
        "average_ticket": int(revenue / transactions) if transactions else 0,
    }


def latest_opname_usage_by_material(
    rows: list[MaterialStockOpname],
) -> dict[int, float]:
    latest_by_key: dict[tuple[int, date], dict[str, MaterialStockOpname]] = {}

    sorted_rows = sorted(
        rows,
        key=lambda row: (row.checked_for_date, row.created_at, row.id),
        reverse=True,
    )

    for row in sorted_rows:
        key = (row.material_id, row.checked_for_date)
        latest_by_key.setdefault(key, {}).setdefault(row.shift_type, row)

    usage_by_material: dict[int, float] = {}
    for (material_id, _checked_date), shifts in latest_by_key.items():
        opening = shifts.get("opening")
        closing = shifts.get("closing")
        if not opening or not closing:
            continue

        usage_by_material[material_id] = usage_by_material.get(material_id, 0) + (
            opening.qty - closing.qty
        )

    return usage_by_material


def calculate_recipe_variance(
    db: Session,
    start_date: date,
    end_date: date,
    branch_id: int | None,
) -> list[dict]:
    filters = sales_filter_for_range(start_date, end_date, branch_id)

    sold_rows = (
        db.query(
            TransactionItem.product_id,
            Product.name.label("product_name"),
            Product.branch_id.label("branch_id"),
            func.sum(TransactionItem.qty).label("qty_sold"),
        )
        .join(Transaction, Transaction.id == TransactionItem.transaction_id)
        .join(Product, Product.id == TransactionItem.product_id)
        .filter(*filters)
        .group_by(TransactionItem.product_id, Product.name, Product.branch_id)
        .all()
    )

    sold_by_product = {
        row.product_id: {
            "product_name": row.product_name,
            "branch_id": row.branch_id,
            "qty_sold": float(row.qty_sold or 0),
        }
        for row in sold_rows
    }

    if not sold_by_product:
        return []

    recipes = (
        db.query(ProductMaterialRecipe)
        .filter(ProductMaterialRecipe.product_id.in_(sold_by_product.keys()))
        .all()
    )

    material_ids = list({recipe.material_id for recipe in recipes})
    materials = (
        db.query(Material).filter(Material.id.in_(material_ids)).all()
        if material_ids
        else []
    )
    material_map = {material.id: material for material in materials}

    expected_by_material: dict[int, float] = {}
    breakdown_by_material: dict[int, list[dict]] = {}

    for recipe in recipes:
        sold = sold_by_product.get(recipe.product_id)
        material = material_map.get(recipe.material_id)
        if not sold or not material:
            continue

        expected_qty = sold["qty_sold"] * recipe.qty_per_unit
        expected_by_material[recipe.material_id] = (
            expected_by_material.get(recipe.material_id, 0) + expected_qty
        )
        breakdown_by_material.setdefault(recipe.material_id, []).append(
            {
                "product_id": recipe.product_id,
                "product_name": sold["product_name"],
                "qty_sold": sold["qty_sold"],
                "qty_per_unit": recipe.qty_per_unit,
                "expected_qty": round(expected_qty, 2),
            }
        )

    opname_rows = (
        db.query(MaterialStockOpname)
        .filter(
            MaterialStockOpname.material_id.in_(material_ids),
            MaterialStockOpname.checked_for_date >= start_date,
            MaterialStockOpname.checked_for_date <= end_date,
        )
        .all()
        if material_ids
        else []
    )
    actual_by_material = latest_opname_usage_by_material(opname_rows)

    result = []
    for material_id, expected_qty in expected_by_material.items():
        material = material_map.get(material_id)
        if not material:
            continue

        actual_qty = actual_by_material.get(material_id)
        variance_qty = None
        variance_percent = None
        status = "pending_opname"

        if actual_qty is not None:
            variance_qty = actual_qty - expected_qty
            variance_percent = (
                round((variance_qty / expected_qty) * 100, 1)
                if expected_qty
                else None
            )

            if expected_qty and actual_qty > expected_qty * 1.1:
                status = "over_usage"
            elif expected_qty and actual_qty < expected_qty * 0.9:
                status = "under_usage"
            else:
                status = "ok"

        result.append(
            {
                "material_id": material.id,
                "material_name": material.name,
                "unit": material.unit,
                "branch_id": material.branch_id,
                "expected_qty": round(expected_qty, 2),
                "actual_qty": round(actual_qty, 2) if actual_qty is not None else None,
                "variance_qty": round(variance_qty, 2) if variance_qty is not None else None,
                "variance_percent": variance_percent,
                "status": status,
                "product_breakdown": breakdown_by_material.get(material_id, []),
            }
        )

    return sorted(
        result,
        key=lambda row: abs(row["variance_percent"] or 0),
        reverse=True,
    )


@router.get("")
def report_summary(
    period: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    start: str | None = None,
    end: str | None = None,
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # 🔒 ROLE CHECK
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Forbidden")

    # ==============================
    # DATE LOGIC
    # ==============================
    if start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    else:
        start_date, end_date = get_date_range(period)

    # ==============================
    # ✅ SINGLE SOURCE FILTER
    # ==============================
    base_filter = [
        func.date(Transaction.created_at) >= start_date,
        func.date(Transaction.created_at) <= end_date,
    ]

    if branch_id:
        base_filter.append(Transaction.branch_id == branch_id)

    sale_filter = [
        Transaction.type == "sale",
        *base_filter,
    ]

    # ==============================
    # KPI
    # ==============================
    total_revenue = (
        db.query(func.sum(TransactionItem.subtotal))
        .join(Transaction)
        .filter(*sale_filter)
        .scalar()
        or 0
    )

    total_cost = (
        db.query(func.sum(TransactionItem.cost_price * TransactionItem.qty))
        .join(Transaction)
        .filter(*sale_filter)
        .scalar()
        or 0
    )

    total_transactions = (
        db.query(Transaction)
        .filter(*sale_filter)
        .count()
    )

    profit = total_revenue - total_cost

    redeem_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.type == "redeem",
            *base_filter,
        )
        .count()
    )

    # ==============================
    # PAYMENT
    # ==============================
    def payment_total(method: str):
        return (
            db.query(func.sum(TransactionItem.subtotal))
            .join(Transaction)
            .filter(*sale_filter, Transaction.payment_method == method)
            .scalar()
            or 0
        )

    cash_total = payment_total("cash")
    qris_total = payment_total("qris")

    # ==============================
    # TOP PRODUCTS
    # ==============================
    top_products = (
        db.query(
            Product.name,
            func.sum(TransactionItem.qty).label("qty")
        )
        .join(TransactionItem)
        .join(Transaction)
        .filter(*sale_filter)
        .group_by(Product.name)
        .order_by(func.sum(TransactionItem.qty).desc())
        .limit(5)
        .all()
    )

    # ==============================
    # HOURLY
    # ==============================
    hourly_sales = []

    if period == "daily" and not (start and end):
        hourly = (
            db.query(
                func.extract("hour", Transaction.created_at).label("hour"),
                func.sum(TransactionItem.subtotal).label("total")
            )
            .join(TransactionItem)
            .filter(*sale_filter)
            .group_by("hour")
            .order_by("hour")
            .all()
        )

        hourly_sales = [
            {"hour": int(h.hour), "total": int(h.total)}
            for h in hourly
        ]

    # ==============================
    # LOYALTY
    # ==============================
    total_points_earned = (
        db.query(func.sum(PointHistory.points))
        .join(Transaction, Transaction.id == PointHistory.transaction_id)
        .filter(
            PointHistory.type == "earn",
            func.date(Transaction.created_at) >= start_date,
            func.date(Transaction.created_at) <= end_date,
            *([Transaction.branch_id == branch_id] if branch_id else []),
        )
        .scalar()
        or 0
    )

    total_points_redeemed = (
        db.query(func.sum(PointHistory.points))
        .join(Transaction, Transaction.id == PointHistory.transaction_id)
        .filter(
            PointHistory.type == "redeem",
            func.date(Transaction.created_at) >= start_date,
            func.date(Transaction.created_at) <= end_date,
            *([Transaction.branch_id == branch_id] if branch_id else []),
        )
        .scalar()
        or 0
    )

    total_points_redeemed = abs(total_points_redeemed)
    net_points = total_points_earned - total_points_redeemed

    # ==============================
    # SALES TREND
    # ==============================
    trend = (
        db.query(
            func.date(Transaction.created_at).label("date"),
            func.sum(TransactionItem.subtotal).label("revenue"),
            func.sum(TransactionItem.cost_price * TransactionItem.qty).label("cost")
        )
        .join(TransactionItem)
        .filter(
            Transaction.type == "sale",
            *base_filter,
        )
        .group_by("date")
        .order_by("date")
        .all()
    )

    trend_sales = [
        {
            "date": str(t.date),
            "revenue": int(t.revenue or 0),
            "profit": int((t.revenue or 0) - (t.cost or 0)),
        }
        for t in trend
    ]

    # ==============================
    # TRANSACTIONS
    # ==============================
    transactions = (
        db.query(Transaction)
        .filter(*base_filter)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    tx_list = [
        {
            "id": tx.id,
            "created_at": tx.created_at,
            "payment_method": tx.payment_method,
            "type": tx.type,
            "total": tx.total,
        }
        for tx in transactions
    ]

    return {
        "period": period,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "total_revenue": int(total_revenue),
        "total_cost": int(total_cost),
        "profit": int(profit),
        "total_transactions": total_transactions,
        "redeem_transactions": redeem_transactions,
        "cash_total": int(cash_total),
        "qris_total": int(qris_total),
        "top_products": [
            {"name": p.name, "qty": int(p.qty)}
            for p in top_products
        ],
        "hourly_sales": hourly_sales,
        "trend_sales": trend_sales,
        "total_points_earned": int(total_points_earned),
        "total_points_redeemed": int(total_points_redeemed),
        "net_points": int(net_points),
        "transactions": tx_list,
    }


@router.get("/insights")
def report_insights(
    period: str = Query("weekly", enum=["daily", "weekly", "monthly"]),
    start: str | None = None,
    end: str | None = None,
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Forbidden")

    if start and end:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    else:
        start_date, end_date = get_date_range(period)

    previous_start, previous_end = previous_date_range(start_date, end_date)
    current_summary = summarize_sales(db, start_date, end_date, branch_id)
    previous_summary = summarize_sales(db, previous_start, previous_end, branch_id)

    filters = sales_filter_for_range(start_date, end_date, branch_id)

    payment_rows = (
        db.query(
            Transaction.payment_method,
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.total).label("total"),
        )
        .filter(*filters)
        .group_by(Transaction.payment_method)
        .all()
    )
    payment_mix = [
        {
            "method": row.payment_method,
            "count": int(row.count or 0),
            "total": int(row.total or 0),
            "share": round(((row.total or 0) / current_summary["revenue"]) * 100, 1)
            if current_summary["revenue"]
            else 0,
        }
        for row in payment_rows
    ]

    top_products = (
        db.query(
            Product.id,
            Product.name,
            func.sum(TransactionItem.qty).label("qty"),
            func.sum(TransactionItem.subtotal).label("revenue"),
        )
        .join(TransactionItem, TransactionItem.product_id == Product.id)
        .join(Transaction, Transaction.id == TransactionItem.transaction_id)
        .filter(*filters)
        .group_by(Product.id, Product.name)
        .order_by(func.sum(TransactionItem.subtotal).desc())
        .limit(5)
        .all()
    )

    top_product_rows = [
        {
            "id": row.id,
            "name": row.name,
            "qty": int(row.qty or 0),
            "revenue": int(row.revenue or 0),
            "share": round(((row.revenue or 0) / current_summary["revenue"]) * 100, 1)
            if current_summary["revenue"]
            else 0,
        }
        for row in top_products
    ]

    tx_rows = db.query(Transaction).filter(*filters).all()
    hourly_map: dict[int, int] = {}
    weekday_map: dict[int, int] = {}

    for tx in tx_rows:
        wib_hour = (tx.created_at.hour + 7) % 24
        hourly_map[wib_hour] = hourly_map.get(wib_hour, 0) + tx.total
        weekday_map[tx.created_at.weekday()] = weekday_map.get(tx.created_at.weekday(), 0) + tx.total

    peak_hour = None
    if hourly_map:
        hour, total = max(hourly_map.items(), key=lambda item: item[1])
        peak_hour = {"hour": hour, "total": int(total)}

    weekday_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    best_day = None
    if weekday_map:
        weekday, total = max(weekday_map.items(), key=lambda item: item[1])
        best_day = {"day": weekday_names[weekday], "total": int(total)}

    low_stock_query = db.query(Product).filter(
        Product.is_active == True,
        Product.is_unlimited == False,
        Product.stock <= 5,
    )
    if branch_id:
        low_stock_query = low_stock_query.filter(Product.branch_id == branch_id)

    low_stock_products = [
        {
            "id": product.id,
            "name": product.name,
            "stock": product.stock,
            "branch_id": product.branch_id,
        }
        for product in low_stock_query.order_by(Product.stock.asc()).limit(8).all()
    ]

    material_query = db.query(Material).filter(Material.is_active == True)
    if branch_id:
        material_query = material_query.filter(Material.branch_id == branch_id)

    materials = material_query.order_by(Material.branch_id, Material.name).all()
    material_ids = [material.id for material in materials]
    latest_rows = (
        db.query(MaterialStockOpname)
        .filter(
            MaterialStockOpname.material_id.in_(material_ids),
            MaterialStockOpname.checked_for_date == date.today(),
        )
        .order_by(MaterialStockOpname.created_at.desc(), MaterialStockOpname.id.desc())
        .all()
        if material_ids
        else []
    )

    latest_by_material: dict[int, dict[str, MaterialStockOpname]] = {}
    for row in latest_rows:
        latest_by_material.setdefault(row.material_id, {}).setdefault(row.shift_type, row)

    material_variance = []
    for material in materials:
        latest = latest_by_material.get(material.id, {})
        opening = latest.get("opening")
        closing = latest.get("closing")
        used_qty = None
        if opening and closing:
            used_qty = round(opening.qty - closing.qty, 2)

        material_variance.append(
            {
                "id": material.id,
                "name": material.name,
                "unit": material.unit,
                "branch_id": material.branch_id,
                "opening_qty": opening.qty if opening else None,
                "closing_qty": closing.qty if closing else None,
                "used_qty": used_qty,
                "status": "low"
                if closing and material.alert_threshold and closing.qty <= material.alert_threshold
                else "ok"
                if closing
                else "pending",
            }
        )

    recipe_variance = calculate_recipe_variance(db, start_date, end_date, branch_id)

    recommendations = []
    revenue_change = percent_change(
        current_summary["revenue"],
        previous_summary["revenue"],
    )
    profit_change = percent_change(
        current_summary["profit"],
        previous_summary["profit"],
    )

    if revenue_change is not None and revenue_change < 0:
        recommendations.append("Pendapatan turun dibanding periode sebelumnya; cek produk terlaris dan jam ramai untuk promo yang lebih terarah.")
    elif revenue_change is not None and revenue_change > 10:
        recommendations.append("Pendapatan naik kuat; pertahankan menu dan jam operasional yang sedang perform.")

    if top_product_rows:
        recommendations.append(f"Produk kontributor terbesar: {top_product_rows[0]['name']} ({top_product_rows[0]['share']}% revenue).")

    if peak_hour:
        recommendations.append(f"Jam ramai terdeteksi sekitar {peak_hour['hour']:02d}:00 WIB; pastikan stok bahan dan staffing aman.")

    if low_stock_products:
        recommendations.append(f"{len(low_stock_products)} produk stok rendah; prioritaskan restock sebelum jam ramai.")

    over_usage = [
        row for row in recipe_variance if row["status"] == "over_usage"
    ]
    if over_usage:
        recommendations.append(
            f"{len(over_usage)} bahan terpakai di atas takaran resep; cek konsistensi takaran kasir dan potensi waste."
        )

    return {
        "period": period,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "previous_start_date": str(previous_start),
        "previous_end_date": str(previous_end),
        "summary": {
            **current_summary,
            "revenue_change_percent": revenue_change,
            "profit_change_percent": profit_change,
            "transaction_change_percent": percent_change(
                current_summary["transactions"],
                previous_summary["transactions"],
            ),
        },
        "previous_summary": previous_summary,
        "payment_mix": payment_mix,
        "top_products": top_product_rows,
        "peak_hour": peak_hour,
        "best_day": best_day,
        "low_stock_products": low_stock_products,
        "material_variance": material_variance,
        "recipe_variance": recipe_variance,
        "recommendations": recommendations,
    }


# =========================================
# TRANSACTION DETAIL (OWNER ONLY)
# =========================================
@router.get("/transaction/{transaction_id}")
def transaction_detail(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Forbidden")

    tx = db.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    items = (
        db.query(TransactionItem)
        .filter(TransactionItem.transaction_id == transaction_id)
        .all()
    )

    return {
        "id": tx.id,
        "created_at": tx.created_at,
        "payment_method": tx.payment_method,
        "type": tx.type,
        "total": tx.total,
        "items": [
            {
                "product_name": item.product.name if item.product else "-",
                "qty": item.qty,
                "subtotal": item.subtotal,
            }
            for item in items
        ]
    }
