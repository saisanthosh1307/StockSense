from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import Product, Category, StockQuant, Location, LocationType
from app.models.ledger import MoveType
from app.models.user import RoleEnum, User
from app.schemas.inventory import (
    ProductCreate,
    ProductUpdate,
    ProductOut,
    CategoryCreate,
    CategoryOut,
    StockQuantOut,
)
from app.services.stock_ledger_service import (
    execute_stock_move,
    get_or_create_virtual_location,
    get_product_total_stock,
)
from app.api.deps import require_auth, require_role

router = APIRouter(prefix="/products", tags=["2. Product Management"])

# Categories
@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name.ilike(payload.name)).first()
    if existing:
        return existing
    cat = Category(name=payload.name, description=payload.description)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

# Products
@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.INVENTORY_MANAGER]))
):
    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU '{payload.sku}' already exists.")

    product = Product(
        name=payload.name,
        sku=payload.sku,
        category_id=payload.category_id,
        uom=payload.uom,
        barcode=payload.barcode or payload.sku,
        description=payload.description,
        unit_cost=payload.unit_cost,
        unit_price=payload.unit_price,
        min_reorder_qty=payload.min_reorder_qty,
        max_reorder_qty=payload.max_reorder_qty,
        lead_time_days=payload.lead_time_days
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # If initial stock provided, create double-entry move from Vendor -> specified location or default internal location
    if payload.initial_stock and payload.initial_stock > 0:
        target_loc_id = payload.initial_location_id
        if not target_loc_id:
            first_internal = db.query(Location).filter(Location.location_type == LocationType.INTERNAL).first()
            if first_internal:
                target_loc_id = first_internal.id
        
        if target_loc_id:
            vendor_loc = get_or_create_virtual_location(db, LocationType.VENDOR)
            execute_stock_move(
                db=db,
                product_id=product.id,
                from_loc_id=vendor_loc.id,
                to_loc_id=target_loc_id,
                quantity=payload.initial_stock,
                reference=f"INIT/{product.sku}",
                move_type=MoveType.RECEIPT,
                user_id=user.id
            )

    return get_product_detail(product.id, db)

@router.get("", response_model=List[ProductOut])
def list_products(
    category_id: Optional[int] = None,
    low_stock_only: bool = False,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if search:
        term = f"%{search}%"
        query = query.filter((Product.name.ilike(term)) | (Product.sku.ilike(term)) | (Product.barcode.ilike(term)))
    
    products = query.all()
    results = []
    for p in products:
        total_qty = get_product_total_stock(db, p.id)
        if low_stock_only and total_qty > p.min_reorder_qty:
            continue
        
        # Build location quants
        quants = (
            db.query(StockQuant)
            .join(Location, StockQuant.location_id == Location.id)
            .filter(StockQuant.product_id == p.id, Location.location_type == LocationType.INTERNAL)
            .all()
        )
        loc_stocks = [
            StockQuantOut(
                id=q.id,
                product_id=q.product_id,
                location_id=q.location_id,
                quantity=q.quantity,
                reserved_quantity=q.reserved_quantity,
                location_name=q.location.name if q.location else None,
                location_code=q.location.code if q.location else None
            )
            for q in quants
        ]

        results.append(
            ProductOut(
                id=p.id,
                name=p.name,
                sku=p.sku,
                category_id=p.category_id,
                uom=p.uom,
                barcode=p.barcode,
                description=p.description,
                unit_cost=p.unit_cost,
                unit_price=p.unit_price,
                min_reorder_qty=p.min_reorder_qty,
                max_reorder_qty=p.max_reorder_qty,
                lead_time_days=p.lead_time_days,
                created_at=p.created_at,
                total_on_hand=total_qty,
                category=CategoryOut.from_orm(p.category) if p.category else None,
                locations_stock=loc_stocks
            )
        )
    return results

@router.get("/{product_id}", response_model=ProductOut)
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")

    total_qty = get_product_total_stock(db, p.id)
    quants = (
        db.query(StockQuant)
        .join(Location, StockQuant.location_id == Location.id)
        .filter(StockQuant.product_id == p.id, Location.location_type == LocationType.INTERNAL)
        .all()
    )
    loc_stocks = [
        StockQuantOut(
            id=q.id,
            product_id=q.product_id,
            location_id=q.location_id,
            quantity=q.quantity,
            reserved_quantity=q.reserved_quantity,
            location_name=q.location.name if q.location else None,
            location_code=q.location.code if q.location else None
        )
        for q in quants
    ]

    return ProductOut(
        id=p.id,
        name=p.name,
        sku=p.sku,
        category_id=p.category_id,
        uom=p.uom,
        barcode=p.barcode,
        description=p.description,
        unit_cost=p.unit_cost,
        unit_price=p.unit_price,
        min_reorder_qty=p.min_reorder_qty,
        max_reorder_qty=p.max_reorder_qty,
        lead_time_days=p.lead_time_days,
        created_at=p.created_at,
        total_on_hand=total_qty,
        category=CategoryOut.from_orm(p.category) if p.category else None,
        locations_stock=loc_stocks
    )

@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role([RoleEnum.ADMIN, RoleEnum.INVENTORY_MANAGER]))
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")

    for field, val in payload.dict(exclude_unset=True).items():
        setattr(p, field, val)

    db.commit()
    db.refresh(p)
    return get_product_detail(p.id, db)
