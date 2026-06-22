from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.core.enums import Timeframe

class Candle(BaseModel):
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[float] = None
