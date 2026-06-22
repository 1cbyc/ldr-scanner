import pandas as pd
from typing import List
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

from app.core.models import Candle
from app.core.enums import Timeframe
from app.data.providers.base import MarketDataProvider
from app.config import settings

class CSVProvider(MarketDataProvider):
    def __init__(self, data_dir: str = settings.CSV_DATA_DIR):
        self.data_dir = Path(data_dir)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int
    ) -> List[Candle]:
        file_path = self.data_dir / symbol / f"{timeframe.value}.csv"
        if not file_path.exists():
            return []

        df = pd.read_csv(file_path)
        # Assume columns: timestamp, open, high, low, close, volume
        # Ensure timestamp is parsed properly and timezone aware (UTC)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        df = df.tail(limit)
        
        candles = []
        for _, row in df.iterrows():
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=row['timestamp'],
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=float(row.get('volume', 0.0))
                )
            )
        return candles

    async def get_latest_price(
        self,
        symbol: str
    ) -> float:
        # For CSV, just return the close of the last H1 candle or something similar
        file_path = self.data_dir / symbol / "H1.csv"
        if not file_path.exists():
            return 0.0
        
        df = pd.read_csv(file_path)
        if df.empty:
            return 0.0
            
        return float(df.iloc[-1]['close'])
