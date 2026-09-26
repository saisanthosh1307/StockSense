import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class DeadStockClassification(str, enum.Enum):
    NORMAL = "Normal"
    SLOW_MOVING = "Slow Moving"
    EXCESS_STOCK = "Excess Stock"
    DEAD_STOCK = "Dead Stock"

class DeadStockRecommendedAction(str, enum.Enum):
    TRANSFER = "Transfer to another warehouse"
    REDUCE_REORDER = "Reduce reorder quantity"
    STOP_PURCHASING = "Stop/reduce future purchasing"
    RETURN_TO_SUPPLIER = "Return to supplier"
    PROMOTE_CLEAR = "Promote/clear inventory"
    REDISTRIBUTE_HIGH_DEMAND = "Redistribute to high-demand warehouse"

class RouteStatus(str, enum.Enum):
    GENERATED = "GENERATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class ImpactLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class DeadStockAnalysis(Base):
    __tablename__ = "dead_stock_analyses"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    
    current_stock = Column(Integer, default=0, nullable=False)
    stock_value = Column(Float, default=0.0, nullable=False)
    days_inactive = Column(Integer, default=0, nullable=False)
    last_movement_date = Column(DateTime, nullable=True)
    average_monthly_demand = Column(Float, default=0.0)
    inventory_age_days = Column(Integer, default=0)
    
    dead_stock_score = Column(Float, default=0.0)  # 0 to 100
    classification = Column(Enum(DeadStockClassification), default=DeadStockClassification.NORMAL, nullable=False)
    recommended_action = Column(Enum(DeadStockRecommendedAction), nullable=True)
    action_rationale = Column(Text, nullable=True)
    target_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    
    is_actioned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    target_warehouse = relationship("Warehouse", foreign_keys=[target_warehouse_id])


class PickingRoute(Base):
    __tablename__ = "picking_routes"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), unique=True, nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    
    route_json = Column(Text, nullable=False)  # JSON ordered list of steps / locations
    total_locations = Column(Integer, default=0)
    estimated_distance_meters = Column(Float, default=0.0)
    estimated_time_minutes = Column(Float, default=0.0)
    original_distance_meters = Column(Float, default=0.0)
    time_saved_minutes = Column(Float, default=0.0)
    
    status = Column(Enum(RouteStatus), default=RouteStatus.GENERATED, nullable=False)
    completed_picks_json = Column(Text, default="[]")  # JSON list of confirmed pick step ids
    created_at = Column(DateTime, default=datetime.utcnow)

    delivery = relationship("Delivery", back_populates="picking_route")
    warehouse = relationship("Warehouse")


class ImpactEvaluation(Base):
    __tablename__ = "impact_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    decision_type = Column(String(50), nullable=False, index=True)  # REORDER, DEAD_STOCK, ANOMALY, EXPIRY, WHAT_IF
    entity_id = Column(String(50), nullable=False, index=True)  # Product SKU or ID, etc.
    entity_name = Column(String(150), nullable=False)
    
    impact_score = Column(Float, default=0.0, nullable=False)  # 0 to 100
    impact_level = Column(Enum(ImpactLevel), default=ImpactLevel.MEDIUM, nullable=False)
    
    # Mathematical factor breakdown
    stockout_risk_score = Column(Float, default=0.0)       # 0 - 100
    financial_exposure_score = Column(Float, default=0.0)   # 0 - 100
    demand_volatility_score = Column(Float, default=0.0)    # 0 - 100
    lead_time_score = Column(Float, default=0.0)            # 0 - 100
    supplier_reliability_score = Column(Float, default=0.0) # 0 - 100
    
    reasons_json = Column(Text, nullable=False)  # JSON array of string reasons
    calculated_at = Column(DateTime, default=datetime.utcnow, index=True)
