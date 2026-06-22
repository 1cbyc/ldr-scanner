from typing import List, Optional
from decimal import Decimal
from app.core.models import Candle
from app.strategy.ldr.models import DetectedRange
from app.core.utils import calculate_atr
from app.config import settings

class RangeDetector:
    def __init__(self):
        self.min_candles = settings.RANGE_MIN_CANDLES
        self.max_candles = settings.RANGE_MAX_CANDLES
        
    def detect(self, candles: List[Candle]) -> Optional[DetectedRange]:
        """
        Scans backwards from the most recent completed candles to find a consolidated range.
        For simplicity in V1, we take a fixed window of recent candles and test if it forms a range.
        """
        if len(candles) < self.min_candles:
            return None
            
        # Consider the last 'max_candles' for our window to analyze
        window = candles[-self.max_candles:] if len(candles) > self.max_candles else candles
        
        # We need to find if there's a valid range in the most recent N candles
        # We iterate backwards through possible range sizes
        for size in range(len(window), self.min_candles - 1, -1):
            subset = window[-size:]
            range_candidate = self._evaluate_subset(subset, candles)
            if range_candidate:
                return range_candidate
                
        return None

    def _evaluate_subset(self, subset: List[Candle], all_candles: List[Candle]) -> Optional[DetectedRange]:
        highest = max(c.high for c in subset)
        lowest = min(c.low for c in subset)
        height = highest - lowest
        
        if height == 0:
            return None
            
        midpoint = lowest + (height / Decimal('2'))
        
        # Calculate ATR up to the end of the subset
        # We need the ATR at the end of this subset.
        idx = all_candles.index(subset[-1])
        atr_window = all_candles[max(0, idx - 14):idx + 1]
        atr = calculate_atr(atr_window)
        
        if atr == 0:
            return None
            
        # Range height relative to ATR
        # Should not be too small (e.g. < 1 ATR) and not too large (e.g. > 5 ATR)
        atr_ratio = float(height / atr)
        if atr_ratio < 1.0 or atr_ratio > 6.0:
            return None
            
        # Count touches
        touches_high = sum(1 for c in subset if (highest - c.high) <= (height * Decimal('0.15')))
        touches_low = sum(1 for c in subset if (c.low - lowest) <= (height * Decimal('0.15')))
        
        if touches_high < 2 or touches_low < 2:
            return None
            
        # Quality score
        # Base score 10, plus bonus for touches, minus penalty for excessive size
        score = 10
        score += min(5, touches_high - 2) * 2
        score += min(5, touches_low - 2) * 2
        
        # Ideal ATR ratio is 2-4
        if 2.0 <= atr_ratio <= 4.0:
            score += 5
            
        quality_score = min(20, score) # Max 20 points for range
        
        return DetectedRange(
            symbol=subset[0].symbol,
            timeframe=subset[0].timeframe,
            start_time=subset[0].timestamp,
            end_time=subset[-1].timestamp,
            high=highest,
            low=lowest,
            midpoint=midpoint,
            height=height,
            atr_at_detection=atr,
            quality_score=quality_score,
            touches_high=touches_high,
            touches_low=touches_low
        )
