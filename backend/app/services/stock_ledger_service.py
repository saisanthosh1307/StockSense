import hashlib
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.inventory import Product, Location, StockQuant, LocationType
from app.models.operations import (
    DocStatus,
    Receipt,
    ReceiptLine,
    Delivery,
    DeliveryLine,
    Transfer,
    TransferLine,
    Adjustment,
    AdjustmentLine,
)
from app.models.ledger import StockMove, MoveType
from app.models.audit import Alert, AlertSeverity, AlertType, AuditLog
from app.services.trust_chain_service import seal_moves_into_block

def get_or_create_virtual_location(db: Session, loc_type: LocationType) -> Location:
    loc = db.query(Location).filter(Location.location_type == loc_type).first()
    if not loc:
        type_names = {
            LocationType.VENDOR: ("Vendors", "VEND/01"),
            LocationType.CUSTOMER: ("Customers", "CUST/01"),
            LocationType.INVENTORY_LOSS: ("Inventory Loss / Scrap", "SCRAP/01"),
            LocationType.TRANSIT: ("Transit Location", "TRANSIT/01")
        }
        name, code = type_names.get(loc_type, ("Virtual Location", "VIRT/01"))
        loc = Location(
            name=name,
            code=code,
            location_type=loc_type,
            max_capacity=9999999.0
        )
        db.add(loc)
        db.commit()
        db.refresh(loc)
    return loc

def get_product_total_stock(db: Session, product_id: int) -> float:
    quants = (
        db.query(StockQuant)
        .join(Location, StockQuant.location_id == Location.id)
        .filter(
            StockQuant.product_id == product_id,
            Location.location_type == LocationType.INTERNAL
        )
        .all()
    )
    return sum(q.quantity for q in quants)

def check_low_stock_and_alert(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return
    total_qty = get_product_total_stock(db, product_id)
    if total_qty <= product.min_reorder_qty:
        severity = AlertSeverity.CRITICAL if total_qty <= 0 else AlertSeverity.WARNING
        alert_type = AlertType.OUT_OF_STOCK if total_qty <= 0 else AlertType.LOW_STOCK
        title = f"Low Stock: {product.name} ({product.sku})"
        message = (
            f"Product '{product.name}' on-hand stock has dropped to {total_qty:.1f} {product.uom}, "
            f"which is at or below the minimum reorder threshold of {product.min_reorder_qty} {product.uom}."
        )
        # Check if active unread alert exists
        existing = db.query(Alert).filter(
            Alert.product_id == product_id,
            Alert.is_read == False
        ).first()
        if not existing:
            alert = Alert(
                title=title,
                message=message,
                severity=severity,
                alert_type=alert_type,
                product_id=product_id,
                is_read=False
            )
            db.add(alert)
            db.commit()

def execute_stock_move(
    db: Session,
    product_id: int,
    from_loc_id: int,
    to_loc_id: int,
    quantity: float,
    reference: str,
    move_type: MoveType,
    user_id: Optional[int] = None
) -> StockMove:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Move quantity must be greater than zero.")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    from_loc = db.query(Location).filter(Location.id == from_loc_id).first()
    to_loc = db.query(Location).filter(Location.id == to_loc_id).first()

    if not from_loc or not to_loc:
        raise HTTPException(status_code=404, detail="Source or destination location not found.")

    # If source is physical internal location, check availability
    if from_loc.location_type == LocationType.INTERNAL:
        source_quant = db.query(StockQuant).filter(
            StockQuant.product_id == product_id,
            StockQuant.location_id == from_loc_id
        ).first()
        available_qty = source_quant.quantity if source_quant else 0.0
        if available_qty < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product '{product.name}' in {from_loc.name}. Available: {available_qty}, Requested: {quantity}"
            )
        source_quant.quantity -= quantity
    else:
        # Virtual location (e.g. Vendor), update or create quant for bookkeeping
        source_quant = db.query(StockQuant).filter(
            StockQuant.product_id == product_id,
            StockQuant.location_id == from_loc_id
        ).first()
        if source_quant:
            source_quant.quantity -= quantity
        else:
            source_quant = StockQuant(product_id=product_id, location_id=from_loc_id, quantity=-quantity)
            db.add(source_quant)

    # Destination quant update
    dest_quant = db.query(StockQuant).filter(
        StockQuant.product_id == product_id,
        StockQuant.location_id == to_loc_id
    ).first()
    if dest_quant:
        dest_quant.quantity += quantity
    else:
        dest_quant = StockQuant(product_id=product_id, location_id=to_loc_id, quantity=quantity)
        db.add(dest_quant)

    # Calculate total valuation
    unit_cost = product.unit_cost
    total_value = quantity * unit_cost
    now = datetime.utcnow()

    # Generate cryptographic hash for record immutability
    raw_sig = f"{reference}:{product_id}:{from_loc_id}:{to_loc_id}:{quantity}:{unit_cost}:{now.isoformat()}"
    rec_hash = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()

    move = StockMove(
        reference=reference,
        move_type=move_type,
        product_id=product_id,
        from_location_id=from_loc_id,
        to_location_id=to_loc_id,
        quantity=quantity,
        unit_cost=unit_cost,
        total_value=total_value,
        user_id=user_id,
        timestamp=now,
        record_hash=rec_hash
    )
    db.add(move)
    db.commit()
    db.refresh(move)

    # Check for low stock triggers
    check_low_stock_and_alert(db, product_id)

    # Seal in cryptographic trust chain
    try:
        seal_moves_into_block(db, [move.id])
    except Exception as e:
        # Log failure if block sealing encounters issue but keep move intact
        pass

    return move

# --- Validation handlers for Odoo-style operations ---

def validate_receipt_operation(db: Session, receipt_id: int, user_id: Optional[int] = None) -> Receipt:
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    if receipt.status == DocStatus.DONE:
        raise HTTPException(status_code=400, detail="Receipt is already validated.")

    vendor_loc = get_or_create_virtual_location(db, LocationType.VENDOR)
    dest_loc_id = receipt.destination_location_id

    for line in receipt.lines:
        qty_to_receive = line.quantity_received if line.quantity_received > 0 else line.quantity_expected
        if line.quantity_received <= 0:
            line.quantity_received = line.quantity_expected

        # Execute double-entry move: Vendor -> Destination
        execute_stock_move(
            db=db,
            product_id=line.product_id,
            from_loc_id=vendor_loc.id,
            to_loc_id=dest_loc_id,
            quantity=qty_to_receive,
            reference=receipt.reference,
            move_type=MoveType.RECEIPT,
            user_id=user_id
        )

    receipt.status = DocStatus.DONE
    receipt.validated_at = datetime.utcnow()
    
    # Audit log
    audit = AuditLog(
        user_id=user_id,
        action="VALIDATE_RECEIPT",
        entity_type="Receipt",
        entity_id=receipt.id,
        details=f"Validated incoming receipt {receipt.reference} from {receipt.supplier_name}"
    )
    db.add(audit)
    db.commit()
    db.refresh(receipt)
    return receipt

def validate_delivery_operation(db: Session, delivery_id: int, user_id: Optional[int] = None) -> Delivery:
    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery order not found.")
    if delivery.status == DocStatus.DONE:
        raise HTTPException(status_code=400, detail="Delivery order is already validated.")

    cust_loc = get_or_create_virtual_location(db, LocationType.CUSTOMER)
    source_loc_id = delivery.source_location_id

    for line in delivery.lines:
        qty_to_ship = line.quantity_done if line.quantity_done > 0 else line.quantity_demanded
        if line.quantity_done <= 0:
            line.quantity_done = line.quantity_demanded

        # Execute double-entry move: Source -> Customer
        execute_stock_move(
            db=db,
            product_id=line.product_id,
            from_loc_id=source_loc_id,
            to_loc_id=cust_loc.id,
            quantity=qty_to_ship,
            reference=delivery.reference,
            move_type=MoveType.DELIVERY,
            user_id=user_id
        )

    delivery.status = DocStatus.DONE
    delivery.is_picked = 1
    delivery.is_packed = 1
    delivery.validated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=user_id,
        action="VALIDATE_DELIVERY",
        entity_type="Delivery",
        entity_id=delivery.id,
        details=f"Validated outgoing delivery {delivery.reference} to customer {delivery.customer_name}"
    )
    db.add(audit)
    db.commit()
    db.refresh(delivery)
    return delivery

def validate_transfer_operation(db: Session, transfer_id: int, user_id: Optional[int] = None) -> Transfer:
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found.")
    if transfer.status == DocStatus.DONE:
        raise HTTPException(status_code=400, detail="Transfer is already validated.")

    for line in transfer.lines:
        execute_stock_move(
            db=db,
            product_id=line.product_id,
            from_loc_id=transfer.source_location_id,
            to_loc_id=transfer.destination_location_id,
            quantity=line.quantity,
            reference=transfer.reference,
            move_type=MoveType.TRANSFER,
            user_id=user_id
        )

    transfer.status = DocStatus.DONE
    transfer.validated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=user_id,
        action="VALIDATE_TRANSFER",
        entity_type="Transfer",
        entity_id=transfer.id,
        details=f"Executed internal transfer {transfer.reference}"
    )
    db.add(audit)
    db.commit()
    db.refresh(transfer)
    return transfer

def validate_adjustment_operation(db: Session, adjustment_id: int, user_id: Optional[int] = None) -> Adjustment:
    adjustment = db.query(Adjustment).filter(Adjustment.id == adjustment_id).first()
    if not adjustment:
        raise HTTPException(status_code=404, detail="Adjustment not found.")
    if adjustment.status == DocStatus.DONE:
        raise HTTPException(status_code=400, detail="Adjustment is already validated.")

    loss_loc = get_or_create_virtual_location(db, LocationType.INVENTORY_LOSS)

    for line in adjustment.lines:
        # Fetch current recorded stock if not populated
        quant = db.query(StockQuant).filter(
            StockQuant.product_id == line.product_id,
            StockQuant.location_id == adjustment.location_id
        ).first()
        recorded = quant.quantity if quant else 0.0
        line.recorded_qty = recorded
        diff = line.counted_qty - recorded
        line.difference_qty = diff

        if diff > 0:
            # Positive adjustment (Found extra items): Inventory Loss -> Physical Location
            execute_stock_move(
                db=db,
                product_id=line.product_id,
                from_loc_id=loss_loc.id,
                to_loc_id=adjustment.location_id,
                quantity=diff,
                reference=adjustment.reference,
                move_type=MoveType.ADJUSTMENT,
                user_id=user_id
            )
        elif diff < 0:
            # Negative adjustment (Damaged / lost items): Physical Location -> Inventory Loss
            execute_stock_move(
                db=db,
                product_id=line.product_id,
                from_loc_id=adjustment.location_id,
                to_loc_id=loss_loc.id,
                quantity=abs(diff),
                reference=adjustment.reference,
                move_type=MoveType.ADJUSTMENT,
                user_id=user_id
            )

    adjustment.status = DocStatus.DONE
    adjustment.validated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=user_id,
        action="VALIDATE_ADJUSTMENT",
        entity_type="Adjustment",
        entity_id=adjustment.id,
        details=f"Validated inventory adjustment {adjustment.reference}"
    )
    db.add(audit)
    db.commit()
    db.refresh(adjustment)
    return adjustment
