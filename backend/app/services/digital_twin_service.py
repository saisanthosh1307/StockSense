from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.inventory import Warehouse, Location, StockQuant, LocationType, Product
from app.models.ledger import StockMove

def get_warehouse_digital_twin(db: Session, warehouse_id: int) -> Dict[str, Any]:
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise ValueError("Warehouse not found")

    # Fetch physical internal locations belonging to warehouse
    locations = (
        db.query(Location)
        .filter(
            Location.warehouse_id == warehouse_id,
            Location.location_type == LocationType.INTERNAL
        )
        .all()
    )

    # Calculate pick frequency per location from StockMove
    pick_counts = (
        db.query(
            StockMove.from_location_id,
            func.count(StockMove.id).label("pick_count")
        )
        .group_by(StockMove.from_location_id)
        .all()
    )
    pick_map = {row[0]: row[1] for row in pick_counts}

    slots = []
    total_capacity = 0.0
    total_used = 0.0
    zones_set = set()
    heatmap_matrix = []

    for loc in locations:
        zone = loc.zone or "Zone A"
        aisle = loc.aisle or "Aisle 1"
        rack = loc.rack or "Rack 01"
        shelf = loc.shelf or "Shelf A"
        zones_set.add(zone)

        # Get items currently in this location
        quants = db.query(StockQuant).filter(StockQuant.location_id == loc.id).all()
        products_stored = []
        loc_used = 0.0
        for q in quants:
            if q.quantity > 0:
                p_name = q.product.name if q.product else "Unknown Product"
                p_sku = q.product.sku if q.product else "SKU"
                products_stored.append({
                    "product_id": q.product_id,
                    "product_name": p_name,
                    "sku": p_sku,
                    "quantity": q.quantity,
                    "reserved": q.reserved_quantity
                })
                loc_used += q.quantity

        cap = loc.max_capacity or 500.0
        utilization_pct = min(100.0, (loc_used / cap) * 100) if cap > 0 else 0.0
        
        if utilization_pct >= 90.0:
            status = "NEAR_FULL"
        elif utilization_pct == 0.0:
            status = "EMPTY"
        else:
            status = "OPTIMAL"

        slots.append({
            "location_id": loc.id,
            "name": loc.name,
            "code": loc.code,
            "zone": zone,
            "aisle": aisle,
            "rack": rack,
            "shelf": shelf,
            "capacity_total": cap,
            "capacity_used": round(loc_used, 1),
            "utilization_pct": round(utilization_pct, 1),
            "products_stored": products_stored,
            "status": status
        })

        total_capacity += cap
        total_used += loc_used

        # Heatmap coordinates (x: aisle index, y: rack index, heat: pick intensity + density)
        heat_score = round(min(1.0, (utilization_pct / 100.0) * 0.6 + (pick_map.get(loc.id, 0) / 10.0) * 0.4), 2)
        heatmap_matrix.append({
            "location_id": loc.id,
            "name": loc.name,
            "code": loc.code,
            "coordinates": {
                "zone": zone,
                "aisle": aisle,
                "rack": rack,
                "shelf": shelf
            },
            "density_pct": round(utilization_pct, 1),
            "pick_activity_count": pick_map.get(loc.id, 0),
            "heat_intensity": heat_score
        })

    overall_util = round((total_used / (total_capacity or 1.0)) * 100, 1)

    return {
        "warehouse_id": warehouse.id,
        "warehouse_name": warehouse.name,
        "warehouse_code": warehouse.code,
        "total_locations": len(locations),
        "overall_capacity_utilization_pct": overall_util,
        "total_items_stored": round(total_used, 1),
        "zones": sorted(list(zones_set)),
        "slots": slots,
        "heatmap_matrix": heatmap_matrix
    }
