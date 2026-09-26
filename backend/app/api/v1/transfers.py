import secrets
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operations import Transfer, TransferLine, DocStatus
from app.models.user import User
from app.schemas.operations import TransferCreate, TransferOut
from app.services.stock_ledger_service import validate_transfer_operation
from app.api.deps import require_auth

router = APIRouter(prefix="/transfers", tags=["6. Internal Transfers"])

@router.post("", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    if payload.source_location_id == payload.destination_location_id:
        raise HTTPException(status_code=400, detail="Source and destination locations cannot be identical.")

    ref_code = f"INT/{datetime.utcnow().year}/{secrets.randbelow(9000) + 1000}"
    transfer = Transfer(
        reference=ref_code,
        source_location_id=payload.source_location_id,
        destination_location_id=payload.destination_location_id,
        status=DocStatus.READY,
        notes=payload.notes,
        created_by_user_id=user.id
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)

    for line_in in payload.lines:
        line = TransferLine(
            transfer_id=transfer.id,
            product_id=line_in.product_id,
            quantity=line_in.quantity
        )
        db.add(line)

    db.commit()
    db.refresh(transfer)
    return transfer

@router.get("", response_model=List[TransferOut])
def list_transfers(
    status: Optional[DocStatus] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Transfer)
    if status:
        query = query.filter(Transfer.status == status)
    return query.order_by(Transfer.created_at.desc()).all()

@router.get("/{transfer_id}", response_model=TransferOut)
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    t = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found.")
    return t

@router.post("/{transfer_id}/validate", response_model=TransferOut)
def validate_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Validates internal move:
    Relocates stock from source rack/warehouse to destination rack/warehouse. Total stock unchanged.
    """
    return validate_transfer_operation(db, transfer_id, user_id=user.id)
