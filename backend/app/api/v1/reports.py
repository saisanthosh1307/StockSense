import io
import csv
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.inventory import Product, Location, StockQuant, LocationType
from app.models.ledger import StockMove, MoveType
from app.services.stock_ledger_service import get_product_total_stock

router = APIRouter(prefix="/reports", tags=["12. Reports & Analytics"])

@router.get("/valuation")
def get_inventory_valuation_report(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    rows = []
    total_val = 0.0
    total_items = 0.0

    for p in products:
        qty = get_product_total_stock(db, p.id)
        val = round(qty * p.unit_cost, 2)
        total_val += val
        total_items += qty

        rows.append({
            "product_id": p.id,
            "sku": p.sku,
            "product_name": p.name,
            "category": p.category.name if p.category else "Uncategorized",
            "uom": p.uom,
            "quantity_on_hand": qty,
            "unit_cost": p.unit_cost,
            "total_valuation": val
        })

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_catalog_products": len(products),
        "total_units_in_stock": total_items,
        "total_inventory_valuation": round(total_val, 2),
        "valuation_breakdown": rows
    }

@router.get("/turnover")
def get_inventory_turnover_report(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    results = []

    for p in products:
        stock = get_product_total_stock(db, p.id)
        # Calculate outbound movement over all time
        outbound = (
            db.query(func.sum(StockMove.quantity))
            .filter(
                StockMove.product_id == p.id,
                StockMove.move_type.in_([MoveType.DELIVERY, MoveType.TRANSFER])
            )
            .scalar() or 0.0
        )
        
        cogs = outbound * p.unit_cost
        avg_inv_val = max(1.0, stock * p.unit_cost)
        turnover_ratio = round((cogs / avg_inv_val) * 1.5, 2) # normalized
        days_on_hand = round(365 / (turnover_ratio or 0.1), 1)

        velocity_class = "A (Fast-moving)" if turnover_ratio > 4.0 else "B (Medium-moving)" if turnover_ratio > 1.5 else "C (Slow-moving)"

        results.append({
            "product_id": p.id,
            "sku": p.sku,
            "product_name": p.name,
            "current_stock": stock,
            "total_delivered_units": outbound,
            "turnover_ratio": turnover_ratio,
            "days_sales_of_inventory": days_on_hand,
            "velocity_classification": velocity_class
        })

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "summary": results
    }

@router.get("/export/csv")
def export_stock_ledger_csv(db: Session = Depends(get_db)):
    moves = db.query(StockMove).order_by(StockMove.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Move ID", "Reference", "Move Type", "Timestamp", "Product SKU", "Product Name",
        "From Location", "To Location", "Quantity", "Unit Cost", "Total Value", "Record Hash"
    ])

    for m in moves:
        writer.writerow([
            m.id,
            m.reference,
            m.move_type.value,
            m.timestamp.isoformat(),
            m.product.sku if m.product else "",
            m.product.name if m.product else "",
            m.from_location.name if m.from_location else "",
            m.to_location.name if m.to_location else "",
            m.quantity,
            m.unit_cost,
            m.total_value,
            m.record_hash
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stocksense_ledger.csv"}
    )
