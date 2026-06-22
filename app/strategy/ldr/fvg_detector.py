from typing import List, Optional
from decimal import Decimal
from app.core.models import Candle
from app.strategy.ldr.models import Displacement, FairValueGap
from app.core.enums import Direction

class FVGDetector:
    def detect(self, displacement: Displacement, candles: List[Candle]) -> Optional[FairValueGap]:
        """
        Looks for a 3-candle Fair Value Gap created during the displacement.
        """
        # Filter candles that cover the displacement period
        # We need at least 3 candles to form an FVG.
        
        disp_candles = [c for c in candles if displacement.start_time <= c.timestamp <= displacement.end_time]
        
        if len(disp_candles) < 3:
            # If the displacement happened too fast, we might need to look slightly past the end_time
            idx_start = next((i for i, c in enumerate(candles) if c.timestamp == displacement.start_time), None)
            if idx_start is not None and idx_start + 2 < len(candles):
                disp_candles = candles[idx_start:idx_start+3]
            else:
                return None
                
        # Scan through the window to find the largest FVG
        best_fvg = None
        best_size = Decimal('0')
        
        for i in range(len(disp_candles) - 2):
            c1 = disp_candles[i]
            # c2 = disp_candles[i+1] (the imbalance candle)
            c3 = disp_candles[i+2]
            
            if displacement.direction == Direction.BULLISH:
                # Bullish FVG: c1.high < c3.low
                if c1.high < c3.low:
                    size = c3.low - c1.high
                    if size > best_size:
                        best_size = size
                        best_fvg = self._create_fvg(Direction.BULLISH, c1, c3, size)
            else:
                # Bearish FVG: c1.low > c3.high
                if c1.low > c3.high:
                    size = c1.low - c3.high
                    if size > best_size:
                        best_size = size
                        best_fvg = self._create_fvg(Direction.BEARISH, c1, c3, size)
                        
        return best_fvg

    def _create_fvg(self, direction: Direction, c1: Candle, c3: Candle, size: Decimal) -> FairValueGap:
        if direction == Direction.BULLISH:
            upper = c3.low
            lower = c1.high
        else:
            upper = c1.low
            lower = c3.high
            
        midpoint = lower + (size / Decimal('2'))
        
        # Base score 10 for existing, +5 for size
        score = 15 
        
        return FairValueGap(
            direction=direction,
            start_time=c1.timestamp,
            end_time=c3.timestamp,
            upper=upper,
            lower=lower,
            midpoint=midpoint,
            size=size,
            filled_percent=0.0,
            quality_score=min(15, score)
        )
