from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models.ledger import StockLedger, TrustChainBlock, AuditLog
from backend.models.inventory import Product, Warehouse, StockLevel
from backend.services.trust_chain import TrustChainService
from backend.services.fefo_service import FefoService

router = APIRouter(tags=["Ledger & Governance"])

# --- Stock Ledger ---
@router.get("/ledger")
def get_stock_ledger(
    product_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    q = db.query(StockLedger)
    if product_id:
        q = q.filter(StockLedger.product_id == product_id)
    if warehouse_id:
        q = q.filter(StockLedger.warehouse_id == warehouse_id)
        
    entries = q.order_by(StockLedger.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "entry_uuid": e.entry_uuid,
            "timestamp": e.timestamp.isoformat(),
            "product_id": e.product_id,
            "product_name": e.product.name if e.product else "",
            "product_sku": e.product.sku if e.product else "",
            "warehouse_name": e.warehouse.name if e.warehouse else "",
            "location_code": e.location.code if e.location else "",
            "change_qty": e.change_qty,
            "balance_after": e.balance_after,
            "transaction_type": e.transaction_type.value,
            "reference_type": e.reference_type,
            "reference_id": e.reference_id,
            "batch_number": e.batch_number,
            "notes": e.notes
        }
        for e in entries
    ]

# --- Cryptographic Trust Chain ---
@router.get("/trust-chain/blocks")
def get_trust_chain_blocks(db: Session = Depends(get_db)):
    blocks = db.query(TrustChainBlock).order_by(TrustChainBlock.block_index.desc()).limit(30).all()
    return [
        {
            "block_index": b.block_index,
            "timestamp": b.timestamp.isoformat(),
            "previous_hash": b.previous_hash,
            "block_hash": b.block_hash,
            "merkle_root": b.merkle_root,
            "transaction_count": b.transaction_count,
            "payload_summary": b.payload_summary
        }
        for b in blocks
    ]

@router.get("/trust-chain/verify")
def verify_trust_chain_integrity(db: Session = Depends(get_db)):
    valid, message, details = TrustChainService.verify_chain_integrity(db)
    return {
        "is_intact": valid,
        "message": message,
        "total_blocks_checked": len(details),
        "audit_timestamp": datetime.utcnow().isoformat(),
        "block_audit_details": details[:10]
    }

# --- Audit Logs ---
@router.get("/audit/logs")
def get_audit_logs(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat(),
            "user": a.user.username if a.user else "system",
            "action": a.action,
            "entity_name": a.entity_name,
            "entity_id": a.entity_id,
            "details": a.details
        }
        for a in logs
    ]

# --- Alerts & Reports ---
@router.get("/alerts")
def get_inventory_alerts(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    alerts = []
    
    # 1. Low stock alerts
    for p in products:
        total = db.query(func.sum(StockLevel.quantity)).filter(StockLevel.product_id == p.id).scalar() or 0
        if total == 0:
            alerts.append({
                "type": "OUT_OF_STOCK",
                "severity": "CRITICAL",
                "title": f"Out of Stock: {p.name}",
                "message": f"Inventory depleted (0 {p.uom}). Reorder point is {p.reorder_point}."
            })
        elif total <= p.min_stock_level:
            alerts.append({
                "type": "LOW_STOCK",
                "severity": "WARNING",
                "title": f"Low Stock Warning: {p.name}",
                "message": f"Current stock ({total} {p.uom}) is at or below minimum threshold ({p.min_stock_level})."
            })

    # 2. Expiry alerts
    exp_summary = FefoService.get_expiry_alerts(db, days_threshold=30)
    if exp_summary.expiring_7_days_count > 0:
        alerts.append({
            "type": "CRITICAL_EXPIRY",
            "severity": "CRITICAL",
            "title": f"{exp_summary.expiring_7_days_count} Batches Expiring in < 7 Days",
            "message": f"Critical perishability risk for ₹{exp_summary.expiring_7_days_value:,.2f} inventory. Prioritize via FEFO."
        })

    return alerts

@router.get("/reports/valuation")
def get_inventory_valuation_report(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    total_val = 0.0
    items = []
    for p in products:
        qty = db.query(func.sum(StockLevel.quantity)).filter(StockLevel.product_id == p.id).scalar() or 0
        val = round(qty * p.cost_price, 2)
        total_val += val
        items.append({
            "product_id": p.id,
            "sku": p.sku,
            "product_name": p.name,
            "category": p.category.name if p.category else "Uncategorized",
            "quantity": qty,
            "uom": p.uom,
            "cost_price": p.cost_price,
            "valuation": val
        })
    return {
        "total_valuation": round(total_val, 2),
        "total_items_count": len(items),
        "valuation_by_product": sorted(items, key=lambda x: x["valuation"], reverse=True)
    }
