from typing import Tuple
from decimal import Decimal
from app.strategy.ldr.models import EntryZone, DetectedRange, LiquiditySweep
from app.core.enums import Direction
from app.config import settings

class InvalidationRules:
    def __init__(self):
        self.min_rr = settings.MIN_RR

    def calculate_risk_reward(
        self, 
        direction: Direction, 
        entry_zone: EntryZone, 
        drange: DetectedRange, 
        sweep: LiquiditySweep
    ) -> Tuple[float, Decimal, bool]:
        """
        Calculates theoretical RR.
        Returns: (rr, target_level, is_valid)
        """
        entry_price = entry_zone.midpoint
        stop_loss = entry_zone.invalidation_level
        
        if direction == Direction.BULLISH:
            # Target is the opposing liquidity (range high)
            target = drange.high
            
            risk = entry_price - stop_loss
            reward = target - entry_price
            
        else:
            # Bearish target is range low
            target = drange.low
            
            risk = stop_loss - entry_price
            reward = entry_price - target
            
        if risk <= 0 or reward <= 0:
            return 0.0, target, False
            
        rr = float(reward / risk)
        
        is_valid = rr >= self.min_rr
        
        return rr, target, is_valid

    def check_invalidation(
        self, 
        direction: Direction, 
        current_price: Decimal, 
        invalidation_level: Decimal
    ) -> bool:
        """
        Returns True if the setup is invalidated (price crossed the invalidation line).
        """
        if direction == Direction.BULLISH:
            return current_price < invalidation_level
        else:
            return current_price > invalidation_level
