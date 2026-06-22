from typing import Optional
from decimal import Decimal
from app.strategy.ldr.models import FairValueGap, OrderBlock, EntryZone, LiquiditySweep
from app.core.enums import Direction, EntryZoneSource
from app.config import settings

class EntryZoneDetector:
    def detect(
        self, 
        direction: Direction, 
        fvg: Optional[FairValueGap], 
        ob: Optional[OrderBlock],
        sweep: LiquiditySweep
    ) -> Optional[EntryZone]:
        
        if not fvg and not ob:
            return None
            
        upper = Decimal('0')
        lower = Decimal('0')
        source = EntryZoneSource.FVG
        
        if fvg and ob:
            # Check overlap
            overlap_upper = min(fvg.upper, ob.zone_upper)
            overlap_lower = max(fvg.lower, ob.zone_lower)
            
            if overlap_upper >= overlap_lower:
                upper = overlap_upper
                lower = overlap_lower
                source = EntryZoneSource.OVERLAP
            else:
                # No overlap, prefer FVG
                upper = fvg.upper
                lower = fvg.lower
                source = EntryZoneSource.FVG
        elif fvg:
            upper = fvg.upper
            lower = fvg.lower
            source = EntryZoneSource.FVG
        elif ob:
            upper = ob.zone_upper
            lower = ob.zone_lower
            source = EntryZoneSource.ORDER_BLOCK
            
        midpoint = lower + ((upper - lower) / Decimal('2'))
        
        # Calculate base invalidation level.
        # The buffer is a configurable multiple of ATR (INVALIDATION_ATR_BUFFER, default 0.1),
        # anchored to the sweep candle's high/low. This prevents the buffer being a
        # meaningless fixed pip value regardless of the instrument's volatility.
        # The sweep model doesn't carry ATR, so we read the configurable buffer directly.
        buffer = Decimal(str(settings.INVALIDATION_ATR_BUFFER))
        if direction == Direction.BULLISH:
            invalidation = sweep.sweep_candle_low - buffer
        else:
            invalidation = sweep.sweep_candle_high + buffer
            
        return EntryZone(
            direction=direction,
            upper=upper,
            lower=lower,
            midpoint=midpoint,
            source=source,
            invalidation_level=invalidation,
            target_level=Decimal('0'), # Target calculated in Risk module
            estimated_rr=0.0,
            quality_score=settings.ENTRY_ZONE_OVERLAP_SCORE if source == EntryZoneSource.OVERLAP else settings.ENTRY_ZONE_BASE_SCORE
        )
