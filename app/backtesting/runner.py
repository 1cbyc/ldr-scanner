from app.data.providers.csv_provider import CSVProvider
from app.backtesting.replay import ReplayEngine
from app.backtesting.metrics import calculate_metrics
from app.core.enums import Timeframe
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class BacktestRunner:
    def __init__(self, provider: CSVProvider):
        self.provider = provider
        self.replay_engine = ReplayEngine()

    async def run_backtest(self, symbol: str, timeframe: Timeframe) -> Dict[str, Any]:
        logger.info(f"Loading data for backtest: {symbol} on {timeframe.value}")
        candles = await self.provider.get_ohlcv(symbol, timeframe, limit=5000)
        
        if not candles:
            logger.warning(f"No candles found for {symbol} on {timeframe.value}")
            return calculate_metrics([])
            
        logger.info(f"Loaded {len(candles)} candles. Starting replay engine...")
        candidates = self.replay_engine.run_replay(candles)
        
        logger.info("Replay finished. Calculating metrics...")
        metrics = calculate_metrics(candidates)
        
        return metrics
