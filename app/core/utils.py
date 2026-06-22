from typing import List
from decimal import Decimal
from app.core.models import Candle

def calculate_atr(candles: List[Candle], period: int = 14) -> Decimal:
    if len(candles) <= 1:
        return Decimal('0')
    
    tr_list = []
    for i in range(1, len(candles)):
        current = candles[i]
        previous = candles[i-1]
        
        tr1 = current.high - current.low
        tr2 = abs(current.high - previous.close)
        tr3 = abs(current.low - previous.close)
        
        tr_list.append(max(tr1, tr2, tr3))
        
    if len(tr_list) < period:
        period = len(tr_list)
        
    if period == 0:
        return Decimal('0')
        
    return sum(tr_list[-period:]) / Decimal(str(period))

def is_bullish(candle: Candle) -> bool:
    return candle.close > candle.open

def is_bearish(candle: Candle) -> bool:
    return candle.close < candle.open
