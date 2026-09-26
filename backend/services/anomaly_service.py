import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.inventory import Product, Warehouse, StockLevel
from backend.models.operations import StockAdjustment, AdjustmentReason, OperationStatus
from backend.models.ledger import StockLedger, TransactionType
from backend.schemas.intelligence import AnomalyItem, CauseOfLossItem
from backend.services.impact_score_service import ImpactScoreService

class AnomalyService:
    @staticmethod
    def detect_anomalies(db: Session) -> List[AnomalyItem]:
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        
        # Analyze movements per product
        products = db.query(Product).all()
        anomalies: List[AnomalyItem] = []

        for p in products:
            txs = db.query(StockLedger).filter(
                StockLedger.product_id == p.id,
                StockLedger.change_qty < 0,
                StockLedger.timestamp >= thirty_days_ago
            ).order_by(StockLedger.timestamp.desc()).all()

            if not txs:
                continue

            qtys = [abs(t.change_qty) for t in txs]
            mean_q = sum(qtys) / len(qtys)
            variance = sum((q - mean_q) ** 2 for q in qtys) / (len(qtys) or 1)
            std_dev = math.sqrt(variance)

            # Check individual spikes
            for t in txs[:5]:  # recent 5 transactions
                qty = abs(t.change_qty)
                z_score = ((qty - mean_q) / std_dev) if std_dev > 0 else 0.0
                
                if z_score >= 2.2 and qty > (mean_q * 2.0):
                    fin_exposure = round(qty * p.cost_price, 2)
                    impact = ImpactScoreService.calculate_impact_score(
                        stockout_risk=80.0,
                        financial_exposure=fin_exposure,
                        demand_volatility=min(100.0, z_score * 25.0),
                        lead_time_days=p.supplier.expected_lead_time_days if p.supplier else 7.0,
                        supplier_reliability_pct=90.0,
                        context_type="ANOMALY"
                    )

                    anomalies.append(AnomalyItem(
                        id=f"ANOM-SPIKE-{t.id}",
                        product_id=p.id,
                        product_name=p.name,
                        sku=p.sku,
                        warehouse_name=t.warehouse.name if t.warehouse else "Main Store",
                        anomaly_type="SUDDEN_SPIKE",
                        severity="HIGH" if z_score < 3.0 else "CRITICAL",
                        detected_value=float(qty),
                        expected_value=round(mean_q, 1),
                        z_score=round(z_score, 2),
                        impact_score=impact.overall_score,
                        impact_level=impact.impact_level,
                        detected_at=t.timestamp,
                        explanation=f"Abnormal single withdrawal of {qty} {p.uom} exceeds typical usage ({round(mean_q, 1)}) by {round(z_score, 1)} standard deviations.",
                        recommended_action="Audit client purchase order and verify physical rack inventory count."
                    ))

            # Check negative adjustments (shrinkage / loss)
            adjustments = db.query(StockAdjustment).filter(
                StockAdjustment.product_id == p.id,
                StockAdjustment.variance_qty < 0,
                StockAdjustment.created_at >= thirty_days_ago
            ).all()

            for adj in adjustments:
                lost_qty = abs(adj.variance_qty)
                lost_val = round(lost_qty * p.cost_price, 2)
                if lost_qty >= 5:
                    impact = ImpactScoreService.calculate_impact_score(
                        stockout_risk=50.0,
                        financial_exposure=lost_val,
                        demand_volatility=60.0,
                        lead_time_days=7.0,
                        supplier_reliability_pct=95.0,
                        context_type="ANOMALY"
                    )

                    anomalies.append(AnomalyItem(
                        id=f"ANOM-SHRINK-{adj.id}",
                        product_id=p.id,
                        product_name=p.name,
                        sku=p.sku,
                        warehouse_name=adj.warehouse.name if adj.warehouse else "Warehouse",
                        anomaly_type="UNUSUAL_SHRINKAGE",
                        severity="CRITICAL" if lost_val > 25000 else "MEDIUM",
                        detected_value=float(lost_qty),
                        expected_value=0.0,
                        z_score=2.8,
                        impact_score=impact.overall_score,
                        impact_level=impact.impact_level,
                        detected_at=adj.created_at,
                        explanation=f"Unexplained physical variance deficit of {lost_qty} {p.uom} logged under '{adj.reason_type.value}'.",
                        recommended_action="Conduct supervisor review of CCTV surveillance and access logs."
                    ))

        return sorted(anomalies, key=lambda x: x.impact_score, reverse=True)

    @staticmethod
    def get_cause_of_loss_analysis(db: Session) -> List[CauseOfLossItem]:
        # Query stock adjustments with negative variance
        adjs = db.query(StockAdjustment).filter(StockAdjustment.variance_qty < 0).all()

        breakdown: Dict[str, Dict[str, Any]] = {
            AdjustmentReason.DAMAGE.value: {"qty": 0, "val": 0.0, "top_p": "N/A"},
            AdjustmentReason.THEFT.value: {"qty": 0, "val": 0.0, "top_p": "N/A"},
            AdjustmentReason.EXPIRY.value: {"qty": 0, "val": 0.0, "top_p": "N/A"},
            AdjustmentReason.RECORDING_ERROR.value: {"qty": 0, "val": 0.0, "top_p": "N/A"},
            AdjustmentReason.OTHER.value: {"qty": 0, "val": 0.0, "top_p": "N/A"},
        }

        total_loss_val = 0.0

        for a in adjs:
            loss_qty = abs(a.variance_qty)
            val = round(loss_qty * a.product.cost_price, 2)
            total_loss_val += val
            r = a.reason_type.value
            if r in breakdown:
                breakdown[r]["qty"] += loss_qty
                breakdown[r]["val"] += val
                breakdown[r]["top_p"] = a.product.name

        mitigations = {
            AdjustmentReason.DAMAGE.value: "Enforce forklift speed limits, inspect pallet racking, and use protective corner guards.",
            AdjustmentReason.THEFT.value: "Tighten warehouse biometric gates, mandate double-signoff on high-value SKUs, and review CCTV.",
            AdjustmentReason.EXPIRY.value: "Strictly enforce FEFO picking policy and activate automated 30-day early clearance alerts.",
            AdjustmentReason.RECORDING_ERROR.value: "Mandate handheld barcode scanner verification on all goods receiving and shelving steps.",
            AdjustmentReason.OTHER.value: "Standardize monthly cycle counting procedure across all secondary storage racks."
        }

        results: List[CauseOfLossItem] = []
        for reason, data in breakdown.items():
            pct = round((data["val"] / total_loss_val * 100.0), 1) if total_loss_val > 0 else 0.0
            
            impact = ImpactScoreService.calculate_impact_score(
                stockout_risk=pct,
                financial_exposure=data["val"],
                demand_volatility=40.0,
                lead_time_days=7.0,
                supplier_reliability_pct=90.0,
                context_type="ANOMALY"
            )

            results.append(CauseOfLossItem(
                reason=reason.replace("_", " ").title(),
                total_quantity_lost=data["qty"],
                total_value_lost=round(data["val"], 2),
                percentage_of_total_loss=pct,
                top_affected_product=data["top_p"],
                impact_score=impact.overall_score,
                mitigation_strategy=mitigations.get(reason, "Review standard warehouse operating procedures.")
            ))

        return sorted(results, key=lambda x: x.total_value_lost, reverse=True)
