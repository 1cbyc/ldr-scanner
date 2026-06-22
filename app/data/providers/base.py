from abc import ABC, abstractmethod
from typing import List
from app.core.models import Candle
from app.core.enums import Timeframe

class MarketDataProvider(ABC):
    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int
    ) -> List[Candle]:
        pass

    @abstractmethod
    async def get_latest_price(
        self,
        symbol: str
    ) -> float:
        pass
