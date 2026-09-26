from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.models.inventory import LocationType

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    sku: str
    category_id: Optional[int] = None
    uom: str = "Units"
    barcode: Optional[str] = None
    description: Optional[str] = None
    unit_cost: float = 0.0
    unit_price: float = 0.0
    min_reorder_qty: float = 10.0
    max_reorder_qty: float = 100.0
    lead_time_days: int = 7

class ProductCreate(ProductBase):
    initial_stock: Optional[float] = 0.0
    initial_location_id: Optional[int] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    uom: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    unit_cost: Optional[float] = None
    unit_price: Optional[float] = None
    min_reorder_qty: Optional[float] = None
    max_reorder_qty: Optional[float] = None
    lead_time_days: Optional[int] = None

class LocationBase(BaseModel):
    name: str
    code: str
    warehouse_id: Optional[int] = None
    location_type: LocationType = LocationType.INTERNAL
    zone: Optional[str] = None
    aisle: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    max_capacity: float = 1000.0

class LocationCreate(LocationBase):
    pass

class LocationOut(LocationBase):
    id: int

    class Config:
        from_attributes = True

class WarehouseBase(BaseModel):
    code: str
    name: str
    address: Optional[str] = None
    is_active: int = 1

class WarehouseCreate(WarehouseBase):
    pass

class WarehouseOut(WarehouseBase):
    id: int
    locations: List[LocationOut] = []

    class Config:
        from_attributes = True

class StockQuantOut(BaseModel):
    id: int
    product_id: int
    location_id: int
    quantity: float
    reserved_quantity: float
    location_name: Optional[str] = None
    location_code: Optional[str] = None

    class Config:
        from_attributes = True

class ProductOut(ProductBase):
    id: int
    created_at: datetime
    total_on_hand: float = 0.0
    category: Optional[CategoryOut] = None
    locations_stock: List[StockQuantOut] = []

    class Config:
        from_attributes = True
