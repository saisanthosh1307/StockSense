from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import Product
from app.schemas.intelligence import (
    ForecastResponse,
    ReorderRecommendation,
    ExplainabilityResponse,
    ConfidenceResponse,
    AnomalyRecord,
    CauseOfLossResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from app.services.intelligence_service import (
    generate_demand_forecast,
    calculate_dynamic_reorder,
    generate_reorder_explainability,
    calculate_model_confidence,
    detect_inventory_anomalies,
    analyze_cause_of_loss,
    run_what_if_simulation,
)

router = APIRouter(prefix="/intelligence", tags=["Intelligent Engine (7 Features)"])

# 1. Forecasting
@router.get("/forecast/{product_id}", response_model=ForecastResponse)
def get_demand_forecast(
    product_id: int,
    horizon_days: int = Query(14, ge=3, le=60),
    db: Session = Depends(get_db)
):
    """
    1. Demand Forecasting: Double Exponential Smoothing with Holt's linear trend & 95% Confidence Intervals.
    """
    try:
        return generate_demand_forecast(db, product_id, horizon_days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# 2. Dynamic Reorder
@router.get("/reorder/{product_id}", response_model=ReorderRecommendation)
def get_reorder_recommendation(product_id: int, db: Session = Depends(get_db)):
    """
    2. Dynamic Reorder: Reorder Point (ROP = (D x L) + SS) and Economic Order Quantity (EOQ).
    """
    try:
        return calculate_dynamic_reorder(db, product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# 3. Explainability
@router.get("/explainability/{product_id}", response_model=ExplainabilityResponse)
def get_explainability(product_id: int, db: Session = Depends(get_db)):
    """
    3. Explainability (XAI): Transparent breakdown of parameters, variances, and algorithmic triggers.
    """
    try:
        return generate_reorder_explainability(db, product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# 4. Confidence Score
@router.get("/confidence/{product_id}", response_model=ConfidenceResponse)
def get_confidence_score(product_id: int, db: Session = Depends(get_db)):
    """
    4. Confidence Score: Statistical reliability rating based on demand dispersion (CV), MAPE, and sample size.
    """
    try:
        return calculate_model_confidence(db, product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# 5. Anomaly Detection
@router.get("/anomalies", response_model=List[AnomalyRecord])
def get_anomalies(db: Session = Depends(get_db)):
    """
    5. Anomaly Detection: Statistical Z-Score and shrinkage outlier detection across stock moves and counts.
    """
    return detect_inventory_anomalies(db)

# 6. Cause-of-Loss Analytics
@router.get("/cause-of-loss", response_model=CauseOfLossResponse)
def get_cause_of_loss(db: Session = Depends(get_db)):
    """
    6. Cause-of-Loss: Categorization of write-offs (Damage, Spoilage, Theft, Transit) with mitigation advice.
    """
    return analyze_cause_of_loss(db)

# 7. What-if Simulator
@router.post("/what-if", response_model=WhatIfResponse)
def simulate_what_if_scenario(payload: WhatIfRequest, db: Session = Depends(get_db)):
    """
    7. What-if Simulator: Dynamic stress-testing for demand surges, supplier lead time delays, and risk buffers.
    """
    try:
        return run_what_if_simulation(
            db=db,
            product_id=payload.product_id,
            demand_surge_pct=payload.demand_surge_pct,
            supplier_delay_days=payload.supplier_delay_days,
            holding_cost_increase_pct=payload.holding_cost_increase_pct,
            simulation_days=payload.simulation_days
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
