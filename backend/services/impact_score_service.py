import math
from typing import Dict, Any, List, Tuple
from backend.models.intelligence import ImpactLevel
from backend.schemas.intelligence import ImpactScoreDetail

class ImpactScoreService:
    @staticmethod
    def calculate_impact_score(
        stockout_risk: float,          # 0 to 100
        financial_exposure: float,     # absolute amount in rupees
        demand_volatility: float,      # 0 to 1 (coefficient of variation) or 0 to 100
        lead_time_days: float,         # days
        supplier_reliability_pct: float, # 0 to 100%
        context_type: str = "REORDER"  # REORDER, DEAD_STOCK, ANOMALY, EXPIRY, WHAT_IF
    ) -> ImpactScoreDetail:
        # 1. Normalize Financial Exposure (0 - 100)
        # ₹1,50,000 is considered top enterprise tier (100 pts)
        fin_score = min(100.0, max(0.0, (financial_exposure / 150000.0) * 100.0))
        
        # 2. Normalize Demand Volatility (0 - 100)
        vol_score = demand_volatility if demand_volatility > 1.0 else (demand_volatility * 100.0)
        vol_score = min(100.0, max(0.0, vol_score))
        
        # 3. Normalize Lead Time Risk (0 - 100)
        # 14 days or more represents maximum lead time criticality
        lead_score = min(100.0, max(0.0, (lead_time_days / 14.0) * 100.0))
        
        # 4. Supplier Reliability Risk (0 - 100)
        supp_risk = max(0.0, min(100.0, 100.0 - supplier_reliability_pct))
        
        # 5. Stockout Risk (0 - 100)
        stock_risk = max(0.0, min(100.0, stockout_risk))

        reasons: List[str] = []

        # Weighted calculation by context
        if context_type == "REORDER":
            overall = (
                (stock_risk * 0.35) +
                (fin_score * 0.25) +
                (lead_score * 0.15) +
                (supp_risk * 0.15) +
                (vol_score * 0.10)
            )
            if stock_risk >= 70:
                reasons.append(f"High stockout risk ({round(stock_risk, 1)}%) threatens production continuity")
            elif stock_risk >= 40:
                reasons.append(f"Moderate stockout exposure ({round(stock_risk, 1)}%) detected")

            if fin_score >= 60:
                reasons.append(f"Significant financial commitment of ₹{financial_exposure:,.2f}")
            
            if lead_time_days >= 7:
                reasons.append(f"Supplier lead time is substantial ({lead_time_days:.1f} days)")
                
            if supplier_reliability_pct < 85:
                reasons.append(f"Supplier reliability is degraded ({supplier_reliability_pct:.1f}%)")

        elif context_type == "DEAD_STOCK":
            # For dead stock, financial holding cost and days idle dominate
            overall = (
                (fin_score * 0.45) +
                (vol_score * 0.20) +
                (supp_risk * 0.10) +
                (min(100.0, (lead_time_days / 30.0) * 100.0) * 0.25)
            )
            if fin_score >= 50:
                reasons.append(f"High capital lockup of ₹{financial_exposure:,.2f} with zero velocity")
            reasons.append("Holding excessive idle inventory impairs warehouse storage density")
            if vol_score < 20:
                reasons.append("Demand has stagnated near zero for over 60 days")

        elif context_type == "ANOMALY":
            overall = (
                (stock_risk * 0.40) +
                (fin_score * 0.35) +
                (vol_score * 0.25)
            )
            reasons.append("Abrupt statistical deviation exceeds 2.5 sigma threshold")
            if fin_score >= 40:
                reasons.append(f"Potential inventory shrinkage valuation of ₹{financial_exposure:,.2f}")
        else:
            overall = (stock_risk * 0.3) + (fin_score * 0.3) + (lead_score * 0.2) + (supp_risk * 0.2)
            reasons.append("Cross-functional inventory risk profile evaluated")

        overall_clamped = round(min(100.0, max(5.0, overall)), 1)

        # Classification
        if overall_clamped >= 80:
            level = ImpactLevel.CRITICAL
        elif overall_clamped >= 65:
            level = ImpactLevel.HIGH
        elif overall_clamped >= 40:
            level = ImpactLevel.MEDIUM
        else:
            level = ImpactLevel.LOW

        if not reasons:
            reasons.append("Standard operational parameters within safe tolerance bounds")

        return ImpactScoreDetail(
            overall_score=overall_clamped,
            impact_level=level,
            stockout_risk_score=round(stock_risk, 1),
            financial_exposure_score=round(fin_score, 1),
            demand_volatility_score=round(vol_score, 1),
            lead_time_score=round(lead_score, 1),
            supplier_reliability_score=round(supp_risk, 1),
            reasons=reasons,
            metrics_summary={
                "financial_exposure_inr": financial_exposure,
                "lead_time_days": lead_time_days,
                "supplier_reliability_pct": supplier_reliability_pct
            }
        )
