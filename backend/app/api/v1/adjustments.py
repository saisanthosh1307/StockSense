import secrets
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operations import Adjustment, AdjustmentLine, DocStatus, LossCauseEnum
from app.models.inventory import StockQuant
from app.models.user import User
from app.schemas.operations import AdjustmentCreate, AdjustmentOut
from app.services.stock_ledger_service import validate_adjustment_operation
from app.api.deps import require_auth

router = APIRouter(prefix="/adjustments", tags=["7. Inventory Adjustments"])

@router.post("", response_model=AdjustmentOut, status_code=status.HTTP_201_CREATED)
def create_adjustment(
    payload: AdjustmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    ref_code = f"ADJ/{datetime.utcnow().year}/{secrets.randbelow(9000) + 1000}"
    adj = Adjustment(
        reference=ref_code,
        location_id=payload.location_id,
        status=DocStatus.READY,
        notes=payload.notes,
        created_by_user_id=user.id
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)

    for line_in in payload.lines:
        quant = db.query(StockQuant).filter(
            StockQuant.product_id == line_in.product_id,
            StockQuant.location_id == payload.location_id
        ).first()
        recorded = quant.quantity if quant else 0.0
        diff = line_in.counted_qty - recorded

        line = AdjustmentLine(
            adjustment_id=adj.id,
            product_id=line_in.product_id,
            recorded_qty=recorded,
            counted_qty=line_in.counted_qty,
            difference_qty=diff,
            loss_cause=line_in.loss_cause or LossCauseEnum.COUNT_MISMATCH
        )
        db.add(line)

    db.commit()
    db.refresh(adj)
    return adj

@router.get("", response_model=List[AdjustmentOut])
def list_adjustments(
    status: Optional[DocStatus] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Adjustment)
    if status:
        query = query.filter(Adjustment.status == status)
    return query.order_by(Adjustment.created_at.desc()).all()

@router.get("/{adjustment_id}", response_model=AdjustmentOut)
def get_adjustment(adjustment_id: int, db: Session = Depends(get_db)):
    adj = db.query(Adjustment).filter(Adjustment.id == adjustment_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="Adjustment not found.")
    return adj

@router.post("/{adjustment_id}/validate", response_model=AdjustmentOut)
def validate_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Validates physical inventory count:
    Auto-updates stock quants and logs discrepancy movement to inventory loss/scrap.
    """
    return validate_adjustment_operation(db, adjustment_id, user_id=user.id)
