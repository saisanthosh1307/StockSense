from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

# 1. Digital Twin Schemas
class RackSlot(BaseModel):
    location_id: int
    name: str
    code: str
    zone: str
    aisle: str
    rack: str
    shelf: str
    capacity_total: float
    capacity_used: float
    utilization_pct: float
    products_stored: List[Dict[str, Any]]
    status: str # 'OPTIMAL', 'NEAR_FULL', 'EMPTY'

class DigitalTwinWarehouseResponse(BaseModel):
    warehouse_id: int
    warehouse_name: str
    warehouse_code: str
    total_locations: int
    overall_capacity_utilization_pct: float
    total_items_stored: float
    zones: List[str]
    slots: List[RackSlot]
    heatmap_matrix: List[Dict[str, Any]] # 2D/3D coordinate heat values

# 2. Trust Chain Schemas
class TrustChainBlockOut(BaseModel):
    id: int
    block_index: int
    timestamp: datetime
    previous_hash: str
    merkle_root: str
    block_hash: str
    move_count: int
    nonce: int

    class Config:
        from_attributes = True

class TrustChainVerifyResponse(BaseModel):
    is_valid: bool
    total_blocks_checked: int
    total_moves_secured: int
    latest_block_hash: str
    verification_status: str # 'INTEGRITY_VERIFIED' or 'CORRUPTED_TAMPER_DETECTED'
    tampered_block_index: Optional[int] = None
    verification_timestamp: datetime
    audit_notes: str

# 3. AI Assistant Schemas
class AIAssistantMessage(BaseModel):
    role: str # 'user' or 'assistant'
    content: str

class AIAssistantRequest(BaseModel):
    message: str
    context_filters: Optional[Dict[str, Any]] = None

class AIAssistantResponse(BaseModel):
    response_text: str
    intent_detected: str # 'QUERY_STOCK', 'FORECAST_DEMAND', 'STOCKOUT_RISK', 'ADVICE', 'GENERAL'
    data_payload: Optional[Dict[str, Any]] = None
    suggested_actions: List[str]
    confidence: float
