from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class CandleModel(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    timeframe = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    open = Column(Numeric, nullable=False)
    high = Column(Numeric, nullable=False)
    low = Column(Numeric, nullable=False)
    close = Column(Numeric, nullable=False)
    volume = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class LDRSetupModel(Base):
    __tablename__ = "ldr_setups"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    direction = Column(String, nullable=False)
    status = Column(String, index=True, nullable=False)
    score = Column(Integer, nullable=False)
    
    range_high = Column(Numeric, nullable=False)
    range_low = Column(Numeric, nullable=False)
    range_midpoint = Column(Numeric, nullable=False)
    
    swept_side = Column(String, nullable=False)
    swept_level = Column(Numeric, nullable=False)
    sweep_time = Column(DateTime(timezone=True), nullable=False)
    
    displacement_start = Column(DateTime(timezone=True), nullable=True)
    displacement_end = Column(DateTime(timezone=True), nullable=True)
    
    entry_zone_upper = Column(Numeric, nullable=True)
    entry_zone_lower = Column(Numeric, nullable=True)
    invalidation_level = Column(Numeric, nullable=True)
    target_level = Column(Numeric, nullable=True)
    estimated_rr = Column(Float, nullable=True)
    
    timeframe_context = Column(String, nullable=False)
    session_label = Column(String, nullable=True)
    
    alert_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    invalidated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    metadata_data = Column(JSONB, nullable=True)
    
    alerts = relationship("AlertModel", back_populates="setup")

class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    setup_id = Column(Integer, ForeignKey("ldr_setups.id"), nullable=False)
    channel = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(String, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    error = Column(String, nullable=True)
    
    setup = relationship("LDRSetupModel", back_populates="alerts")
