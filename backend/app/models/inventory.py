import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class LocationType(str, enum.Enum):
    INTERNAL = "INTERNAL"
    VENDOR = "VENDOR"
    CUSTOMER = "CUSTOMER"
    INVENTORY_LOSS = "INVENTORY_LOSS"
    TRANSIT = "TRANSIT"

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), index=True, nullable=False)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    uom = Column(String(30), default="Units", nullable=False)  # Unit of Measure: Units, kg, m, L, Boxes
    barcode = Column(String(100), unique=True, index=True, nullable=True)
    description = Column(Text, nullable=True)
    unit_cost = Column(Float, default=0.0, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)
    
    # Reordering rules
    min_reorder_qty = Column(Float, default=10.0, nullable=False)
    max_reorder_qty = Column(Float, default=100.0, nullable=False)
    lead_time_days = Column(Integer, default=7, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    quants = relationship("StockQuant", back_populates="product", cascade="all, delete-orphan")

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    address = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1, nullable=False)
    
    locations = relationship("Location", back_populates="warehouse", cascade="all, delete-orphan")

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    location_type = Column(Enum(LocationType), default=LocationType.INTERNAL, nullable=False)
    
    # Physical Digital Twin slotting coordinates
    zone = Column(String(20), nullable=True)     # e.g., 'Zone A', 'Zone B'
    aisle = Column(String(20), nullable=True)    # e.g., 'Aisle 1', 'Aisle 2'
    rack = Column(String(20), nullable=True)     # e.g., 'Rack 01', 'Rack 02'
    shelf = Column(String(20), nullable=True)    # e.g., 'Shelf A', 'Shelf B'
    max_capacity = Column(Float, default=1000.0, nullable=False) # max units/volume
    
    warehouse = relationship("Warehouse", back_populates="locations")
    quants = relationship("StockQuant", back_populates="location", cascade="all, delete-orphan")

class StockQuant(Base):
    __tablename__ = "stock_quants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    quantity = Column(Float, default=0.0, nullable=False)
    reserved_quantity = Column(Float, default=0.0, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("product_id", "location_id", name="_product_location_uc"),)

    product = relationship("Product", back_populates="quants")
    location = relationship("Location", back_populates="quants")
