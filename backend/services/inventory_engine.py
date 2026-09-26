import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.models.inventory import Product, Warehouse, Location, StockLevel
from backend.models.operations import (
    Receipt, ReceiptItem, Delivery, DeliveryItem, InternalTransfer, StockAdjustment,
    OperationStatus, AdjustmentReason
)
from backend.models.batch import InventoryBatch, BatchStatus
from backend.models.supplier import Supplier, SupplierMetric
from backend.models.ledger import StockLedger, TransactionType, AuditLog
from backend.services.trust_chain import TrustChainService

class InventoryEngine:
    @staticmethod
    def get_or_create_stock_level(
        db: Session, product_id: int, warehouse_id: int, location_id: int
    ) -> StockLevel:
        stock_level = db.query(StockLevel).filter(
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.location_id == location_id,
        ).first()
        
        if not stock_level:
            stock_level = StockLevel(
                product_id=product_id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                quantity=0,
                reserved_quantity=0,
                updated_at=datetime.utcnow()
            )
            db.add(stock_level)
            db.flush()
        return stock_level

    @staticmethod
    def record_stock_change(
        db: Session,
        product_id: int,
        warehouse_id: int,
        location_id: int,
        change_qty: int,
        transaction_type: TransactionType,
        reference_type: str,
        reference_id: str,
        user_id: Optional[int] = None,
        batch_number: Optional[str] = None,
        notes: Optional[str] = None
    ) -> StockLedger:
        stock_level = InventoryEngine.get_or_create_stock_level(db, product_id, warehouse_id, location_id)
        
        new_quantity = stock_level.quantity + change_qty
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for Product #{product_id} in Location #{location_id}. Current: {stock_level.quantity}, Needed: {-change_qty}"
            )
            
        stock_level.quantity = new_quantity
        stock_level.updated_at = datetime.utcnow()
        
        # Add to immutable stock ledger
        ledger_entry = StockLedger(
            entry_uuid=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            product_id=product_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            change_qty=change_qty,
            balance_after=new_quantity,
            transaction_type=transaction_type,
            reference_type=reference_type,
            reference_id=str(reference_id),
            batch_number=batch_number,
            user_id=user_id,
            notes=notes
        )
        db.add(ledger_entry)
        db.flush()

        # Audit Log
        audit = AuditLog(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action=f"STOCK_{transaction_type.value}",
            entity_name="StockLedger",
            entity_id=ledger_entry.entry_uuid,
            details=f"Qty: {change_qty} -> Balance: {new_quantity}. Ref: {reference_type} #{reference_id}"
        )
        db.add(audit)
        
        # Append to Cryptographic Trust Chain
        tx_data = {
            "uuid": ledger_entry.entry_uuid,
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "location_id": location_id,
            "change": change_qty,
            "balance": new_quantity,
            "type": transaction_type.value,
            "ref": f"{reference_type}:{reference_id}"
        }
        TrustChainService.append_transaction_block(
            db, [tx_data], f"Stock transaction {transaction_type.value} for Product #{product_id}"
        )

        return ledger_entry

    @staticmethod
    def validate_receipt(db: Session, receipt_id: int, user_id: Optional[int] = None) -> Receipt:
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        if receipt.status == OperationStatus.DONE:
            raise HTTPException(status_code=400, detail="Receipt is already completed")
            
        receipt.received_date = datetime.utcnow()
        receipt.status = OperationStatus.DONE
        
        total_ordered = 0
        total_received = 0
        total_damaged = 0

        for item in receipt.items:
            usable_qty = item.received_qty - item.damaged_qty
            total_ordered += item.ordered_qty
            total_received += item.received_qty
            total_damaged += item.damaged_qty

            if usable_qty > 0:
                # 1. Update stock level & ledger
                InventoryEngine.record_stock_change(
                    db=db,
                    product_id=item.product_id,
                    warehouse_id=receipt.warehouse_id,
                    location_id=item.location_id,
                    change_qty=usable_qty,
                    transaction_type=TransactionType.RECEIPT,
                    reference_type="RECEIPT",
                    reference_id=receipt.receipt_number,
                    user_id=user_id,
                    batch_number=item.batch_number,
                    notes=f"Receipt item validation. Usable: {usable_qty}, Damaged: {item.damaged_qty}"
                )

                # 2. Batch Creation if batch or perishable
                if item.batch_number or item.expiry_date:
                    batch = db.query(InventoryBatch).filter(
                        InventoryBatch.batch_number == item.batch_number,
                        InventoryBatch.product_id == item.product_id,
                        InventoryBatch.warehouse_id == receipt.warehouse_id,
                        InventoryBatch.location_id == item.location_id,
                    ).first()
                    
                    if batch:
                        batch.current_quantity += usable_qty
                        batch.updated_at = datetime.utcnow()
                    else:
                        batch = InventoryBatch(
                            batch_number=item.batch_number or f"BATCH-{uuid.uuid4().hex[:6].upper()}",
                            product_id=item.product_id,
                            warehouse_id=receipt.warehouse_id,
                            location_id=item.location_id,
                            initial_quantity=usable_qty,
                            current_quantity=usable_qty,
                            reserved_quantity=0,
                            manufacturing_date=datetime.utcnow(),
                            expiry_date=item.expiry_date or (datetime.utcnow().replace(year=datetime.utcnow().year + 1)),
                            cost_per_unit=item.unit_cost,
                            status=BatchStatus.ACTIVE
                        )
                        db.add(batch)

        # 3. Update Supplier Metrics based on this receipt
        InventoryEngine._update_supplier_metrics(db, receipt, total_ordered, total_received, total_damaged)
        
        db.commit()
        db.refresh(receipt)
        return receipt

    @staticmethod
    def _update_supplier_metrics(
        db: Session, receipt: Receipt, total_ordered: int, total_received: int, total_damaged: int
    ):
        supplier = db.query(Supplier).filter(Supplier.id == receipt.supplier_id).first()
        if not supplier:
            return
            
        actual_lead_time_days = 0.0
        if receipt.received_date and receipt.order_date:
            delta = receipt.received_date - receipt.order_date
            actual_lead_time_days = max(0.5, delta.total_seconds() / 86400.0)
            
        is_on_time = True
        if receipt.expected_date and receipt.received_date:
            is_on_time = receipt.received_date <= receipt.expected_date

        metric = db.query(SupplierMetric).filter(SupplierMetric.supplier_id == supplier.id).first()
        if not metric:
            metric = SupplierMetric(
                supplier_id=supplier.id,
                total_orders=0,
                completed_orders=0,
                on_time_orders=0,
                delayed_orders=0,
                total_ordered_qty=0.0,
                total_received_qty=0.0,
                total_damaged_qty=0.0,
                average_lead_time_days=actual_lead_time_days or supplier.expected_lead_time_days,
                expected_avg_lead_time_days=supplier.expected_lead_time_days,
                on_time_delivery_pct=100.0,
                quantity_accuracy_pct=100.0,
                damage_rate_pct=0.0,
                reliability_score=95.0,
            )
            db.add(metric)
            db.flush()

        # Update accumulators
        metric.total_orders += 1
        metric.completed_orders += 1
        if is_on_time:
            metric.on_time_orders += 1
        else:
            metric.delayed_orders += 1

        metric.total_ordered_qty += total_ordered
        metric.total_received_qty += total_received
        metric.total_damaged_qty += total_damaged

        # Rolling averages
        if metric.completed_orders > 0:
            metric.on_time_delivery_pct = round((metric.on_time_orders / metric.completed_orders) * 100.0, 1)
            metric.average_lead_time_days = round(
                ((metric.average_lead_time_days * (metric.completed_orders - 1)) + actual_lead_time_days) / metric.completed_orders,
                1
            )
        
        if metric.total_ordered_qty > 0:
            metric.quantity_accuracy_pct = round(
                max(0.0, min(100.0, (metric.total_received_qty / metric.total_ordered_qty) * 100.0)),
                1
            )
        
        if metric.total_received_qty > 0:
            metric.damage_rate_pct = round(
                (metric.total_damaged_qty / metric.total_received_qty) * 100.0,
                2
            )

        # Calculate composite Supplier Reliability Score (0-100)
        # 40% on-time, 35% accuracy, 15% (100 - damage rate), 10% lead time factor
        lead_time_factor = 100.0
        if metric.expected_avg_lead_time_days > 0:
            lead_time_factor = max(0.0, min(100.0, 100.0 - ((metric.average_lead_time_days - metric.expected_avg_lead_time_days) * 10.0)))
            
        reliability = (
            (metric.on_time_delivery_pct * 0.40) +
            (metric.quantity_accuracy_pct * 0.35) +
            (max(0.0, 100.0 - (metric.damage_rate_pct * 5.0)) * 0.15) +
            (lead_time_factor * 0.10)
        )
        metric.reliability_score = round(max(0.0, min(100.0, reliability)), 1)
        metric.calculated_at = datetime.utcnow()

    @staticmethod
    def validate_delivery(db: Session, delivery_id: int, user_id: Optional[int] = None) -> Delivery:
        delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()
        if not delivery:
            raise HTTPException(status_code=404, detail="Delivery not found")
        if delivery.status == OperationStatus.DONE:
            raise HTTPException(status_code=400, detail="Delivery is already completed")
            
        delivery.shipped_date = datetime.utcnow()
        delivery.status = OperationStatus.DONE

        for item in delivery.items:
            qty_to_deduct = item.picked_qty if item.picked_qty > 0 else item.requested_qty
            
            # Record inventory reduction
            InventoryEngine.record_stock_change(
                db=db,
                product_id=item.product_id,
                warehouse_id=delivery.warehouse_id,
                location_id=item.location_id,
                change_qty=-qty_to_deduct,
                transaction_type=TransactionType.DELIVERY,
                reference_type="DELIVERY",
                reference_id=delivery.delivery_number,
                user_id=user_id,
                batch_number=item.batch.batch_number if item.batch else None,
                notes=f"Delivery fulfillment for {delivery.customer_name}"
            )

            # Update batch if applicable
            if item.batch_id:
                batch = db.query(InventoryBatch).filter(InventoryBatch.id == item.batch_id).first()
                if batch:
                    batch.current_quantity = max(0, batch.current_quantity - qty_to_deduct)
                    if batch.current_quantity == 0:
                        batch.status = BatchStatus.DEPLETED
                    batch.updated_at = datetime.utcnow()

            item.picked_qty = qty_to_deduct
            item.packed_qty = qty_to_deduct

        db.commit()
        db.refresh(delivery)
        return delivery

    @staticmethod
    def execute_internal_transfer(db: Session, transfer_id: int, user_id: Optional[int] = None) -> InternalTransfer:
        transfer = db.query(InternalTransfer).filter(InternalTransfer.id == transfer_id).first()
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        if transfer.status == OperationStatus.DONE:
            raise HTTPException(status_code=400, detail="Transfer is already completed")

        # 1. Deduct from source
        InventoryEngine.record_stock_change(
            db=db,
            product_id=transfer.product_id,
            warehouse_id=transfer.from_warehouse_id,
            location_id=transfer.from_location_id,
            change_qty=-transfer.quantity,
            transaction_type=TransactionType.TRANSFER_OUT,
            reference_type="TRANSFER",
            reference_id=transfer.transfer_number,
            user_id=user_id,
            notes=f"Internal transfer to WH #{transfer.to_warehouse_id}"
        )

        # 2. Add to destination
        InventoryEngine.record_stock_change(
            db=db,
            product_id=transfer.product_id,
            warehouse_id=transfer.to_warehouse_id,
            location_id=transfer.to_location_id,
            change_qty=transfer.quantity,
            transaction_type=TransactionType.TRANSFER_IN,
            reference_type="TRANSFER",
            reference_id=transfer.transfer_number,
            user_id=user_id,
            notes=f"Internal transfer from WH #{transfer.from_warehouse_id}"
        )

        # 3. Update batch location if batch involved
        if transfer.batch_id:
            batch = db.query(InventoryBatch).filter(InventoryBatch.id == transfer.batch_id).first()
            if batch:
                if batch.current_quantity == transfer.quantity:
                    batch.warehouse_id = transfer.to_warehouse_id
                    batch.location_id = transfer.to_location_id
                else:
                    batch.current_quantity -= transfer.quantity
                    new_batch = InventoryBatch(
                        batch_number=batch.batch_number,
                        product_id=batch.product_id,
                        warehouse_id=transfer.to_warehouse_id,
                        location_id=transfer.to_location_id,
                        initial_quantity=transfer.quantity,
                        current_quantity=transfer.quantity,
                        manufacturing_date=batch.manufacturing_date,
                        expiry_date=batch.expiry_date,
                        cost_per_unit=batch.cost_per_unit,
                        status=BatchStatus.ACTIVE
                    )
                    db.add(new_batch)

        transfer.status = OperationStatus.DONE
        transfer.completed_date = datetime.utcnow()
        db.commit()
        db.refresh(transfer)
        return transfer

    @staticmethod
    def execute_stock_adjustment(db: Session, adjustment_id: int, user_id: Optional[int] = None) -> StockAdjustment:
        adj = db.query(StockAdjustment).filter(StockAdjustment.id == adjustment_id).first()
        if not adj:
            raise HTTPException(status_code=404, detail="Stock adjustment not found")
        if adj.status == OperationStatus.DONE:
            raise HTTPException(status_code=400, detail="Adjustment is already completed")

        variance = adj.variance_qty
        tx_type = TransactionType.ADJUSTMENT_INCREASE if variance > 0 else TransactionType.ADJUSTMENT_DECREASE

        InventoryEngine.record_stock_change(
            db=db,
            product_id=adj.product_id,
            warehouse_id=adj.warehouse_id,
            location_id=adj.location_id,
            change_qty=variance,
            transaction_type=tx_type,
            reference_type="ADJUSTMENT",
            reference_id=adj.adjustment_number,
            user_id=user_id,
            notes=f"Count variance: Reason: {adj.reason_type.value}. Notes: {adj.notes or 'None'}"
        )

        if adj.batch_id:
            batch = db.query(InventoryBatch).filter(InventoryBatch.id == adj.batch_id).first()
            if batch:
                batch.current_quantity = max(0, batch.current_quantity + variance)
                if batch.current_quantity == 0:
                    batch.status = BatchStatus.DEPLETED

        adj.status = OperationStatus.DONE
        adj.approved_by_id = user_id
        db.commit()
        db.refresh(adj)
        return adj
