from typing import List, Optional
from decimal import Decimal
from app.core.models import Candle
from app.strategy.ldr.models import DetectedRange, LiquiditySweep
from app.core.enums import Direction, SweptSide
from app.config import settings

class LiquiditySweepDetector:
    def __init__(self):
        self.max_atr_multiple = settings.SWEEP_MAX_ATR_MULTIPLE

    def detect(self, drange: DetectedRange, candles: List[Candle]) -> Optional[LiquiditySweep]:
        """
        Looks for a liquidity sweep after the range ends.
        We only look forward from the range end time.
        """
        # Filter candles to only those after the range
        post_range = [c for c in candles if c.timestamp > drange.end_time]
        
        if not post_range:
            return None
            
        for i, c in enumerate(post_range):
            # Check Bearish LDR (Buy-side sweep)
            if c.high > drange.high:
                sweep = self._evaluate_sweep(
                    drange=drange, 
                    candle=c, 
                    next_candles=post_range[i+1:], 
                    swept_side=SweptSide.BUY_SIDE
                )
                if sweep:
                    return sweep
                    
            # Check Bullish LDR (Sell-side sweep)
            if c.low < drange.low:
                sweep = self._evaluate_sweep(
                    drange=drange, 
                    candle=c, 
                    next_candles=post_range[i+1:], 
                    swept_side=SweptSide.SELL_SIDE
                )
                if sweep:
                    return sweep
                    
        return None

    def _evaluate_sweep(
        self, 
        drange: DetectedRange, 
        candle: Candle, 
        next_candles: List[Candle], 
        swept_side: SweptSide
    ) -> Optional[LiquiditySweep]:
        
        if swept_side == SweptSide.BUY_SIDE:
            sweep_distance = candle.high - drange.high
            
            # Reject if sweep is too huge (breakout continuation instead of sweep)
            max_allowed = drange.atr_at_detection * Decimal(str(self.max_atr_multiple))
            if sweep_distance > max_allowed:
                return None
                
            # Check reclaim/rejection
            close_reclaimed = candle.close < drange.high
            rejection_confirmed = close_reclaimed
            
            if not close_reclaimed and next_candles:
                # Next candle must reject below
                if next_candles[0].close < drange.high:
                    rejection_confirmed = True
                    
            if not rejection_confirmed:
                return None
                
            wick_size = candle.high - max(candle.open, candle.close)
            total_size = candle.high - candle.low
            wick_ratio = float(wick_size / total_size) if total_size > 0 else 0.0
            
            # Score 0-20
            score = 10
            if close_reclaimed:
                score += 5
            if wick_ratio > 0.4:
                score += 5
                
            return LiquiditySweep(
                direction_after_sweep=Direction.BEARISH,
                swept_side=swept_side,
                swept_level=drange.high,
                sweep_candle_time=candle.timestamp,
                sweep_candle_high=candle.high,
                sweep_candle_low=candle.low,
                sweep_distance=sweep_distance,
                wick_rejection_ratio=wick_ratio,
                close_reclaimed=close_reclaimed,
                quality_score=min(20, score)
            )
            
        else:
            sweep_distance = drange.low - candle.low
            
            max_allowed = drange.atr_at_detection * Decimal(str(self.max_atr_multiple))
            if sweep_distance > max_allowed:
                return None
                
            close_reclaimed = candle.close > drange.low
            rejection_confirmed = close_reclaimed
            
            if not close_reclaimed and next_candles:
                if next_candles[0].close > drange.low:
                    rejection_confirmed = True
                    
            if not rejection_confirmed:
                return None
                
            wick_size = min(candle.open, candle.close) - candle.low
            total_size = candle.high - candle.low
            wick_ratio = float(wick_size / total_size) if total_size > 0 else 0.0
            
            score = 10
            if close_reclaimed:
                score += 5
            if wick_ratio > 0.4:
                score += 5
                
            return LiquiditySweep(
                direction_after_sweep=Direction.BULLISH,
                swept_side=swept_side,
                swept_level=drange.low,
                sweep_candle_time=candle.timestamp,
                sweep_candle_high=candle.high,
                sweep_candle_low=candle.low,
                sweep_distance=sweep_distance,
                wick_rejection_ratio=wick_ratio,
                close_reclaimed=close_reclaimed,
                quality_score=min(20, score)
            )
