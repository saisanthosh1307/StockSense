import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from app.database import Base

class DocStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    WAITING = "WAITING"
    READY = "READY"
    DONE = "DONE"
    CANCELED = "CANCELED"

class LossCauseEnum(str, enum.Enum):
    DAMAGE_HANDLING = "DAMAGE_HANDLING"
    SPOILAGE_EXPIRY = "SPOILAGE_EXPIRY"
    SHRINKAGE_THEFT = "SHRINKAGE_THEFT"
    VENDOR_DEFECT = "VENDOR_DEFECT"
    TRANSIT_LOSS = "TRANSIT_LOSS"
    COUNT_MISMATCH = "COUNT_MISMATCH"
    OTHER = "OTHER"

# 1. Receipts (Incoming Stock)
class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(50), unique=True, index=True, nullable=False) # e.g. REC/2026/0001
    supplier_name = Column(String(150), nullable=False)
    destination_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    status = Column(Enum(DocStatus), default=DocStatus.DRAFT, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)

    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    lines = relationship("ReceiptLine", back_populates="receipt", cascade="all, delete-orphan")

class ReceiptLine(Base):
    __tablename__ = "receipt_lines"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_expected = Column(Float, default=0.0, nullable=False)
    quantity_received = Column(Float, default=0.0, nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)

    receipt = relationship("Receipt", back_populates="lines")
    product = relationship("Product")

# 2. Deliveries (Outgoing Goods)
class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(50), unique=True, index=True, nullable=False) # e.g. DEL/2026/0001
    customer_name = Column(String(150), nullable=False)
    source_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    status = Column(Enum(DocStatus), default=DocStatus.DRAFT, nullable=False)
    is_picked = Column(Integer, default=0, nullable=False)
    is_packed = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)

    source_location = relationship("Location", foreign_keys=[source_location_id])
    lines = relationship("DeliveryLine", back_populates="delivery", cascade="all, delete-orphan")

class DeliveryLine(Base):
    __tablename__ = "delivery_lines"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_demanded = Column(Float, default=0.0, nullable=False)
    quantity_done = Column(Float, default=0.0, nullable=False)

    delivery = relationship("Delivery", back_populates="lines")
    product = relationship("Product")

# 3. Internal Transfers
class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(50), unique=True, index=True, nullable=False) # e.g. INT/2026/0001
    source_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    destination_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    status = Column(Enum(DocStatus), default=DocStatus.DRAFT, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)

    source_location = relationship("Location", foreign_keys=[source_location_id])
    destination_location = relationship("Location", foreign_keys=[destination_location_id])
    lines = relationship("TransferLine", back_populates="transfer", cascade="all, delete-orphan")

class TransferLine(Base):
    __tablename__ = "transfer_lines"

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(Integer, ForeignKey("transfers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, default=0.0, nullable=False)

    transfer = relationship("Transfer", back_populates="lines")
    product = relationship("Product")

# 4. Stock Adjustments (Physical count reconciliation)
class Adjustment(Base):
    __tablename__ = "adjustments"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(50), unique=True, index=True, nullable=False) # e.g. ADJ/2026/0001
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    status = Column(Enum(DocStatus), default=DocStatus.DRAFT, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime, nullable=True)

    location = relationship("Location", foreign_keys=[location_id])
    lines = relationship("AdjustmentLine", back_populates="adjustment", cascade="all, delete-orphan")

class AdjustmentLine(Base):
    __tablename__ = "adjustment_lines"

    id = Column(Integer, primary_key=True, index=True)
    adjustment_id = Column(Integer, ForeignKey("adjustments.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    recorded_qty = Column(Float, default=0.0, nullable=False)
    counted_qty = Column(Float, default=0.0, nullable=False)
    difference_qty = Column(Float, default=0.0, nullable=False) # counted - recorded
    loss_cause = Column(Enum(LossCauseEnum), default=LossCauseEnum.COUNT_MISMATCH, nullable=False)

    adjustment = relationship("Adjustment", back_populates="lines")
    product = relationship("Product")
