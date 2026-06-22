from typing import List
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import random

from app.core.models import Candle
from app.core.enums import Timeframe
from app.data.providers.base import MarketDataProvider

class MockProvider(MarketDataProvider):
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int
    ) -> List[Candle]:
        # Generate synthetic candles
        candles = []
        now = datetime.now(timezone.utc)
        
        # Simple timeframe to minutes mapping
        tf_mins = {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.D1: 1440,
        }
        mins = tf_mins.get(timeframe, 60)
        
        base_price = 4300.0 if symbol == "XAUUSD" else 15000.0
        
        for i in range(limit):
            ts = now - timedelta(minutes=mins * (limit - i - 1))
            open_p = base_price + random.uniform(-10, 10)
            close_p = open_p + random.uniform(-10, 10)
            high_p = max(open_p, close_p) + random.uniform(0, 5)
            low_p = min(open_p, close_p) - random.uniform(0, 5)
            
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=ts,
                    open=Decimal(str(round(open_p, 2))),
                    high=Decimal(str(round(high_p, 2))),
                    low=Decimal(str(round(low_p, 2))),
                    close=Decimal(str(round(close_p, 2))),
                    volume=random.uniform(100, 1000)
                )
            )
            base_price = close_p
            
        return candles

    async def get_latest_price(
        self,
        symbol: str
    ) -> float:
        return 4300.0 if symbol == "XAUUSD" else 15000.0
