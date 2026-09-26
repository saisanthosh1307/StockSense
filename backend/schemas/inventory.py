from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class CategoryBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LocationBase(BaseModel):
    warehouse_id: int
    code: str
    aisle: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    bin: Optional[str] = None
    x_coord: float = 0.0
    y_coord: float = 0.0
    z_coord: float = 0.0
    capacity: int = 1000
    is_active: bool = True

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    id: int

    class Config:
        from_attributes = True


class WarehouseBase(BaseModel):
    name: str
    code: str
    address: Optional[str] = None
    capacity: int = 10000
    is_active: bool = True

class WarehouseCreate(WarehouseBase):
    pass

class WarehouseResponse(WarehouseBase):
    id: int
    created_at: Optional[datetime] = None
    locations: List[LocationResponse] = []

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    sku: str
    barcode: Optional[str] = None
    category_id: Optional[int] = None
    uom: str = "Units"
    min_stock_level: int = 10
    max_stock_level: int = 500
    reorder_point: int = 50
    cost_price: float = 0.0
    selling_price: float = 0.0
    is_perishable: bool = False
    shelf_life_days: int = 365
    default_supplier_id: Optional[int] = None

class ProductCreate(ProductBase):
    initial_stock: Optional[int] = 0
    initial_warehouse_id: Optional[int] = None
    initial_location_id: Optional[int] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    category_id: Optional[int] = None
    uom: Optional[str] = None
    min_stock_level: Optional[int] = None
    max_stock_level: Optional[int] = None
    reorder_point: Optional[int] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    is_perishable: Optional[bool] = None
    shelf_life_days: Optional[int] = None
    default_supplier_id: Optional[int] = None

class StockLevelResponse(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    location_id: int
    warehouse_name: Optional[str] = None
    location_code: Optional[str] = None
    quantity: int
    reserved_quantity: int
    available_quantity: int = 0
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProductResponse(ProductBase):
    id: int
    created_at: Optional[datetime] = None
    category_name: Optional[str] = None
    total_stock: int = 0
    available_stock: int = 0
    inventory_value: float = 0.0
    stock_levels: List[StockLevelResponse] = []

    class Config:
        from_attributes = True
