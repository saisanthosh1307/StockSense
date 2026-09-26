from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.user import User
from backend.schemas.advanced import (
    DeadStockSummary, DeadStockActionConfirmRequest,
    SupplierMetricResponse, SupplierComparisonResponse,
    InventoryBatchResponse, ExpiryAlertGroup, FefoPickPlanResponse,
    PickingRouteResponse, RoutePickConfirmRequest
)
from backend.services.auth_service import get_current_user
from backend.services.dead_stock_service import DeadStockService
from backend.services.supplier_intelligence_service import SupplierIntelligenceService
from backend.services.fefo_service import FefoService
from backend.services.picking_route_service import PickingRouteService

router = APIRouter(prefix="/advanced", tags=["Advanced StockSense Modules"])

# ==========================================
# 1. Dead-Stock Rescue
# ==========================================
@router.get("/dead-stock", response_model=DeadStockSummary)
def get_dead_stock_analysis(
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Identifies products that are not moving, very slow-moving, excessively stocked,
    or holding inventory for long durations. Computes Dead Stock Score (0-100),
    classification, and recommendations.
    """
    return DeadStockService.analyze_dead_stock(db, warehouse_id)

@router.post("/dead-stock/confirm-action")
def confirm_dead_stock_action(
    req: DeadStockActionConfirmRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Requires explicit user confirmation before executing any dead stock redistribution,
    transfer, return to supplier, or policy adjustment.
    """
    try:
        return DeadStockService.execute_confirmed_action(
            db, req, user_id=current_user.id if current_user else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# 2. Supplier Intelligence
# ==========================================
@router.get("/suppliers", response_model=SupplierComparisonResponse)
def get_supplier_intelligence_comparison(db: Session = Depends(get_db)):
    """
    Returns supplier network comparison, performance trends, lead time analysis,
    damage rate, on-time delivery %, and calculated Supplier Reliability Scores.
    """
    return SupplierIntelligenceService.get_supplier_comparison(db)

@router.get("/suppliers/{supplier_id}", response_model=SupplierMetricResponse)
def get_single_supplier_metrics(supplier_id: int, db: Session = Depends(get_db)):
    try:
        return SupplierIntelligenceService.get_or_calculate_supplier_metrics(db, supplier_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# 3. Expiry / FEFO Management
# ==========================================
@router.get("/expiry/batches", response_model=List[InventoryBatchResponse])
def get_inventory_batches(
    product_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Lists batch-level inventory sorted primarily by expiry date ascending.
    """
    return FefoService.get_batches(db, product_id, warehouse_id)

@router.get("/expiry/alerts", response_model=ExpiryAlertGroup)
def get_expiry_alerts(
    days_threshold: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Returns Expiring Stock dashboard data: expired, expiring within 7 days,
    expiring within 30 days, total valuation at risk.
    """
    return FefoService.get_expiry_alerts(db, days_threshold)

@router.get("/fefo/plan", response_model=FefoPickPlanResponse)
def plan_fefo_picking(
    product_id: int = Query(..., description="Target Product ID"),
    warehouse_id: int = Query(..., description="Target Warehouse ID"),
    requested_qty: int = Query(..., ge=1, description="Quantity required for picking"),
    db: Session = Depends(get_db)
):
    """
    FEFO (First Expired, First Out) picking planner allocating required stock
    from earliest expiring batch to newest batch.
    """
    try:
        return FefoService.plan_fefo_picking(db, product_id, warehouse_id, requested_qty)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# 4. Smart Picking Route
# ==========================================
@router.get("/picking-route/{delivery_id}", response_model=PickingRouteResponse)
def get_or_generate_picking_route(delivery_id: int, db: Session = Depends(get_db)):
    """
    Generates an optimized TSP picking route sequence for a delivery order,
    calculating distance saved, time saved, and waypoint coordinates for Digital Twin.
    """
    return PickingRouteService.generate_route_for_delivery(db, delivery_id)

@router.post("/picking-route/{delivery_id}/confirm-step")
def confirm_route_pick_step(
    delivery_id: int,
    req: RoutePickConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Confirms an individual pick step along the route.
    Does NOT auto-complete; requires manual worker confirmation.
    """
    return PickingRouteService.confirm_pick_step(
        db, delivery_id, req.step_order, req.picked_quantity
    )
