from typing import List, Dict, Any
from app.strategy.ldr.engine import LDRStrategyEngine, LDRSetupCandidate
from app.core.models import Candle
from app.core.enums import SetupStatus

class ReplayEngine:
    def __init__(self):
        self.strategy = LDRStrategyEngine()

    def run_replay(self, all_candles: List[Candle]) -> List[LDRSetupCandidate]:
        """
        Runs the strategy engine over historical candles without future leakage.
        It simulates stepping forward in time, feeding only up to 'current' candle.
        """
        setups_found = []
        
        # We need a minimum number of candles to even start finding ranges
        min_candles = self.strategy.range_detector.min_candles
        if len(all_candles) < min_candles:
            return setups_found
            
        # Stepping forward through time
        for i in range(min_candles, len(all_candles)):
            # Subset of candles available exactly at this point in time
            window = all_candles[:i+1]
            
            candidate = self.strategy.process_candles(window)
            
            # We are only interested in valid setups that are ready or triggered
            if candidate.status in [SetupStatus.MITIGATION_PENDING, SetupStatus.ENTRY_ZONE_TOUCHED]:
                # In a real replay, we'd also track if this is a new setup 
                # or an update to an existing one, to calculate deduplicated metrics.
                # For simplicity here, we append them and deduplicate later based on start time.
                setups_found.append(candidate)
                
        return setups_found
