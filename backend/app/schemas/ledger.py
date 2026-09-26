from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.ledger import MoveType

class StockMoveOut(BaseModel):
    id: int
    reference: str
    move_type: MoveType
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    from_location_id: int
    from_location_name: Optional[str] = None
    to_location_id: int
    to_location_name: Optional[str] = None
    quantity: float
    unit_cost: float
    total_value: float
    user_id: Optional[int] = None
    timestamp: datetime
    record_hash: Optional[str] = None

    class Config:
        from_attributes = True
