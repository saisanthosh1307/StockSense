from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import Alert, AlertSeverity, AlertType
from app.models.inventory import Product
from app.schemas.audit import AlertOut
from app.services.stock_ledger_service import check_low_stock_and_alert

router = APIRouter(prefix="/alerts", tags=["11. Alerts & Notifications"])

@router.get("", response_model=List[AlertOut])
def list_alerts(
    unread_only: bool = False,
    severity: Optional[AlertSeverity] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if unread_only:
        query = query.filter(Alert.is_read == False)
    if severity:
        query = query.filter(Alert.severity == severity)

    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    return [
        AlertOut(
            id=a.id,
            title=a.title,
            message=a.message,
            severity=a.severity,
            alert_type=a.alert_type,
            product_id=a.product_id,
            product_name=a.product.name if a.product else None,
            is_read=a.is_read,
            created_at=a.created_at
        )
        for a in alerts
    ]

@router.post("/{alert_id}/read", response_model=AlertOut)
def mark_alert_read(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return AlertOut(
        id=alert.id,
        title=alert.title,
        message=alert.message,
        severity=alert.severity,
        alert_type=alert.alert_type,
        product_id=alert.product_id,
        product_name=alert.product.name if alert.product else None,
        is_read=alert.is_read,
        created_at=alert.created_at
    )

@router.post("/scan")
def scan_all_products_for_low_stock(db: Session = Depends(get_db)):
    """
    Scans entire inventory catalog and automatically raises alerts for products hitting reorder thresholds.
    """
    products = db.query(Product).all()
    triggered_count = 0
    for p in products:
        check_low_stock_and_alert(db, p.id)
        triggered_count += 1

    unread = db.query(Alert).filter(Alert.is_read == False).count()
    return {
        "message": f"Scan completed across {triggered_count} products.",
        "active_unread_alerts": unread
    }
