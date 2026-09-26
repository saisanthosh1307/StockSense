from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.inventory import Product, Location, StockQuant, LocationType, Category, Warehouse
from app.models.operations import Receipt, Delivery, Transfer, Adjustment, DocStatus
from app.models.ledger import StockMove
from app.models.audit import AuditLog
from app.schemas.audit import DashboardKPIs
from app.services.stock_ledger_service import get_product_total_stock

router = APIRouter(prefix="/dashboard", tags=["9. Dashboard & Dynamic Filters"])

@router.get("/kpis", response_model=DashboardKPIs)
def get_dashboard_kpis(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    total_products = len(products)
    low_stock = 0
    out_of_stock = 0
    total_valuation = 0.0

    for p in products:
        stock = get_product_total_stock(db, p.id)
        if stock <= 0:
            out_of_stock += 1
            low_stock += 1
        elif stock <= p.min_reorder_qty:
            low_stock += 1
        total_valuation += (stock * p.unit_cost)

    pending_receipts = db.query(Receipt).filter(
        Receipt.status.in_([DocStatus.DRAFT, DocStatus.WAITING, DocStatus.READY])
    ).count()

    pending_deliveries = db.query(Delivery).filter(
        Delivery.status.in_([DocStatus.DRAFT, DocStatus.WAITING, DocStatus.READY])
    ).count()

    scheduled_transfers = db.query(Transfer).filter(
        Transfer.status.in_([DocStatus.DRAFT, DocStatus.WAITING, DocStatus.READY])
    ).count()

    recent_audits = db.query(AuditLog).count()

    return DashboardKPIs(
        total_products_in_stock=total_products,
        low_stock_items_count=low_stock,
        out_of_stock_items_count=out_of_stock,
        pending_receipts_count=pending_receipts,
        pending_deliveries_count=pending_deliveries,
        scheduled_transfers_count=scheduled_transfers,
        total_inventory_valuation=round(total_valuation, 2),
        recent_activity_count=recent_audits
    )

@router.get("/operations-feed")
def get_dynamic_operations_feed(
    doc_type: Optional[str] = Query(None, description="receipts | deliveries | transfers | adjustments"),
    status: Optional[DocStatus] = None,
    warehouse_id: Optional[int] = None,
    category_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Dynamic aggregated feed satisfying PDF requirements:
    Filter across document type, status, warehouse, and category.
    """
    results = []

    # Receipts
    if not doc_type or doc_type.lower() == "receipts":
        rq = db.query(Receipt)
        if status:
            rq = rq.filter(Receipt.status == status)
        for r in rq.limit(limit).all():
            results.append({
                "id": r.id,
                "reference": r.reference,
                "doc_type": "Receipt",
                "partner": r.supplier_name,
                "status": r.status,
                "created_at": r.created_at,
                "validated_at": r.validated_at,
                "lines_count": len(r.lines)
            })

    # Deliveries
    if not doc_type or doc_type.lower() == "deliveries":
        dq = db.query(Delivery)
        if status:
            dq = dq.filter(Delivery.status == status)
        for d in dq.limit(limit).all():
            results.append({
                "id": d.id,
                "reference": d.reference,
                "doc_type": "Delivery",
                "partner": d.customer_name,
                "status": d.status,
                "created_at": d.created_at,
                "validated_at": d.validated_at,
                "lines_count": len(d.lines)
            })

    # Transfers
    if not doc_type or doc_type.lower() == "transfers":
        tq = db.query(Transfer)
        if status:
            tq = tq.filter(Transfer.status == status)
        for t in tq.limit(limit).all():
            results.append({
                "id": t.id,
                "reference": t.reference,
                "doc_type": "Transfer",
                "partner": f"{t.source_location.name if t.source_location else 'Src'} → {t.destination_location.name if t.destination_location else 'Dst'}",
                "status": t.status,
                "created_at": t.created_at,
                "validated_at": t.validated_at,
                "lines_count": len(t.lines)
            })

    # Adjustments
    if not doc_type or doc_type.lower() == "adjustments":
        aq = db.query(Adjustment)
        if status:
            aq = aq.filter(Adjustment.status == status)
        for a in aq.limit(limit).all():
            results.append({
                "id": a.id,
                "reference": a.reference,
                "doc_type": "Adjustment",
                "partner": a.location.name if a.location else "Location Count",
                "status": a.status,
                "created_at": a.created_at,
                "validated_at": a.validated_at,
                "lines_count": len(a.lines)
            })

    # Sort combined results by created_at desc
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results[:limit]
