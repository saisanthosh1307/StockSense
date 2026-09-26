from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="category")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    address = Column(String(255), nullable=True)
    capacity = Column(Integer, default=10000)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    locations = relationship("Location", back_populates="warehouse", cascade="all, delete-orphan")
    stock_levels = relationship("StockLevel", back_populates="warehouse")


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)  # e.g., "Rack A1", "Rack B2"
    aisle = Column(String(20), nullable=True)
    rack = Column(String(20), nullable=True)
    shelf = Column(String(20), nullable=True)
    bin = Column(String(20), nullable=True)
    x_coord = Column(Float, default=0.0)  # Warehouse layout X in meters
    y_coord = Column(Float, default=0.0)  # Warehouse layout Y in meters
    z_coord = Column(Float, default=0.0)  # Warehouse layout Z (height) in meters
    capacity = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("warehouse_id", "code", name="uix_warehouse_location_code"),)

    warehouse = relationship("Warehouse", back_populates="locations")
    stock_levels = relationship("StockLevel", back_populates="location")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    barcode = Column(String(100), unique=True, nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    uom = Column(String(20), default="Units")  # Units, kg, Litres, Boxes, Meters
    
    # Inventory control thresholds
    min_stock_level = Column(Integer, default=10)
    max_stock_level = Column(Integer, default=500)
    reorder_point = Column(Integer, default=50)
    
    # Financial metrics
    cost_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    
    # Perishable & Expiry tracking
    is_perishable = Column(Boolean, default=False)
    shelf_life_days = Column(Integer, default=365)
    
    default_supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products", foreign_keys=[default_supplier_id])
    stock_levels = relationship("StockLevel", back_populates="product", cascade="all, delete-orphan")
    batches = relationship("InventoryBatch", back_populates="product", cascade="all, delete-orphan")


class StockLevel(Base):
    __tablename__ = "stock_levels"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", "location_id", name="uix_prod_wh_loc"),
    )

    product = relationship("Product", back_populates="stock_levels")
    warehouse = relationship("Warehouse", back_populates="stock_levels")
    location = relationship("Location", back_populates="stock_levels")
