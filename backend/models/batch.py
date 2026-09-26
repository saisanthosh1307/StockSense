import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.database import Base

class BatchStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RECALLED = "RECALLED"
    DEPLETED = "DEPLETED"

class InventoryBatch(Base):
    __tablename__ = "inventory_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(100), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    
    initial_quantity = Column(Integer, default=0, nullable=False)
    current_quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    
    manufacturing_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=False, index=True)
    cost_per_unit = Column(Float, default=0.0)
    
    status = Column(Enum(BatchStatus), default=BatchStatus.ACTIVE, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("batch_number", "product_id", "warehouse_id", "location_id", name="uix_batch_prod_wh_loc"),
    )

    product = relationship("Product", back_populates="batches")
    warehouse = relationship("Warehouse")
    location = relationship("Location")
