from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from backend.database import get_db
from backend.models.inventory import Category, Warehouse, Location, Product, StockLevel
from backend.models.user import User, UserRole
from backend.schemas.inventory import (
    CategoryCreate, CategoryResponse,
    WarehouseCreate, WarehouseResponse,
    LocationCreate, LocationResponse,
    ProductCreate, ProductUpdate, ProductResponse, StockLevelResponse
)
from backend.services.auth_service import get_current_user, require_roles
from backend.services.inventory_engine import InventoryEngine
from backend.models.ledger import TransactionType

router = APIRouter(tags=["Inventory Master Data"])

# --- Categories ---
@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.post("/categories", response_model=CategoryResponse)
def create_category(cat_in: CategoryCreate, db: Session = Depends(get_db)):
    cat = Category(**cat_in.dict())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

# --- Warehouses ---
@router.get("/warehouses", response_model=List[WarehouseResponse])
def list_warehouses(db: Session = Depends(get_db)):
    return db.query(Warehouse).filter(Warehouse.is_active == True).all()

@router.post("/warehouses", response_model=WarehouseResponse)
def create_warehouse(wh_in: WarehouseCreate, db: Session = Depends(get_db)):
    wh = Warehouse(**wh_in.dict())
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh

# --- Locations ---
@router.get("/locations", response_model=List[LocationResponse])
def list_locations(warehouse_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Location).filter(Location.is_active == True)
    if warehouse_id:
        query = query.filter(Location.warehouse_id == warehouse_id)
    return query.all()

@router.post("/locations", response_model=LocationResponse)
def create_location(loc_in: LocationCreate, db: Session = Depends(get_db)):
    loc = Location(**loc_in.dict())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc

# --- Products ---
@router.get("/products", response_model=List[ProductResponse])
def list_products(
    category_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if search:
        s = f"%{search}%"
        query = query.filter(or_(Product.name.ilike(s), Product.sku.ilike(s), Product.barcode.ilike(s)))
        
    products = query.all()
    results = []
    for p in products:
        # Calculate stock levels
        sl_query = db.query(StockLevel).filter(StockLevel.product_id == p.id)
        if warehouse_id:
            sl_query = sl_query.filter(StockLevel.warehouse_id == warehouse_id)
        stock_levels = sl_query.all()
        
        total_stk = sum(sl.quantity for sl in stock_levels)
        res_stk = sum(sl.reserved_quantity for sl in stock_levels)
        avail = max(0, total_stk - res_stk)
        inv_val = round(total_stk * p.cost_price, 2)
        
        sl_responses = [
            StockLevelResponse(
                id=sl.id,
                product_id=sl.product_id,
                warehouse_id=sl.warehouse_id,
                location_id=sl.location_id,
                warehouse_name=sl.warehouse.name if sl.warehouse else "",
                location_code=sl.location.code if sl.location else "",
                quantity=sl.quantity,
                reserved_quantity=sl.reserved_quantity,
                available_quantity=max(0, sl.quantity - sl.reserved_quantity),
                updated_at=sl.updated_at
            ) for sl in stock_levels
        ]

        p_res = ProductResponse(
            id=p.id,
            name=p.name,
            sku=p.sku,
            barcode=p.barcode,
            category_id=p.category_id,
            category_name=p.category.name if p.category else None,
            uom=p.uom,
            min_stock_level=p.min_stock_level,
            max_stock_level=p.max_stock_level,
            reorder_point=p.reorder_point,
            cost_price=p.cost_price,
            selling_price=p.selling_price,
            is_perishable=p.is_perishable,
            shelf_life_days=p.shelf_life_days,
            default_supplier_id=p.default_supplier_id,
            created_at=p.created_at,
            total_stock=total_stk,
            available_stock=avail,
            inventory_value=inv_val,
            stock_levels=sl_responses
        )
        results.append(p_res)
    return results

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    stock_levels = db.query(StockLevel).filter(StockLevel.product_id == p.id).all()
    total_stk = sum(sl.quantity for sl in stock_levels)
    res_stk = sum(sl.reserved_quantity for sl in stock_levels)
    avail = max(0, total_stk - res_stk)
    inv_val = round(total_stk * p.cost_price, 2)

    sl_responses = [
        StockLevelResponse(
            id=sl.id,
            product_id=sl.product_id,
            warehouse_id=sl.warehouse_id,
            location_id=sl.location_id,
            warehouse_name=sl.warehouse.name if sl.warehouse else "",
            location_code=sl.location.code if sl.location else "",
            quantity=sl.quantity,
            reserved_quantity=sl.reserved_quantity,
            available_quantity=max(0, sl.quantity - sl.reserved_quantity),
            updated_at=sl.updated_at
        ) for sl in stock_levels
    ]

    return ProductResponse(
        id=p.id,
        name=p.name,
        sku=p.sku,
        barcode=p.barcode,
        category_id=p.category_id,
        category_name=p.category.name if p.category else None,
        uom=p.uom,
        min_stock_level=p.min_stock_level,
        max_stock_level=p.max_stock_level,
        reorder_point=p.reorder_point,
        cost_price=p.cost_price,
        selling_price=p.selling_price,
        is_perishable=p.is_perishable,
        shelf_life_days=p.shelf_life_days,
        default_supplier_id=p.default_supplier_id,
        created_at=p.created_at,
        total_stock=total_stk,
        available_stock=avail,
        inventory_value=inv_val,
        stock_levels=sl_responses
    )

@router.post("/products", response_model=ProductResponse)
def create_product(
    prod_in: ProductCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(Product).filter(
        (Product.sku == prod_in.sku) | ((Product.barcode != None) & (Product.barcode == prod_in.barcode))
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU or Barcode already exists")

    product = Product(
        name=prod_in.name,
        sku=prod_in.sku,
        barcode=prod_in.barcode,
        category_id=prod_in.category_id,
        uom=prod_in.uom,
        min_stock_level=prod_in.min_stock_level,
        max_stock_level=prod_in.max_stock_level,
        reorder_point=prod_in.reorder_point,
        cost_price=prod_in.cost_price,
        selling_price=prod_in.selling_price,
        is_perishable=prod_in.is_perishable,
        shelf_life_days=prod_in.shelf_life_days,
        default_supplier_id=prod_in.default_supplier_id
    )
    db.add(product)
    db.flush()

    # Initial stock if provided
    if prod_in.initial_stock and prod_in.initial_stock > 0:
        wh_id = prod_in.initial_warehouse_id or 1
        loc_id = prod_in.initial_location_id or 1
        InventoryEngine.record_stock_change(
            db=db,
            product_id=product.id,
            warehouse_id=wh_id,
            location_id=loc_id,
            change_qty=prod_in.initial_stock,
            transaction_type=TransactionType.RECEIPT,
            reference_type="INITIAL_STOCK",
            reference_id=product.sku,
            user_id=current_user.id if current_user else None,
            notes="Initial stock registration"
        )

    db.commit()
    return get_product(product.id, db)

@router.get("/search")
def search_inventory(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    term = f"%{q}%"
    products = db.query(Product).filter(
        or_(Product.name.ilike(term), Product.sku.ilike(term), Product.barcode.ilike(term))
    ).limit(20).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "barcode": p.barcode,
            "category": p.category.name if p.category else "General",
            "cost_price": p.cost_price,
            "selling_price": p.selling_price,
            "uom": p.uom
        } for p in products
    ]
