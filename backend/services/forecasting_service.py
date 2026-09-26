import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.inventory import Product, Warehouse, StockLevel
from backend.models.ledger import StockLedger
from backend.models.intelligence import ImpactLevel
from backend.schemas.intelligence import ForecastResponse, ForecastPoint
from backend.services.impact_score_service import ImpactScoreService

class ForecastingService:
    @staticmethod
    def generate_demand_forecast(
        db: Session, product_id: int, days_ahead: int = 30, warehouse_id: Optional[int] = None
    ) -> ForecastResponse:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product #{product_id} not found")

        now = datetime.utcnow()
        ninety_days_ago = now - timedelta(days=90)

        # Pull historical outgoing transactions
        tx_query = db.query(StockLedger).filter(
            StockLedger.product_id == product.id,
            StockLedger.change_qty < 0,
            StockLedger.timestamp >= ninety_days_ago
        )
        if warehouse_id:
            tx_query = tx_query.filter(StockLedger.warehouse_id == warehouse_id)

        history = tx_query.order_by(StockLedger.timestamp.asc()).all()

        # Group by day
        daily_consumed: Dict[str, float] = {}
        for d in range(90):
            day_str = (ninety_days_ago + timedelta(days=d)).strftime("%Y-%m-%d")
            daily_consumed[day_str] = 0.0

        for tx in history:
            day_str = tx.timestamp.strftime("%Y-%m-%d")
            if day_str in daily_consumed:
                daily_consumed[day_str] += abs(tx.change_qty)

        values = list(daily_consumed.values())
        total_qty = sum(values)
        mean_daily = (total_qty / len(values)) if values else 2.0
        if mean_daily == 0:
            mean_daily = 1.0  # fallback baseline

        # Variance & std dev
        variance = sum((x - mean_daily) ** 2 for x in values) / (len(values) or 1)
        std_dev = math.sqrt(variance)
        cv = (std_dev / mean_daily) if mean_daily > 0 else 0.5

        # Linear trend analysis
        n = len(values)
        x_bar = (n - 1) / 2.0
        y_bar = mean_daily
        cov_xy = sum((i - x_bar) * (values[i] - y_bar) for i in range(n))
        var_x = sum((i - x_bar) ** 2 for i in range(n))
        slope = (cov_xy / var_x) if var_x > 0 else 0.0

        if slope > 0.02:
            trend_str = "INCREASING"
        elif slope < -0.02:
            trend_str = "DECREASING"
        else:
            trend_str = "STABLE"

        # Confidence score based on historical data consistency
        confidence = round(max(60.0, min(96.0, 95.0 - (cv * 20.0) + (min(len(history), 30) * 0.3))), 1)

        # Generate future projection points
        points: List[ForecastPoint] = []
        monthly_demand_sum = 0.0

        for day in range(1, days_ahead + 1):
            future_date = (now + timedelta(days=day)).strftime("%Y-%m-%d")
            # Trend + subtle weekly seasonality
            day_of_week = (now + timedelta(days=day)).weekday()
            seasonality = 1.15 if day_of_week in [0, 1] else (0.85 if day_of_week in [5, 6] else 1.0)
            
            projected = max(0.5, (mean_daily + (slope * (n + day))) * seasonality)
            margin = max(1.0, 1.96 * std_dev * math.sqrt(1 + (day / 60.0)))

            lower = round(max(0.0, projected - margin), 1)
            upper = round(projected + margin, 1)
            proj_val = round(projected, 1)

            points.append(ForecastPoint(
                date=future_date,
                projected_demand=proj_val,
                confidence_lower=lower,
                confidence_upper=upper
            ))
            if day <= 30:
                monthly_demand_sum += proj_val

        # Current stock
        stock_query = db.query(func.sum(StockLevel.quantity)).filter(StockLevel.product_id == product.id)
        if warehouse_id:
            stock_query = stock_query.filter(StockLevel.warehouse_id == warehouse_id)
        current_stock = stock_query.scalar() or 0

        # Feature 5: Impact Score integration
        lead_time = product.supplier.expected_lead_time_days if product.supplier else 7.0
        supp_rel = product.supplier.metrics[0].reliability_score if (product.supplier and product.supplier.metrics) else 90.0
        lead_demand = mean_daily * lead_time
        stockout_risk = round(min(100.0, max(0.0, ((lead_demand - current_stock) / (lead_demand + 1.0)) * 100.0)), 1)
        fin_exposure = round(monthly_demand_sum * product.cost_price, 2)

        impact_detail = ImpactScoreService.calculate_impact_score(
            stockout_risk=stockout_risk,
            financial_exposure=fin_exposure,
            demand_volatility=cv,
            lead_time_days=lead_time,
            supplier_reliability_pct=supp_rel,
            context_type="REORDER"
        )

        explainability = [
            f"Analyzed {len(history)} actual outgoing transactions over the past 90 days.",
            f"Demand trend is {trend_str} with an average velocity of {round(mean_daily, 1)} {product.uom}/day.",
            f"Forecast model incorporates weekly cyclicality and 95% Gaussian prediction intervals.",
            f"Impact Score of {impact_detail.overall_score}/100 reflects working capital commitment and stockout risk."
        ]

        return ForecastResponse(
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            projected_monthly_demand=round(monthly_demand_sum, 1),
            trend=trend_str,
            confidence_score=confidence,
            impact_score=impact_detail.overall_score,
            impact_level=impact_detail.impact_level,
            daily_forecasts=points,
            explainability=explainability
        )
