from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models.inventory import Product, Warehouse, Location
from backend.models.batch import InventoryBatch, BatchStatus
from backend.schemas.advanced import (
    InventoryBatchResponse, FefoPickStep, FefoPickPlanResponse, ExpiryAlertGroup
)

class FefoService:
    @staticmethod
    def get_batches(
        db: Session,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        only_active: bool = True
    ) -> List[InventoryBatchResponse]:
        query = db.query(InventoryBatch).join(Product).join(Warehouse).join(Location)
        
        if product_id:
            query = query.filter(InventoryBatch.product_id == product_id)
        if warehouse_id:
            query = query.filter(InventoryBatch.warehouse_id == warehouse_id)
        if only_active:
            query = query.filter(InventoryBatch.current_quantity > 0)

        # Sort primarily by expiry_date ascending (FEFO)
        batches = query.order_by(InventoryBatch.expiry_date.asc()).all()

        now = datetime.utcnow()
        results: List[InventoryBatchResponse] = []
        for b in batches:
            days_left = (b.expiry_date - now).days
            is_expired = days_left < 0
            is_critical = 0 <= days_left <= 7
            is_soon = 0 <= days_left <= 30
            val = round(b.current_quantity * (b.cost_per_unit or b.product.cost_price), 2)
            avail = max(0, b.current_quantity - b.reserved_quantity)

            # Update status if expired
            if is_expired and b.status == BatchStatus.ACTIVE:
                b.status = BatchStatus.EXPIRED

            results.append(InventoryBatchResponse(
                id=b.id,
                batch_number=b.batch_number,
                product_id=b.product_id,
                product_name=b.product.name,
                product_sku=b.product.sku,
                warehouse_id=b.warehouse_id,
                warehouse_name=b.warehouse.name,
                location_id=b.location_id,
                location_code=b.location.code,
                initial_quantity=b.initial_quantity,
                current_quantity=b.current_quantity,
                reserved_quantity=b.reserved_quantity,
                available_quantity=avail,
                manufacturing_date=b.manufacturing_date,
                expiry_date=b.expiry_date,
                days_to_expiry=days_left,
                cost_per_unit=b.cost_per_unit or b.product.cost_price,
                total_value=val,
                status=b.status,
                is_expired=is_expired,
                is_expiring_soon=is_soon,
                is_critical=is_critical
            ))

        db.commit()
        return results

    @staticmethod
    def get_expiry_alerts(db: Session, days_threshold: int = 30) -> ExpiryAlertGroup:
        all_batches = FefoService.get_batches(db, only_active=True)
        
        expired = [b for b in all_batches if b.days_to_expiry < 0]
        crit_7 = [b for b in all_batches if 0 <= b.days_to_expiry <= 7]
        soon_30 = [b for b in all_batches if 7 < b.days_to_expiry <= days_threshold]

        expired_val = round(sum(b.total_value for b in expired), 2)
        crit_val = round(sum(b.total_value for b in crit_7), 2)
        soon_val = round(sum(b.total_value for b in soon_30), 2)

        return ExpiryAlertGroup(
            expired_count=len(expired),
            expired_value=expired_val,
            expiring_7_days_count=len(crit_7),
            expiring_7_days_value=crit_val,
            expiring_30_days_count=len(soon_30),
            expiring_30_days_value=soon_val,
            batches=sorted(all_batches, key=lambda x: x.days_to_expiry)
        )

    @staticmethod
    def plan_fefo_picking(
        db: Session, product_id: int, warehouse_id: int, requested_qty: int
    ) -> FefoPickPlanResponse:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product #{product_id} not found")

        # Query all active non-expired batches for this product in this warehouse
        # Order strictly by earliest expiry date first (FEFO)
        now = datetime.utcnow()
        batches = db.query(InventoryBatch).join(Location).filter(
            InventoryBatch.product_id == product_id,
            InventoryBatch.warehouse_id == warehouse_id,
            InventoryBatch.current_quantity > 0,
            InventoryBatch.expiry_date > now
        ).order_by(InventoryBatch.expiry_date.asc()).all()

        picking_steps: List[FefoPickStep] = []
        remaining_needed = requested_qty
        fulfilled_qty = 0

        for idx, b in enumerate(batches, start=1):
            if remaining_needed <= 0:
                break
                
            avail = max(0, b.current_quantity - b.reserved_quantity)
            if avail <= 0:
                continue

            pick_from_this_batch = min(remaining_needed, avail)
            days_left = (b.expiry_date - now).days

            picking_steps.append(FefoPickStep(
                step_number=idx,
                batch_id=b.id,
                batch_number=b.batch_number,
                product_id=product.id,
                product_name=product.name,
                location_id=b.location_id,
                location_code=b.location.code,
                warehouse_id=b.warehouse_id,
                expiry_date=b.expiry_date,
                days_to_expiry=days_left,
                available_in_batch=avail,
                recommended_pick_qty=pick_from_this_batch
            ))

            fulfilled_qty += pick_from_this_batch
            remaining_needed -= pick_from_this_batch

        shortage = max(0, requested_qty - fulfilled_qty)
        explanation = (
            f"FEFO allocation complete: Prioritized {len(picking_steps)} batch(es) "
            f"in ascending order of expiration date. Fulfilled {fulfilled_qty}/{requested_qty} {product.uom}."
        )
        if shortage > 0:
            explanation += f" Warning: Stock shortage of {shortage} {product.uom}."

        return FefoPickPlanResponse(
            product_id=product.id,
            product_name=product.name,
            requested_quantity=requested_qty,
            fulfilled_quantity=fulfilled_qty,
            shortage_quantity=shortage,
            picking_steps=picking_steps,
            fefo_explanation=explanation
        )
