from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.inventory import Product, Location, StockQuant
from app.services.stock_ledger_service import get_product_total_stock

router = APIRouter(prefix="/search", tags=["10. Search & Smart Filters"])

@router.get("")
def smart_inventory_search(
    q: str = Query(..., min_length=1, description="Search query by SKU, barcode, name, or rack"),
    category_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Fast SKU search & smart multi-attribute query filter.
    """
    pattern = f"%{q.strip()}%"
    
    # 1. Product Matches
    prod_query = db.query(Product).filter(
        or_(
            Product.sku.ilike(pattern),
            Product.barcode.ilike(pattern),
            Product.name.ilike(pattern),
            Product.description.ilike(pattern)
        )
    )
    if category_id:
        prod_query = prod_query.filter(Product.category_id == category_id)

    products = prod_query.limit(20).all()
    product_results = []
    for p in products:
        stock = get_product_total_stock(db, p.id)
        product_results.append({
            "type": "PRODUCT",
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "barcode": p.barcode,
            "uom": p.uom,
            "unit_price": p.unit_price,
            "on_hand": stock,
            "category": p.category.name if p.category else None,
            "is_low_stock": stock <= p.min_reorder_qty
        })

    # 2. Location / Rack Matches
    loc_query = db.query(Location).filter(
        or_(
            Location.name.ilike(pattern),
            Location.code.ilike(pattern),
            Location.rack.ilike(pattern),
            Location.shelf.ilike(pattern)
        )
    )
    if warehouse_id:
        loc_query = loc_query.filter(Location.warehouse_id == warehouse_id)

    locations = loc_query.limit(10).all()
    location_results = [
        {
            "type": "LOCATION",
            "id": loc.id,
            "code": loc.code,
            "name": loc.name,
            "zone": loc.zone,
            "rack": loc.rack,
            "shelf": loc.shelf,
            "warehouse": loc.warehouse.name if loc.warehouse else None
        }
        for loc in locations
    ]

    return {
        "query": q,
        "total_matches": len(product_results) + len(location_results),
        "products": product_results,
        "locations": location_results
    }
