from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    contact_name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    expected_lead_time_days = Column(Float, default=7.0)
    rating = Column(Float, default=5.0)  # 1.0 to 5.0
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="supplier")
    receipts = relationship("Receipt", back_populates="supplier")
    metrics = relationship("SupplierMetric", back_populates="supplier", cascade="all, delete-orphan")


class SupplierMetric(Base):
    __tablename__ = "supplier_metrics"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    total_orders = Column(Integer, default=0)
    completed_orders = Column(Integer, default=0)
    on_time_orders = Column(Integer, default=0)
    delayed_orders = Column(Integer, default=0)
    
    total_ordered_qty = Column(Float, default=0.0)
    total_received_qty = Column(Float, default=0.0)
    total_damaged_qty = Column(Float, default=0.0)
    
    average_lead_time_days = Column(Float, default=0.0)
    expected_avg_lead_time_days = Column(Float, default=7.0)
    
    on_time_delivery_pct = Column(Float, default=100.0)
    quantity_accuracy_pct = Column(Float, default=100.0)
    damage_rate_pct = Column(Float, default=0.0)
    reliability_score = Column(Float, default=100.0)  # 0 to 100
    
    calculated_at = Column(DateTime, default=datetime.utcnow)

    supplier = relationship("Supplier", back_populates="metrics")
