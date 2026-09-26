from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.supplier import Supplier, SupplierMetric
from backend.models.operations import Receipt, ReceiptItem, OperationStatus
from backend.schemas.advanced import SupplierMetricResponse, SupplierComparisonResponse

class SupplierIntelligenceService:
    @staticmethod
    def get_or_calculate_supplier_metrics(db: Session, supplier_id: int) -> SupplierMetricResponse:
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise ValueError(f"Supplier #{supplier_id} not found")

        # Pull all receipts for this supplier
        receipts = db.query(Receipt).filter(
            Receipt.supplier_id == supplier.id,
            Receipt.status == OperationStatus.DONE
        ).all()

        total_orders = len(receipts)
        completed_orders = total_orders
        on_time_orders = 0
        delayed_orders = 0
        lead_times: List[float] = []
        total_ordered_qty = 0.0
        total_received_qty = 0.0
        total_damaged_qty = 0.0

        for r in receipts:
            # Lead time calculation
            if r.order_date and r.received_date:
                days = max(0.5, (r.received_date - r.order_date).total_seconds() / 86400.0)
                lead_times.append(days)
            else:
                lead_times.append(supplier.expected_lead_time_days)

            # On-time delivery
            if r.expected_date and r.received_date:
                if r.received_date <= r.expected_date:
                    on_time_orders += 1
                else:
                    delayed_orders += 1
            else:
                on_time_orders += 1

            for item in r.items:
                total_ordered_qty += item.ordered_qty
                total_received_qty += item.received_qty
                total_damaged_qty += item.damaged_qty

        existing_metric = db.query(SupplierMetric).filter(SupplierMetric.supplier_id == supplier.id).first()
        if existing_metric and existing_metric.total_orders > len(receipts):
            total_orders = existing_metric.total_orders
            completed_orders = existing_metric.completed_orders
            avg_lead_time = existing_metric.average_lead_time_days
            on_time_pct = existing_metric.on_time_delivery_pct
            qty_accuracy = existing_metric.quantity_accuracy_pct
            damage_rate = existing_metric.damage_rate_pct
            reliability_score = existing_metric.reliability_score
        else:
            # Computations
            avg_lead_time = round(sum(lead_times) / len(lead_times), 1) if lead_times else supplier.expected_lead_time_days
            on_time_pct = round((on_time_orders / total_orders) * 100.0, 1) if total_orders > 0 else 100.0
            qty_accuracy = round(min(100.0, (total_received_qty / total_ordered_qty) * 100.0), 1) if total_ordered_qty > 0 else 100.0
            damage_rate = round((total_damaged_qty / total_received_qty) * 100.0, 2) if total_received_qty > 0 else 0.0

            lead_variance = round(avg_lead_time - supplier.expected_lead_time_days, 1)
            lead_punctuality = max(0.0, min(100.0, 100.0 - (max(0.0, lead_variance) * 10.0)))
            undamaged_score = max(0.0, min(100.0, 100.0 - (damage_rate * 5.0)))
            
            reliability_score = round(
                (on_time_pct * 0.40) +
                (qty_accuracy * 0.35) +
                (undamaged_score * 0.15) +
                (lead_punctuality * 0.10),
                1
            )

        lead_variance = round(avg_lead_time - supplier.expected_lead_time_days, 1)

        # Monthly purchase frequency
        oldest_date = min((r.order_date for r in receipts), default=datetime.utcnow() - timedelta(days=90))
        span_months = max(1.0, (datetime.utcnow() - oldest_date).total_seconds() / (86400.0 * 30.4))
        monthly_freq = round(total_orders / span_months, 1)

        trend = "STABLE"
        if len(lead_times) >= 2:
            recent_lead = lead_times[-1]
            if recent_lead < avg_lead_time - 0.5 and on_time_pct >= 90:
                trend = "IMPROVING"
            elif recent_lead > avg_lead_time + 1.0 or on_time_pct < 80:
                trend = "DECLINING"

        summary = (
            f"On-time delivery is {on_time_pct}%, with an average lead time of {avg_lead_time} days "
            f"(expected: {supplier.expected_lead_time_days} days). Quantity accuracy stands at {qty_accuracy}% "
            f"with a {damage_rate}% damage rate."
        )

        # Update or create SupplierMetric record in DB
        metric = db.query(SupplierMetric).filter(SupplierMetric.supplier_id == supplier.id).first()
        if not metric:
            metric = SupplierMetric(supplier_id=supplier.id)
            db.add(metric)
            
        metric.total_orders = total_orders
        metric.completed_orders = completed_orders
        metric.on_time_orders = on_time_orders
        metric.delayed_orders = delayed_orders
        metric.total_ordered_qty = total_ordered_qty
        metric.total_received_qty = total_received_qty
        metric.total_damaged_qty = total_damaged_qty
        metric.average_lead_time_days = avg_lead_time
        metric.expected_avg_lead_time_days = supplier.expected_lead_time_days
        metric.on_time_delivery_pct = on_time_pct
        metric.quantity_accuracy_pct = qty_accuracy
        metric.damage_rate_pct = damage_rate
        metric.reliability_score = reliability_score
        metric.calculated_at = datetime.utcnow()
        db.commit()

        return SupplierMetricResponse(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            supplier_code=supplier.code,
            total_orders=total_orders,
            completed_orders=completed_orders,
            on_time_delivery_pct=on_time_pct,
            average_lead_time_days=avg_lead_time,
            expected_avg_lead_time_days=supplier.expected_lead_time_days,
            lead_time_variance_days=lead_variance,
            quantity_accuracy_pct=qty_accuracy,
            damage_rate_pct=damage_rate,
            purchase_frequency_monthly=monthly_freq,
            reliability_score=reliability_score,
            rating=supplier.rating,
            historical_trend=trend,
            performance_summary=summary
        )

    @staticmethod
    def get_supplier_comparison(db: Session) -> SupplierComparisonResponse:
        suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()
        results: List[SupplierMetricResponse] = []
        for s in suppliers:
            try:
                res = SupplierIntelligenceService.get_or_calculate_supplier_metrics(db, s.id)
                results.append(res)
            except Exception:
                continue

        if not results:
            return SupplierComparisonResponse(
                average_network_reliability=100.0,
                average_network_lead_time=7.0,
                average_network_accuracy=100.0,
                average_network_damage_rate=0.0,
                suppliers=[]
            )

        avg_rel = round(sum(r.reliability_score for r in results) / len(results), 1)
        avg_lt = round(sum(r.average_lead_time_days for r in results) / len(results), 1)
        avg_acc = round(sum(r.quantity_accuracy_pct for r in results) / len(results), 1)
        avg_dmg = round(sum(r.damage_rate_pct for r in results) / len(results), 2)

        return SupplierComparisonResponse(
            average_network_reliability=avg_rel,
            average_network_lead_time=avg_lt,
            average_network_accuracy=avg_acc,
            average_network_damage_rate=avg_dmg,
            suppliers=sorted(results, key=lambda x: x.reliability_score, reverse=True)
        )
