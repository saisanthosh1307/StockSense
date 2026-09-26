from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.intelligence import (
    ForecastRequest, ForecastResponse, ReorderRecommendation,
    AnomalyItem, CauseOfLossItem, WhatIfSimulationRequest, WhatIfSimulationResponse,
    ImpactScoreDetail
)
from backend.services.forecasting_service import ForecastingService
from backend.services.reorder_service import ReorderService
from backend.services.anomaly_service import AnomalyService
from backend.services.whatif_service import WhatIfService
from backend.services.impact_score_service import ImpactScoreService

router = APIRouter(prefix="/intelligence", tags=["AI Intelligence Engine"])

@router.post("/forecast", response_model=ForecastResponse)
def get_demand_forecast(req: ForecastRequest, db: Session = Depends(get_db)):
    try:
        return ForecastingService.generate_demand_forecast(
            db, req.product_id, req.days_ahead, req.warehouse_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/reorder", response_model=List[ReorderRecommendation])
def get_reorder_recommendations(warehouse_id: Optional[int] = None, db: Session = Depends(get_db)):
    return ReorderService.get_reorder_recommendations(db, warehouse_id)

@router.get("/anomalies", response_model=List[AnomalyItem])
def get_anomalies(db: Session = Depends(get_db)):
    return AnomalyService.detect_anomalies(db)

@router.get("/cause-of-loss", response_model=List[CauseOfLossItem])
def get_cause_of_loss(db: Session = Depends(get_db)):
    return AnomalyService.get_cause_of_loss_analysis(db)

@router.post("/what-if", response_model=WhatIfSimulationResponse)
def run_what_if_simulation(req: WhatIfSimulationRequest, db: Session = Depends(get_db)):
    try:
        return WhatIfService.run_simulation(db, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/impact", response_model=ImpactScoreDetail)
def compute_impact_score(
    stockout_risk: float = Query(50.0, ge=0.0, le=100.0),
    financial_exposure: float = Query(25000.0, ge=0.0),
    demand_volatility: float = Query(0.3, ge=0.0),
    lead_time_days: float = Query(7.0, ge=0.0),
    supplier_reliability_pct: float = Query(95.0, ge=0.0, le=100.0),
    context_type: str = Query("REORDER")
):
    """
    Direct endpoint for calculating real-data Impact Score (0 - 100) with explainable reasons.
    """
    return ImpactScoreService.calculate_impact_score(
        stockout_risk=stockout_risk,
        financial_exposure=financial_exposure,
        demand_volatility=demand_volatility,
        lead_time_days=lead_time_days,
        supplier_reliability_pct=supplier_reliability_pct,
        context_type=context_type
    )
