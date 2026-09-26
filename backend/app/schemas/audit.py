from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.models.audit import AlertSeverity, AlertType

class AlertOut(BaseModel):
    id: int
    title: str
    message: str
    severity: AlertSeverity
    alert_type: AlertType
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class DashboardKPIs(BaseModel):
    total_products_in_stock: int
    low_stock_items_count: int
    out_of_stock_items_count: int
    pending_receipts_count: int
    pending_deliveries_count: int
    scheduled_transfers_count: int
    total_inventory_valuation: float
    recent_activity_count: int
