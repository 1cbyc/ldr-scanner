import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from app.core.models import Candle
from app.core.enums import Timeframe, Direction
from app.strategy.ldr.range_detector import RangeDetector

def create_candle(base_time, minutes_offset, o, h, l, c):
    return Candle(
        symbol="XAUUSD",
        timeframe=Timeframe.H1,
        timestamp=base_time + timedelta(minutes=minutes_offset),
        open=Decimal(str(o)),
        high=Decimal(str(h)),
        low=Decimal(str(l)),
        close=Decimal(str(c)),
        volume=1000
    )

def test_range_detector_finds_range():
    detector = RangeDetector()
    detector.min_candles = 5
    detector.max_candles = 10
    
    base_time = datetime.now(timezone.utc)
    
    candles = [
        create_candle(base_time, 0, 100, 105, 95, 100),
        create_candle(base_time, 60, 100, 104, 96, 101),
        create_candle(base_time, 120, 101, 106, 94, 99),
        create_candle(base_time, 180, 99, 105, 95, 102),
        create_candle(base_time, 240, 102, 104, 96, 100),
        create_candle(base_time, 300, 100, 105, 95, 100),
    ]
    
    detected = detector.detect(candles)
    assert detected is not None
    assert detected.high == Decimal('106')
    assert detected.low == Decimal('94')
    assert detected.quality_score > 0
