import httpx
import logging
from typing import List
from decimal import Decimal
from datetime import datetime, timezone
import pytz

from app.core.models import Candle
from app.core.enums import Timeframe
from app.data.providers.base import MarketDataProvider
from app.config import settings

logger = logging.getLogger(__name__)

class TwelveDataProvider(MarketDataProvider):
    def __init__(self):
        self.api_key = settings.TWELVEDATA_API_KEY
        self.base_url = "https://api.twelvedata.com"
        
        # Map our Timeframe enum to TwelveData intervals
        self.interval_map = {
            Timeframe.M1: "1min",
            Timeframe.M5: "5min",
            Timeframe.M15: "15min",
            Timeframe.H1: "1h",
            Timeframe.H4: "4h",
            Timeframe.D1: "1day"
        }

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int
    ) -> List[Candle]:
        if not self.api_key:
            logger.error("TwelveData API key not set")
            return []
            
        interval = self.interval_map.get(timeframe)
        if not interval:
            logger.error(f"Unsupported timeframe for TwelveData: {timeframe}")
            return []
            
        url = f"{self.base_url}/time_series"
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": limit,
            "apikey": self.api_key,
            "format": "JSON",
            "timezone": "UTC"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                
                if "status" in data and data["status"] == "error":
                    logger.error(f"TwelveData API error: {data.get('message')}")
                    return []
                    
                values = data.get("values", [])
                
                candles = []
                for v in values:
                    # TwelveData returns newest first, so we reverse it or just append and reverse later
                    ts = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    
                    candles.append(
                        Candle(
                            symbol=symbol,
                            timeframe=timeframe,
                            timestamp=ts,
                            open=Decimal(v["open"]),
                            high=Decimal(v["high"]),
                            low=Decimal(v["low"]),
                            close=Decimal(v["close"]),
                            volume=float(v.get("volume", 0.0))
                        )
                    )
                    
                # Reverse to make it oldest to newest
                candles.reverse()
                return candles
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching from TwelveData: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in TwelveDataProvider: {e}")
            return []

    async def get_latest_price(
        self,
        symbol: str
    ) -> float:
        if not self.api_key:
            return 0.0
            
        url = f"{self.base_url}/price"
        params = {
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return float(data.get("price", 0.0))
        except Exception as e:
            logger.error(f"Error fetching latest price from TwelveData: {e}")
            return 0.0
