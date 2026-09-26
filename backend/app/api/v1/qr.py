from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import Product, Location
from app.models.operations import Receipt, Delivery, Transfer
from app.services.qr_service import generate_qr_code_base64, parse_qr_payload
from app.services.stock_ledger_service import get_product_total_stock

router = APIRouter(prefix="/qr", tags=["14. QR Code Engine"])

@router.get("/product/{product_id}")
def get_product_qr(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    stock = get_product_total_stock(db, product.id)
    payload = {
        "entity": "PRODUCT",
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "barcode": product.barcode,
        "uom": product.uom,
        "unit_price": product.unit_price
    }
    qr_data_uri = generate_qr_code_base64(payload)
    return {
        "entity_type": "PRODUCT",
        "entity_id": product.id,
        "sku": product.sku,
        "qr_code_data_uri": qr_data_uri,
        "current_stock": stock
    }

@router.get("/location/{location_id}")
def get_location_qr(location_id: int, db: Session = Depends(get_db)):
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found.")

    payload = {
        "entity": "LOCATION",
        "id": loc.id,
        "code": loc.code,
        "name": loc.name,
        "zone": loc.zone,
        "rack": loc.rack,
        "shelf": loc.shelf
    }
    qr_data_uri = generate_qr_code_base64(payload)
    return {
        "entity_type": "LOCATION",
        "entity_id": loc.id,
        "code": loc.code,
        "qr_code_data_uri": qr_data_uri
    }

@router.post("/scan")
def scan_and_resolve_qr(
    raw_payload: str = Body(..., embed=True, description="Decoded QR string from scanner"),
    db: Session = Depends(get_db)
):
    """
    Resolves a scanned QR code into rich inventory entities with context-aware warehouse actions.
    """
    data = parse_qr_payload(raw_payload)
    entity_type = data.get("entity")

    if entity_type == "PRODUCT" or "sku" in data:
        p_id = data.get("id")
        sku = data.get("sku") or data.get("value")
        product = db.query(Product).filter((Product.id == p_id) | (Product.sku == sku) | (Product.barcode == sku)).first()
        if product:
            stock = get_product_total_stock(db, product.id)
            return {
                "status": "RESOLVED",
                "entity_type": "PRODUCT",
                "data": {
                    "id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "uom": product.uom,
                    "current_stock": stock,
                    "unit_cost": product.unit_cost,
                    "unit_price": product.unit_price
                },
                "available_actions": ["INITIATE_TRANSFER", "COUNT_ADJUSTMENT", "VIEW_LEAD_TIME"]
            }

    if entity_type == "LOCATION" or "code" in data:
        loc_id = data.get("id")
        code = data.get("code") or data.get("value")
        loc = db.query(Location).filter((Location.id == loc_id) | (Location.code == code)).first()
        if loc:
            return {
                "status": "RESOLVED",
                "entity_type": "LOCATION",
                "data": {
                    "id": loc.id,
                    "code": loc.code,
                    "name": loc.name,
                    "zone": loc.zone,
                    "rack": loc.rack,
                    "shelf": loc.shelf,
                    "warehouse": loc.warehouse.name if loc.warehouse else None
                },
                "available_actions": ["VIEW_STORED_ITEMS", "AUDIT_RACK", "TRANSFER_TO_LOCATION"]
            }

    # Fallback search by string query
    product = db.query(Product).filter((Product.sku == raw_payload) | (Product.barcode == raw_payload)).first()
    if product:
        stock = get_product_total_stock(db, product.id)
        return {
            "status": "RESOLVED",
            "entity_type": "PRODUCT",
            "data": {"id": product.id, "name": product.name, "sku": product.sku, "current_stock": stock},
            "available_actions": ["INITIATE_TRANSFER", "COUNT_ADJUSTMENT"]
        }

    return {
        "status": "UNRESOLVED",
        "raw_content": raw_payload,
        "message": "Barcode or QR code does not match any registered inventory entity."
    }
