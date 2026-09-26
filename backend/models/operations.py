import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class OperationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    WAITING = "WAITING"
    READY = "READY"
    DONE = "DONE"
    CANCELED = "CANCELED"

class AdjustmentReason(str, enum.Enum):
    DAMAGE = "DAMAGE"
    THEFT = "THEFT"
    EXPIRY = "EXPIRY"
    RECORDING_ERROR = "RECORDING_ERROR"
    OTHER = "OTHER"

class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    status = Column(Enum(OperationStatus), default=OperationStatus.DRAFT, nullable=False, index=True)
    
    order_date = Column(DateTime, default=datetime.utcnow)
    expected_date = Column(DateTime, nullable=True)
    received_date = Column(DateTime, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="receipts")
    warehouse = relationship("Warehouse")
    created_by = relationship("User")
    items = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    
    ordered_qty = Column(Integer, default=0, nullable=False)
    received_qty = Column(Integer, default=0, nullable=False)
    damaged_qty = Column(Integer, default=0, nullable=False)
    unit_cost = Column(Float, default=0.0)
    
    batch_number = Column(String(100), nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    receipt = relationship("Receipt", back_populates="items")
    product = relationship("Product")
    location = relationship("Location")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    delivery_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_name = Column(String(150), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    status = Column(Enum(OperationStatus), default=OperationStatus.DRAFT, nullable=False, index=True)
    
    order_date = Column(DateTime, default=datetime.utcnow)
    scheduled_date = Column(DateTime, nullable=True)
    shipped_date = Column(DateTime, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    warehouse = relationship("Warehouse")
    created_by = relationship("User")
    items = relationship("DeliveryItem", back_populates="delivery", cascade="all, delete-orphan")
    picking_route = relationship("PickingRoute", back_populates="delivery", uselist=False)


class DeliveryItem(Base):
    __tablename__ = "delivery_items"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id"), nullable=True, index=True)
    
    requested_qty = Column(Integer, default=0, nullable=False)
    picked_qty = Column(Integer, default=0, nullable=False)
    packed_qty = Column(Integer, default=0, nullable=False)
    unit_price = Column(Float, default=0.0)

    delivery = relationship("Delivery", back_populates="items")
    product = relationship("Product")
    location = relationship("Location")
    batch = relationship("InventoryBatch")


class InternalTransfer(Base):
    __tablename__ = "internal_transfers"

    id = Column(Integer, primary_key=True, index=True)
    transfer_number = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id"), nullable=True)
    
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    
    quantity = Column(Integer, nullable=False)
    status = Column(Enum(OperationStatus), default=OperationStatus.DRAFT, nullable=False, index=True)
    scheduled_date = Column(DateTime, default=datetime.utcnow)
    completed_date = Column(DateTime, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product")
    batch = relationship("InventoryBatch")
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])
    created_by = relationship("User")


class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    adjustment_number = Column(String(50), unique=True, nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("inventory_batches.id"), nullable=True)
    
    recorded_qty = Column(Integer, nullable=False)
    counted_qty = Column(Integer, nullable=False)
    variance_qty = Column(Integer, nullable=False)  # counted_qty - recorded_qty
    
    reason_type = Column(Enum(AdjustmentReason), default=AdjustmentReason.OTHER, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(Enum(OperationStatus), default=OperationStatus.DRAFT, nullable=False)
    
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    warehouse = relationship("Warehouse")
    location = relationship("Location")
    product = relationship("Product")
    batch = relationship("InventoryBatch")
    approved_by = relationship("User")
