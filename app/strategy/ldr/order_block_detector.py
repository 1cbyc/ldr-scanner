from typing import List, Optional
from decimal import Decimal
from app.core.models import Candle
from app.strategy.ldr.models import Displacement, OrderBlock, LiquiditySweep
from app.core.enums import Direction

class OrderBlockDetector:
    def detect(self, sweep: LiquiditySweep, displacement: Displacement, candles: List[Candle]) -> Optional[OrderBlock]:
        """
        Finds the last opposing candle before the displacement.
        """
        # We look between the sweep and the start of the displacement
        # Or even including the sweep candle itself.
        
        relevant_candles = [c for c in candles if c.timestamp >= sweep.sweep_candle_time and c.timestamp <= displacement.start_time]
        
        if not relevant_candles:
            # Fallback: check just before displacement start
            idx = next((i for i, c in enumerate(candles) if c.timestamp == displacement.start_time), None)
            if idx is not None and idx > 0:
                relevant_candles = [candles[idx-1], candles[idx]]
            else:
                return None
                
        # Traverse backwards to find the last opposing candle
        relevant_candles.reverse()
        
        for c in relevant_candles:
            if displacement.direction == Direction.BULLISH:
                if c.close < c.open: # Bearish candle
                    return self._create_ob(Direction.BULLISH, c)
            else:
                if c.close > c.open: # Bullish candle
                    return self._create_ob(Direction.BEARISH, c)
                    
        return None

    def _create_ob(self, direction: Direction, c: Candle) -> OrderBlock:
        return OrderBlock(
            direction=direction,
            candle_time=c.timestamp,
            high=c.high,
            low=c.low,
            open=c.open,
            close=c.close,
            zone_upper=c.high, # Using entire candle range for OB zone in V1
            zone_lower=c.low,
            quality_score=15
        )
