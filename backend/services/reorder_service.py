import math
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.inventory import Product, StockLevel
from backend.models.supplier import Supplier, SupplierMetric
from backend.models.ledger import StockLedger
from backend.schemas.intelligence import ReorderRecommendation
from backend.services.impact_score_service import ImpactScoreService

class ReorderService:
    @staticmethod
    def get_reorder_recommendations(db: Session, warehouse_id: Optional[int] = None) -> List[ReorderRecommendation]:
        products = db.query(Product).all()
        now = datetime.utcnow()
        ninety_days_ago = now - timedelta(days=90)

        results: List[ReorderRecommendation] = []

        for p in products:
            # 1. Total current stock
            stock_q = db.query(func.sum(StockLevel.quantity)).filter(StockLevel.product_id == p.id)
            if warehouse_id:
                stock_q = stock_q.filter(StockLevel.warehouse_id == warehouse_id)
            current_stock = stock_q.scalar() or 0

            # 2. Demand history
            txs = db.query(StockLedger).filter(
                StockLedger.product_id == p.id,
                StockLedger.change_qty < 0,
                StockLedger.timestamp >= ninety_days_ago
            ).all()

            total_consumed = sum(abs(t.change_qty) for t in txs)
            avg_daily_demand = max(0.5, total_consumed / 90.0)

            # 3. Supplier Intelligence integration
            supplier = p.supplier
            lead_time = 7.0
            supplier_name = "Standard Supplier"
            supplier_id = None
            reliability_pct = 95.0
            lead_time_variance = 1.0

            if supplier:
                supplier_id = supplier.id
                supplier_name = supplier.name
                lead_time = supplier.expected_lead_time_days
                if supplier.metrics:
                    m = supplier.metrics[0]
                    lead_time = m.average_lead_time_days
                    reliability_pct = m.reliability_score
                    lead_time_variance = max(0.5, abs(m.average_lead_time_days - m.expected_avg_lead_time_days))

            # Service level factor Z: base 1.65 (95% service level). If supplier is unreliable, increase buffer!
            z_factor = 1.65
            if reliability_pct < 85.0:
                z_factor = 2.05  # buffer against unreliable supplier
            elif reliability_pct < 92.0:
                z_factor = 1.85

            # Demand variance estimation
            sigma_d = max(0.5, avg_daily_demand * 0.35)
            sigma_l = lead_time_variance

            # Dynamic Safety Stock = Z * sqrt( L * sigma_d^2 + d^2 * sigma_L^2 )
            variance_term = (lead_time * (sigma_d ** 2)) + ((avg_daily_demand ** 2) * (sigma_l ** 2))
            safety_stock = int(math.ceil(z_factor * math.sqrt(variance_term)))

            # Reorder Point = (Avg Daily Demand * Lead Time) + Safety Stock
            lead_demand = avg_daily_demand * lead_time
            reorder_point = int(math.ceil(lead_demand + safety_stock))

            # Trigger check: recommend if stock is at or below reorder point or min stock level
            should_reorder = current_stock <= max(reorder_point, p.min_stock_level)

            # Economic Order Quantity (EOQ): sqrt( (2 * Annual Demand * Ordering Cost) / Holding Cost )
            annual_demand = avg_daily_demand * 365.0
            ordering_cost = 500.0  # ₹500 per PO administration
            unit_cost = max(10.0, p.cost_price)
            holding_cost_rate = 0.20  # 20% annual inventory holding cost
            holding_cost_per_unit = unit_cost * holding_cost_rate

            eoq = int(math.ceil(math.sqrt((2.0 * annual_demand * ordering_cost) / holding_cost_per_unit)))
            recommended_order_qty = max(eoq, reorder_point - current_stock + safety_stock)

            # Confidence score (higher with stable demand & reliable supplier)
            conf = round(min(97.0, max(70.0, (reliability_pct * 0.6) + (35.0 - (sigma_d * 2.0)))), 1)

            # Feature 5: Impact Score integration
            stockout_risk = round(min(100.0, max(0.0, ((reorder_point - current_stock) / (reorder_point + 1.0)) * 100.0)), 1)
            est_cost = round(recommended_order_qty * unit_cost, 2)

            impact_detail = ImpactScoreService.calculate_impact_score(
                stockout_risk=stockout_risk,
                financial_exposure=est_cost,
                demand_volatility=round(sigma_d / avg_daily_demand, 2),
                lead_time_days=lead_time,
                supplier_reliability_pct=reliability_pct,
                context_type="REORDER"
            )

            # Urgency classification
            if current_stock == 0:
                urgency = "CRITICAL"
            elif current_stock <= safety_stock:
                urgency = "HIGH"
            elif should_reorder:
                urgency = "MEDIUM"
            else:
                urgency = "LOW"

            if should_reorder or current_stock < p.min_stock_level or urgency in ["CRITICAL", "HIGH"]:
                results.append(ReorderRecommendation(
                    product_id=p.id,
                    sku=p.sku,
                    product_name=p.name,
                    current_stock=current_stock,
                    min_stock_level=p.min_stock_level,
                    reorder_point=reorder_point,
                    safety_stock=safety_stock,
                    recommended_order_qty=recommended_order_qty,
                    supplier_id=supplier_id,
                    supplier_name=supplier_name,
                    supplier_lead_time_days=round(lead_time, 1),
                    supplier_reliability_pct=round(reliability_pct, 1),
                    confidence_score=conf,
                    impact_score=impact_detail.overall_score,
                    impact_level=impact_detail.impact_level,
                    impact_reasons=impact_detail.reasons,
                    estimated_cost=est_cost,
                    urgency=urgency
                ))

        return sorted(results, key=lambda x: x.impact_score, reverse=True)
