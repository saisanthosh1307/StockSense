from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ledger import StockMove, MoveType
from app.schemas.ledger import StockMoveOut

router = APIRouter(prefix="/ledger", tags=["8. Move History & Stock Ledger"])

@router.get("", response_model=List[StockMoveOut])
def get_stock_ledger(
    product_id: Optional[int] = None,
    move_type: Optional[MoveType] = None,
    location_id: Optional[int] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Immutable double-entry stock ledger. Every movement of goods is recorded here with
    source location, destination location, timestamp, user, and cryptographic signature.
    """
    query = db.query(StockMove)
    if product_id:
        query = query.filter(StockMove.product_id == product_id)
    if move_type:
        query = query.filter(StockMove.move_type == move_type)
    if location_id:
        query = query.filter(
            (StockMove.from_location_id == location_id) | (StockMove.to_location_id == location_id)
        )

    moves = query.order_by(StockMove.timestamp.desc()).offset(offset).limit(limit).all()

    return [
        StockMoveOut(
            id=m.id,
            reference=m.reference,
            move_type=m.move_type,
            product_id=m.product_id,
            product_name=m.product.name if m.product else None,
            product_sku=m.product.sku if m.product else None,
            from_location_id=m.from_location_id,
            from_location_name=m.from_location.name if m.from_location else None,
            to_location_id=m.to_location_id,
            to_location_name=m.to_location.name if m.to_location else None,
            quantity=m.quantity,
            unit_cost=m.unit_cost,
            total_value=m.total_value,
            user_id=m.user_id,
            timestamp=m.timestamp,
            record_hash=m.record_hash
        )
        for m in moves
    ]
