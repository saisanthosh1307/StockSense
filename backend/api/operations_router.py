from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.operations import (
    Receipt, ReceiptItem, Delivery, DeliveryItem, InternalTransfer, StockAdjustment,
    OperationStatus, AdjustmentReason
)
from backend.models.inventory import Product, Warehouse, Location, StockLevel
from backend.models.user import User
from backend.schemas.operations import (
    ReceiptCreate, ReceiptResponse,
    DeliveryCreate, DeliveryResponse,
    InternalTransferCreate, InternalTransferResponse,
    StockAdjustmentCreate, StockAdjustmentResponse
)
from backend.services.auth_service import get_current_user
from backend.services.inventory_engine import InventoryEngine

router = APIRouter(tags=["Inventory Operations"])

# --- Receipts ---
@router.get("/receipts", response_model=List[ReceiptResponse])
def list_receipts(
    status: Optional[OperationStatus] = None,
    warehouse_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Receipt)
    if status:
        q = q.filter(Receipt.status == status)
    if warehouse_id:
        q = q.filter(Receipt.warehouse_id == warehouse_id)
    if supplier_id:
        q = q.filter(Receipt.supplier_id == supplier_id)
    receipts = q.order_by(Receipt.created_at.desc()).all()
    
    res = []
    for r in receipts:
        items_dto = [
            {
                "id": itm.id,
                "product_id": itm.product_id,
                "product_name": itm.product.name if itm.product else "",
                "product_sku": itm.product.sku if itm.product else "",
                "location_id": itm.location_id,
                "location_code": itm.location.code if itm.location else "",
                "ordered_qty": itm.ordered_qty,
                "received_qty": itm.received_qty,
                "damaged_qty": itm.damaged_qty,
                "unit_cost": itm.unit_cost,
                "batch_number": itm.batch_number,
                "expiry_date": itm.expiry_date
            } for itm in r.items
        ]
        res.append(ReceiptResponse(
            id=r.id,
            receipt_number=r.receipt_number,
            supplier_id=r.supplier_id,
            supplier_name=r.supplier.name if r.supplier else "",
            warehouse_id=r.warehouse_id,
            warehouse_name=r.warehouse.name if r.warehouse else "",
            status=r.status,
            order_date=r.order_date,
            expected_date=r.expected_date,
            received_date=r.received_date,
            notes=r.notes,
            items=items_dto,
            created_at=r.created_at
        ))
    return res

@router.post("/receipts", response_model=ReceiptResponse)
def create_receipt(
    rec_in: ReceiptCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec_num = rec_in.receipt_number or f"REC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    receipt = Receipt(
        receipt_number=rec_num,
        supplier_id=rec_in.supplier_id,
        warehouse_id=rec_in.warehouse_id,
        status=OperationStatus.READY,
        order_date=datetime.utcnow(),
        expected_date=rec_in.expected_date or (datetime.utcnow() + timedelta(days=7)),
        notes=rec_in.notes,
        created_by_id=current_user.id if current_user else None
    )
    db.add(receipt)
    db.flush()

    for item_data in rec_in.items:
        item = ReceiptItem(
            receipt_id=receipt.id,
            product_id=item_data.product_id,
            location_id=item_data.location_id,
            ordered_qty=item_data.ordered_qty,
            received_qty=item_data.received_qty,
            damaged_qty=item_data.damaged_qty,
            unit_cost=item_data.unit_cost,
            batch_number=item_data.batch_number,
            expiry_date=item_data.expiry_date
        )
        db.add(item)

    db.commit()
    return list_receipts(supplier_id=receipt.supplier_id, db=db)[0]

@router.post("/receipts/{receipt_id}/validate", response_model=ReceiptResponse)
def validate_receipt(
    receipt_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt = InventoryEngine.validate_receipt(db, receipt_id, user_id=current_user.id if current_user else None)
    return list_receipts(supplier_id=receipt.supplier_id, db=db)[0]


# --- Deliveries ---
@router.get("/deliveries", response_model=List[DeliveryResponse])
def list_deliveries(
    status: Optional[OperationStatus] = None,
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Delivery)
    if status:
        q = q.filter(Delivery.status == status)
    if warehouse_id:
        q = q.filter(Delivery.warehouse_id == warehouse_id)
    deliveries = q.order_by(Delivery.created_at.desc()).all()

    res = []
    for d in deliveries:
        items_dto = [
            {
                "id": itm.id,
                "product_id": itm.product_id,
                "product_name": itm.product.name if itm.product else "",
                "product_sku": itm.product.sku if itm.product else "",
                "location_id": itm.location_id,
                "location_code": itm.location.code if itm.location else "",
                "batch_id": itm.batch_id,
                "batch_number": itm.batch.batch_number if itm.batch else None,
                "requested_qty": itm.requested_qty,
                "picked_qty": itm.picked_qty,
                "packed_qty": itm.packed_qty,
                "unit_price": itm.unit_price
            } for itm in d.items
        ]
        res.append(DeliveryResponse(
            id=d.id,
            delivery_number=d.delivery_number,
            customer_name=d.customer_name,
            warehouse_id=d.warehouse_id,
            warehouse_name=d.warehouse.name if d.warehouse else "",
            status=d.status,
            order_date=d.order_date,
            scheduled_date=d.scheduled_date,
            shipped_date=d.shipped_date,
            notes=d.notes,
            items=items_dto,
            created_at=d.created_at
        ))
    return res

@router.post("/deliveries", response_model=DeliveryResponse)
def create_delivery(
    del_in: DeliveryCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    del_num = del_in.delivery_number or f"DEL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    delivery = Delivery(
        delivery_number=del_num,
        customer_name=del_in.customer_name,
        warehouse_id=del_in.warehouse_id,
        status=OperationStatus.READY,
        order_date=datetime.utcnow(),
        scheduled_date=del_in.scheduled_date or datetime.utcnow(),
        notes=del_in.notes,
        created_by_id=current_user.id if current_user else None
    )
    db.add(delivery)
    db.flush()

    for item_data in del_in.items:
        item = DeliveryItem(
            delivery_id=delivery.id,
            product_id=item_data.product_id,
            location_id=item_data.location_id,
            batch_id=item_data.batch_id,
            requested_qty=item_data.requested_qty,
            picked_qty=0,
            packed_qty=0,
            unit_price=item_data.unit_price
        )
        db.add(item)

    db.commit()
    return list_deliveries(warehouse_id=delivery.warehouse_id, db=db)[0]

@router.post("/deliveries/{delivery_id}/validate", response_model=DeliveryResponse)
def validate_delivery(
    delivery_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    delivery = InventoryEngine.validate_delivery(db, delivery_id, user_id=current_user.id if current_user else None)
    return list_deliveries(warehouse_id=delivery.warehouse_id, db=db)[0]


# --- Internal Transfers ---
@router.get("/transfers", response_model=List[InternalTransferResponse])
def list_transfers(db: Session = Depends(get_db)):
    transfers = db.query(InternalTransfer).order_by(InternalTransfer.created_at.desc()).all()
    res = []
    for t in transfers:
        res.append(InternalTransferResponse(
            id=t.id,
            transfer_number=t.transfer_number,
            product_id=t.product_id,
            product_name=t.product.name if t.product else "",
            product_sku=t.product.sku if t.product else "",
            batch_id=t.batch_id,
            from_warehouse_id=t.from_warehouse_id,
            from_warehouse_name=t.from_warehouse.name if t.from_warehouse else "",
            to_warehouse_id=t.to_warehouse_id,
            to_warehouse_name=t.to_warehouse.name if t.to_warehouse else "",
            from_location_id=t.from_location_id,
            from_location_code=t.from_location.code if t.from_location else "",
            to_location_id=t.to_location_id,
            to_location_code=t.to_location.code if t.to_location else "",
            quantity=t.quantity,
            status=t.status,
            scheduled_date=t.scheduled_date,
            completed_date=t.completed_date,
            notes=t.notes
        ))
    return res

@router.post("/transfers", response_model=InternalTransferResponse)
def create_transfer(
    trans_in: InternalTransferCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    num = trans_in.transfer_number or f"TR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    transfer = InternalTransfer(
        transfer_number=num,
        product_id=trans_in.product_id,
        batch_id=trans_in.batch_id,
        from_warehouse_id=trans_in.from_warehouse_id,
        to_warehouse_id=trans_in.to_warehouse_id,
        from_location_id=trans_in.from_location_id,
        to_location_id=trans_in.to_location_id,
        quantity=trans_in.quantity,
        status=OperationStatus.READY,
        notes=trans_in.notes,
        created_by_id=current_user.id if current_user else None
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return list_transfers(db=db)[0]

@router.post("/transfers/{transfer_id}/validate", response_model=InternalTransferResponse)
def validate_transfer(
    transfer_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    InventoryEngine.execute_internal_transfer(db, transfer_id, user_id=current_user.id if current_user else None)
    return list_transfers(db=db)[0]


# --- Stock Adjustments ---
@router.get("/adjustments", response_model=List[StockAdjustmentResponse])
def list_adjustments(db: Session = Depends(get_db)):
    adjs = db.query(StockAdjustment).order_by(StockAdjustment.created_at.desc()).all()
    res = []
    for a in adjs:
        res.append(StockAdjustmentResponse(
            id=a.id,
            adjustment_number=a.adjustment_number,
            warehouse_id=a.warehouse_id,
            warehouse_name=a.warehouse.name if a.warehouse else "",
            location_id=a.location_id,
            location_code=a.location.code if a.location else "",
            product_id=a.product_id,
            product_name=a.product.name if a.product else "",
            product_sku=a.product.sku if a.product else "",
            batch_id=a.batch_id,
            recorded_qty=a.recorded_qty,
            counted_qty=a.counted_qty,
            variance_qty=a.variance_qty,
            reason_type=a.reason_type,
            status=a.status,
            notes=a.notes,
            created_at=a.created_at
        ))
    return res

@router.post("/adjustments", response_model=StockAdjustmentResponse)
def create_adjustment(
    adj_in: StockAdjustmentCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Lookup recorded quantity
    sl = db.query(StockLevel).filter(
        StockLevel.product_id == adj_in.product_id,
        StockLevel.warehouse_id == adj_in.warehouse_id,
        StockLevel.location_id == adj_in.location_id
    ).first()
    recorded_qty = sl.quantity if sl else 0
    variance = adj_in.counted_qty - recorded_qty

    num = f"ADJ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    adj = StockAdjustment(
        adjustment_number=num,
        warehouse_id=adj_in.warehouse_id,
        location_id=adj_in.location_id,
        product_id=adj_in.product_id,
        batch_id=adj_in.batch_id,
        recorded_qty=recorded_qty,
        counted_qty=adj_in.counted_qty,
        variance_qty=variance,
        reason_type=adj_in.reason_type,
        notes=adj_in.notes,
        status=OperationStatus.READY,
        approved_by_id=current_user.id if current_user else None
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)
    return list_adjustments(db=db)[0]

@router.post("/adjustments/{adjustment_id}/validate", response_model=StockAdjustmentResponse)
def validate_adjustment(
    adjustment_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    InventoryEngine.execute_stock_adjustment(db, adjustment_id, user_id=current_user.id if current_user else None)
    return list_adjustments(db=db)[0]
