from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ForecastDataPoint(BaseModel):
    date: str
    historical_demand: Optional[float] = None
    forecasted_demand: Optional[float] = None
    lower_bound_95: Optional[float] = None
    upper_bound_95: Optional[float] = None

class ForecastResponse(BaseModel):
    product_id: int
    product_name: str
    sku: str
    horizon_days: int
    algorithm_used: str
    total_forecasted_demand: float
    daily_average_demand: float
    data: List[ForecastDataPoint]

class ReorderRecommendation(BaseModel):
    product_id: int
    product_name: str
    sku: str
    current_on_hand: float
    safety_stock: float
    lead_time_days: int
    lead_time_demand: float
    reorder_point: float
    reorder_triggered: bool
    recommended_order_qty: float
    economic_order_qty_eoq: float
    urgency_level: str # 'NORMAL', 'WARNING', 'CRITICAL'

class ExplainabilityResponse(BaseModel):
    product_id: int
    product_name: str
    title: str
    executive_summary: str
    factors_breakdown: List[Dict[str, Any]]
    formula_derivation: str
    actionable_recommendations: List[str]

class ConfidenceMetric(BaseModel):
    metric_name: str
    value: float
    interpretation: str

class ConfidenceResponse(BaseModel):
    product_id: int
    product_name: str
    confidence_score: float # 0 - 100%
    confidence_tier: str    # 'VERY_HIGH', 'HIGH', 'MODERATE', 'LOW'
    metrics: List[ConfidenceMetric]
    margin_of_error_pct: float
    sample_size_days: int

class AnomalyRecord(BaseModel):
    id: str
    entity_type: str
    product_id: int
    product_name: str
    anomaly_type: str # 'UNUSUAL_CONSUMPTION_SPIKE', 'ABNORMAL_STOCK_DROP', 'HIGH_FREQUENCY_ADJUSTMENT'
    severity: str     # 'LOW', 'MEDIUM', 'HIGH'
    z_score: float
    expected_value: float
    observed_value: float
    timestamp: str
    explanation: str

class CauseOfLossCategory(BaseModel):
    cause: str
    incident_count: int
    lost_units: float
    financial_impact: float
    percentage_of_total_loss: float

class CauseOfLossResponse(BaseModel):
    total_financial_loss: float
    total_units_lost: float
    top_affected_product: Optional[str] = None
    categories: List[CauseOfLossCategory]
    ai_risk_mitigation: List[str]

class WhatIfRequest(BaseModel):
    product_id: int
    demand_surge_pct: float = 25.0       # e.g., +25%
    supplier_delay_days: int = 5         # e.g., +5 days vendor delay
    holding_cost_increase_pct: float = 0.0
    simulation_days: int = 30

class WhatIfDailySimulation(BaseModel):
    day: int
    date: str
    projected_stock: float
    stockout_occurred: bool
    unmet_demand: float

class WhatIfResponse(BaseModel):
    product_id: int
    product_name: str
    scenario_description: str
    baseline_stockout_day: Optional[int] = None
    simulated_stockout_day: Optional[int] = None
    days_to_stockout: Optional[int] = None
    projected_revenue_loss: float
    recommended_emergency_buffer: float
    timeline: List[WhatIfDailySimulation]
