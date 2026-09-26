import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class TransactionType(str, enum.Enum):
    RECEIPT = "RECEIPT"
    DELIVERY = "DELIVERY"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    ADJUSTMENT_INCREASE = "ADJUSTMENT_INCREASE"
    ADJUSTMENT_DECREASE = "ADJUSTMENT_DECREASE"
    SCRAP = "SCRAP"

class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id = Column(Integer, primary_key=True, index=True)
    entry_uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    
    change_qty = Column(Integer, nullable=False)  # positive for addition, negative for deduction
    balance_after = Column(Integer, nullable=False)
    
    transaction_type = Column(Enum(TransactionType), nullable=False, index=True)
    reference_type = Column(String(50), nullable=True)  # RECEIPT, DELIVERY, TRANSFER, ADJUSTMENT
    reference_id = Column(String(100), nullable=True, index=True)
    batch_number = Column(String(100), nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    product = relationship("Product")
    warehouse = relationship("Warehouse")
    location = relationship("Location")
    user = relationship("User")


class TrustChainBlock(Base):
    __tablename__ = "trust_chain_blocks"

    id = Column(Integer, primary_key=True, index=True)
    block_index = Column(Integer, unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    previous_hash = Column(String(64), nullable=False)
    block_hash = Column(String(64), unique=True, nullable=False, index=True)
    merkle_root = Column(String(64), nullable=False)
    
    transaction_count = Column(Integer, default=1)
    payload_summary = Column(Text, nullable=False)  # JSON summary of included transactions
    nonce = Column(Integer, default=0)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # CREATE, UPDATE, DELETE, VALIDATE, PICK
    entity_name = Column(String(100), nullable=False, index=True)  # Product, Receipt, Delivery, etc.
    entity_id = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)  # JSON or human readable diff
    ip_address = Column(String(50), nullable=True)

    user = relationship("User")
