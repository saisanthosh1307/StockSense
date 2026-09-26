import secrets
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operations import Delivery, DeliveryLine, DocStatus
from app.models.user import User
from app.schemas.operations import DeliveryCreate, DeliveryOut, DeliveryValidateRequest
from app.services.stock_ledger_service import validate_delivery_operation
from app.api.deps import require_auth

router = APIRouter(prefix="/deliveries", tags=["5. Delivery Orders (Outgoing Goods)"])

@router.post("", response_model=DeliveryOut, status_code=status.HTTP_201_CREATED)
def create_delivery(
    payload: DeliveryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    ref_code = f"DEL/{datetime.utcnow().year}/{secrets.randbelow(9000) + 1000}"
    delivery = Delivery(
        reference=ref_code,
        customer_name=payload.customer_name,
        source_location_id=payload.source_location_id,
        status=DocStatus.WAITING,
        notes=payload.notes,
        created_by_user_id=user.id
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    for line_in in payload.lines:
        line = DeliveryLine(
            delivery_id=delivery.id,
            product_id=line_in.product_id,
            quantity_demanded=line_in.quantity_demanded,
            quantity_done=line_in.quantity_demanded
        )
        db.add(line)

    db.commit()
    db.refresh(delivery)
    return delivery

@router.get("", response_model=List[DeliveryOut])
def list_deliveries(
    status: Optional[DocStatus] = None,
    customer: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Delivery)
    if status:
        query = query.filter(Delivery.status == status)
    if customer:
        query = query.filter(Delivery.customer_name.ilike(f"%{customer}%"))
    return query.order_by(Delivery.created_at.desc()).all()

@router.get("/{delivery_id}", response_model=DeliveryOut)
def get_delivery(delivery_id: int, db: Session = Depends(get_db)):
    deliv = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not deliv:
        raise HTTPException(status_code=404, detail="Delivery order not found.")
    return deliv

@router.post("/{delivery_id}/pick", response_model=DeliveryOut)
def pick_delivery_items(delivery_id: int, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    deliv = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not deliv:
        raise HTTPException(status_code=404, detail="Delivery order not found.")
    deliv.is_picked = 1
    deliv.status = DocStatus.READY
    db.commit()
    db.refresh(deliv)
    return deliv

@router.post("/{delivery_id}/pack", response_model=DeliveryOut)
def pack_delivery_items(delivery_id: int, db: Session = Depends(get_db), user: User = Depends(require_auth)):
    deliv = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not deliv:
        raise HTTPException(status_code=404, detail="Delivery order not found.")
    deliv.is_packed = 1
    db.commit()
    db.refresh(deliv)
    return deliv

@router.post("/{delivery_id}/validate", response_model=DeliveryOut)
def validate_delivery(
    delivery_id: int,
    payload: Optional[DeliveryValidateRequest] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Validates outgoing shipment:
    Decreases stock from source location and sends to Customer location via double-entry move.
    """
    deliv = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not deliv:
        raise HTTPException(status_code=404, detail="Delivery order not found.")

    if payload and payload.done_lines:
        for item in payload.done_lines:
            line = db.query(DeliveryLine).filter(
                DeliveryLine.id == item.get("line_id"),
                DeliveryLine.delivery_id == deliv.id
            ).first()
            if line and "quantity_done" in item:
                line.quantity_done = float(item["quantity_done"])
        db.commit()

    return validate_delivery_operation(db, delivery_id, user_id=user.id)
