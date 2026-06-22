import asyncio
import logging
from arq import worker
from arq.connections import RedisSettings
from app.config import settings
from app.strategy.ldr.engine import LDRStrategyEngine
from app.alerts.telegram import TelegramAlertService
from app.alerts.renderer import AlertRenderer
from app.data.providers.csv_provider import CSVProvider
from app.core.enums import Timeframe, SetupStatus

logger = logging.getLogger(__name__)

async def scan_market(ctx):
    """
    Background job to scan the market for LDR setups.
    """
    logger.info("Starting market scan cycle...")
    
    engine = LDRStrategyEngine()
    telegram = TelegramAlertService()
    renderer = AlertRenderer()
    
    provider = CSVProvider() # We can dynamically load this based on settings later
    
    # Simple threshold
    threshold = settings.ALERT_SCORE_THRESHOLD
    
    for symbol in settings.symbols_list:
        for tf_str in settings.timeframes_list:
            try:
                tf = Timeframe(tf_str)
                candles = await provider.get_ohlcv(symbol, tf, limit=100)
                
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
        worker.cron(scan_market, second={0, 30}) # Run every 30 seconds for demonstration
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
