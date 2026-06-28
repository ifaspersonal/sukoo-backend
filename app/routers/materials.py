from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.roles import require_role
from app.core.security import get_current_user
from app.models.material import Material
from app.models.material_stock_opname import MaterialStockOpname
from app.models.product import Product
from app.models.product_material_recipe import ProductMaterialRecipe
from app.models.user import User
from app.schemas.material import (
    MaterialCreate,
    MaterialOpnameCreate,
    MaterialOpnameOut,
    MaterialOut,
    ProductRecipeOut,
    ProductRecipeSave,
    MaterialUpdate,
)

router = APIRouter(prefix="/materials", tags=["Materials"])


def resolve_branch_id(current_user: User, requested_branch_id: int | None) -> int | None:
    if current_user.role == "owner":
        return requested_branch_id
    return current_user.branch_id


def material_status(current_qty: float | None, threshold: float | None) -> str:
    if current_qty is None:
        return "unknown"
    if threshold and current_qty <= threshold:
        return "low"
    return "ok"


def build_material_out(
    material: Material,
    opening: MaterialStockOpname | None,
    closing: MaterialStockOpname | None,
) -> dict:
    current_qty = closing.qty if closing else opening.qty if opening else None
    return {
        "id": material.id,
        "name": material.name,
        "unit": material.unit,
        "branch_id": material.branch_id,
        "par_stock": material.par_stock or 0,
        "alert_threshold": material.alert_threshold or 0,
        "is_active": material.is_active,
        "latest_opening_qty": opening.qty if opening else None,
        "latest_closing_qty": closing.qty if closing else None,
        "current_qty": current_qty,
        "stock_status": material_status(current_qty, material.alert_threshold),
    }


def build_product_recipe_out(product: Product, recipes: list[ProductMaterialRecipe]) -> dict:
    return {
        "product_id": product.id,
        "product_name": product.name,
        "branch_id": product.branch_id,
        "items": [
            {
                "id": recipe.id,
                "material_id": recipe.material_id,
                "material_name": recipe.material.name if recipe.material else "-",
                "unit": recipe.material.unit if recipe.material else "",
                "qty_per_unit": recipe.qty_per_unit,
            }
            for recipe in recipes
        ],
    }


def latest_opnames_by_material(
    db: Session,
    material_ids: list[int],
    checked_for_date: date,
) -> dict[int, dict[str, MaterialStockOpname]]:
    if not material_ids:
        return {}

    rows = (
        db.query(MaterialStockOpname)
        .filter(
            MaterialStockOpname.material_id.in_(material_ids),
            MaterialStockOpname.checked_for_date == checked_for_date,
        )
        .order_by(MaterialStockOpname.created_at.desc(), MaterialStockOpname.id.desc())
        .all()
    )

    latest: dict[int, dict[str, MaterialStockOpname]] = defaultdict(dict)
    for row in rows:
        latest[row.material_id].setdefault(row.shift_type, row)

    return latest


@router.get("", response_model=list[MaterialOut])
def list_materials(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved_branch_id = resolve_branch_id(current_user, branch_id)

    query = db.query(Material).filter(Material.is_active == True)
    if resolved_branch_id:
        query = query.filter(Material.branch_id == resolved_branch_id)

    materials = query.order_by(Material.branch_id, Material.name).all()
    latest = latest_opnames_by_material(db, [m.id for m in materials], date.today())

    return [
        build_material_out(
            material,
            latest.get(material.id, {}).get("opening"),
            latest.get(material.id, {}).get("closing"),
        )
        for material in materials
    ]


@router.post(
    "",
    response_model=MaterialOut,
    dependencies=[Depends(require_role("owner", "supervisor"))],
)
def create_material(payload: MaterialCreate, db: Session = Depends(get_db)):
    material = Material(**payload.dict())
    db.add(material)
    db.commit()
    db.refresh(material)

    return build_material_out(material, None, None)


@router.get("/recipes", response_model=list[ProductRecipeOut])
def list_product_recipes(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved_branch_id = resolve_branch_id(current_user, branch_id)

    product_query = db.query(Product).filter(Product.is_active == True)
    if resolved_branch_id:
        product_query = product_query.filter(Product.branch_id == resolved_branch_id)

    products = product_query.order_by(Product.branch_id, Product.name).all()
    product_ids = [product.id for product in products]

    recipes = (
        db.query(ProductMaterialRecipe)
        .filter(ProductMaterialRecipe.product_id.in_(product_ids))
        .all()
        if product_ids
        else []
    )

    recipes_by_product: dict[int, list[ProductMaterialRecipe]] = defaultdict(list)
    for recipe in recipes:
        recipes_by_product[recipe.product_id].append(recipe)

    return [
        build_product_recipe_out(product, recipes_by_product.get(product.id, []))
        for product in products
    ]


@router.get("/recipes/product/{product_id}", response_model=ProductRecipeOut)
def get_product_recipe(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")

    if current_user.role != "owner" and product.branch_id != current_user.branch_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    recipes = (
        db.query(ProductMaterialRecipe)
        .filter(ProductMaterialRecipe.product_id == product_id)
        .all()
    )

    return build_product_recipe_out(product, recipes)


@router.put(
    "/recipes/product/{product_id}",
    response_model=ProductRecipeOut,
    dependencies=[Depends(require_role("owner", "supervisor"))],
)
def save_product_recipe(
    product_id: int,
    payload: ProductRecipeSave,
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")

    material_ids = [item.material_id for item in payload.items]
    materials = (
        db.query(Material)
        .filter(Material.id.in_(material_ids), Material.is_active == True)
        .all()
        if material_ids
        else []
    )
    material_map = {material.id: material for material in materials}

    missing = set(material_ids) - set(material_map.keys())
    if missing:
        raise HTTPException(status_code=404, detail="Material not found")

    for material in materials:
        if product.branch_id and material.branch_id != product.branch_id:
            raise HTTPException(
                status_code=400,
                detail=f"{material.name} tidak satu cabang dengan produk",
            )

    db.query(ProductMaterialRecipe).filter(
        ProductMaterialRecipe.product_id == product_id
    ).delete()

    recipes: list[ProductMaterialRecipe] = []
    for item in payload.items:
        if item.qty_per_unit <= 0:
            continue

        recipe = ProductMaterialRecipe(
            product_id=product_id,
            material_id=item.material_id,
            branch_id=product.branch_id or material_map[item.material_id].branch_id,
            qty_per_unit=item.qty_per_unit,
        )
        db.add(recipe)
        recipes.append(recipe)

    db.commit()

    for recipe in recipes:
        db.refresh(recipe)

    return build_product_recipe_out(product, recipes)


@router.put(
    "/{material_id}",
    response_model=MaterialOut,
    dependencies=[Depends(require_role("owner", "supervisor"))],
)
def update_material(
    material_id: int,
    payload: MaterialUpdate,
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    for key, value in payload.dict(exclude_unset=True).items():
        setattr(material, key, value)

    db.commit()
    db.refresh(material)

    latest = latest_opnames_by_material(db, [material.id], date.today())
    return build_material_out(
        material,
        latest.get(material.id, {}).get("opening"),
        latest.get(material.id, {}).get("closing"),
    )


@router.post("/opname", response_model=list[MaterialOpnameOut])
def create_material_opname(
    payload: MaterialOpnameCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("owner", "supervisor", "kasir"):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Items cannot be empty")

    material_ids = [item.material_id for item in payload.items]
    materials = db.query(Material).filter(Material.id.in_(material_ids)).all()
    material_map = {material.id: material for material in materials}

    missing = set(material_ids) - set(material_map.keys())
    if missing:
        raise HTTPException(status_code=404, detail="Material not found")

    checked_for_date = payload.checked_for_date or date.today()
    rows: list[MaterialStockOpname] = []

    for item in payload.items:
        material = material_map[item.material_id]

        if not material.is_active:
            raise HTTPException(status_code=400, detail=f"{material.name} is inactive")

        if current_user.role != "owner" and material.branch_id != current_user.branch_id:
            raise HTTPException(status_code=403, detail="Material branch mismatch")

        row = MaterialStockOpname(
            material_id=material.id,
            branch_id=material.branch_id,
            shift_type=payload.shift_type,
            qty=item.qty,
            unit=material.unit,
            checked_for_date=checked_for_date,
            note=payload.note,
            created_by=current_user.id,
        )
        rows.append(row)
        db.add(row)

    db.commit()

    for row in rows:
        db.refresh(row)

    return [
        {
            "id": row.id,
            "material_id": row.material_id,
            "material_name": material_map[row.material_id].name,
            "branch_id": row.branch_id,
            "shift_type": row.shift_type,
            "qty": row.qty,
            "unit": row.unit,
            "checked_for_date": row.checked_for_date,
            "note": row.note,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/opname/today")
def material_opname_today(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved_branch_id = resolve_branch_id(current_user, branch_id)

    query = db.query(Material).filter(Material.is_active == True)
    if resolved_branch_id:
        query = query.filter(Material.branch_id == resolved_branch_id)

    materials = query.order_by(Material.name).all()
    latest = latest_opnames_by_material(db, [m.id for m in materials], date.today())

    material_rows = [
        build_material_out(
            material,
            latest.get(material.id, {}).get("opening"),
            latest.get(material.id, {}).get("closing"),
        )
        for material in materials
    ]

    opening_done = bool(material_rows) and all(
        material["latest_opening_qty"] is not None for material in material_rows
    )
    closing_done = bool(material_rows) and all(
        material["latest_closing_qty"] is not None for material in material_rows
    )

    return {
        "date": str(date.today()),
        "opening_done": opening_done,
        "closing_done": closing_done,
        "materials": material_rows,
    }


@router.get("/opname/history")
def material_opname_history(
    branch_id: int | None = None,
    days: int = Query(7, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved_branch_id = resolve_branch_id(current_user, branch_id)
    start_date = date.today() - timedelta(days=days - 1)

    query = (
        db.query(MaterialStockOpname)
        .join(Material, Material.id == MaterialStockOpname.material_id)
        .filter(MaterialStockOpname.checked_for_date >= start_date)
    )

    if resolved_branch_id:
        query = query.filter(MaterialStockOpname.branch_id == resolved_branch_id)

    rows = query.order_by(
        MaterialStockOpname.checked_for_date.desc(),
        MaterialStockOpname.created_at.desc(),
    ).all()

    return [
        {
            "id": row.id,
            "material_id": row.material_id,
            "material_name": row.material.name if row.material else "-",
            "branch_id": row.branch_id,
            "shift_type": row.shift_type,
            "qty": row.qty,
            "unit": row.unit,
            "checked_for_date": row.checked_for_date,
            "note": row.note,
            "created_at": row.created_at,
        }
        for row in rows
    ]
