from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from app.core.models import Candle
from app.strategy.ldr.models import (
    DetectedRange, LiquiditySweep, Displacement, FairValueGap, OrderBlock, EntryZone
)
from app.strategy.ldr.range_detector import RangeDetector
from app.strategy.ldr.liquidity_sweep_detector import LiquiditySweepDetector
from app.strategy.ldr.displacement_detector import DisplacementDetector
from app.strategy.ldr.fvg_detector import FVGDetector
from app.strategy.ldr.order_block_detector import OrderBlockDetector
from app.strategy.ldr.entry_zone_detector import EntryZoneDetector
from app.strategy.ldr.invalidation import InvalidationRules
from app.core.enums import SetupStatus, Direction, SweptSide
from pydantic import BaseModel

class LDRSetupCandidate(BaseModel):
    symbol: str
    direction: Direction
    status: SetupStatus
    score: int
    drange: DetectedRange
    sweep: LiquiditySweep
    displacement: Optional[Displacement] = None
    fvg: Optional[FairValueGap] = None
    order_block: Optional[OrderBlock] = None
    entry_zone: Optional[EntryZone] = None
    target_level: Optional[float] = None
    estimated_rr: Optional[float] = None
    rejection_reason: Optional[str] = None

class LDRStrategyEngine:
    def __init__(self):
        self.range_detector = RangeDetector()
        self.sweep_detector = LiquiditySweepDetector()
        self.displacement_detector = DisplacementDetector()
        self.fvg_detector = FVGDetector()
        self.ob_detector = OrderBlockDetector()
        self.entry_detector = EntryZoneDetector()
        self.invalidation_rules = InvalidationRules()

    def process_candles(self, candles: List[Candle]) -> LDRSetupCandidate:
        """
        Runs the full LDR detection pipeline over the given candles.
        Returns a setup candidate with its current status.
        """
        if not candles:
            return self._rejected(candles[0].symbol if candles else "UNKNOWN", "Not enough candles")
            
        symbol = candles[0].symbol

        # 1. Detect Range
        drange = self.range_detector.detect(candles)
        if not drange:
            return self._rejected(symbol, "No valid range detected")
            
        # 2. Detect Sweep
        sweep = self.sweep_detector.detect(drange, candles)
        if not sweep:
            return LDRSetupCandidate(
                symbol=symbol,
                direction=Direction.BULLISH,  # Arbitrary — range only, no sweep yet
                status=SetupStatus.OBSERVING_RANGE,
                score=drange.quality_score,
                drange=drange,
                sweep=LiquiditySweep(
                    direction_after_sweep=Direction.BULLISH,
                    swept_side=SweptSide.BUY_SIDE,  # Placeholder — no real sweep yet
                    swept_level=drange.high,
                    sweep_candle_time=datetime.now(timezone.utc),
                    sweep_candle_high=drange.high,
                    sweep_candle_low=drange.low,
                    sweep_distance=Decimal("0"),
                    wick_rejection_ratio=0.0,
                    close_reclaimed=False,
                    quality_score=0
                )
            )
            
        direction = sweep.direction_after_sweep
        score = drange.quality_score + sweep.quality_score
        
        # 3. Detect Displacement
        displacement = self.displacement_detector.detect(drange, sweep, candles)
        if not displacement:
            return LDRSetupCandidate(
                symbol=symbol,
                direction=direction,
                status=SetupStatus.LIQUIDITY_SWEPT,
                score=score,
                drange=drange,
                sweep=sweep
            )
            
        score += displacement.quality_score
        
        # 4. FVG and Order Block
        fvg = self.fvg_detector.detect(displacement, candles)
        ob = self.ob_detector.detect(sweep, displacement, candles)
        
        fvg_score = fvg.quality_score if fvg else 0
        ob_score = ob.quality_score if ob else 0
        score += max(fvg_score, ob_score)
        
        # 5. Entry Zone
        entry_zone = self.entry_detector.detect(direction, fvg, ob, sweep)
        if not entry_zone:
            return LDRSetupCandidate(
                symbol=symbol,
                direction=direction,
                status=SetupStatus.REJECTED,
                score=score,
                drange=drange,
                sweep=sweep,
                displacement=displacement,
                rejection_reason="No valid entry zone formed"
            )
            
        score += entry_zone.quality_score
        
        # 6. Risk and Reward
        rr, target, is_valid = self.invalidation_rules.calculate_risk_reward(direction, entry_zone, drange, sweep)
        
        if not is_valid:
            return LDRSetupCandidate(
                symbol=symbol,
                direction=direction,
                status=SetupStatus.REJECTED,
                score=score,
                drange=drange,
                sweep=sweep,
                displacement=displacement,
                fvg=fvg,
                order_block=ob,
                entry_zone=entry_zone,
                target_level=float(target),
                estimated_rr=rr,
                rejection_reason=f"RR ({rr:.2f}) is below minimum"
            )
            
        # Add RR quality score
        if rr >= 10.0:
            score += 10
        elif rr >= 7.0:
            score += 5
            
        return LDRSetupCandidate(
            symbol=symbol,
            direction=direction,
            status=SetupStatus.MITIGATION_PENDING,
            score=min(100, score),
            drange=drange,
            sweep=sweep,
            displacement=displacement,
            fvg=fvg,
            order_block=ob,
            entry_zone=entry_zone,
            target_level=float(target),
            estimated_rr=rr
        )

    def _rejected(self, symbol: str, reason: str) -> LDRSetupCandidate:
        dummy_time = datetime.now(timezone.utc)
        return LDRSetupCandidate(
            symbol=symbol,
            direction=Direction.BULLISH,
            status=SetupStatus.REJECTED,
            score=0,
            drange=DetectedRange(symbol=symbol, timeframe="H1", start_time=dummy_time, end_time=dummy_time, high=0, low=0, midpoint=0, height=0, atr_at_detection=0, quality_score=0, touches_high=0, touches_low=0),
            sweep=LiquiditySweep(direction_after_sweep=Direction.BULLISH, swept_side="buy_side", swept_level=0, sweep_candle_time=dummy_time, sweep_candle_high=0, sweep_candle_low=0, sweep_distance=0, wick_rejection_ratio=0, close_reclaimed=False, quality_score=0),
            rejection_reason=reason
        )
