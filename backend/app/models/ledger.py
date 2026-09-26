import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class MoveType(str, enum.Enum):
    RECEIPT = "RECEIPT"         # Vendor -> Internal
    DELIVERY = "DELIVERY"       # Internal -> Customer
    TRANSFER = "TRANSFER"       # Internal -> Internal (e.g. WH1->WH2, Rack A->Rack B)
    ADJUSTMENT = "ADJUSTMENT"   # Internal <-> Inventory Loss / Scrap

class StockMove(Base):
    __tablename__ = "stock_moves"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(100), index=True, nullable=False) # e.g. REC/2026/0001, DEL/2026/0001
    move_type = Column(Enum(MoveType), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)
    total_value = Column(Float, default=0.0, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Cryptographic integrity signature of this individual transaction
    record_hash = Column(String(64), nullable=True)

    product = relationship("Product")
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])
    user = relationship("User")
