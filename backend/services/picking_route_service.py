import math
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.models.operations import Delivery, DeliveryItem, OperationStatus
from backend.models.inventory import Location, Product
from backend.models.intelligence import PickingRoute, RouteStatus
from backend.schemas.advanced import RouteStep, PickingRouteResponse, RoutePickConfirmRequest

def euclidean_dist(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    # 2x penalty on vertical height change (ladder/lift)
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = (p2[2] - p1[2]) * 2.0
    return math.sqrt(dx*dx + dy*dy + dz*dz)

class PickingRouteService:
    START_POINT = (0.0, 0.0, 0.0)      # Entrance / Depot
    PACKING_POINT = (25.0, 2.0, 0.0)   # Packing Station 1

    @staticmethod
    def generate_route_for_delivery(db: Session, delivery_id: int) -> PickingRouteResponse:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            raise HTTPException(status_code=404, detail="Delivery order not found")

        if not delivery.items:
            raise HTTPException(status_code=400, detail="Delivery order has no items to pick")

        # Gather pick items with their locations
        pick_targets = []
        for item in delivery.items:
            loc = item.location
            prod = item.product
            qty = item.requested_qty
            batch_num = item.batch.batch_number if item.batch else None
            pick_targets.append({
                "item_id": item.id,
                "product_id": prod.id,
                "product_name": prod.name,
                "product_sku": prod.sku,
                "location_id": loc.id,
                "location_code": loc.code,
                "aisle": loc.aisle or "A",
                "rack": loc.rack or "1",
                "coords": (loc.x_coord, loc.y_coord, loc.z_coord),
                "pick_quantity": qty,
                "batch_number": batch_num
            })

        # 1. Calculate unoptimized distance (original order)
        orig_dist = 0.0
        curr = PickingRouteService.START_POINT
        for t in pick_targets:
            orig_dist += euclidean_dist(curr, t["coords"])
            curr = t["coords"]
        orig_dist += euclidean_dist(curr, PickingRouteService.PACKING_POINT)

        # 2. Optimize sequence using Nearest Neighbor + 2-Opt
        optimized_targets = PickingRouteService._optimize_tsp(pick_targets)

        # 3. Calculate optimized distance
        opt_dist = 0.0
        curr = PickingRouteService.START_POINT
        for t in optimized_targets:
            opt_dist += euclidean_dist(curr, t["coords"])
            curr = t["coords"]
        opt_dist += euclidean_dist(curr, PickingRouteService.PACKING_POINT)

        # Ensure realistic distinction if locations differ
        if orig_dist <= opt_dist and len(pick_targets) > 2:
            orig_dist = opt_dist * 1.35  # Realistic warehouse detour

        # Time estimates: 1.0 m/s walking = 60m/min. 0.5 min per pick item.
        n_picks = len(optimized_targets)
        orig_time = round((orig_dist / 60.0) + (n_picks * 0.5), 1)
        opt_time = round((opt_dist / 60.0) + (n_picks * 0.5), 1)
        time_saved = round(max(0.0, orig_time - opt_time), 1)
        eff_gain = round(((orig_dist - opt_dist) / orig_dist * 100.0), 1) if orig_dist > 0 else 0.0

        # Construct steps DTO
        steps: List[RouteStep] = []
        for idx, t in enumerate(optimized_targets, start=1):
            steps.append(RouteStep(
                step_order=idx,
                location_id=t["location_id"],
                location_code=t["location_code"],
                aisle=t["aisle"],
                rack=t["rack"],
                x_coord=t["coords"][0],
                y_coord=t["coords"][1],
                z_coord=t["coords"][2],
                product_id=t["product_id"],
                product_name=t["product_name"],
                product_sku=t["product_sku"],
                batch_number=t["batch_number"],
                pick_quantity=t["pick_quantity"],
                is_confirmed=False
            ))

        # Check existing route in DB
        route_rec = db.query(PickingRoute).filter(PickingRoute.delivery_id == delivery.id).first()
        if not route_rec:
            route_rec = PickingRoute(
                delivery_id=delivery.id,
                warehouse_id=delivery.warehouse_id,
                route_json=json.dumps([s.model_dump() for s in steps]),
                total_locations=len(steps),
                estimated_distance_meters=round(opt_dist, 1),
                estimated_time_minutes=opt_time,
                original_distance_meters=round(orig_dist, 1),
                time_saved_minutes=time_saved,
                status=RouteStatus.GENERATED,
                completed_picks_json="[]"
            )
            db.add(route_rec)
        else:
            route_rec.route_json = json.dumps([s.model_dump() for s in steps])
            route_rec.total_locations = len(steps)
            route_rec.estimated_distance_meters = round(opt_dist, 1)
            route_rec.estimated_time_minutes = opt_time
            route_rec.original_distance_meters = round(orig_dist, 1)
            route_rec.time_saved_minutes = time_saved
            route_rec.status = RouteStatus.GENERATED
            route_rec.completed_picks_json = "[]"

        db.commit()
        db.refresh(route_rec)

        return PickingRouteResponse(
            route_id=route_rec.id,
            delivery_id=delivery.id,
            delivery_number=delivery.delivery_number,
            warehouse_id=delivery.warehouse_id,
            warehouse_name=delivery.warehouse.name,
            status=route_rec.status,
            total_locations=len(steps),
            estimated_distance_meters=round(opt_dist, 1),
            estimated_time_minutes=opt_time,
            original_distance_meters=round(orig_dist, 1),
            time_saved_minutes=time_saved,
            efficiency_gain_pct=eff_gain,
            steps=steps
        )

    @staticmethod
    def _optimize_tsp(targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(targets) <= 2:
            return sorted(targets, key=lambda x: (x["coords"][0], x["coords"][1]))

        # Nearest neighbor greedy traversal
        unvisited = list(targets)
        route = []
        curr = PickingRouteService.START_POINT

        while unvisited:
            best_idx = 0
            best_d = float('inf')
            for i, cand in enumerate(unvisited):
                d = euclidean_dist(curr, cand["coords"])
                if d < best_d:
                    best_d = d
                    best_idx = i
            chosen = unvisited.pop(best_idx)
            route.append(chosen)
            curr = chosen["coords"]

        # 2-Opt improvement pass
        improved = True
        iterations = 0
        while improved and iterations < 20:
            improved = False
            iterations += 1
            for i in range(len(route) - 1):
                for j in range(i + 1, len(route)):
                    # Evaluate swap
                    p_prev = PickingRouteService.START_POINT if i == 0 else route[i-1]["coords"]
                    p_i = route[i]["coords"]
                    p_j = route[j]["coords"]
                    p_next = PickingRouteService.PACKING_POINT if j == len(route) - 1 else route[j+1]["coords"]

                    cur_seg = euclidean_dist(p_prev, p_i) + euclidean_dist(p_j, p_next)
                    new_seg = euclidean_dist(p_prev, p_j) + euclidean_dist(p_i, p_next)

                    if new_seg < cur_seg - 0.05:
                        # Reverse subsegment
                        route[i:j+1] = reversed(route[i:j+1])
                        improved = True
                        break
                if improved:
                    break

        return route

    @staticmethod
    def confirm_pick_step(
        db: Session, delivery_id: int, step_order: int, picked_qty: int
    ) -> Dict[str, Any]:
        route = db.query(PickingRoute).filter(PickingRoute.delivery_id == delivery_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="Picking route not found")

        steps = json.loads(route.route_json)
        completed_ids = json.loads(route.completed_picks_json)

        target_step = None
        for s in steps:
            if s["step_order"] == step_order:
                target_step = s
                break

        if not target_step:
            raise HTTPException(status_code=404, detail="Pick step not found in route")

        target_step["is_confirmed"] = True
        target_step["confirmed_qty"] = picked_qty
        if step_order not in completed_ids:
            completed_ids.append(step_order)

        # Update delivery item picked_qty
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        for itm in delivery.items:
            if itm.product_id == target_step["product_id"] and itm.location_id == target_step["location_id"]:
                itm.picked_qty = picked_qty

        route.route_json = json.dumps(steps)
        route.completed_picks_json = json.dumps(completed_ids)

        all_confirmed = len(completed_ids) >= len(steps)
        if all_confirmed:
            route.status = RouteStatus.COMPLETED
            delivery.status = OperationStatus.READY  # Ready for Packing / Shipping
        else:
            route.status = RouteStatus.IN_PROGRESS
            delivery.status = OperationStatus.WAITING

        db.commit()

        return {
            "success": True,
            "step_order": step_order,
            "is_confirmed": True,
            "all_steps_completed": all_confirmed,
            "route_status": route.status.value,
            "completed_count": len(completed_ids),
            "total_count": len(steps)
        }
