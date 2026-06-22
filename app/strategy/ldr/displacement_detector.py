from typing import List, Optional
from decimal import Decimal
from app.core.models import Candle
from app.strategy.ldr.models import DetectedRange, LiquiditySweep, Displacement
from app.core.enums import Direction
from app.config import settings

class DisplacementDetector:
    def __init__(self):
        self.min_atr_multiple = settings.DISPLACEMENT_MIN_ATR_MULTIPLE

    def detect(self, drange: DetectedRange, sweep: LiquiditySweep, candles: List[Candle]) -> Optional[Displacement]:
        """
        Looks for a displacement move immediately following the sweep.
        """
        post_sweep = [c for c in candles if c.timestamp >= sweep.sweep_candle_time]
        
        if len(post_sweep) < 2:
            return None
            
        # We look at the first 3-5 candles after the sweep
        window = post_sweep[:5]
        
        if sweep.direction_after_sweep == Direction.BEARISH:
            return self._evaluate_bearish_displacement(drange, sweep, window)
        else:
            return self._evaluate_bullish_displacement(drange, sweep, window)
            
    def _evaluate_bearish_displacement(
        self, drange: DetectedRange, sweep: LiquiditySweep, window: List[Candle]
    ) -> Optional[Displacement]:
        
        # We need cumulative bearish body strength
        cumulative_drop = Decimal('0')
        impulse_candles = 0
        broke_micro = False
        
        start_time = window[0].timestamp
        end_time = window[0].timestamp
        
        for c in window:
            if c.close < c.open: # Bearish candle
                body = c.open - c.close
                cumulative_drop += body
                impulse_candles += 1
                end_time = c.timestamp
                
                # Check if it broke micro structure (close below range midpoint)
                if c.close < drange.midpoint:
                    broke_micro = True
            elif c.close > c.open:
                # If strong bullish rejection immediately, displacement fails
                if (c.close - c.open) > (drange.atr_at_detection * Decimal('0.5')):
                    break

        if impulse_candles == 0:
            return None
            
        atr_multiple = float(cumulative_drop / drange.atr_at_detection)
        
        if atr_multiple < self.min_atr_multiple:
            return None
            
        score = 15
        if broke_micro:
            score += 5
        if atr_multiple > 2.0:
            score += 5
            
        return Displacement(
            direction=Direction.BEARISH,
            start_time=start_time,
            end_time=end_time,
            impulse_candles=impulse_candles,
            body_strength=float(cumulative_drop),
            atr_multiple=atr_multiple,
            broke_micro_structure=broke_micro,
            created_fvg=False, # We'll determine FVG in the FVG detector, but keep the flag
            quality_score=min(25, score)
        )
        
    def _evaluate_bullish_displacement(
        self, drange: DetectedRange, sweep: LiquiditySweep, window: List[Candle]
    ) -> Optional[Displacement]:
        
        cumulative_rise = Decimal('0')
        impulse_candles = 0
        broke_micro = False
        
        start_time = window[0].timestamp
        end_time = window[0].timestamp
        
        for c in window:
            if c.close > c.open: # Bullish candle
                body = c.close - c.open
                cumulative_rise += body
                impulse_candles += 1
                end_time = c.timestamp
                
                if c.close > drange.midpoint:
                    broke_micro = True
            elif c.close < c.open:
                if (c.open - c.close) > (drange.atr_at_detection * Decimal('0.5')):
                    break
                    
        if impulse_candles == 0:
            return None
            
        atr_multiple = float(cumulative_rise / drange.atr_at_detection)
        
        if atr_multiple < self.min_atr_multiple:
            return None
            
        score = 15
        if broke_micro:
            score += 5
        if atr_multiple > 2.0:
            score += 5
            
        return Displacement(
            direction=Direction.BULLISH,
            start_time=start_time,
            end_time=end_time,
            impulse_candles=impulse_candles,
            body_strength=float(cumulative_rise),
            atr_multiple=atr_multiple,
            broke_micro_structure=broke_micro,
            created_fvg=False,
            quality_score=min(25, score)
        )
