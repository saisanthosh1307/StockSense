from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from backend.models.intelligence import ImpactLevel

class ForecastRequest(BaseModel):
    product_id: int
    days_ahead: int = 30
    warehouse_id: Optional[int] = None

class ForecastPoint(BaseModel):
    date: str
    projected_demand: float
    confidence_lower: float
    confidence_upper: float

class ForecastResponse(BaseModel):
    product_id: int
    product_name: str
    sku: str
    projected_monthly_demand: float
    trend: str  # INCREASING, DECREASING, STABLE
    confidence_score: float  # 0 to 100%
    impact_score: float     # Feature 5 integration
    impact_level: ImpactLevel
    daily_forecasts: List[ForecastPoint]
    explainability: List[str]


class ReorderRecommendation(BaseModel):
    product_id: int
    sku: str
    product_name: str
    current_stock: int
    min_stock_level: int
    reorder_point: int
    safety_stock: int
    recommended_order_qty: int
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    supplier_lead_time_days: float = 7.0
    supplier_reliability_pct: float = 100.0
    confidence_score: float  # e.g. 94%
    impact_score: float      # Feature 5 integration (e.g. 87/100)
    impact_level: ImpactLevel
    impact_reasons: List[str]
    estimated_cost: float
    urgency: str  # CRITICAL, HIGH, MEDIUM, LOW


class AnomalyItem(BaseModel):
    id: str
    product_id: int
    product_name: str
    sku: str
    warehouse_name: str
    anomaly_type: str  # SUDDEN_SPIKE, SUDDEN_DROP, UNUSUAL_SHRINKAGE, DRAIN
    severity: str      # CRITICAL, HIGH, MEDIUM
    detected_value: float
    expected_value: float
    z_score: float
    impact_score: float  # Feature 5 integration
    impact_level: ImpactLevel
    detected_at: datetime
    explanation: str
    recommended_action: str


class CauseOfLossItem(BaseModel):
    reason: str
    total_quantity_lost: int
    total_value_lost: float
    percentage_of_total_loss: float
    top_affected_product: str
    impact_score: float
    mitigation_strategy: str


class WhatIfSimulationRequest(BaseModel):
    product_id: int
    demand_change_pct: float = 0.0      # e.g. +25%
    lead_time_change_days: float = 0.0  # e.g. +5 days
    supplier_reliability_pct: Optional[float] = None
    cost_price_change_pct: float = 0.0

class WhatIfSimulationResponse(BaseModel):
    product_id: int
    product_name: str
    baseline_stockout_risk_pct: float
    simulated_stockout_risk_pct: float
    baseline_safety_stock: int
    simulated_safety_stock: int
    baseline_reorder_qty: int
    simulated_reorder_qty: int
    financial_impact_difference: float
    impact_score: float  # Feature 5 integration
    impact_level: ImpactLevel
    insights: List[str]


class ImpactScoreDetail(BaseModel):
    overall_score: float  # 0 to 100
    impact_level: ImpactLevel
    stockout_risk_score: float
    financial_exposure_score: float
    demand_volatility_score: float
    lead_time_score: float
    supplier_reliability_score: float
    reasons: List[str]
    metrics_summary: Dict[str, Any]
