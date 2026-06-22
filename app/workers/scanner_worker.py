import asyncio
import logging
from arq import cron
from arq.connections import RedisSettings
from app.config import settings
from app.strategy.ldr.engine import LDRStrategyEngine
from app.alerts.telegram import TelegramAlertService
from app.alerts.renderer import AlertRenderer
from app.data.providers.base import MarketDataProvider
from app.data.providers.csv_provider import CSVProvider
from app.data.providers.mock_provider import MockProvider
from app.data.providers.twelvedata_provider import TwelveDataProvider
from app.core.enums import Timeframe, SetupStatus

logger = logging.getLogger(__name__)

def _resolve_provider() -> MarketDataProvider:
    """Selects the data provider based on the DATA_PROVIDER setting."""
    name = settings.DATA_PROVIDER.strip().lower()
    if name == "twelvedata":
        return TwelveDataProvider()
    elif name == "mock":
        return MockProvider()
    else:
        return CSVProvider()


async def scan_market(ctx):
    """
    Background job to scan the market for LDR setups.
    """
    logger.info("Starting market scan cycle...")

    engine = LDRStrategyEngine()
    telegram = TelegramAlertService()
    renderer = AlertRenderer()
    provider = _resolve_provider()
    threshold = settings.ALERT_SCORE_THRESHOLD
    candle_limit = settings.SCANNER_CANDLE_LIMIT
    
    for symbol in settings.symbols_list:
        for tf_str in settings.timeframes_list:
            try:
                tf = Timeframe(tf_str)
                candles = await provider.get_ohlcv(symbol, tf, limit=candle_limit)
                
                if not candles:
                    continue
                    
                candidate = engine.process_candles(candles)
                
                # Check if we should alert
                # In a real app we'd query the DB to check if we already alerted this exact setup
                if candidate.status in [SetupStatus.MITIGATION_PENDING, SetupStatus.ENTRY_ZONE_TOUCHED]:
                    if candidate.score >= threshold:
                        msg = renderer.render_telegram_message(candidate)
                        await telegram.send_alert(msg)
                        logger.info(f"Alert sent for {symbol} on {tf.value}")
                        
            except Exception as e:
                logger.error(f"Error scanning {symbol} on {tf_str}: {e}")
                
    logger.info("Market scan cycle completed.")

class WorkerSettings:
    functions = [scan_market]
    cron_jobs = [
        cron(scan_market, second={0}),  # Fires once per minute; interval is SCAN_INTERVAL_SECONDS
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
