import math
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.inventory import Product, StockLevel
from backend.models.supplier import Supplier
from backend.schemas.intelligence import WhatIfSimulationRequest, WhatIfSimulationResponse
from backend.services.impact_score_service import ImpactScoreService

class WhatIfService:
    @staticmethod
    def run_simulation(db: Session, req: WhatIfSimulationRequest) -> WhatIfSimulationResponse:
        product = db.query(Product).filter(Product.id == req.product_id).first()
        if not product:
            raise ValueError(f"Product #{req.product_id} not found")

        current_stock = db.query(func.sum(StockLevel.quantity)).filter(
            StockLevel.product_id == product.id
        ).scalar() or 0

        # Baseline parameters
        base_demand_daily = max(1.0, product.reorder_point / 14.0)
        base_lead_time = product.supplier.expected_lead_time_days if product.supplier else 7.0
        base_supplier_reliability = (
            product.supplier.metrics[0].reliability_score
            if (product.supplier and product.supplier.metrics)
            else 95.0
        )
        base_cost = product.cost_price

        # Baseline safety stock & reorder
        base_z = 1.65 if base_supplier_reliability >= 90.0 else 1.95
        base_sigma = base_demand_daily * 0.3
        base_safety_stock = int(math.ceil(base_z * math.sqrt(base_lead_time * (base_sigma ** 2))))
        base_rp = int(math.ceil((base_demand_daily * base_lead_time) + base_safety_stock))
        base_reorder_qty = max(product.min_stock_level * 2, base_rp)
        
        base_lead_demand = base_demand_daily * base_lead_time
        base_stockout_risk = round(min(100.0, max(0.0, ((base_lead_demand - current_stock) / (base_lead_demand + 1.0)) * 100.0)), 1)

        # Simulated parameters
        sim_demand_daily = base_demand_daily * (1.0 + (req.demand_change_pct / 100.0))
        sim_lead_time = max(1.0, base_lead_time + req.lead_time_change_days)
        sim_reliability = (
            req.supplier_reliability_pct
            if req.supplier_reliability_pct is not None
            else base_supplier_reliability
        )
        sim_cost = base_cost * (1.0 + (req.cost_price_change_pct / 100.0))

        # Simulated safety stock & reorder
        sim_z = 1.65 if sim_reliability >= 90.0 else 2.15
        sim_sigma = sim_demand_daily * 0.35
        sim_variance = (sim_lead_time * (sim_sigma ** 2)) + ((sim_demand_daily ** 2) * (1.5 ** 2))
        sim_safety_stock = int(math.ceil(sim_z * math.sqrt(sim_variance)))
        sim_rp = int(math.ceil((sim_demand_daily * sim_lead_time) + sim_safety_stock))
        sim_reorder_qty = max(product.min_stock_level * 2, sim_rp)

        sim_lead_demand = sim_demand_daily * sim_lead_time
        sim_stockout_risk = round(min(100.0, max(0.0, ((sim_lead_demand - current_stock) / (sim_lead_demand + 1.0)) * 100.0)), 1)

        # Financial impact difference
        base_fin = base_reorder_qty * base_cost
        sim_fin = sim_reorder_qty * sim_cost
        fin_diff = round(sim_fin - base_fin, 2)

        # Impact Score calculation (Feature 5 integration)
        impact = ImpactScoreService.calculate_impact_score(
            stockout_risk=sim_stockout_risk,
            financial_exposure=abs(fin_diff) if fin_diff != 0 else sim_fin,
            demand_volatility=round(sim_sigma / sim_demand_daily, 2),
            lead_time_days=sim_lead_time,
            supplier_reliability_pct=sim_reliability,
            context_type="REORDER"
        )

        insights: List[str] = []
        if req.demand_change_pct > 0:
            insights.append(f"A {req.demand_change_pct}% demand surge elevates daily consumption to {round(sim_demand_daily, 1)} {product.uom}/day.")
        if req.lead_time_change_days > 0:
            insights.append(f"Adding {req.lead_time_change_days} days to supplier lead time expands required safety stock buffer from {base_safety_stock} to {sim_safety_stock} units.")
        if sim_stockout_risk > base_stockout_risk:
            insights.append(f"Stockout risk jumps by +{round(sim_stockout_risk - base_stockout_risk, 1)}% under simulated constraints.")
        if fin_diff > 0:
            insights.append(f"Estimated procurement budget increases by ₹{fin_diff:,.2f}.")
        else:
            insights.append("Capital requirement remains stable under tested variations.")

        return WhatIfSimulationResponse(
            product_id=product.id,
            product_name=product.name,
            baseline_stockout_risk_pct=base_stockout_risk,
            simulated_stockout_risk_pct=sim_stockout_risk,
            baseline_safety_stock=base_safety_stock,
            simulated_safety_stock=sim_safety_stock,
            baseline_reorder_qty=base_reorder_qty,
            simulated_reorder_qty=sim_reorder_qty,
            financial_impact_difference=fin_diff,
            impact_score=impact.overall_score,
            impact_level=impact.impact_level,
            insights=insights
        )
