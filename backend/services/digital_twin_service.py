import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.inventory import Warehouse, Location, StockLevel, Product
from backend.models.batch import InventoryBatch, BatchStatus
from backend.models.intelligence import DeadStockAnalysis, DeadStockClassification, PickingRoute
from backend.models.ledger import StockLedger

class DigitalTwinService:
    @staticmethod
    def get_warehouse_twin_data(db: Session, warehouse_id: int, delivery_route_id: Optional[int] = None) -> Dict[str, Any]:
        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
        if not warehouse:
            raise ValueError(f"Warehouse #{warehouse_id} not found")

        locations = db.query(Location).filter(
            Location.warehouse_id == warehouse.id,
            Location.is_active == True
        ).all()

        now = datetime.utcnow()
        thirty_days_ahead = now + timedelta(days=30)
        thirty_days_ago = now - timedelta(days=30)

        # 1. Identify dead-stock locations
        dead_stock_loc_ids = set()
        dead_analyses = db.query(DeadStockAnalysis).filter(
            DeadStockAnalysis.warehouse_id == warehouse.id,
            DeadStockAnalysis.classification == DeadStockClassification.DEAD_STOCK
        ).all()
        for da in dead_analyses:
            sls = db.query(StockLevel).filter(
                StockLevel.product_id == da.product_id,
                StockLevel.warehouse_id == warehouse.id
            ).all()
            for s in sls:
                dead_stock_loc_ids.add(s.location_id)

        # 2. Identify expiring batch locations
        expiring_loc_ids = set()
        exp_batches = db.query(InventoryBatch).filter(
            InventoryBatch.warehouse_id == warehouse.id,
            InventoryBatch.current_quantity > 0,
            InventoryBatch.expiry_date <= thirty_days_ahead
        ).all()
        for eb in exp_batches:
            expiring_loc_ids.add(eb.location_id)

        # 3. Identify high pick frequency locations
        pick_freq_locs: Dict[int, int] = {}
        recent_picks = db.query(StockLedger.location_id, func.count(StockLedger.id)).filter(
            StockLedger.warehouse_id == warehouse.id,
            StockLedger.change_qty < 0,
            StockLedger.timestamp >= thirty_days_ago
        ).group_by(StockLedger.location_id).all()
        for loc_id, count in recent_picks:
            if loc_id:
                pick_freq_locs[loc_id] = count

        # 4. Process each location node
        location_nodes: List[Dict[str, Any]] = []
        for loc in locations:
            # Aggregate items stored
            stock_items = db.query(StockLevel).join(Product).filter(
                StockLevel.location_id == loc.id,
                StockLevel.quantity > 0
            ).all()

            total_qty = sum(s.quantity for s in stock_items)
            items_summary = [
                {"product_name": s.product.name, "sku": s.product.sku, "quantity": s.quantity, "uom": s.product.uom}
                for s in stock_items
            ]

            occupancy_pct = round(min(100.0, (total_qty / loc.capacity) * 100.0), 1) if loc.capacity > 0 else 0.0

            # Tags & Status
            tags = []
            status_color = "normal"  # normal, dead_stock, expiring, high_stock, high_pick

            if loc.id in dead_stock_loc_ids:
                tags.append("DEAD_STOCK")
                status_color = "dead_stock"
            elif loc.id in expiring_loc_ids:
                tags.append("EXPIRING_SOON")
                status_color = "expiring"
            elif occupancy_pct >= 85.0:
                tags.append("HIGH_STOCK")
                status_color = "high_stock"
            elif pick_freq_locs.get(loc.id, 0) >= 5:
                tags.append("HIGH_PICK_FREQUENCY")
                status_color = "high_pick"

            location_nodes.append({
                "id": loc.id,
                "code": loc.code,
                "aisle": loc.aisle or "A",
                "rack": loc.rack or "1",
                "shelf": loc.shelf or "1",
                "x": loc.x_coord,
                "y": loc.y_coord,
                "z": loc.z_coord,
                "capacity": loc.capacity,
                "current_quantity": total_qty,
                "occupancy_pct": occupancy_pct,
                "status_color": status_color,
                "tags": tags,
                "pick_frequency": pick_freq_locs.get(loc.id, 0),
                "items": items_summary
            })

        # 5. Picking Route Overlay if specified
        active_route_data = None
        if delivery_route_id:
            route = db.query(PickingRoute).filter(PickingRoute.id == delivery_route_id).first()
            if route:
                steps = json.loads(route.route_json)
                waypoints = [{"name": "Start / Inbound Staging", "x": 0.0, "y": 0.0, "z": 0.0}]
                for s in steps:
                    waypoints.append({
                        "step_order": s["step_order"],
                        "name": f"Rack {s['location_code']} ({s['product_name']})",
                        "location_code": s["location_code"],
                        "x": s["x_coord"],
                        "y": s["y_coord"],
                        "z": s["z_coord"],
                        "pick_qty": s["pick_quantity"],
                        "is_confirmed": s.get("is_confirmed", False)
                    })
                waypoints.append({"name": "Packing Area", "x": 25.0, "y": 2.0, "z": 0.0})

                active_route_data = {
                    "route_id": route.id,
                    "delivery_id": route.delivery_id,
                    "status": route.status.value,
                    "estimated_distance_m": route.estimated_distance_meters,
                    "estimated_time_min": route.estimated_time_minutes,
                    "waypoints": waypoints
                }

        return {
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name,
            "warehouse_code": warehouse.code,
            "dimensions": {"width_m": 30.0, "length_m": 20.0, "height_m": 6.0},
            "packing_station": {"name": "Packing Area", "x": 25.0, "y": 2.0, "z": 0.0},
            "staging_dock": {"name": "Inbound Dock", "x": 0.0, "y": 0.0, "z": 0.0},
            "locations": location_nodes,
            "active_picking_route": active_route_data,
            "summary": {
                "total_locations": len(locations),
                "dead_stock_locations_count": len(dead_stock_loc_ids),
                "expiring_locations_count": len(expiring_loc_ids),
                "high_occupancy_locations_count": sum(1 for l in location_nodes if l["occupancy_pct"] >= 85.0)
            }
        }
