from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from backend.models.intelligence import DeadStockClassification, DeadStockRecommendedAction, RouteStatus, ImpactLevel
from backend.models.batch import BatchStatus

# --- 1. Dead-Stock Rescue ---
class DeadStockRescueItem(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str
    warehouse_id: int
    warehouse_name: str
    current_stock: int
    stock_value: float
    days_inactive: int
    last_movement_date: Optional[datetime] = None
    average_monthly_demand: float
    inventory_age_days: int
    dead_stock_score: float  # 0 to 100
    classification: DeadStockClassification
    recommended_action: Optional[DeadStockRecommendedAction] = None
    action_rationale: Optional[str] = None
    target_warehouse_id: Optional[int] = None
    target_warehouse_name: Optional[str] = None
    impact_score: float
    impact_level: ImpactLevel
    is_actioned: bool = False

class DeadStockSummary(BaseModel):
    total_dead_stock_value: float
    total_dead_stock_products_count: int
    total_excess_stock_value: float
    total_slow_moving_count: int
    warehouse_breakdown: List[Dict[str, Any]]
    items: List[DeadStockRescueItem]

class DeadStockActionConfirmRequest(BaseModel):
    analysis_id: int
    action: DeadStockRecommendedAction
    target_warehouse_id: Optional[int] = None
    target_location_id: Optional[int] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None


# --- 2. Supplier Intelligence ---
class SupplierMetricResponse(BaseModel):
    supplier_id: int
    supplier_name: str
    supplier_code: str
    total_orders: int
    completed_orders: int
    on_time_delivery_pct: float
    average_lead_time_days: float
    expected_avg_lead_time_days: float
    lead_time_variance_days: float
    quantity_accuracy_pct: float
    damage_rate_pct: float
    purchase_frequency_monthly: float
    reliability_score: float  # 0 to 100
    rating: float
    historical_trend: str  # IMPROVING, STABLE, DECLINING
    performance_summary: str

class SupplierComparisonResponse(BaseModel):
    average_network_reliability: float
    average_network_lead_time: float
    average_network_accuracy: float
    average_network_damage_rate: float
    suppliers: List[SupplierMetricResponse]


# --- 3. Expiry / FEFO Management ---
class InventoryBatchCreate(BaseModel):
    batch_number: str
    product_id: int
    warehouse_id: int
    location_id: int
    initial_quantity: int
    manufacturing_date: Optional[datetime] = None
    expiry_date: datetime
    cost_per_unit: float = 0.0

class InventoryBatchResponse(BaseModel):
    id: int
    batch_number: str
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    warehouse_id: int
    warehouse_name: Optional[str] = None
    location_id: int
    location_code: Optional[str] = None
    initial_quantity: int
    current_quantity: int
    reserved_quantity: int
    available_quantity: int = 0
    manufacturing_date: Optional[datetime] = None
    expiry_date: datetime
    days_to_expiry: int
    cost_per_unit: float
    total_value: float
    status: BatchStatus
    is_expired: bool
    is_expiring_soon: bool  # within 30 days
    is_critical: bool       # within 7 days

    class Config:
        from_attributes = True

class FefoPickStep(BaseModel):
    step_number: int
    batch_id: int
    batch_number: str
    product_id: int
    product_name: str
    location_id: int
    location_code: str
    warehouse_id: int
    expiry_date: datetime
    days_to_expiry: int
    available_in_batch: int
    recommended_pick_qty: int

class FefoPickPlanResponse(BaseModel):
    product_id: int
    product_name: str
    requested_quantity: int
    fulfilled_quantity: int
    shortage_quantity: int
    picking_steps: List[FefoPickStep]
    fefo_explanation: str

class ExpiryAlertGroup(BaseModel):
    expired_count: int
    expired_value: float
    expiring_7_days_count: int
    expiring_7_days_value: float
    expiring_30_days_count: int
    expiring_30_days_value: float
    batches: List[InventoryBatchResponse]


# --- 4. Smart Picking Route ---
class RouteStep(BaseModel):
    step_order: int
    location_id: int
    location_code: str
    aisle: Optional[str] = None
    rack: Optional[str] = None
    x_coord: float
    y_coord: float
    z_coord: float
    product_id: int
    product_name: str
    product_sku: str
    batch_number: Optional[str] = None
    pick_quantity: int
    is_confirmed: bool = False

class PickingRouteResponse(BaseModel):
    route_id: int
    delivery_id: int
    delivery_number: str
    warehouse_id: int
    warehouse_name: str
    status: RouteStatus
    total_locations: int
    estimated_distance_meters: float
    estimated_time_minutes: float
    original_distance_meters: float
    time_saved_minutes: float
    efficiency_gain_pct: float
    steps: List[RouteStep]
    packing_area_location: str = "Packing Station 1 (X: 25.0, Y: 2.0)"

class RoutePickConfirmRequest(BaseModel):
    step_order: int
    picked_quantity: int
    worker_notes: Optional[str] = None
