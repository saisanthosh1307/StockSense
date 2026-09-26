from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.models.operations import DocStatus, LossCauseEnum

# --- Receipt Schemas ---
class ReceiptLineCreate(BaseModel):
    product_id: int
    quantity_expected: float
    unit_cost: float = 0.0

class ReceiptLineOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity_expected: float
    quantity_received: float
    unit_cost: float

    class Config:
        from_attributes = True

class ReceiptCreate(BaseModel):
    supplier_name: str
    destination_location_id: int
    notes: Optional[str] = None
    lines: List[ReceiptLineCreate]

class ReceiptValidateRequest(BaseModel):
    received_lines: Optional[List[dict]] = None # [{"line_id": 1, "quantity_received": 50}]

class ReceiptOut(BaseModel):
    id: int
    reference: str
    supplier_name: str
    destination_location_id: int
    status: DocStatus
    notes: Optional[str] = None
    created_at: datetime
    validated_at: Optional[datetime] = None
    lines: List[ReceiptLineOut] = []

    class Config:
        from_attributes = True

# --- Delivery Schemas ---
class DeliveryLineCreate(BaseModel):
    product_id: int
    quantity_demanded: float

class DeliveryLineOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity_demanded: float
    quantity_done: float

    class Config:
        from_attributes = True

class DeliveryCreate(BaseModel):
    customer_name: str
    source_location_id: int
    notes: Optional[str] = None
    lines: List[DeliveryLineCreate]

class DeliveryValidateRequest(BaseModel):
    done_lines: Optional[List[dict]] = None # [{"line_id": 1, "quantity_done": 10}]

class DeliveryOut(BaseModel):
    id: int
    reference: str
    customer_name: str
    source_location_id: int
    status: DocStatus
    is_picked: int
    is_packed: int
    notes: Optional[str] = None
    created_at: datetime
    validated_at: Optional[datetime] = None
    lines: List[DeliveryLineOut] = []

    class Config:
        from_attributes = True

# --- Transfer Schemas ---
class TransferLineCreate(BaseModel):
    product_id: int
    quantity: float

class TransferLineOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: float

    class Config:
        from_attributes = True

class TransferCreate(BaseModel):
    source_location_id: int
    destination_location_id: int
    notes: Optional[str] = None
    lines: List[TransferLineCreate]

class TransferOut(BaseModel):
    id: int
    reference: str
    source_location_id: int
    destination_location_id: int
    status: DocStatus
    notes: Optional[str] = None
    created_at: datetime
    validated_at: Optional[datetime] = None
    lines: List[TransferLineOut] = []

    class Config:
        from_attributes = True

# --- Adjustment Schemas ---
class AdjustmentLineCreate(BaseModel):
    product_id: int
    counted_qty: float
    loss_cause: Optional[LossCauseEnum] = LossCauseEnum.COUNT_MISMATCH

class AdjustmentLineOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    recorded_qty: float
    counted_qty: float
    difference_qty: float
    loss_cause: LossCauseEnum

    class Config:
        from_attributes = True

class AdjustmentCreate(BaseModel):
    location_id: int
    notes: Optional[str] = None
    lines: List[AdjustmentLineCreate]

class AdjustmentOut(BaseModel):
    id: int
    reference: str
    location_id: int
    status: DocStatus
    notes: Optional[str] = None
    created_at: datetime
    validated_at: Optional[datetime] = None
    lines: List[AdjustmentLineOut] = []

    class Config:
        from_attributes = True
