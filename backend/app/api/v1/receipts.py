import secrets
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.operations import Receipt, ReceiptLine, DocStatus
from app.models.user import User, RoleEnum
from app.schemas.operations import ReceiptCreate, ReceiptOut, ReceiptValidateRequest
from app.services.stock_ledger_service import validate_receipt_operation
from app.api.deps import require_auth, require_role

router = APIRouter(prefix="/receipts", tags=["4. Receipts (Incoming Stock)"])

@router.post("", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
def create_receipt(
    payload: ReceiptCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    ref_code = f"REC/{datetime.utcnow().year}/{secrets.randbelow(9000) + 1000}"
    receipt = Receipt(
        reference=ref_code,
        supplier_name=payload.supplier_name,
        destination_location_id=payload.destination_location_id,
        status=DocStatus.READY, # Ready to receive and validate
        notes=payload.notes,
        created_by_user_id=user.id
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    for line_in in payload.lines:
        line = ReceiptLine(
            receipt_id=receipt.id,
            product_id=line_in.product_id,
            quantity_expected=line_in.quantity_expected,
            quantity_received=line_in.quantity_expected, # default to expected
            unit_cost=line_in.unit_cost
        )
        db.add(line)

    db.commit()
    db.refresh(receipt)
    return receipt

@router.get("", response_model=List[ReceiptOut])
def list_receipts(
    status: Optional[DocStatus] = None,
    supplier: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Receipt)
    if status:
        query = query.filter(Receipt.status == status)
    if supplier:
        query = query.filter(Receipt.supplier_name.ilike(f"%{supplier}%"))
    return query.order_by(Receipt.created_at.desc()).all()

@router.get("/{receipt_id}", response_model=ReceiptOut)
def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    rec = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    return rec

@router.post("/{receipt_id}/validate", response_model=ReceiptOut)
def validate_receipt(
    receipt_id: int,
    payload: Optional[ReceiptValidateRequest] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """
    Validates incoming receipt:
    Stock moves from Vendor -> Destination Location, increasing product stock automatically.
    """
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    
    if payload and payload.received_lines:
        for item in payload.received_lines:
            line = db.query(ReceiptLine).filter(
                ReceiptLine.id == item.get("line_id"),
                ReceiptLine.receipt_id == receipt.id
            ).first()
            if line and "quantity_received" in item:
                line.quantity_received = float(item["quantity_received"])
        db.commit()

    return validate_receipt_operation(db, receipt_id, user_id=user.id)
