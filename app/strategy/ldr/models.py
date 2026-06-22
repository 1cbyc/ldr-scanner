from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from app.core.enums import Direction, SweptSide, EntryZoneSource, Timeframe

class DetectedRange(BaseModel):
    symbol: str
    timeframe: Timeframe
    start_time: datetime
    end_time: datetime
    high: Decimal
    low: Decimal
    midpoint: Decimal
    height: Decimal
    atr_at_detection: Decimal
    quality_score: int
    touches_high: int
    touches_low: int

class LiquiditySweep(BaseModel):
    direction_after_sweep: Direction
    swept_side: SweptSide
    swept_level: Decimal
    sweep_candle_time: datetime
    sweep_candle_high: Decimal
    sweep_candle_low: Decimal
    sweep_distance: Decimal
    wick_rejection_ratio: float
    close_reclaimed: bool
    quality_score: int

class Displacement(BaseModel):
    direction: Direction
    start_time: datetime
    end_time: datetime
    impulse_candles: int
    body_strength: float
    atr_multiple: float
    broke_micro_structure: bool
    created_fvg: bool
    quality_score: int

class FairValueGap(BaseModel):
    direction: Direction
    start_time: datetime
    end_time: datetime
    upper: Decimal
    lower: Decimal
    midpoint: Decimal
    size: Decimal
    filled_percent: float
    quality_score: int

class OrderBlock(BaseModel):
    direction: Direction
    candle_time: datetime
    high: Decimal
    low: Decimal
    open: Decimal
    close: Decimal
    zone_upper: Decimal
    zone_lower: Decimal
    quality_score: int

class EntryZone(BaseModel):
    direction: Direction
    upper: Decimal
    lower: Decimal
    midpoint: Decimal
    source: EntryZoneSource
    invalidation_level: Decimal
    target_level: Decimal
    estimated_rr: float
    quality_score: int
