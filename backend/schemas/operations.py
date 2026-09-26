from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from backend.models.operations import OperationStatus, AdjustmentReason

# --- Receipts ---
class ReceiptItemCreate(BaseModel):
    product_id: int
    location_id: int
    ordered_qty: int
    received_qty: int
    damaged_qty: int = 0
    unit_cost: float = 0.0
    batch_number: Optional[str] = None
    expiry_date: Optional[datetime] = None

class ReceiptItemResponse(ReceiptItemCreate):
    id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    location_code: Optional[str] = None

    class Config:
        from_attributes = True

class ReceiptCreate(BaseModel):
    receipt_number: Optional[str] = None
    supplier_id: int
    warehouse_id: int
    expected_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[ReceiptItemCreate]

class ReceiptResponse(BaseModel):
    id: int
    receipt_number: str
    supplier_id: int
    supplier_name: Optional[str] = None
    warehouse_id: int
    warehouse_name: Optional[str] = None
    status: OperationStatus
    order_date: datetime
    expected_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[ReceiptItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# --- Deliveries ---
class DeliveryItemCreate(BaseModel):
    product_id: int
    location_id: int
    batch_id: Optional[int] = None
    requested_qty: int
    unit_price: float = 0.0

class DeliveryItemResponse(DeliveryItemCreate):
    id: int
    picked_qty: int
    packed_qty: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    location_code: Optional[str] = None
    batch_number: Optional[str] = None

    class Config:
        from_attributes = True

class DeliveryCreate(BaseModel):
    delivery_number: Optional[str] = None
    customer_name: str
    warehouse_id: int
    scheduled_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[DeliveryItemCreate]

class DeliveryResponse(BaseModel):
    id: int
    delivery_number: str
    customer_name: str
    warehouse_id: int
    warehouse_name: Optional[str] = None
    status: OperationStatus
    order_date: datetime
    scheduled_date: Optional[datetime] = None
    shipped_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[DeliveryItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# --- Internal Transfers ---
class InternalTransferCreate(BaseModel):
    transfer_number: Optional[str] = None
    product_id: int
    batch_id: Optional[int] = None
    from_warehouse_id: int
    to_warehouse_id: int
    from_location_id: int
    to_location_id: int
    quantity: int
    notes: Optional[str] = None

class InternalTransferResponse(BaseModel):
    id: int
    transfer_number: str
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    batch_id: Optional[int] = None
    from_warehouse_id: int
    from_warehouse_name: Optional[str] = None
    to_warehouse_id: int
    to_warehouse_name: Optional[str] = None
    from_location_id: int
    from_location_code: Optional[str] = None
    to_location_id: int
    to_location_code: Optional[str] = None
    quantity: int
    status: OperationStatus
    scheduled_date: datetime
    completed_date: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# --- Stock Adjustments ---
class StockAdjustmentCreate(BaseModel):
    warehouse_id: int
    location_id: int
    product_id: int
    batch_id: Optional[int] = None
    counted_qty: int
    reason_type: AdjustmentReason
    notes: Optional[str] = None

class StockAdjustmentResponse(BaseModel):
    id: int
    adjustment_number: str
    warehouse_id: int
    warehouse_name: Optional[str] = None
    location_id: int
    location_code: Optional[str] = None
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    batch_id: Optional[int] = None
    recorded_qty: int
    counted_qty: int
    variance_qty: int
    reason_type: AdjustmentReason
    status: OperationStatus
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
